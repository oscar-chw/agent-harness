# Node 5 — SETTLEMENT IMPLEMENTATION: src/agent_harness/settlement.py + scripts/check_settlement.py + pipeline --settle opt-in + tests/test_settlement.py

plan: v3-settlement-plugin-loop
gate: `/usr/bin/python3 -m pytest -q tests/test_settlement.py && /usr/bin/python3 .harness-work/v3-settlement-plugin-loop/check_settlement.py`
ctx: (none)

## Attempt 2026-11-11T02:49:44Z — agent@redacted-host — 0s — exit 0

```
.................                                                        [100%]
17 passed in 0.18s
settlement master check — 4 checks, 0 bad
  OK    real scan: 18 settled, 3 open, 0 failed (verification modes: direct, inverse-redacted)
  OK    intact skeleton: 7 settled, 0 failed
  OK    fabricated done: reported failed, exit 1 (unsettled ≠ settled)
  OK    tampered receipt: verification failed, exit 1
VERDICT: PASS (real plans settle; fabricated-done and tampered-receipt controls refuse)
```
