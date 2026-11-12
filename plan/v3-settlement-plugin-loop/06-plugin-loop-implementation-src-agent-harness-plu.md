# Node 6 — PLUGIN LOOP IMPLEMENTATION: src/agent_harness/plugin_loop.py + scripts/admit_capability.py + docs/v3/jev/lever-pattern-adoption-20261111.json + candidate + registry + tests/test_plugin_loop.py

plan: v3-settlement-plugin-loop
gate: `/usr/bin/python3 -m pytest -q tests/test_plugin_loop.py && /usr/bin/python3 .harness-work/v3-settlement-plugin-loop/check_plugin_loop.py`
ctx: (none)

## Attempt 2026-11-11T03:05:07Z — agent@redacted-host — 0s — exit 0

```
..............                                                           [100%]
14 passed in 0.17s
plugin-loop master check — 5 checks, 0 bad
  OK    real admission: admitted, hash-bound, both records re-verify on disk (1 entry in registry)
  OK    intact skeleton: admitted, registry written
  OK    no REA record: refused at qualification, refusal registered, exit 1
  OK    below-threshold confidence: ESCALATED, refused, never auto-admitted
  OK    tampered REA record: refused at the declared hash
VERDICT: PASS (Lever pattern admitted with full receipts; no-REA, escalation and tamper controls refuse)
```
