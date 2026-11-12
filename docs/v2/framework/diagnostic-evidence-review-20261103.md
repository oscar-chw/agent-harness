# Diagnostic exit-evidence correction — bounded review

3 November 2026. Verdict: **NO ADDITIONAL MATERIAL FINDING in the inspected
correction; original guessed-exit defect addressed at this source boundary.**
Static source/test-source and retained-log review only. No tests, native/model/
Claude calls, runtime/test/config/guard edits, network or Git mutations. Root
owns final verification, any correction and activation. This does not qualify
all diagnostic receipt fields, actual process authenticity or stable v2.

## Source correction and preserved controls

`diagnose.py:26,48–57` now accepts a complete leading reported exit header,
including zero/nonzero/negative codes, and labels it `tool_output_header`.
Absent, malformed suffix or nonleading headers yield NOT_OBSERVABLE; successful
tool delivery no longer supplies exit0 and an error flag no longer supplies
exit1. Tool result status is a separate field. A reported0 contradicting an
error flag yields NOT_OBSERVABLE/CONFLICTING_TOOL_RESULT. `explain` reports
uncertain tool errors visibly rather than silently dropping them. Existing
Codex missing-exit observations remain unknown.

The module now describes these values as reported observations and explicitly
rejects treating a text header as authenticated process telemetry or independent
proof of sound acceptance. Rendering counts remain observations derived from
that labelled record; main task/graph verification is still a separate authority.

The new test source checks plain/empty output, malformed and nonleading markers,
unknown exit with a visible tool error, explicit0/1/-9 headers and provenance,
and contradictory error-plus-zero. Explicit failed-check/missing-rules/unloaded
rules/unknown usage/redaction/compact rendering controls remain in the old suite.
This is source inspection, not a reviewer execution result or mutation proof.

## Original test correction is justified

The old helper emits plain “3 passed” and “ok” without exit evidence. Expecting
exit0 or301passes from that output contradicted both the existing module's
Nothing-is-guessed rule and the user requirement for observable exits. Main
preserved failing evidence: before.log records10new failing cases; the original
gate after source correction records2failures/18passes, including the invalid
301passed expectation. Current tests preserve uncertainty instead of accepting
those fabricated passes: the initial session is unknown and the long fixture
expects0passed/0failed/301unobserved while retaining its compactness assertion.

Although the activation description proposed changing a success fixture to an
explicit0 header, the actual diff leaves that original fixture unknown and
places explicit-header positive controls in test_diagnose_evidence.py. This
preserves valid positive and negative coverage and does not weaken a requirement.
It is a permissible demonstrated wrong-check correction under the later user
override; no new user approval is required for the old unsupported expectation.
Main still must rerun the original gate and affected checks. This reviewer did
not run them or assert a final green result.

## Traceability and limits

The frozen requirements audit must remain unchanged. Its direct actual-exit and
unknown-telemetry clauses are H05-10.12 and H05-10.19. H05-10.15 is worker-handoff
continuity, so this patch alone must not be used to qualify that broader clause.
This numbering note corrects the activation pointer, not an acceptance oracle.

No complete project/task/session/source/permission/worker/usage receipt, cold+
resume+Codex-under-Claude demonstration or instrumentation-overhead benefit is
established by this narrow source repair. Other existing capture/log consumers
are outside this assigned diff; no claim their exit inference changed follows.
Explicit text headers remain forgeable text, with the provenance label retained.

## Inspected identities

Observed shared-tree/retained-file hashes; root must bind the exact candidate
it verifies. Historical logs are retained results, not a test rerun by reviewer.

- `src/agent_harness/diagnose.py`: `c30e459d1d56987cf2223f3ddf947891f33bc2ef0d5246f5a113449b49d2278e`
- `tests/test_diagnose.py`: `4d5092e6b8c90df17b46f785ae4faaec36646e8f9114545841b59c50e6a16f04`
- `tests/test_diagnose_evidence.py`: `4e800cb55dc87031f052145f4799f3614a54e0043fc776004ddc76d70a6b50ea`
- `.harness-work/diagnostic-evidence/before.log`: `7f8a590863a5da3cbaba9b144fed78cea733017e20d13d7da6696f8447c9b2c6`
- `.harness-work/diagnostic-evidence/original-after-fix.log`: `bc72e8084b01fb7804bf351e7946ceb55c80957b30a9829525fbcc12ce4175d3`
