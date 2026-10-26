# Node 12 — Suppress an explicitly rejected learned procedure

plan: v1-memory-teaching-acceptance
gate: `PYTHONPATH=src python3 -m pytest -q tests/test_v1_learning_loop.py -k explicit_negative_procedure`
ctx: src/agent_harness/procedures.py

## Attempt 2026-10-25T08:53:47Z — local-runner — 1s — exit 0

```
.                                                                        [100%]
1 passed, 29 deselected in 1.04s
```
