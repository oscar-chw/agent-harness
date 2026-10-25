# Node 8 — Lint the changed Python files

plan: v1-memory-teaching-acceptance
gate: `python3 -m ruff check src/agent_harness/project_memory.py src/agent_harness/procedures.py src/agent_harness/workgraph/plan.py tests/test_project_memory_claim_support.py tests/test_v1_learning_loop.py tests/test_plan_component.py`
ctx: (none)

## Attempt 2026-10-25T08:42:08Z — local-runner — 0s — exit 0

```
All checks passed!
```
