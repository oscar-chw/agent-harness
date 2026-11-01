# Node 1 — Prepare and inspect source-bound skill candidates without activating them

plan: v1-usable-loop
gate: `PYTHONPATH=src python3 -m pytest -q tests/test_procedure_preparation.py tests/test_v1_learning_loop.py tests/test_procedure_independence.py`
ctx: src/agent_harness/procedures.py

## Summary 2026-10-28T11:23:24Z — local operator

Initial CLI acceptance: 12 failed because prepare/inspect options were absent. Added read-only source hashing and inspection; focused CLI tests now 12 passed. No promotion or native-store edits.

## Attempt 2026-10-28T11:23:48Z — local operator — 23s — exit 0

```
........................................................                 [100%]
56 passed in 22.97s
```

## Summary 2026-10-28T11:34:35Z — local operator

Independent review found a prepared evidence path replaced by FIFO could hang draft revalidation. Main reproduced TimeoutExpired at 2 seconds. Nonblocking open plus fstat now rejects nonregular sources; affected lifecycle checks 57 passed. In-memory mutation removing candidate validation incorrectly accepted duplicate source evidence, while the real control refused it. One initial probe omitted PYTHONPATH and failed import; corrected probe passed. Source comparison and promotion boundaries unchanged.

## Attempt 2026-10-28T11:34:59Z — local operator — 23s — exit 0

```
.........................................................                [100%]
57 passed in 23.55s
```
