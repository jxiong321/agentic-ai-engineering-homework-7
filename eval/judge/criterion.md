# Evidence grounding criterion

Authorship: Codex prepared this criterion and the reference labels. Human validation is pending.

Question: Does the comment cite only evidence that is in the issue or in what RepoMind's tools returned?

Pass means every concrete evidence claim is supported by the supplied issue or tool results. A search excerpt can support the fact it actually shows, even without a full-file read. Ordinary deductions from shown code and reported examples are allowed. A proposed change, recommendation, or explicitly uncertain diagnosis is not a claim that a test or deployment occurred. Judge grounding, not whether the fix is optimal or the tracker outcome is complete.

Fail means at least one concrete evidence claim is unsupported or contradicts the supplied evidence:

1. File or document contents attributed to a source whose relevant text was never returned. Merely seeing an import or path does not establish its contents.
2. A line number not supplied by a matching search hit. File reads have no line numbers; do not invent them or count an excerpt as the full file.
3. A claimed test, CI check, browser reproduction, benchmark, or runtime observation without its result. Saying tests were not run does not cancel a separate claim that CI passed.
4. An exact error, log message, HTTP response, count, timing, or customer-data fact absent from the issue and returned evidence.
5. A maintainer quotation, earlier discussion, decision, or historical event that was never supplied.
6. A function, constant, behavior, default, route, or data-flow connection contradicted by the shown code or asserted without supporting evidence. A relative router path does not establish its public mount point.
7. A completed write, test, fix, merge, or deployment without a confirming tool result. An opened draft proposal does not prove the implementation changed.
8. A claim supported only by the agent's own proposed PR body or other self-authored text. Tool acknowledgement confirms that text was posted, not that its technical assertions are true.

Scope clarification: a diagnostic explanation grounded in specific symptoms and returned code may use ordinary programming knowledge; it need not quote dependency internals. It must not invent an additional observation, quotation, source, or confirmation. If the evidence is insufficient to establish a concrete evidence claim, fail it. Ignore verbosity, formatting, politeness, and source model identity.
