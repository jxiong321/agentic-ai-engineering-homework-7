"""Summarize a pilot without exposing gains, or report a preregistered comparison.

python -m eval.comparison_07 pilot --claim plan --delta 0.5
python -m eval.comparison_07 report --threshold eval/thresholds/claim.yaml

The pilot prints only SDs, costs and sizing, never arm means or differences.
The report prints the computed claim/arms sections; it does not overwrite the
student's report, choose a threshold, or establish that anything was pushed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from statistics import mean

import yaml

from eval.stats import interval, over_tasks, spread, sweeps_needed
from harness import ROOT
from harness.formats import CLAIMS, STRATA
from harness.switches import DEFAULTS
from harness.tasks import load_tasks, read_subset


def validate(rows, subset, sweeps, arm, strata=None):
    """Require exactly one run per selected task in each requested sweep."""
    if not subset or len(set(subset)) != len(subset):
        raise ValueError('subset must be nonempty and unique')
    wanted = {(task, sweep) for task in subset for sweep in sweeps}
    observed = Counter((r['task'], r['sweep']) for r in rows)
    if set(observed) != wanted or any(n != 1 for n in observed.values()):
        raise ValueError(f'{arm}: incomplete, extra, or duplicate task/sweep results')
    if len({r['run_id'] for r in rows}) != len(rows):
        raise ValueError(f'{arm}: repeated run ID')
    ways = {r['way'] for r in rows}
    switches = {json.dumps({**DEFAULTS, **r['switches']}, sort_keys=True) for r in rows}
    if len(ways) != 1 or len(switches) != 1:
        raise ValueError(f'{arm}: mixed configurations')
    for r in rows:
        if r['arm'] != arm or r['stratum'] not in STRATA:
            raise ValueError(f'{arm}: wrong arm or unknown stratum')
        if strata is not None and r['stratum'] != strata[r['task']]:
            raise ValueError(f'{arm}: stratum differs from golden task')
        if type(r['passed']) is not bool:
            raise ValueError('passed must be boolean')
        for key in ('measure', 'cost_usd', 'tokens', 'wall_clock_s'):
            if isinstance(r[key], bool) or not isinstance(r[key], (int, float)) or not math.isfinite(r[key]) or r[key] < 0:
                raise ValueError(f'invalid {key}')
        facts = r['facts']
        if not (0 <= facts['present'] <= facts['total'] and facts['total'] > 0):
            raise ValueError('invalid fact counts')
        if r['passed'] != (facts['present'] == facts['total']):
            raise ValueError('pass disagrees with fact counts')


def sweep_values(rows, field='measure'):
    grouped = defaultdict(list)
    for r in rows:
        grouped[r['sweep']].append(100 * r['passed'] if field == 'score' else r[field])
    return [mean(grouped[s]) for s in sorted(grouped)]


def pilot(first, second, subset, claim, delta, strata=None):
    if claim not in CLAIMS:
        raise ValueError('unknown claim')
    for arm, rows in (('A', first), ('B', second)):
        validate(rows, subset, range(1, 4), arm, strata)
    observed_a, observed_b = spread(sweep_values(first)), spread(sweep_values(second))
    step = (100 if claim == 'split' else 1) / len(subset)
    s_a, s_b = observed_a or step, observed_b or step
    n = sweeps_needed(s_a, s_b, delta)
    cost_a = sum(r['cost_usd'] for r in first) / 3
    cost_b = sum(r['cost_usd'] for r in second) / 3
    shared_cost = (cost_a + cost_b) / 2
    result = {'pilot_sweeps': 3, 'observed_s_a': observed_a, 'observed_s_b': observed_b,
              's_a': s_a, 's_b': s_b, 'zero_sd_fallback': step,
              'delta': delta, 'n_needed': n, 'mean_sweep_cost_usd': shared_cost,
              'price_usd': n * 2 * shared_cost,
              'caution': 'Three sweeps give a rough spread; zero SD uses one step of a sweep value.'}
    # Token cost is closely tied to the claim measure: pool both arms as required.
    if claim != 'tokens':
        result['sweep_cost_usd_by_arm'] = {'A': cost_a, 'B': cost_b}
    return result


def summarize_arm(rows, k):
    counts = defaultdict(lambda: [0, 0])
    for r in rows:
        counts[r['task']][0] += 1
        counts[r['task']][1] += r['passed']
    at, hat = over_tasks(counts, k)
    measure, score = sweep_values(rows), sweep_values(rows, 'score')
    return {'way': rows[0]['way'], 'switches': rows[0]['switches'], 'runs': len(rows),
            'sweeps': len(measure), 'measure': {'mean': mean(measure), 'sd': spread(measure)},
            'score': {'mean': mean(score), 'sd': spread(score)},
            'pass_at_k': at, 'pass_hat_k': hat,
            'facts_share': sum(r['facts']['present'] for r in rows)/sum(r['facts']['total'] for r in rows),
            'cost_per_run_usd': mean(r['cost_usd'] for r in rows),
            'no_tools': sum(r['metrics']['no_tools'] for r in rows)}


def comparison(first, second, subset, threshold, strata=None):
    claim = threshold['claim']
    if claim not in CLAIMS or threshold['measure'] != CLAIMS[claim]:
        raise ValueError('claim and measure do not agree')
    sign = 'A - B' if claim in ('tokens', 'split') else 'B - A'
    if threshold['gain'] != sign:
        raise ValueError('gain sign does not match the claim')
    if threshold['sweeps'] != 5:
        raise ValueError('the assignment requires five sweeps per arm')
    if threshold['group_floor'] > 0:
        raise ValueError('group floor must be zero or below')
    for arm, rows in (('A', first), ('B', second)):
        validate(rows, subset, range(1, 6), arm, strata)
        expected = threshold['arm_' + arm.lower()]
        if rows[0]['way'] != expected['way'] or {**DEFAULTS, **rows[0]['switches']} != {**DEFAULTS, **expected.get('switches', {})}:
            raise ValueError(f'{arm}: results disagree with registered configuration')
    for task in subset:
        groups = {r['stratum'] for r in first + second if r['task'] == task}
        if len(groups) != 1:
            raise ValueError('arms disagree on task strata')
    groups = {r['stratum'] for r in first}
    if groups != set(STRATA):
        raise ValueError('comparison must cover every stratum')
    by_stratum = {}
    arms = {'A': summarize_arm(first, threshold['k']), 'B': summarize_arm(second, threshold['k'])}
    for arm in arms:
        arms[arm]['by_stratum'] = {}
    def difference(a, b):
        gain, low, high = interval(sweep_values(a if sign == 'A - B' else b),
                                   sweep_values(b if sign == 'A - B' else a))
        return {'difference': gain, 'interval': [low, high]}
    overall = difference(first, second)
    for group in sorted(groups):
        a = [r for r in first if r['stratum'] == group]
        b = [r for r in second if r['stratum'] == group]
        by_stratum[group] = difference(a, b)
        for arm, rows in (('A', a), ('B', b)):
            summary = summarize_arm(rows, threshold['k'])
            # FORMATS 15.8 expects scalar stratum means; retain their SDs separately.
            summary['measure_sd'] = summary['measure']['sd']
            summary['score_sd'] = summary['score']['sd']
            summary['measure'] = summary['measure']['mean']
            summary['score'] = summary['score']['mean']
            arms[arm]['by_stratum'][group] = summary
    low, high = overall['interval']
    if low > threshold['bar'] and all(x['difference'] >= threshold['group_floor'] for x in by_stratum.values()):
        verdict = 'holds'
    elif high < threshold['bar']:
        verdict = 'fails'
    else:
        verdict = 'cannot_settle'
    result = {key: threshold[key] for key in ('claim','measure','gain','k','sweeps','s_a','s_b','delta','n_needed','price_usd')}
    result.update(overall, by_stratum=by_stratum, verdict=verdict)
    return {'claim': result, 'arms': arms}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['pilot', 'report'])
    parser.add_argument('--a', default='results/A.jsonl')
    parser.add_argument('--b', default='results/B.jsonl')
    parser.add_argument('--tasks', default='eval/golden/v1/tasks')
    parser.add_argument('--subset', default='eval/subsets/claim.txt')
    parser.add_argument('--claim', choices=sorted(CLAIMS))
    parser.add_argument('--delta', type=float)
    parser.add_argument('--threshold', default='eval/thresholds/claim.yaml')
    args = parser.parse_args(argv)
    def path(value):
        p = Path(value)
        return p if p.is_absolute() else ROOT/p
    def read(value):
        return [json.loads(line) for line in path(value).read_text().splitlines() if line.strip()]
    first, second = read(args.a), read(args.b)
    subset = read_subset(args.subset)
    strata = {t.id: t.stratum for t in load_tasks(args.tasks)}
    if set(subset) - strata.keys():
        parser.error('subset includes unknown golden tasks')
    if not 8 <= len(subset) <= 10 or any(sum(strata[t] == s for t in subset) < 2 for s in STRATA):
        parser.error('subset needs 8–10 tasks with at least two in each stratum')
    if args.mode == 'pilot':
        if args.claim is None or args.delta is None:
            parser.error('pilot requires --claim and --delta')
        result = pilot(first, second, subset, args.claim, args.delta, strata)
    else:
        result = comparison(first, second, subset, yaml.safe_load(path(args.threshold).read_text()), strata)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
