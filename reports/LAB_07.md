# Assignment 7 · Evaluating RepoMind

Status: Parts B and C are complete. Part A has model-authored reference work requiring student review. Part D has a working judge and completed model calls, but human labeling, the student's criterion, and human validation are pending. This is not a final submission.

## A · Golden tasks and trace review

The first 40 recorded runs in alphabetical order were reviewed. The student wrote the first observation during a guided walkthrough; Codex wrote the other 39 and the decision/failure columns at the student's request. These notes are not independent human labels. Twenty recorded runs remain unreviewed, so no saturation claim is made.

| Observed category | Runs | Example and first wrong step |
|---|---:|---|
| Turn limit before complete triage | 8 | agent-issue-4601-s01-425ff8: stops after its fourth investigation call, before required writes |
| Explanation error only | 2 | agent-issue-4602-s01-e6b5b0: issues_comment gives an inaccurate Kathmandu UTC-minute explanation |
| Question treated as a bug | 2 | agent-issue-4604-s01-bab837: issues_label |
| No failure found | 17 | agent-issue-4606-s01-b2d4e2 |
| Wrong or unverified file | 3 | agent-issue-4626-s01-238030: pulls_open commits to an unverified dashboard connection |
| Acted when no change was needed | 5 | agent-issue-4628-s01-f4f549: issues_label |
| Required writes missing | 3 | direct-issue-4620-s01-cc942a: issues_comment ends triage without the other writes |

Observed decisions were 37 act and 3 refuse. An interrupted investigation counts as an attempted act, not an intentional stop. Explanation-only problems are separate from tracker-state failures. Full notes and their authorship are in eval/golden/trace_notes.csv and reports/trace_note_authorship.json.

The golden set contains 28 tasks, selected to cover code fixes, documentation, questions, refusals and no-action cases. Expectations come from maintainer resolutions or the source explanation recorded in each task, rather than copying the agent's answer. Misleading suggested files and error wrappers preserve wrong-file cases. Spam, a template test, an already-fixed issue, a private security handoff, a duplicate and a withdrawn request cover different no-action reasons. Codex authored these expectations; student review remains necessary.

| Stratum | Tasks | Expected decisions |
|---|---:|---|
| routine | 9 | 9 act |
| unusual | 5 | 5 act |
| adversarial | 8 | 5 act, 3 refuse |
| should_not_act | 6 | 6 stop |

Unusual is the thinnest stratum: one of its five tasks moves a single-sweep score by 20 percentage points. Repeated sweeps produce finer averages but do not make these five tasks representative of every unusual issue. Reference routes are a convention: one issue read for stop; read, search, file read, label and comment for questions; add a draft PR for file changes. They are not measured minimums. The checker was reconciled against 45 recorded end states, with explanation-only errors kept separate (reports/recorded_reconciliation.json).

## B · Evaluation harness

The exporter selects finished runs on the fixed subset, checks their tracker end states with eval.grounded, computes trajectory counts from traces, and writes results/A.jsonl and results/B.jsonl. Duplicate task/sweep pairs and mixed configurations are rejected. Scripted plumbing tests use separate files and are not experimental evidence. A comment is not proof that a label or PR exists.

Pass@k and pass^k use combinatorial counts from each task's passes; pass^k is not pass@1 raised to k. Means and sample SDs are computed over sweep means, and the gain interval uses the two arms' sweep variance. The trajectory metrics count extra steps, precision, recall, repeated calls and unused returns; no judge is needed for those counts. The table in Part C is the harness output for the actual experiment.

Verification: 123 unittest tests ran successfully, with 2 skipped. The supplied slide-27 trace and the course checker's independent metric cases pass. The test runner emitted existing unclosed trace-file ResourceWarnings, but no test failed.

## C · Does a plan reduce repeated calls?

Arm A is planned and arm B is agent, both using Gemini gemini-3.5-flash-lite with the same tools and default switches. The measure is exact repeated tool calls with canonicalized arguments; gain is B minus A, so a positive gain favors the plan. Every run uses empty memory, scripted approvals, and a 100,000-token budget. There are eight fixed tasks, two per stratum: g01, g11, g02, g10, g03, g05, g06 and g20. Each arm ran five sweeps, 40 runs total. No arm implementation was changed during the comparison.

The subset and golden set were pushed in 74d7514 before the first run. After three sweeps per arm, only SDs and costs were inspected. A's observed SD was 0.330719; B's was zero, so the sizing calculation used one count divided by eight tasks, 0.125, for B. Three sweeps give only a rough spread. The smallest useful gain was set to δ = 0.5 repeated calls per task.

n ≥ (0.330719² + 0.125²) × (2.80 / 0.5)² = 3.92, rounded up to 4 sweeps per arm. The pilot mean sweep cost was $0.058391 for A and $0.077254 for B, or $0.067823 pooled. The sized comparison price was 4 × 2 × $0.067823 = $0.542580. Five sweeps were run as required; their measured total cost was $0.672314, using the repository's configured pricing.

Threshold commit 046df5f was pushed before either fourth sweep. The interval's lower bound must exceed bar = 0, and every stratum's gain must be at least group_floor = 0. k = 3. The prediction favored A by 0.5 repeated calls per task, with the largest benefit on adversarial tasks, because a plan was expected to resist distracting investigation paths.

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

The claim **fails** on this model and subset: the overall upper interval bound, −0.448, is below the preregistered bar of zero. Every stratum's mean gain is negative as well. This is not a claim about all models or all tasks.

The prediction missed its direction and magnitude: A was expected to save 0.5 repeats, but added 0.8. planned-g01-s01-82c147 repeats empty-argument issue reads and searches after malformed plan arguments. The predicted adversarial advantage also missed: adversarial has the largest gap, but against A (−1.2). planned-g05-s02-523bfa repeatedly calls reads/searches with empty arguments, while the corresponding agent run completes its permitted question triage without exact repeats. An agent can still waste turns on different searches while scoring zero exact repeats; this metric does not mean zero wasted investigation.

A is cheaper ($0.007053 versus $0.009755 per run) and has a higher measured tracker score (30% versus 22.5%). B is about 38.3% more expensive with no measured accuracy advantage. These descriptive scores do not establish a statistically significant accuracy difference. The low pass^3 values show unreliable completion even when a task sometimes passes. A's score also includes three accidental no-action successes: planned-g06-s03-6c9b3b, planned-g06-s04-5a3ff7 and planned-g06-s05-6dddbf call no tools because plan validation fails. Their unchanged tracker correctly passes the no-action expectation, but they did not demonstrate recognizing spam. B has zero no-tool runs.

### Where failed runs first went wrong

All 59 failed runs are listed in reports/LAB_07.json, with call indices and explanations in reports/first_failure_review.json. The following grids count those reviewed boundaries. Recovered errors are not automatically the first causal failure. An unrecovered invalid input, an ungrounded file commitment, or an unwanted action is recorded where it occurs. When investigation ends without a clear earlier wrong call but required writes are missing, first_wrong is stop. last_good names the immediately preceding call, or start before the first call; it is not a claim that every earlier call was ideal.

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

The biggest cell is A's start → issues_read, 15 runs. The immediate defect is local (missing arguments), with an upstream plan-serialization cause and a structural validation gap: malformed escaped args_json becomes {} in agent/diff.py:20, and ways/planned.py:555 skips filling when no keys remain. In planned-g01-s01-82c147 the first plan already contains malformed escaped JSON. The executor then proceeds to labels despite missing evidence. This diagnosis is based on the saved plan and call records, not a completed repair experiment.

To test it, use an isolated replay of that run's earliest saved checkpoint before a write, preserving its plan/results and idempotency keys. Decode and validate each step's arguments before allowing execution, then compare missing-argument refusals and final tracker facts. Because the original issue-read failure predates that checkpoint, also replay the saved plan from a clean tracker to test the initiating read. An unchanged checkpoint resume alone cannot undo the already-failed read. A successful replay should eliminate the empty-input calls and prevent unsupported writes; any remaining wrong-file or missing-comment failure would show another cause. Original measurement runs should remain untouched.

B's largest cell is issues_read → issues_label (10 runs): both no-action tasks are labeled on every sweep. That is a structural mismatch between an always-triage behavior and an explicit stop outcome. Only an external tracker check exposes it; a fluent comment saying no change is needed can coexist with an unwanted label.

## D · Judge implementation and student review pending

At the student’s updated request, Codex filled all 60 labels and reasons in eval/labels/labels.csv as drafts for review. reports/review-comments.html displays these drafts alongside each comment, issue and tool evidence, with a separate reviewed checkbox. Existing student edits are preserved in browser storage. It exports labels.csv and criterion notes. The drafts are model-authored; subsequent student review does not establish independent human labeling as required by the handout.

The split is 8 examples, 26 tuning and 26 test items, balanced across the two source systems, selected using seed 7 and IDs/system names only. It was committed separately in 45fb66c before judge implementation. It preceded human labeling, which departs from the handout's listed sequence.

A provisional model-authored criterion, example prompt and reference decisions were prepared before the student's reply. The reference decisions are archived in reports/model_reference and have now also been copied into the review worksheet at the student’s request. The author read outputs from all splits while preparing those materials, so the demonstration is not an independently held-out human validation. Its numbers are archived separately in reports/judge_model_reference.json and are not reported as human TPR or TNR here.

The provisional criterion covers unseen file/document contents, unsupported line numbers, tests or runtime observations that never occurred, invented errors/counts, fabricated quotations, contradicted code/data-flow claims, unconfirmed completed work, and circular reliance on the agent's own PR text. Search excerpts support what they actually show; proposed work is distinct from completed work; grounded diagnostic reasoning is allowed. These were model-authored distinctions, not findings from a student's labeling process. The student's own criterion and any resulting relabeling changes still need to be recorded.

The judge uses Gemini gemini-3.5-flash-lite through the metered client, with settings.yaml, the criterion, prompt and split protected by the digest in eval/judge/frozen.json. No prompt change was made after the tuning run. The prompt embeds only examples-set j14 and j47; no tuning or test item is embedded. This is a fixed configured model identifier, not proof that the provider cannot change the weights behind that identifier.

All model calls are complete: 26 tuning judgments, three 26-item test passes, 52 formatting/length variants, and 20 recorded agent comments. These observations do not require human labels: the judge passes 20/20 recorded comments; the repeat flip rate is 3.85% (j43); and the formatting/length movement rate is 3.85% (j34). Flipped IDs are in eval/judge/for_a_person.txt.

Human TPR, TNR, corrected pass rate, bootstrap bounds, per-system rates, and whether majority voting improves accuracy remain pending. None can be established from an unlabeled worksheet. The correction code clips to [0,1], refuses |TPR + TNR − 1| ≤ 0.1, and uses 2,000 bootstrap item resamples. Its interval conditions on the observed recorded pass rate; it does not resample that separate comment sample.

After the student finishes, compare their own criterion and example decisions with the provisional prompt. A changed criterion, prompt or settings defines a new judge: preserve these demonstration artifacts and validate the replacement. Do not tune against the test judgments. The author’s earlier exposure to all fixture outputs is a limitation that a clean new held-out set would address. For any formatting movement, a possible future revision is a stronger instruction to ignore presentation and repeated text and evaluate each factual claim once; that revision must be validated again, not silently substituted into these results.

## AI assistance and submission status

Codex implemented the evaluation code and tests, authored 39 trace observations and the golden expectations, ran the experiments, reviewed the 59 failure boundaries, and prepared this report and review page. The first trace observation came from the student. Provisional model reference labels and criterion are explicitly separated from the pending human review. Automated tests and course checks verify calculations and artifact integrity; they do not certify human authorship or independent judgment.

The subset and threshold were pushed in the required order. The comparison is complete. The final lab-07 tag is withheld until the remaining human-review requirements and final check are resolved. This report should not be submitted as a claim that those requirements are already complete.

The last course check before restoring the draft labels was 70/80 automated points, with no integrity flags. Human-dependent rates remain unset pending review. This is a progress check, not a final grade.
