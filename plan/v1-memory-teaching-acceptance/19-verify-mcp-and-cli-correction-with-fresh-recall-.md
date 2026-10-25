# Node 19 — Verify MCP and CLI correction with fresh recall and legacy readback

plan: v1-memory-teaching-acceptance
gate: `PYTHONPATH=src python3 -m pytest -q tests/test_v1_learning_loop.py -k 'skill_manage_correct or cli_correct_procedure or legacy_procedure_database'`
ctx: src/agent_harness/mcp/server.py

## Attempt 2026-10-25T09:28:20Z — local-runner — 1s — exit 0

```
...                                                                      [100%]
3 passed, 32 deselected in 1.54s
```
