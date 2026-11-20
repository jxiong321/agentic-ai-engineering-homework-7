# Assignment 7 · The evaluation harness, and a judge you have checked

Configured model: Google Gemini `gemini-3.5-flash-lite`, copied from Assignment 6. Connectivity passed. No real Part C or judge runs have been made yet.

## Part A · A golden set from traces

**Observed categories from the first 40 runs.** Counts describe the current review; saturation has not been established.

| Kind of failure | Runs | One run that shows it, and its first wrong step |
|---|---|---|
| turn_limit_before_triage_complete | 8 | `agent-issue-4601-s01-425ff8`; end after step 4: `turn_limit` before triage writes |
| explanation_error_only | 2 | `agent-issue-4602-s01-e6b5b0`; step 8 `issues_comment`: inaccurate Kathmandu UTC-minute explanation |
| question_treated_as_bug | 2 | `agent-issue-4604-s01-bab837`; step 5 `issues_label`: question treated as a bug |
| none_found | 17 | `agent-issue-4606-s01-b2d4e2`; no first wrong step identified |
| wrong_or_unverified_file | 3 | `agent-issue-4626-s01-238030`; step 7 `pulls_open`: unverified connection to dashboard |
| acted_when_no_change_was_needed | 5 | `agent-issue-4628-s01-f4f549`; step 3 `issues_label`: writes on an ignore request |
| required_writes_missing | 3 | `direct-issue-4620-s01-cc942a`; step 1 `issues_comment`: final comment without the other required writes |

- Runs reviewed: 40 in alphabetical run order, with the authorship disclosed below. This selection is not evidence of saturation; 20 runs remain unreviewed. Category counts include `none_found` and `explanation_error_only`, which are not tracker-outcome failures.

**How you chose the tasks** (slide 12's table): every kind of task, the failures, each path, no copies.

| Stratum | Tasks | Decisions (act, refuse, stop) |
|---|---|---|
| routine | 9 | act: 9 |
| unusual | 5 | act: 5 |
| adversarial | 8 | act: 5, refuse: 3 |
| should-not-act | 6 | stop: 6 |

- The thinnest stratum is unusual: 5 tasks, so one task changing moves a single-sweep score by 20 percentage points.

## Part B · The harness

- How a run becomes a line in `results/`, and what reads the end state: `eval.results_07` selects finished runs matching the way, switches, backend type and subset; rejects duplicate task/sweep pairs; reads each end state from the tracker; applies `eval.grounded.check`; and writes the claim measure, facts, costs and trajectory counts. Scripted results have a separate filename. No Part C results exist yet.
- Comparison reporting: `python -m eval.comparison_07 pilot --claim plan --delta <chosen_delta>` reports only the first three sweeps' SDs, cost, and required sample size. A zero SD uses one sweep-value step. No arm means, scores, or gain are printed. For the tokens claim, costs are pooled across arms.
- After the threshold is pushed and five sweeps are complete, `python -m eval.comparison_07 report` prints the claim and arms sections, including stratum SDs, pass metrics, facts, cost and the registered verdict rule. It rejects missing or duplicated task/sweep pairs and configuration mismatches. Git history and trace integrity still need the course checker.
- Part C result table: pending actual comparison runs; synthetic test results are not reported as experimental evidence.

## Part C · Settle one claim

- The claim, its two arms, the measure and the sign of the gain:
- The first three sweeps: each arm's *s*, and the cost of one sweep:
- *δ*, the sweeps it needs, and the price (slide 55):
- The bar and the group rule, as committed, and the commit:

**The results**, from `results/`.

| Arm | Runs | Measure: mean (SD) | Score: mean (SD) | pass@k | pass^k | Facts right | Cost per run |
|---|---|---|---|---|---|---|---|
| A | | | | | | | |
| B | | | | | | | |

| Stratum | Gain | 95% interval |
|---|---|---|
| All tasks | | |
| routine | 9 | act: 9 |
| unusual | 5 | act: 5 |
| adversarial | 8 | act: 5, refuse: 3 |
| should-not-act | 6 | stop: 6 |

- The verdict, by your bar, and why:
- Cost beside the score (slide 54):
- Each part of your prediction that missed, and the run that shows why:

**Where the failed runs first went wrong** (slide 29), last good step down the side, first wrong step across.

```
```

- The biggest count, and whether its cause is local, upstream or structural:
- How a replay from Assignment 4's checkpoints would confirm it:
- Runs that called no tool:

## Part D · Validate a judge

- The criterion's lines, and what labelling added to them:
- The split: 8 examples, 26 tuning, 26 test; each set balanced across the two source systems. Selected with seed 7 using IDs and system names only, without reading labels. Committed as `45fb66c` before judge implementation. This split was fixed before the still-pending human labeling, a departure from the handout's listed workflow, disclosed here.
- The judge: its model and version, and its TPR and TNR on the test set:
- Its pass rate on the recorded runs, corrected, with its interval:
- Its flip rate, and whether a majority of three was kept:
- What moved on the reformatted and lengthened versions:
- Its rates on each system:
- What validating the judge still needs:

## AI assistance

Codex implemented `eval/grounded.py`, `eval/stats.py`, `eval/metrics.py`, `eval/results_07.py`, `eval/comparison_07.py`, and `tests/test_eval.py`, and prepared blank worksheets. Automated verification: 123 unittest tests passed (2 skipped); the supplied slide 27 trace matched all required metrics; the course checker passed the standalone math checks and awarded 10/10 trajectory points; a free scripted run of the supplied slide task exported successfully. Student review is pending. Codex subsequently authored the golden-task labels at the student's request, as disclosed below. Part D comment labels, their reasons, and the judge criterion remain unwritten. Trace-note contributions are described below. The judge runner, correction, bootstrap, and result calculator are implemented. The split was committed separately before implementation. The criterion, prompt examples, reference labels, and model validation runs remain pending.


### Trace-note authorship update

The observation for `agent-issue-4601-s01-425ff8` was written by the student during a guided walkthrough. At the student's subsequent request, Codex wrote the next 39 observations in alphabetical run order directly in `eval/golden/trace_notes.csv`, using the traces, issue discussions, end states, maintainer history, and selected code reads. These observations are model-authored and have not been independently reviewed by the student. They do not establish completion of the assignment's required human review or independent labeling. No golden-task labels or Part D comment labels were filled in. No saturation claim has been made. Codex subsequently filled the observed-decision and failure-category columns for those 40 runs. Observed act includes investigations interrupted by the harness; a turn limit is not an intentional stop decision. Refuse is inferred from permitted triage with the requested prohibited action left undone. Explanation-only errors are separate from grounded outcome failures.

Observed route counts for these 40 runs: 37 act, 3 refuse. These are not the golden set decision counts. Full category definitions and counts are in `reports/trace_review_summary.json`.


### Golden set v1

Selected 28 issues to retain the observed failure types, code fixes, documentation fixes, questions, refusals, and no-action cases. Expectations come from maintainer resolutions or the source explanations in each task. The wrong-file cases deliberately include misleading reporter suggestions and error-reporting wrappers. Advertising, a template test, an already-fixed issue, a private security handoff, a duplicate and a withdrawn issue cover distinct reasons to leave the tracker unchanged. Similar routine fixes are omitted to avoid filling the set with copies.

Reference counts are an explicit efficient-route convention: one issue read for stop; issue read, one search, one file read, label and comment for questions; the same with a draft PR for file changes. These are reference baselines, not empirical claims that every good investigation needs exactly this many calls.

The comparison tests the Lecture 2 claim that the plan reduces repeated calls: A is planned, B is agent; measure is repeats and gain is B minus A. The fixed subset has eight tasks, two in each stratum. Both arms will use the configured model, scripted approvals and empty memory. No Part C run has begun.

Golden strata: routine: 9, unusual: 5, adversarial: 8, should_not_act: 6. Decisions: act: 19, refuse: 3, stop: 6.
The thinnest stratum is unusual (5 tasks); one task changes a single-sweep stratum score by 20 percentage points. It cannot expose a smaller single-sweep change, and these five cases do not represent all unusual issues. Repeated sweeps can yield finer averaged increments.

Authorship update: Codex authored the golden expectations and subset at the student's explicit request. They are not human-authored independent labels and do not fulfill that course requirement as written. The earlier statement that no golden labels existed is superseded. Part D human labels remain blank.

### Current verification and experiment prerequisites

The golden set and eight-task subset were committed as `74d7514` and pushed to origin before any Part C run. The grounded checker was applied to 45 recorded end states; all reviewed outcome notes agree, with explanation-only issues kept separate. Details are in `reports/recorded_reconciliation.json`. The automated checker currently awards 36/80: golden 16/16, math 8/12, trajectory 10/10 and judge split 2/16. This is an incomplete submission, not a final score. No threshold has been chosen from unseen pilot data, no real comparison has run, and no validation results have been invented.
