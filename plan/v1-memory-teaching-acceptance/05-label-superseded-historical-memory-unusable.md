# Node 5 — Label superseded historical memory unusable

plan: v1-memory-teaching-acceptance
gate: `PYTHONPATH=src python3 -m pytest -q tests/test_project_memory_claim_support.py tests/test_operational_context.py tests/test_memory_transport.py tests/test_operational_state.py tests/test_v1_recovery.py`
ctx: src/agent_harness/project_memory.py

## Attempt 2026-10-25T08:40:42Z — local-runner — 6s — exit 0

```
.......................................................................  [100%]
71 passed in 5.70s
```
