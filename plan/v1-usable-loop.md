## goal: Integrate a usable project workflow and evidence-bound skill preparation into the v1 candidate

Done-condition: focused CLI/lifecycle tests and the configured full source gate pass, templates are packaged, and existing memory/promotion boundaries stay intact. This source slice does not declare v1 deployed or model learning qualified.

## analysis

The user wants one useful composite harness with retained memory and skill improvement. Existing plan, vault, procedure and operational engines already own state. The shipped plan prompt instead sends a multi-step plan to a small state summary, and preparing a procedure requires manually computing source hashes. Fix these usability seams without replacing the underlying stores or activating unverified advice.

## research

existing: workgraph/plan.py, procedures.py, improve CLI, source-check workflow, project memory and operational state. Cursor Pstack architect/interrogate at c742dd61706fbacc1b95f1a20b7b988cf096ce6c and community port README at e397ed54d211a8040ffb46490322708d3536b1fe were read. Reuse bounded design sketches and executable review evidence as patterns; do not import mandatory model fan-out, startup routing hooks or another task store. No upstream code is copied.

## plan

1. Add a read-only preparation command that binds explicitly supplied project episode files and emits a candidate accepted by the existing draft API; add a read-only inspection command. Keep unsupported promotion refused.
2. Package task, worker, source-intake and skill-candidate templates; route the existing plan prompt to the durable graph. Provide one concrete code/research/learning walkthrough and a source-disposition note.
3. Run negative/positive controls, integration/lifecycle checks, full source checks and privacy review. Preserve old evidence, exact failure results and candidate-only limits. No installation, live store migration, guard edits or extra native recall calls.

- [x] 1. Prepare and inspect source-bound skill candidates without activating them | ctx: src/agent_harness/procedures.py | gate: PYTHONPATH=src python3 -m pytest -q tests/test_procedure_preparation.py tests/test_v1_learning_loop.py tests/test_procedure_independence.py
      2026-10-28T11:23:48Z exit 0 in 23s [1b9c17b5] — ........................................................                 [100%] / 56 passed in 22.97s
      2026-10-28T11:34:59Z exit 0 in 23s [b070b819] — .........................................................                [100%] / 57 passed in 23.55s
- [x] 2. Package coherent workflow templates and prove the documented local lifecycle | needs: 1 | ctx: content/prompts/plan.md | gate: PYTHONPATH=src python3 -m pytest -q tests/test_workflow_templates.py tests/test_content.py tests/test_context_budget.py
      2026-10-28T11:28:18Z exit 0 in 2s [d153f8a4] — ..............s..........                                                [100%] / 24 passed, 1 skipped in 0.96s
- [x] 3. Verify integrated candidate | needs: 1,2 | gate: bash scripts/check.sh
      2026-10-28T11:35:26Z exit 0 in 411s [533804be] — DEMO: PASS / CHECK: PASS / agent-harness guard blocked this: rm -r on ~ (the home directory). If it is really intended, ask the human to run it themselves.
      2026-10-28T11:43:35Z exit 0 in 416s [ac83fbf7] — DEMO: PASS / CHECK: PASS / agent-harness guard blocked this: rm -r on ~ (the home directory). If it is really intended, ask the human to run it themselves.
