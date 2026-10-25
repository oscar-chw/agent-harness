## goal: Qualify the CPU memory correction and teaching-to-method hold boundary without model calls

Done-condition: `PYTHONPATH=src python3 -m pytest -q tests/test_project_memory_claim_support.py tests/test_v1_learning_loop.py tests/test_operational_context.py tests/test_memory_transport.py tests/test_operational_state.py tests/test_v1_recovery.py` exits 0, with the new same-source negative and distinct-source control; lint, diff and privacy checks also pass. No claim of native model transfer.

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
- Native actor isolation, independent grader provenance, model transfer and rollout: NOT_RUN or BLOCKED by their separate acceptance boundaries.

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
      2026-10-25T08:42:16Z exit 0 in 0s [da39a3ee] — (no output)
