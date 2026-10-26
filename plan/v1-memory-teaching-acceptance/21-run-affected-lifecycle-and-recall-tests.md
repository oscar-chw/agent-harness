# Node 21 — Run affected lifecycle and recall tests

plan: v1-memory-teaching-acceptance
gate: `PYTHONPATH=src python3 -m pytest -q tests/test_v1_learning_loop.py tests/test_procedure_independence.py tests/test_v1_prompt_recall.py`
ctx: (none)

## Attempt 2026-10-25T09:28:50Z — local-runner — 22s — exit 0

```
...........................................................              [100%]
59 passed in 22.28s
```
