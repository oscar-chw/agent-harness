# Node 1 — Persist and bind automatic State packets for cold pickup

plan: v3-memory-checkpoint-20261117
gate: `PYTHONPATH=src python3 -m pytest -q tests/test_board_automatic.py tests/test_v3_board_followups.py tests/test_v3_workplace_board.py tests/test_operational_idle_recovery.py tests/test_session_memory_protocol.py tests/test_task_control_bridge.py tests/test_board_hooks.py tests/test_operational_context.py`
ctx: src/agent_harness/shared_board.py,src/agent_harness/mcp/server.py

## Attempt 2026-11-17T07:03:16Z — agent@redacted-host — 5s — exit 0

```
........................................................................ [ 54%]
............................................................             [100%]
132 passed in 5.74s
```
