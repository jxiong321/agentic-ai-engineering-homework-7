"""Assignment 7, Part B, task 1: one line per run, in results/<arm>.jsonl
(checks/FORMATS.md, section 15.4).

    python -m eval.results_07 --arm A --way planned --claim plan
    python -m eval.results_07 --arm B --way planned --switch TOOL_EXAMPLES=off --claim examples

Reads the arm's finished runs on your subset's golden tasks in runs/, checks each with your
grounded check, computes Part C's measure and the five metrics, and writes one line
per run. The helpers below find the runs and read them; the rest is yours.

A line (section 15.4):

    {"arm": "A", "way": "planned", "switches": {...}, "run_id": "...", "task": "g07",
     "stratum": "routine", "sweep": 1, "passed": true, "facts": {"present": 6, "total": 6},
     "measure": 0, "tokens": 31234, "cost_usd": 0.0412, "wall_clock_s": 18.2,
     "metrics": {"step_count": 2, "precision": 1.0, "recall": 1.0, "repeats": 0,
                 "orphans": 1, "no_tools": false, "cost_usd": 0.0412, "latency_s": 18.2}}

Part C's measure, per run, by claim (section 15.4): tokens, the run_end line's
totals.total_tokens; plan, the run's repeats; examples, its wasted calls: the lines of
its call record (runs/<run_id>.calls.jsonl) whose outcome is "rejected", "error" or
"protocol", plus the search calls whose result has "count": 0; checkpoint, its duplicate
writes: the comments beyond one, plus the open pull requests beyond one, on its issue
in its end state; split, 100 when the run passed and 0 when it did not.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from harness import LAB, ROOT
from harness import switches as switch_board
from harness.formats import UNFINISHED
from harness.trace import read_trace


def finished_runs(way: str, switches: dict | None = None, root: Path = ROOT,
                  scripted: bool = False) -> list[list[dict]]:
    """Every finished Assignment 7 run of `way` with these switches (unset ones at their
    defaults), on a real model, as its trace's lines: one list per run. A run is finished
    when its last line is run_end and it did not end quota or rate_limited. With
    scripted=True, the runs on a scripted model instead, to test your code for free."""
    want = {**switch_board.DEFAULTS, **(switches or {})}
    out = []
    for path in sorted((root / "runs").glob("*.jsonl")):
        if path.name.startswith("_") or path.name.count(".") > 1:
            continue
        lines = read_trace(path)
        start = lines[0] if lines else {}
        if start.get("type") != "run_start" or start.get("lab") != LAB or start.get("way") != way:
            continue
        if {**switch_board.DEFAULTS, **(start.get("switches") or {})} != want:
            continue
        free = str(start.get("backend", "")).startswith("harness.scripted:") or start.get("backend") == "never-stops"
        if free != scripted:
            continue
        ends = [r.get("terminal_reason") for r in lines if r.get("type") == "end"]
        if lines[-1].get("type") != "run_end" or set(ends) & set(UNFINISHED):
            continue
        out.append(lines)
    return out


def call_record(run_id: str, root: Path = ROOT) -> list[dict]:
    """A run's call record, runs/<run_id>.calls.jsonl, one dict per line."""
    path = root / "runs" / f"{run_id}.calls.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def measure_value(claim, totals, counted, graded, state, task, records):
    """Compute a claim's measure using the documented trace and tracker fields."""
    if claim == "tokens":
        return totals["total_tokens"]
    if claim == "plan":
        return counted["repeats"]
    if claim == "split":
        return 100 if graded["passed"] else 0
    if claim == "checkpoint":
        return sum(max(0, len(state[n]["comments"])-1) + max(0, len(state[n]["prs"])-1)
                   for n in task.issues)
    if claim != "examples":
        raise ValueError(f"unknown claim {claim}")
    from harness.roles import role_of
    wasted = 0
    for row in records:
        wasted += row.get("outcome") in ("rejected", "error", "protocol")
        if role_of(row.get("tool", "")) == "search":
            result = row.get("result", {})
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except ValueError:
                    result = {}
            wasted += isinstance(result, dict) and result.get("count") == 0
    return wasted


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--arm", required=True, choices=["A", "B"])
    p.add_argument("--way", required=True)
    p.add_argument("--switch", action="append", default=[], metavar="NAME=VALUE")
    p.add_argument("--claim", required=True, choices=["tokens", "plan", "examples", "checkpoint", "split"])
    p.add_argument("--tasks", default="eval/golden/v1/tasks")
    p.add_argument("--subset", default="eval/subsets/claim.txt", help="only these task IDs (Part C)")
    p.add_argument("--scripted", action="store_true",
                   help="the runs on a scripted model, to test this script for free: writes "
                        "results/scripted_<arm>.jsonl, which the checker never reads")
    args = p.parse_args(argv)
    from harness.tasks import load_tasks, read_subset, end_state
    from harness.tracker import Tracker
    from eval.grounded import check
    from eval.metrics import metrics
    switches = {}
    for setting in args.switch:
        key, sep, value = setting.partition("=")
        key = key.lower()
        if not sep or key not in switch_board.DEFAULTS:
            p.error("switch must be a known NAME=VALUE")
        if isinstance(switch_board.DEFAULTS[key], bool):
            if value.lower() not in ("1", "0", "true", "false", "on", "off"):
                p.error("boolean switch must be 1/0, true/false, or on/off")
            value = value.lower() in ("1", "true", "on")
        switches[key] = value
    tasks = {t.id: t for t in load_tasks(args.tasks)}
    subset = set(read_subset(args.subset))
    if not subset or subset - tasks.keys():
        p.error("subset must contain known golden task IDs")
    tracker = Tracker(flaky=False, readback_fail=False)
    rows, seen = [], set()
    for lines in finished_runs(args.way, switches, scripted=args.scripted):
        start, end = lines[0], lines[-1]
        if start.get("task") not in subset:
            continue
        task = tasks[start["task"]]
        identity = (task.id, start["sweep"])
        if identity in seen:
            raise ValueError(f"duplicate finished task/sweep: {identity}; resolve before reporting")
        seen.add(identity)
        state = end_state(tracker, start["run_id"], task)
        graded = check(task, state)
        counted = metrics(lines, task)
        totals = end["totals"]
        measure = measure_value(args.claim, totals, counted, graded, state, task,
                                call_record(start["run_id"]))
        rows.append({"arm": args.arm, "way": args.way,
                     "switches": {**switch_board.DEFAULTS, **switches},
                     "run_id": start["run_id"], "task": task.id, "stratum": task.stratum,
                     "sweep": start["sweep"], "passed": graded["passed"],
                     "facts": {"present": sum(v == "present" for v in graded["facts"].values()),
                               "total": len(graded["facts"])},
                     "measure": measure, "tokens": totals["total_tokens"],
                     "cost_usd": totals["cost_usd"], "wall_clock_s": end["elapsed_s"],
                     "metrics": counted})
    if not rows:
        p.error("no matching finished runs; no result file was written")
    target = ROOT / "results" / (("scripted_" if args.scripted else "") + args.arm + ".jsonl")
    target.parent.mkdir(parents=True, exist_ok=True)
    rows.sort(key=lambda row: (row["sweep"], row["task"]))
    temporary = target.with_suffix(".tmp")
    temporary.write_text("".join(json.dumps(row) + "\n" for row in rows))
    temporary.replace(target)
    print(f"wrote {len(rows)} runs to {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
