# Node 2 — Package coherent workflow templates and prove the documented local lifecycle

plan: v1-usable-loop
gate: `PYTHONPATH=src python3 -m pytest -q tests/test_workflow_templates.py tests/test_content.py tests/test_context_budget.py`
ctx: content/prompts/plan.md

## Summary 2026-10-28T11:28:16Z — local operator

Missing templates reproduced as 2 failures with one existing graph control passing. Added six on-demand templates, packaging and graph-based plan prompt. Template/content/context checks: 24 passed, 1 existing environmental skip. No global configuration or native memory edits.

## Attempt 2026-10-28T11:28:18Z — local operator — 2s — exit 0

```
..............s..........                                                [100%]
24 passed, 1 skipped in 0.96s
```
