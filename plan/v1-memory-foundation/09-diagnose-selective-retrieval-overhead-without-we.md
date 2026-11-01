# Node 9 — Diagnose selective retrieval overhead without weakening freshness or scope

plan: v1-memory-foundation
gate: `PYTHONPATH=src python3 -m pytest -q tests/test_kb_scope.py tests/test_retrieval_canaries.py tests/test_kb_performance_cache.py`
ctx: src/agent_harness/mcp/kb.py

## Attempt 2026-10-26T10:29:06Z — local developer — 1s — exit 0

```
...........                                                              [100%]
11 passed in 1.19s
```

## Attempt 2026-10-26T10:35:00Z — local developer — 1s — exit 0

```
...........                                                              [100%]
11 passed in 1.05s
```

Public copy: local author/path identifiers redacted; original retained privately.
Original SHA-256: `da26dd8e77177fc5b613d8efefc0e19aff83c3feb12450366ae5b4b2cb02a567`. Test outcomes are unchanged.
