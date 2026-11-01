## goal: Test cold-session handoff discovery and proactive checkpoint behavior under the installed protocol

Done-condition: independently grade cold-context native readers/writers against frozen project artifacts, retain failures, and distinguish tested client behavior from universal compliance. No invented guarantee that all providers obey prose.

## analysis

The owner requests actual automatic compliance, not installation proof. A fresh model session is the test subject; root owns its acceptance. Existing shared-session-memory is complete, with broader model compliance explicitly unmeasured. A reader must find that boundary without the parent conversation or supplied answers. A separate writer fixture tests proactive record creation during bounded implementation.

## research

existing: session-memory skill, global native pointers, task checkpoint/status, context_hook and operational brief, Codex lifecycle hooks, native harness-quick agent profile. Official hook reference: https://learn.chatgpt.com/docs/hooks . Lifecycle hooks can inject context or check artifacts but do not prove semantic correctness or all-client execution. No guard/trust bypass or FYP maintenance retry is included.

## plan

At most two fresh native CLI subjects (one reader, one writer), using installed settings and no parent conversation; root freezes outcomes first and verifies artifacts. The automatic routing policy returned SHADOW/dispatch_allowed=false; it is not enabled and supplies no dispatch authority. These are directly user-requested root-owned evaluation processes, not delegated production work. No model/effort override. Allow 90 seconds per subject before closing; included ordinary quota only, no paid extra usage/reset. Check remaining quota before each; pause native calls at <=50 percent remaining. No model-performance ranking. A failed canary stays FAIL; no hidden retries. Further repairs must preserve the independent oracle and existing authority.

- [x] 1. Independently qualify cold reader outcome | gate: python3.11 "${HARNESS_MEMORY_NATIVE_READER_GATE:?private grader required}"
      2026-10-29T09:09:36Z exit 0 in 0s [b2a0dc9c] — PASS: fresh reader identifies completed slice, outstanding limits and next action from unchanged project evidence
- [ ] 2. Independently qualify proactive writer artifacts | needs: 1 | gate: python3.11 "${HARNESS_MEMORY_NATIVE_WRITER_GATE:?private grader required}"
      2026-10-29T09:12:57Z exit 1 in 0s [55dd9ca0] — assert runtime['exit'] == 0 and not runtime['timed_out'], 'native writer did not complete in budget' / ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ / AssertionError: native writer did not complete in budget
- [x] 3. Qualify database-independent handoff inspection | needs: 1 | gate: python3 -m pytest -q tests/test_handoff_readback.py tests/test_session_memory_protocol.py tests/test_content.py tests/test_context_budget.py
      2026-10-29T09:21:19Z exit 0 in 1s [31b883b9] — ...................s..........                                           [100%] / 29 passed, 1 skipped in 1.22s
- [x] 4. Verify integrated inspection repair | needs: 3 | gate: bash scripts/check.sh
      2026-10-29T09:27:58Z exit 1 in 398s [b823b952] — =========================== short test summary info ============================ / FAILED tests/test_harness_best.py::TestV041b::test_every_skip_names_an_environmental_reason / 1 failed, 1478 passed, 2 skipped, 2 xfailed in 397.85s (0:06:37)
      2026-10-29T09:36:02Z exit 1 in 397s [a2391a3f] — == secret scan / plan/session-memory-native/02-independently-qualify-proactive-writer-artifacts.md:11:  File "$HOME/Documents/Codex/2026-10-29/session-memory-native/grade_writer.py", line 13, in <module> / SECRET-SCAN: FAIL (see lines above)
      2026-10-29T09:44:59Z exit 0 in 417s [9e34249b] — DEMO: PASS / CHECK: PASS / agent-harness guard blocked this: rm -r on ~ (the home directory). If it is really intended, ask the human to run it themselves.
- [x] 5. Read back installed inspection repair against the native writer artifact | needs: 4 | gate: python3.11 "${HARNESS_MEMORY_LOCAL_READBACK_GATE:?private readback required}"
      2026-10-29T09:45:11Z exit 0 in 0s [188b032c] — PASS: installed CLI finds unchanged native peer packet without opening global task storage / Original native writer timeout/registration gate remains FAIL

## Native observation and repair scope

Reader completed in 86.325 seconds without parent history: original graph and
handoff read in its tool trace; completed slice and unverified broader behavior
correctly separated. Reader gate PASS. Writer independently implemented the
frozen four-case function, ran its graph gate, and spontaneously wrote a full
per-session packet without a save reminder. Its bounded process exceeded 90
seconds (91.53 total after interruption); the global registry was unavailable
inside its workspace boundary. Original writer gate remains FAIL, not weakened.
No bypass or alternate access to the refused global store was attempted.

Repair: expose bounded read-only project packet inspection through `harness
handoff --task <task>` without opening a global database. Local packet discovery
does not imply registry registration, completion proof or broader access. Keep
the original writer failure distinct from this independently tested component.
The two native invocation budget is exhausted; no hidden model retry is included.

## Separate repair qualification slice

After the source repair and installed readback, run at most one additional
90-second cold reader on the writer fixture, with the frozen peer packet/test
hashes as oracle. This is a new producer-to-consumer transfer case on the repaired
version, not a rerun or regrading of the failed writer. Keep the original failure
and strict writer acceptance unchanged. No new writer, paid usage, config or
trust changes; check ordinary quota and pause at <=50 percent remaining.

- [x] 6. Qualify native peer-to-peer handoff transfer after repair | needs: 5 | gate: python3.11 "${HARNESS_MEMORY_PEER_READER_GATE:?private peer grader required}"
      2026-10-29T09:48:33Z exit 1 in 0s [59cdd190] — AssertionError: evidence citation paths did not resolve to frozen packet and graph
      2026-10-29T09:48:44Z exit 0 in 0s [f9fce5f1] — PASS: cold native peer reads another session packet, identifies done work and the correct next action / Scope: one native producer/consumer case; universal enforcement remains unproven

