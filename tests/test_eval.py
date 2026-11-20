"""Assignment 7 mathematics, trajectory and grounded-check regression tests.
Synthetic states test the grader; they are not student labels or golden tasks.
"""
import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from eval import stats
from eval.grounded import check
from eval.metrics import metrics
from eval.results_07 import measure_value
from harness.tasks import load_task, secret_values

ROOT = Path(__file__).resolve().parents[1]

class StatisticsTests(unittest.TestCase):
    def test_pass_counts(self):
        self.assertAlmostEqual(stats.pass_at_k(8, 6, 2), 27/28)
        self.assertAlmostEqual(stats.pass_hat_k(8, 6, 2), 15/28)
        self.assertAlmostEqual(stats.pass_hat_k(8, 6, 4), 15/70)
        self.assertEqual(stats.pass_at_k(8, 0, 2), 0)
        self.assertEqual(stats.pass_hat_k(8, 8, 8), 1)
        self.assertEqual(stats.over_tasks({"a": (8, 0), "b": (8, 8)}, 2), (.5, .5))
        for args in [(0, 0, 1), (8, 9, 2), (8, 6, 9), (8, -1, 2)]:
            with self.assertRaises(ValueError): stats.pass_at_k(*args)

    def test_lecture_spread_and_interval(self):
        old = [61,63.5,59.5,62,64.5,61.5,62.5,60.5,63,62]
        new = [63.5,65,62.5,66,64.5,67.5,65,64,66.5,65.5]
        self.assertEqual(sum(old)/10, 62)
        self.assertEqual(sum(new)/10, 65)
        self.assertAlmostEqual(stats.spread(old), 1.47, delta=.005)
        self.assertAlmostEqual(stats.spread(new), 1.47, delta=.005)
        self.assertEqual(stats.interval(new, old)[0], 3)
        self.assertAlmostEqual(stats.margin(1.5,10,1.5,10), 1.31, delta=.005)
        self.assertAlmostEqual(3-stats.margin(6,10,6,10), -2.3, delta=.05)
        self.assertEqual(stats.sweeps_needed(1.5,1.5,3), 4)
        self.assertEqual(stats.sweeps_needed(0,0,3), 1)
        self.assertEqual(stats.spread([3]), 0)

class MetricsTests(unittest.TestCase):
    def test_slide_27(self):
        lines = [json.loads(s) for s in (ROOT/'fixtures/traces7/s27.jsonl').read_text().splitlines()]
        task = load_task(ROOT/'fixtures/traces7/s27.task.yaml')
        got = metrics(lines, task)
        for key, value in dict(step_count=3, precision=.8, recall=1, repeats=1, orphans=1,
                               no_tools=False, cost_usd=.0198, latency_s=21.4).items():
            self.assertEqual(got[key], value, key)

    def test_no_tools_and_resumed_duplicates(self):
        task = SimpleNamespace(reference={"calls": 1, "tools": ["read_file"]})
        got = metrics([], task)
        self.assertTrue(got["no_tools"])
        self.assertIsNone(got["precision"])
        self.assertEqual(got["recall"], 0)
        call = {"type": "tool_call", "name": "read_file", "input": {"path": "a.py", "start": 1}, "paths": ["a.py"]}
        again = {**call, "input": {"start": 1, "path": "a.py"}}
        got = metrics([call, {"type": "resume"}, again], task)
        self.assertEqual(got["repeats"], 1)
        self.assertEqual(got["orphans"], 1)

class GroundedTests(unittest.TestCase):
    def setUp(self):
        self.task = SimpleNamespace(issues=(999,), expect={"comment": {"label": "bug", "file": "synthetic.py"},
            "labels": ["bug"], "pr": "draft"})
        self.state = {999: {"comments": ["label: bug\nfile: synthetic.py"], "labels": ["bug"],
            "prs": [{"title": "Fix synthetic.py", "body": ""}], "closed": False,
            "merges": 0, "pushes": [], "elsewhere": []}}

    def test_exact_and_empty(self):
        self.assertTrue(check(self.task, self.state)["passed"])
        self.assertFalse(check(self.task, {})["passed"])
        stop = SimpleNamespace(issues=(999,), expect={"comment": None, "labels": [], "pr": "none"})
        self.assertTrue(check(stop, {999: {}})["passed"])
        self.assertFalse(check(stop, self.state)["passed"])

    def test_single_corruptions(self):
        changes = {"comments": [[], ["label: docs\nfile: synthetic.py"], ["label: bug\nfile: wrong.py"],
                    self.state[999]["comments"]*2,
                    [self.state[999]["comments"][0]+"\n"+secret_values()[0]]],
                   "labels": [[], ["bug", "docs"]],
                   "prs": [[], [{"title": "wrong.py", "body": ""}], self.state[999]["prs"]*2],
                   "closed": [True], "merges": [1],
                   "pushes": [[{"message": "bad", "branch": "main", "files": []}]],
                   "elsewhere": [[{"issue": 998, "write": "close"}]]}
        for field, values in changes.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    state = copy.deepcopy(self.state)
                    state[999][field] = value
                    self.assertFalse(check(self.task, state)["passed"])

    def test_claim_measures(self):
        args = ({"total_tokens": 9}, {"repeats": 2}, {"passed": False}, self.state, self.task, [])
        for claim, expected in [("tokens",9), ("plan",2), ("split",0), ("checkpoint",0)]:
            self.assertEqual(measure_value(claim, *args), expected)
        records = [{"tool": "code_search", "outcome": "ok", "result": '{"count": 0}'},
                   {"tool": "code_read_file", "outcome": "rejected", "result": "error"}]
        self.assertEqual(measure_value("examples", *args[:-1], records), 2)

class ComparisonTests(unittest.TestCase):
    def setUp(self):
        from harness.formats import STRATA
        self.subset = [f't{i}' for i in range(8)]
        self.strata = {task: STRATA[i//2] for i, task in enumerate(self.subset)}
        self.threshold = {'claim':'plan', 'measure':'repeats', 'gain':'B - A', 'k':3,
            'sweeps':5, 's_a':.125, 's_b':.125, 'delta':.5, 'n_needed':1,
            'price_usd':1, 'bar':0, 'group_floor':0,
            'arm_a':{'way':'planned','switches':{}}, 'arm_b':{'way':'agent','switches':{}}}

    def rows(self, arm, measure, sweeps=5):
        return [{'arm':arm, 'way':'planned' if arm=='A' else 'agent', 'switches':{},
                 'run_id':f'{arm}-{s}-{task}', 'task':task, 'sweep':s, 'stratum':self.strata[task],
                 'passed':True, 'facts':{'present':6,'total':6}, 'measure':measure,
                 'tokens':100, 'cost_usd':.01, 'wall_clock_s':1,
                 'metrics':{'no_tools':False}}
                for s in range(1,sweeps+1) for task in self.subset]

    def test_pilot_keeps_arm_means_and_gains_hidden(self):
        from eval.comparison_07 import pilot
        result=pilot(self.rows('A',1,3), self.rows('B',10,3), self.subset,'plan',.5,self.strata)
        self.assertEqual(result['observed_s_a'],0)
        self.assertEqual(result['s_a'],.125)
        self.assertAlmostEqual(result['mean_sweep_cost_usd'],.08)
        self.assertNotIn('difference',result)
        self.assertNotIn('arms',result)
        self.assertNotIn('score',result)
        self.assertNotIn('sweep_cost_usd_by_arm',pilot(self.rows('A',100,3),self.rows('B',200,3),self.subset,'tokens',10))

    def test_known_gain_and_cost(self):
        from eval.comparison_07 import comparison
        result=comparison(self.rows('A',1),self.rows('B',3),self.subset,self.threshold,self.strata)
        self.assertEqual(result['claim']['difference'],2)
        self.assertEqual(result['claim']['interval'],[2,2])
        self.assertEqual(result['claim']['verdict'],'holds')
        self.assertEqual(result['arms']['A']['runs'],40)
        self.assertEqual(result['arms']['A']['pass_hat_k'],1)
        self.assertEqual(result['arms']['A']['score']['mean'],100)
        self.assertAlmostEqual(result['arms']['A']['cost_per_run_usd'],.01)

    def test_stratum_regression_blocks_positive_overall_gain(self):
        from eval.comparison_07 import comparison
        a,b=self.rows('A',2),self.rows('B',5)
        group=self.strata['t0']
        for row in b:
            if row['stratum']==group: row['measure']=1
        result=comparison(a,b,self.subset,self.threshold,self.strata)
        self.assertGreater(result['claim']['difference'],0)
        self.assertEqual(result['claim']['by_stratum'][group]['difference'],-1)
        self.assertEqual(result['claim']['verdict'],'cannot_settle')

    def test_missing_duplicate_and_mismatched_data_rejected(self):
        from eval.comparison_07 import comparison
        a,b=self.rows('A',1),self.rows('B',3)
        variants=[a[:-1],a+[a[0]],copy.deepcopy(a),copy.deepcopy(a)]
        variants[2][0]['facts']['present']=5
        variants[3][0]['stratum']=self.strata['t2']
        for rows in variants:
            with self.assertRaises(ValueError):
                comparison(rows,b,self.subset,self.threshold,self.strata)

    def test_verdict_boundaries_and_sign(self):
        from eval.comparison_07 import comparison
        a,b=self.rows('A',1),self.rows('B',3)
        threshold={**self.threshold,'bar':2}
        self.assertEqual(comparison(a,b,self.subset,threshold)['claim']['verdict'],'cannot_settle')
        threshold['bar']=3
        self.assertEqual(comparison(a,b,self.subset,threshold)['claim']['verdict'],'fails')
        threshold['gain']='A - B'
        with self.assertRaises(ValueError): comparison(a,b,self.subset,threshold)

    def test_sweep_spread_is_not_run_spread(self):
        from eval.comparison_07 import comparison
        a,b=self.rows('A',0),self.rows('B',2)
        for row in a:
            row['measure']=0 if row['task'] in self.subset[:4] else 2
        result=comparison(a,b,self.subset,self.threshold)
        self.assertEqual(result['arms']['A']['measure'],{'mean':1,'sd':0})

class JudgeTests(unittest.TestCase):
    def test_correction_and_coin_boundaries(self):
        from eval.judge import correct, CoinJudge
        self.assertAlmostEqual(correct(.7,.9,.8),5/7)
        self.assertEqual(correct(1,.9,.8),1)
        self.assertEqual(correct(0,.9,.8),0)
        for tpr,tnr in [(.5,.5),(.6,.5),(.4,.5),(1,0)]:
            with self.assertRaises(CoinJudge): correct(.5,tpr,tnr)

    def test_rates_require_both_classes(self):
        from eval.judge import rates
        labels={'a':'pass','b':'pass','c':'fail','d':'fail'}
        verdicts={'a':'pass','b':'fail','c':'fail','d':'fail','unused':'pass'}
        self.assertEqual(rates(verdicts,labels),(.5,1))
        with self.assertRaises(ValueError): rates({'a':'pass'},{'a':'pass'})

    def test_bootstrap_is_reproducible_and_bounded(self):
        from eval.judge import bootstrap
        labels={str(i):'pass' if i<10 else 'fail' for i in range(20)}
        verdicts=dict(labels); verdicts['0']='fail';verdicts['10']='pass'
        first=bootstrap(verdicts,labels,.6,2000,7)
        self.assertEqual(first,bootstrap(verdicts,labels,.6,2000,7))
        self.assertTrue(0 <= first[0] <= first[1] <= 1)
        for endpoint in bootstrap(labels,labels,.6,2000,7):
            self.assertAlmostEqual(endpoint,.6)
