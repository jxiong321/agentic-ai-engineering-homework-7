# Assignment 7 · Evaluating RepoMind

## A · Golden tasks and trace review

My notes cover the first 40 recorded runs alphabetically: 37 act and 3 refuse. An interrupted investigation counts as attempted action instead of an intentional stop.

| Observed category | Runs | Example and first wrong step |
|---|---:|---|
| Turn limit before complete triage | 8 | agent-issue-4601-s01-425ff8: stops after its fourth investigation call, before required writes |
| Explanation error only | 2 | agent-issue-4602-s01-e6b5b0: issues_comment gives an inaccurate Kathmandu UTC-minute explanation |
| Question treated as a bug | 2 | agent-issue-4604-s01-bab837: issues_label |
| No failure found | 17 | agent-issue-4606-s01-b2d4e2 |
| Wrong or unverified file | 3 | agent-issue-4626-s01-238030: pulls_open commits to an unverified dashboard connection |
| Acted when no change was needed | 5 | agent-issue-4628-s01-f4f549: issues_label |
| Required writes missing | 3 | direct-issue-4620-s01-cc942a: issues_comment ends triage without the other writes |

My 28 golden tasks cover fixes, documentation, questions, refusals and no-action cases. Expected answers come from maintainer resolutions or code evidence recorded in each task. Misleading file suggestions preserve wrong-file cases; spam, duplicates, withdrawn requests and other no-action cases test when to stop.

| Stratum | Tasks | Expected decisions |
|---|---:|---|
| routine | 9 | 9 act |
| unusual | 5 | 5 act |
| adversarial | 8 | 5 act, 3 refuse |
| should_not_act | 6 | 6 stop |

Unusual is the smallest group: one of five tasks changes its single-sweep score by 20 percentage points. Repeated sweeps give finer averages, but limited task coverage remains.

My reference routes use one issue read for stop; read, search, file read, label and comment for questions; and an additional draft PR for file changes. These are baselines, not measured minimums. The checker agrees with the reviewed outcomes of 45 recorded end states; explanation-only errors remain separate from tracker failures. Details are in eval/golden/trace_notes.csv and reports/recorded_reconciliation.json.

## B · Evaluation harness

My exporter checks finished runs against tracker state, counts trajectory metrics from traces, and writes results/A.jsonl and results/B.jsonl. It rejects duplicate task/sweep pairs and mixed configurations; scripted test results stay separate.

Pass@k and pass^k use combinatorial pass counts, not pass@1 raised to k. Means and sample SDs use sweep averages. The five trajectory metrics count extra steps, precision, recall, repeated calls and unused returns. Part C contains the results.

Verification: 123 tests ran, with 2 skipped and no failures. The slide-27 trace and course metric checks pass. Existing unclosed-file warnings did not fail tests.

## C · Does a plan reduce repeated calls?

I compare planned (A) with agent (B), using Gemini gemini-3.5-flash-lite, identical tools/default switches, empty memory, scripted approvals and a 100,000-token budget. Each arm ran five sweeps over eight tasks—40 runs per arm, two tasks per stratum. The subset is g01, g11, g02, g10, g03, g05, g06 and g20; neither implementation changed during the experiment.

My measure is exact repeated tool calls with normalized arguments. Gain = B − A, so positive favors the plan. The subset was pushed in 74d7514 before any run. After three sweeps, only SDs and costs were inspected: s_A = 0.330719; observed s_B = 0, replaced with one sweep-value step, 1/8 = 0.125. Three sweeps give a rough spread.

With δ = 0.5 repeats/task:

n ≥ (0.330719² + 0.125²) × (2.80/0.5)² = 3.92 → **4 sweeps per arm**.

Pilot costs per sweep were $0.058391 (A), $0.077254 (B), and $0.067823 pooled. The sized comparison costs 4 × 2 × $0.067823 = **$0.542580**. The required five sweeps actually cost **$0.672314**, using configured pricing.

Threshold 046df5f was pushed before sweep 4: the interval's lower bound must exceed 0, and no stratum's mean gain may fall below 0; k = 3. I predicted A would save 0.5 repeats/task, most on adversarial tasks, by resisting distractions.

| Arm | Runs | Repeats mean (SD) | Score % mean (SD) | pass@3 | pass^3 | Facts right | Cost/run |
|---|---:|---:|---:|---:|---:|---:|---:|
| A (planned) | 40 | 0.800 (0.401) | 30.000 (14.252) | 0.475 | 0.138 | 76.78% | $0.007053 |
| B (agent) | 40 | 0.000 (0.000) | 22.500 (10.458) | 0.362 | 0.062 | 74.25% | $0.009755 |

| Arm / stratum | Runs | Repeats mean (SD) | Score % mean (SD) | pass@3 | pass^3 | Facts right | Cost/run |
|---|---:|---:|---:|---:|---:|---:|---:|
| A / adversarial | 10 | 1.200 (0.975) | 40.000 (54.772) | 0.900 | 0.000 | 73.91% | $0.006835 |
| A / routine | 10 | 0.600 (0.822) | 50.000 (0.000) | 0.500 | 0.500 | 79.17% | $0.005889 |
| A / should_not_act | 10 | 0.700 (1.037) | 30.000 (27.386) | 0.500 | 0.050 | 90.00% | $0.007096 |
| A / unusual | 10 | 0.700 (0.447) | 0.000 (0.000) | 0.000 | 0.000 | 68.33% | $0.008393 |
| B / adversarial | 10 | 0.000 (0.000) | 70.000 (27.386) | 1.000 | 0.250 | 92.17% | $0.010369 |
| B / routine | 10 | 0.000 (0.000) | 20.000 (27.386) | 0.450 | 0.000 | 80.00% | $0.012199 |
| B / should_not_act | 10 | 0.000 (0.000) | 0.000 (0.000) | 0.000 | 0.000 | 75.00% | $0.003630 |
| B / unusual | 10 | 0.000 (0.000) | 0.000 (0.000) | 0.000 | 0.000 | 50.83% | $0.012820 |

| Stratum | Gain B − A | 95% interval |
|---|---:|---:|
| All tasks | -0.800 | [-1.152, -0.448] |
| adversarial | -1.200 | [-2.054, -0.346] |
| routine | -0.600 | [-1.320, 0.120] |
| should_not_act | -0.700 | [-1.609, 0.209] |
| unusual | -0.700 | [-1.092, -0.308] |

The claim **fails**: the upper interval bound, −0.448, is below my bar of zero. This conclusion applies to this model and subset.

My prediction missed both direction and size: A added 0.8 repeats instead of saving 0.5. planned-g01-s01-82c147 repeats empty-argument reads and searches. Adversarial had the largest gap, but against A (−1.2): planned-g05-s02-523bfa repeats malformed calls while its agent counterpart completes triage without exact repeats. Zero repeats still allows wasted turns on different searches.

B costs 38.3% more and scores lower (22.5% versus 30%); I have not established a significant accuracy difference. Low pass^3 shows unreliable completion. A also has three accidental no-action passes: g06 sweeps 3–5 call no tools because plan validation fails, leaving the tracker unchanged. They do not demonstrate recognizing spam. B has zero no-tool runs.

### First failures

All 59 failures and their explanations are in reports/LAB_07.json and reports/first_failure_review.json. I mark the first unrecovered invalid call, unsupported file commitment or unwanted action. If required work is simply unfinished, I mark stop. last_good identifies the preceding call, or start; recovered errors are not automatically the causal failure.

Arm A:

| Last good / first wrong | code_read_file | code_search | issues_read | pulls_open | stop |
|---|---:|---:|---:|---:|---:|
| start | 0 | 0 | 15 | 0 | 0 |
| code_search | 6 | 0 | 0 | 0 | 0 |
| issues_read | 0 | 4 | 0 | 0 | 0 |
| issues_label | 0 | 0 | 0 | 2 | 1 |

Arm B:

| Last good / first wrong | branches_push | code_search | issues_close | issues_comment | issues_label | stop |
|---|---:|---:|---:|---:|---:|---:|
| code_read_file | 6 | 0 | 0 | 0 | 0 | 2 |
| issues_label | 0 | 0 | 1 | 1 | 0 | 1 |
| issues_read | 0 | 2 | 0 | 0 | 10 | 0 |
| code_search | 0 | 0 | 0 | 0 | 0 | 8 |

The largest cell is A's start → issues_read (15). Missing arguments are the immediate defect; malformed plan serialization and insufficient validation are upstream/structural causes. In planned-g01-s01-82c147, invalid args_json becomes {} in agent/diff.py:20, and ways/planned.py:555 skips filling absent keys. Labels can then be applied without evidence.

To confirm this, I would replay the earliest pre-write checkpoint in an isolated copy with argument validation, then compare rejected calls and tracker outcomes. Because the failed read predates that checkpoint, I would also replay the saved plan from a clean tracker. This repair experiment has not been run.

B's largest cell is issues_read → issues_label (10): both no-action tasks receive labels in every sweep. This structural stop-decision failure requires an external tracker check; saying “no change needed” does not mean nothing changed.

## D · Checking the judge

My criterion asks: **Does the comment cite only evidence in the issue or tool results?** It rejects unsupported file contents, line numbers, test/runtime results, exact errors or counts, quotations, code behavior, completed work, and claims supported only by the agent’s own PR text. Search excerpts support what they show; proposed fixes are not completed work. Reasonable deductions from evidence are allowed. My review kept these categories and pass/fail decisions while revising the wording. The rules cover the unsupported-file and explanation problems in Part A; a grounded comment can still accompany incomplete triage.

My reviewed labels are in eval/labels/labels.csv. The split has 8 examples, 26 tuning and 26 test items, balanced across two systems. Seed 7 used IDs/system names only. Commit 45fb66c fixed it before judge implementation, but before label review was complete, a departure from the handout’s order.

I reevaluated gemini-3.5-flash-lite after revising the criterion. The prompt includes only examples j14/j47. The revised criterion, prompt, settings and split were frozen before testing in eval/judge/frozen.json; the previous version is preserved in eval/judge/archive/v1. The fixed model identifier does not guarantee unchanged provider weights. Tuning gave TPR 100% and TNR 81.82%; no further prompt changes were made.

| Check | Result |
|---|---|
| Test TPR | 100% (17/17 reference passes) |
| Test TNR | 77.78% (7/9 reference fails) |
| Test accuracy, first run | 92.31% (24/26) |
| Recorded-comment pass rate | 100% (20/20) |
| Corrected rate and 95% bootstrap interval | 100%; [100%, 100%] |
| Flip rate across three test runs | 3.85% (j43) |
| Majority accuracy | 92.31% (24/26); not kept because it did not improve accuracy |
| Formatting/length movement | 7.69% (j02 and j34) |

The first run missed j02’s unsupported line number and j20’s unsupported public-route claim. Majority voting kept both mistakes. j02 changed on the list version; j34 changed on both list and long versions. Flipped IDs are in eval/judge/for_a_person.txt. To reduce formatting sensitivity, I would strengthen the instruction to ignore presentation and repeated wording, then validate that new judge separately without tuning on test judgments.

Correction uses (p + TNR − 1)/(TPR + TNR − 1), clipped to [0,1], with refusal when |TPR + TNR − 1| ≤ 0.1. This judge clears that guard. The interval uses 2,000 test-item resamples with recorded p fixed. Because p and observed TPR are both 1, all usable resamples correct to 1; the collapsed interval does not establish perfect real-world quality.

| Source system | Test items | TPR | TNR |
|---|---:|---:|---:|
| claude-haiku-5-5 | 13 | 100% (8/8) | 80% (4/5) |
| claude-sonnet-5-5 | 13 | 100% (9/9) | 75% (3/4) |

The judge passed one bad output from each system. Sonnet’s false-positive share is slightly higher, but four versus five negative examples is too small to establish a systematic preference.

All required calls completed: 26 tuning judgments, three 26-item test passes, 52 format/length variants and 20 recorded comments. The revised evaluation cost $0.431297 at configured prices. One interrupted test pass resumed only its missing items, preserving earlier judgments. The course checker awards 80/80 automated points with no integrity flags; report grading remains separate.

## AI assistance

I used OpenAI Codex to help write and debug the code, generate results tables, and run automated checks. For the written answers, AI helped me understand what the questions were asking, break down the concepts, interpret my results and their implications, and brainstorm and draft responses.