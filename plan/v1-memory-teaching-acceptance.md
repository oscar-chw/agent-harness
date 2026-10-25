## goal: Qualify the CPU memory correction and teaching-to-method hold boundary without model calls

Done-condition: the memory, teaching-source, explicit negative-cue and correction/withdrawal checks pass with their controls; the configured CPU suite exits 0 on the final source, and lint, diff and privacy checks pass. No claim of native model transfer.

## analysis

Observed: a superseded historical memory receipt omitted an explicit unusable marker; the supplied test reproduced a KeyError. Separate procedure drafts require two task-input hashes, but may count one copied source observation twice. Done when: the command above passes with both failure-first regressions, while unverified procedures remain dormant.

## research

existing: `src/agent_harness/project_memory.py`, `src/agent_harness/procedures.py`, `tests/test_v1_learning_loop.py`, `content/skills/work-loop/SKILL.md` and the public v1 acceptance matrix already provide source receipts, draft validation and gates. The patch at the reviewed SHA fixes the historical label. Distinct task-input hashes alone do not prove distinct source observations; distinct source bytes are a necessary CPU check, not semantic relevance or independent native qualification.

## plan

1. Preserve the red historical-memory regression, apply the minimal patch, and gate affected memory tests.
2. Freeze a negative with different task files but the same copied source observation; require a distinct-source positive control, then make the smallest validator change.
3. Gate affected tests, Ruff, diff check and privacy scan. Stop if a gate repeats the same failure; no `plan run`, model call, install or rollout.
The user's existing autonomous-work authorization covers this bounded reversible source work; there is no pending user decision in this graph.

## verification

- Historical-memory negative: `KeyError: usable_for_current_decisions` before the patch; the affected memory gate later passed 71 tests.
- Teaching-source negative: a copied source observation was accepted before the validator change; the distinct-source positive control and combined gate later passed 100 tests.
- Linked-worktree negative: `plan new` tried `/plan` when `.git` was a file; the focused regression passed after root detection changed. An initial combined test command named a nonexistent test file and exited 4; the corrected affected command passed.
- Supplemental CPU tests for procedure, Codex-hook, legacy-promotion and vendored work-graph behavior: 55 passed in 76.00s.
- Clean-commit baseline `13fc76f98d9b7572fbf3b211a42c5df1cf83f23a`: `HARNESS_STAGING_PYTHON=/opt/homebrew/bin/python3.11 PYTHONPATH=src python3 -m pytest -q tests ./eval` exited 0 with 1334 passed, 2 skipped, 2 xfailed in 360.86s. This is source evidence, not an installed/native runtime check.
- Explicit-negative test failed before the matcher change because "Do not use archive recovery" injected that method. Four direct negative phrasings and an unrelated-warning positive control then passed. Final affected gate: 54 passed in 21.84s. Final-source configured CPU gate: 1335 passed, 2 skipped, 2 xfailed in 364.76s, exit 0. Native model effectiveness remains untested.
- Correction tests were red before code: no `procedures.correct` or MCP action. The first implementation exposed a read-only legacy-store failure (`no such table: procedure_corrections`), repaired without mutating the legacy store. Core, MCP/CLI, and concurrent-retry gates then passed; affected lifecycle/recall gate passed 59 tests in 22.28s.
- First correction-source full suite failed: MCP tools 4629 bytes exceeded the fixed 4600-byte cap. The description was shortened by 51 bytes without changing the cap; focused context budget passed 7 tests, and the rerun full suite passed 1340 tests, 2 skipped, 2 xfailed in 363.21s (exit 0). The failed attempt remains in node 22's record.
- Native actor isolation, independent grader provenance, model transfer and rollout: NOT_RUN or BLOCKED by their separate acceptance boundaries.

## continuation

The next non-model lifecycle check is deliberately narrow: an explicit instruction not to use a procedure must not cause that procedure to be injected by lexical overlap. A warning about an unrelated target must still allow the relevant offline method. Failure-first test, smallest matcher change, affected tests, final CPU suite, lint and privacy are separate gates. No unattended `plan run` or model worker is authorized here.

## correction continuation

An explicit correction names the old source-bound method and a replacement candidate. The safe result is one auditable link, old advice withdrawn, replacement proposed, no fresh-session recall of either until independent promotion, and no duplicate replacement under concurrent retries. Invalid replacement data must leave the old row unchanged and produce an explicit error so the caller can roll it back separately. These are CPU lifecycle checks, not native model learning evidence.

- [x] 1. Analyse the observed defect and bounded done-condition | gate: python3 src/agent_harness/workgraph/phase_check.py v1-memory-teaching-acceptance analysis
      2026-10-25T08:40:22Z exit 0 in 0s [730c08b7] — phase analysis: OK (47 words)
- [x] 2. Research existing source and disconfirming evidence | needs: 1 | gate: python3 src/agent_harness/workgraph/phase_check.py v1-memory-teaching-acceptance research
      2026-10-25T08:40:26Z exit 0 in 0s [15f8596d] — phase research: OK (54 words)
- [x] 3. Freeze acceptance tests and plan the CPU checks | needs: 2 | gate: python3 src/agent_harness/workgraph/phase_check.py v1-memory-teaching-acceptance plan
      2026-10-25T08:40:29Z exit 0 in 0s [7618e43b] — phase plan: OK (303 words)
- [x] 5. Label superseded historical memory unusable | needs: 3 | ctx: src/agent_harness/project_memory.py | gate: PYTHONPATH=src python3 -m pytest -q tests/test_project_memory_claim_support.py tests/test_operational_context.py tests/test_memory_transport.py tests/test_operational_state.py tests/test_v1_recovery.py
      2026-10-25T08:40:42Z exit 0 in 6s [529e5903] — .......................................................................  [100%] / 71 passed in 5.70s
- [x] 6. Refuse two episodes copied from one source observation | needs: 5 | ctx: src/agent_harness/procedures.py | gate: PYTHONPATH=src python3 -m pytest -q tests/test_v1_learning_loop.py -k two_task_inputs_one_observation
      2026-10-25T08:41:08Z exit 0 in 0s [a95f75a0] — .                                                                        [100%] / 1 passed, 28 deselected in 0.40s
- [x] 7. Verify the combined memory and teaching slice | needs: 6 | gate: PYTHONPATH=src python3 -m pytest -q tests/test_project_memory_claim_support.py tests/test_v1_learning_loop.py tests/test_operational_context.py tests/test_memory_transport.py tests/test_operational_state.py tests/test_v1_recovery.py
      2026-10-25T08:41:34Z exit 0 in 17s [a3b8dafc] — ........................................................................ [ 72%] / ............................                                             [100%] / 100 passed in 17.77s
- [x] 11. Verify linked-worktree plan-root behavior | needs: 7 | gate: PYTHONPATH=src python3 -m pytest -q tests/test_plan_component.py -k 'not vendored_suite'
      2026-10-25T08:42:05Z exit 0 in 1s [7819885f] — ................                                                         [100%] / 16 passed, 14 deselected in 1.42s
- [x] 8. Lint the changed Python files | needs: 7,11 | gate: python3 -m ruff check src/agent_harness/project_memory.py src/agent_harness/procedures.py src/agent_harness/workgraph/plan.py tests/test_project_memory_claim_support.py tests/test_v1_learning_loop.py tests/test_plan_component.py
      2026-10-25T08:42:08Z exit 0 in 0s [e857c711] — All checks passed!
- [x] 9. Screen the candidate tree for private content | needs: 8 | gate: bash scripts/secret-scan.sh --tree-only
      2026-10-25T08:42:13Z exit 0 in 2s [057fcc92] — SECRET-SCAN: PASS
- [x] 10. Reject malformed diffs | needs: 9 | gate: git diff --check
- [x] 12. Suppress an explicitly rejected learned procedure | needs: 10 | ctx: src/agent_harness/procedures.py | gate: PYTHONPATH=src python3 -m pytest -q tests/test_v1_learning_loop.py -k explicit_negative_procedure
      2026-10-25T08:53:47Z exit 0 in 1s [ec2afd46] — .                                                                        [100%] / 1 passed, 29 deselected in 1.04s
- [x] 13. Check fresh recall and lifecycle controls | needs: 12 | gate: PYTHONPATH=src python3 -m pytest -q tests/test_v1_learning_loop.py tests/test_v1_prompt_recall.py tests/test_procedure_independence.py
      2026-10-25T08:54:13Z exit 0 in 22s [e6fe08ac] — ......................................................                   [100%] / 54 passed in 21.84s
- [x] 14. Run the configured CPU suite on the final source | needs: 13 | gate: HARNESS_STAGING_PYTHON=/opt/homebrew/bin/python3.11 PYTHONPATH=src python3 -m pytest -q tests ./eval
      2026-10-25T09:00:32Z exit 0 in 364s [69368a2e] — ........................................................................ [ 96%] / ...........................................                              [100%] / 1335 passed, 2 skipped, 2 xfailed in 364.76s (0:06:04)
- [x] 15. Lint the changed matcher and tests | needs: 14 | gate: python3 -m ruff check src/agent_harness/procedures.py tests/test_v1_learning_loop.py
      2026-10-25T09:00:42Z exit 0 in 0s [e857c711] — All checks passed!
- [x] 16. Screen the public candidate tree | needs: 15 | gate: bash scripts/secret-scan.sh --tree-only
      2026-10-25T09:00:49Z exit 0 in 2s [057fcc92] — SECRET-SCAN: PASS
- [x] 17. Reject malformed final diff | needs: 16 | gate: git diff --check
- [x] 18. Atomically withdraw old method and propose linked correction | needs: 17 | ctx: src/agent_harness/procedures.py | gate: PYTHONPATH=src python3 -m pytest -q tests/test_v1_learning_loop.py -k correct_procedure_atomic
      2026-10-25T09:28:13Z exit 0 in 0s [05893eb4] — .                                                                        [100%] / 1 passed, 34 deselected in 0.37s
- [x] 19. Verify MCP and CLI correction with fresh recall and legacy readback | needs: 18 | ctx: src/agent_harness/mcp/server.py | gate: PYTHONPATH=src python3 -m pytest -q tests/test_v1_learning_loop.py -k 'skill_manage_correct or cli_correct_procedure or legacy_procedure_database'
      2026-10-25T09:28:20Z exit 0 in 1s [36c3812c] — ...                                                                      [100%] / 3 passed, 32 deselected in 1.54s
- [x] 20. Verify concurrent correction retries cannot fork versions | needs: 19 | gate: PYTHONPATH=src python3 -m pytest -q tests/test_v1_learning_loop.py -k concurrent_correction
      2026-10-25T09:28:23Z exit 0 in 0s [05893eb4] — .                                                                        [100%] / 1 passed, 34 deselected in 0.36s
- [x] 21. Run affected lifecycle and recall tests | needs: 20 | gate: PYTHONPATH=src python3 -m pytest -q tests/test_v1_learning_loop.py tests/test_procedure_independence.py tests/test_v1_prompt_recall.py
      2026-10-25T09:28:50Z exit 0 in 22s [62eb41d0] — ...........................................................              [100%] / 59 passed in 22.28s
- [x] 22. Run configured CPU suite on correction source | needs: 21 | gate: HARNESS_STAGING_PYTHON=/opt/homebrew/bin/python3.11 PYTHONPATH=src python3 -m pytest -q tests ./eval
      2026-10-25T09:35:04Z exit 1 in 359s [325a3649] — =========================== short test summary info ============================ / FAILED tests/test_context_budget.py::test_each_part_within_its_cap[tools] - A... / 1 failed, 1339 passed, 2 skipped, 2 xfailed in 359.41s (0:05:59)
      2026-10-25T09:35:34Z First full gate failed: MCP tools 4629 bytes exceeded 4600-byte cap. Shortened skill_manage description by 51 bytes; focused context-budget suite now 7 passed. Rerun full gate on corrected source.
      2026-10-25T09:41:40Z exit 0 in 363s [22d20ab9] — ........................................................................ [ 96%] / ................................................                         [100%] / 1340 passed, 2 skipped, 2 xfailed in 363.21s (0:06:03)
- [x] 23. Lint correction code and tests | needs: 22 | gate: python3 -m ruff check src/agent_harness/procedures.py src/agent_harness/mcp/server.py src/agent_harness/cli.py tests/test_v1_learning_loop.py
      2026-10-25T09:41:48Z exit 0 in 0s [e857c711] — All checks passed!
- [x] 24. Screen public candidate tree after correction | needs: 23 | gate: bash scripts/secret-scan.sh --tree-only
      2026-10-25T09:41:54Z exit 0 in 2s [057fcc92] — SECRET-SCAN: PASS
- [x] 25. Reject malformed correction diff | needs: 24 | gate: git diff --check
      2026-10-25T08:42:16Z exit 0 in 0s [da39a3ee] — (no output)
      2026-10-25T09:00:52Z exit 0 in 0s [da39a3ee] — (no output)
      2026-10-25T09:41:56Z exit 0 in 0s [da39a3ee] — (no output)
