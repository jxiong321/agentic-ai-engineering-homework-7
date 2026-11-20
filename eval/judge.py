"""Assignment 7, Part D: the judge, its rates and its correction (checks/FORMATS.md,
section 15.10).

    python -m eval.judge test 1        # run 1 on the test set: eval/judge/verdicts/test_1.jsonl
    python -m eval.judge versions      # the test items' list and long versions: versions.jsonl
    python -m eval.judge recorded      # the agent way's recorded comments: recorded.jsonl

Your judge reads one output, its issue and what RepoMind's tools returned, and
answers with slide 36's fixed reply: JSON with a one-line "reasoning", then an
"answer", "Pass" or "Fail". Every call goes through a metered judge session, so its
tokens and cost are recorded and priced, and count against lab_token_ceiling:

    from harness.meter import judge_session
    with judge_session("test-1") as session:
        response = session.client.create(system=prompt, messages=[{"role": "user", "content": text}])
        session.trace.model_call(0, response, purpose="judge")

Write session.id on every verdict line. To test the plumbing for nothing, pass
backend="harness.scripted:PassEverything", a judge that passes everything: a coin.

The checker calls `correct`, `rates` and `bootstrap` on cases of its own, and
`correct` on a coin, so keep their names, arguments and returns.
"""

from __future__ import annotations

import json
import math
import random
import argparse
import hashlib
import yaml
from pathlib import Path

from harness import ROOT
from harness.meter import judge_session  # noqa: F401

OUTPUTS = ROOT / "fixtures" / "judge" / "outputs"
VERDICTS = ROOT / "eval" / "judge" / "verdicts"
PROMPT = ROOT / "prompts" / "judge.md"


class CoinJudge(ValueError):
    """TPR + TNR is within 0.1 of 1: the judge is no better than a coin. Fix it, do not
    correct it (slide 44)."""


def correct(p: float, tpr: float, tnr: float) -> float:
    """The share you would pass, labelling by hand, from the judge's pass rate p on
    outputs nobody labelled: (p + TNR - 1) / (TPR + TNR - 1) (slide 44), clipped to
    0 to 1. Raises CoinJudge when TPR + TNR is within 0.1 of 1."""
    if any(not math.isfinite(x) or not 0 <= x <= 1 for x in (p, tpr, tnr)):
        raise ValueError("rates must be finite probabilities")
    denominator = tpr + tnr - 1
    if abs(denominator) <= 0.1 + 1e-12:
        raise CoinJudge("TPR + TNR is within 0.1 of 1; correction refused")
    return min(1.0, max(0.0, (p + tnr - 1) / denominator))


def rates(verdicts: dict[str, str], labels: dict[str, str]) -> tuple[float, float]:
    """(TPR, TNR) of the judge's verdicts against your labels, each "pass" or "fail",
    on the items both cover (slide 43): TPR is the share of the labelled passes the
    judge passed, TNR the share of the labelled fails it failed."""
    ids = sorted(verdicts.keys() & labels.keys())
    if any(verdicts[i] not in ("pass", "fail") or labels[i] not in ("pass", "fail") for i in ids):
        raise ValueError("labels and verdicts must be pass or fail")
    positives = [i for i in ids if labels[i] == "pass"]
    negatives = [i for i in ids if labels[i] == "fail"]
    if not positives or not negatives:
        raise ValueError("both human label classes are required to estimate TPR and TNR")
    return (sum(verdicts[i] == "pass" for i in positives) / len(positives),
            sum(verdicts[i] == "fail" for i in negatives) / len(negatives))


def bootstrap(verdicts: dict[str, str], labels: dict[str, str], p: float,
              resamples: int = 2000, seed: int = 0) -> tuple[float, float]:
    """The middle 95% of the corrected rate over resamples of the test items, drawn
    with replacement, as many as there are, each time recomputing TPR and TNR
    (slide 44). A resample on which the judge is a coin is left out."""
    if resamples < 2000:
        raise ValueError("at least 2000 resamples are required")
    correct(p, *rates(verdicts, labels))
    ids = sorted(verdicts.keys() & labels.keys())
    rng = random.Random(seed)
    values = []
    for _ in range(resamples):
        drawn = rng.choices(ids, k=len(ids))
        # Index each draw, rather than each ID, to preserve repeated items.
        sampled_labels = {str(j): labels[i] for j, i in enumerate(drawn)}
        sampled_verdicts = {str(j): verdicts[i] for j, i in enumerate(drawn)}
        try:
            values.append(correct(p, *rates(sampled_verdicts, sampled_labels)))
        except ValueError:
            continue
    if len(values) < 2:
        raise CoinJudge("too few valid bootstrap resamples")
    values.sort()
    def quantile(q):
        position = q * (len(values) - 1)
        left = int(position)
        right = min(left + 1, len(values) - 1)
        return values[left] + (values[right] - values[left]) * (position - left)
    return quantile(.025), quantile(.975)


def load_outputs(root: Path = ROOT) -> dict[str, dict]:
    """The 60 outputs to label, by ID (section 15.9)."""
    return {p.stem: json.loads(p.read_text()) for p in sorted((root / "fixtures" / "judge" / "outputs").glob("*.json"))}


def configuration_digest():
    files = [PROMPT, ROOT / "eval/judge/criterion.md", ROOT / "settings.yaml", ROOT / "eval/labels/split.yaml"]
    return hashlib.sha256(b"\0".join(p.read_bytes() for p in files)).hexdigest()


def judge_one(session, output, prompt, step):
    payload = {k: output[k] for k in ("issue", "evidence", "comment")}
    response = session.client.create(system=prompt, messages=[{"role": "user", "content": json.dumps(payload)}])
    session.trace.model_call(step, response, purpose="judge")
    text = response.text.strip()
    if text.startswith("```"):
        text = "\n".join(text.splitlines()[1:-1])
    verdict = json.loads(text)
    answer = str(verdict.get("answer", "")).lower()
    reasoning = verdict.get("reasoning")
    if answer not in ("pass", "fail") or not isinstance(reasoning, str) or not reasoning.strip():
        raise ValueError("judge did not return a valid answer and reasoning")
    return {"id": output["id"], "answer": answer, "reasoning": reasoning,
            "session": session.id, "model": response.model}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["tuning", "freeze", "test", "versions", "recorded"])
    parser.add_argument("repeat", nargs="?", type=int, default=1, choices=[1, 2, 3])
    parser.add_argument("--backend", help="scripted backend for plumbing checks")
    args = parser.parse_args(argv)
    criterion = ROOT / "eval/judge/criterion.md"
    if not criterion.exists() or not PROMPT.exists():
        parser.error("write the criterion and example-based prompt before running the judge")
    frozen = ROOT / "eval/judge/frozen.json"
    digest = configuration_digest()
    if args.mode == "freeze":
        if frozen.exists():
            parser.error("judge already frozen; preserve existing validation before defining another judge")
        frozen.write_text(json.dumps({"digest": digest, "model": yaml.safe_load((ROOT / "settings.yaml").read_text())["model"]}, indent=2)+"\n")
        return 0
    if args.mode != "tuning" and not args.backend:
        if not frozen.exists() or json.loads(frozen.read_text())["digest"] != digest:
            parser.error("freeze the judge after tuning; prompt, criterion, settings and split must remain unchanged")
    if args.mode == "tuning" and frozen.exists():
        parser.error("judge is frozen; tuning has ended")
    split = yaml.safe_load((ROOT / "eval/labels/split.yaml").read_text())
    outputs = load_outputs()
    entries = []
    if args.mode in ("test", "tuning", "versions"):
        ids = split["tuning" if args.mode == "tuning" else "test"]
        for ident in ids:
            output = outputs[ident]
            if args.mode == "versions":
                entries += [({**output, "comment": output["versions"][version]}, version) for version in ("list", "long")]
            else:
                entries.append((output, None))
    else:
        for path in sorted((ROOT / "fixtures/traces7").glob("agent-*.jsonl")):
            lines = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
            calls = [line for line in lines if line.get("type") == "tool_call"]
            comments = [i for i, c in enumerate(calls) if c["name"] in ("issues_comment", "post_comment")]
            if not comments:
                continue
            last = comments[-1]
            issue = next((c.get("result", c.get("result_excerpt", "")) for c in calls[:last] if c["name"] in ("issues_read", "read_issue")), "")
            evidence = [{"tool": c["name"], "input": c["input"], "result": c.get("result", c.get("result_excerpt", ""))} for c in calls[:last]]
            entries.append(({"id": path.stem, "issue": issue, "evidence": evidence, "comment": calls[last]["input"]["body"]}, None))
    name = f"test_{args.repeat}" if args.mode == "test" else args.mode
    directory = VERDICTS / "scripted" if args.backend else VERDICTS
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (name+".jsonl")
    if target.exists():
        parser.error("verdict file already exists; do not overwrite validation evidence")
    prompt = PROMPT.read_text()+"\n\nCriterion:\n"+criterion.read_text()
    with judge_session(name, backend=args.backend) as session:
        with target.open("x") as handle:
            for step, (output, version) in enumerate(entries):
                verdict = judge_one(session, output, prompt, step)
                if version:
                    verdict["version"] = version
                handle.write(json.dumps(verdict)+"\n")
                handle.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
