# Node 10 — Reconcile source denominator and native memory boundaries with bounded receipts

plan: v1-memory-foundation
gate: `PYTHONPATH=src python3 -m pytest -q tests/test_archive_sources.py tests/test_source_inventory.py tests/test_archive_reconciliation.py && python3 eval/check_source_reconciliation.py --inventory "${HARNESS_SOURCE_INVENTORY:?}" --report "${HARNESS_SOURCE_RECONCILIATION:?}"`
ctx: docs/v1/archive-checkpoint.md

## Attempt 2026-10-26T10:40:54Z — local developer — 0s — exit 0

```
...............................                                          [100%]
31 passed in 0.27s
{"admission": {"CANDIDATE_COPY_ONLY": 2405, "EXCLUDED_DERIVED_RECORDS": 85, "EXISTING_READER_BYTE_OFFSET_COVERED": 183, "EXISTING_READER_EVICTED": 520, "EXISTING_READER_STALE": 2, "EXISTING_READER_UNINDEXED": 2}, "complete_migration": false, "sources": 3197, "status": "RECONCILED_METADATA"}
```

Public copy: local author/path identifiers redacted; original retained privately.
Original SHA-256: `fb00cd67fad922dbf2048f4a78c9f570ab485a6da6e31b48043bc20a28ca9d27`. Test outcomes are unchanged.
