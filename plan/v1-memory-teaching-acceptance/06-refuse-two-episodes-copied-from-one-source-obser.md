# Node 6 — Refuse two episodes copied from one source observation

plan: v1-memory-teaching-acceptance
gate: `PYTHONPATH=src python3 -m pytest -q tests/test_v1_learning_loop.py -k two_task_inputs_one_observation`
ctx: src/agent_harness/procedures.py

## Attempt 2026-10-25T08:41:08Z — local-runner — 0s — exit 0

```
.                                                                        [100%]
1 passed, 28 deselected in 0.40s
```
