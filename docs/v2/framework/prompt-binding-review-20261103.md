# Prompt-binding correction review — 3 November 2026

Verdict: **CHANGES_REQUESTED — one P1 functional regression.** Static source and
test-source review only. No tests/native calls/model calls/runtime edits or
activation performed. Root's reported72affected passes and rejected constant-
binding mutant remain main-owned evidence; this review does not certify them.

## P1: Persist the new binding in actual execution receipts

Location: `src/agent_harness/launch.py:512`–`:513` (result projection), with
consumers `launch.py:301` and `method_control.py:36`.

`prepare()` now computes `prompt_sha256`, and both the resume preflight and method
feedback correctly require that value to match the freshly prepared prompt.
However, `execute()` copies only schema/request_sha256/context_sha256/
memory_receipts/method_policy from `prepared` into `result`. The subsequent
`result.update(...)` never adds prompt_sha256, and the exact result is written
as the receipt at lines538–540.

Consequently every real receipt emitted by the corrected execution path is
missing the new binding. For an unchanged valid failed/named invocation, a
subsequent execute(...resume_receipt=...) gets None for the prior binding and
rejects recovery as changed context; method_control.decide(...receipt_path=...)
likewise rejects it as stale. This is not the intended refusal of legacy
unbound evidence: newly generated current receipts are also unbound. It blocks
normal automatic recovery and completed-artifact failed-gate feedback.

The new tests build prior receipts from launch.prepare() plus status fields,
so they retain prompt_sha256 and do not traverse execute -> saved receipt ->
resume/method decision. Existing execution-result tests do not assert this
new persistence requirement. A constant-binding mutant on prepare therefore
does not detect the missing downstream field.

Smallest correction: include the prepared prompt binding in execute's returned
and saved result projection. Keep context_sha256 data-only and keep legacy
missing-binding refusal; do not loosen either comparison to accept None.

Required main-owned regression (specified, **NOT_RUN** here): use a disposable
stub transport, call real prepare/execute to produce a FAILED or TIMEOUT receipt
with a valid named thread, read the saved JSON and require its prompt_sha256 to
match prepare. Feed that actual saved receipt to decide and unchanged native
resume preflight; it must remain usable. Then change PROMPT_PREFLIGHT with the
same request/source and require rejection before native lookup. Retain the
adaptive-policy positive control and truly legacy-unbound negative case; rerun
the original affected gates. No native model is needed for this boundary check.

## Other scoped observations

The data-vs-instruction identity split itself is coherent in the inspected code:
context remains comparable across existing/adaptive preparation, the prepared
prompt hash incorporates the policy text, and decide reconstructs with the
recorded method_policy rather than assuming existing. No additional concrete
finding in the scoped read. This does not certify full sent-prompt, inherited
native history, performance, authority or installed behavior.

## Inspected source identities

Observed shared-tree hashes, not a frozen release or worker test result:

- `src/agent_harness/launch.py`: `bfc38c1ff54171e2312c239bc9e8eb1f1f74d134bc07def685f4c864db170810`
- `src/agent_harness/method_control.py`: `f3cc51acd4ee3f4f1fbcf7ed139c5ea87e0c432078e0ad15c54f0208343fe93b`
- `tests/test_prompt_binding.py`: `e03d37e0ab9830e88f8d925e889ee87836471668d693b5f172ce2d54ea13022c`
