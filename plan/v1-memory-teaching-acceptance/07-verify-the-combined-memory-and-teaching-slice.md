# Node 7 — Verify the combined memory and teaching slice

plan: v1-memory-teaching-acceptance
gate: `PYTHONPATH=src python3 -m pytest -q tests/test_project_memory_claim_support.py tests/test_v1_learning_loop.py tests/test_operational_context.py tests/test_memory_transport.py tests/test_operational_state.py tests/test_v1_recovery.py`
ctx: (none)

## Attempt 2026-10-25T08:41:34Z — local-runner — 17s — exit 0

```
........................................................................ [ 72%]
............................                                             [100%]
100 passed in 17.77s
```
