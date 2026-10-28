## goal: v1.1 first development milestone - observed model families and bounded daily discovery

Scope: source development only. No production release, native config writes or live scheduler activation. User authorized Luna low per-link research and higher-effort synthesis, plus evidence-backed learning; family names do not establish performance rankings.

existing: checked routing.py and its gate-bound progression, procedures.py source-bound draft/correct and held promotion, selfupdate.py release installation (different responsibility), local Codex registry, official https://learn.chatgpt.com/docs/models, and five-link Luna-low research. Reuse those seams rather than replacing memory or building an unverified self-edit loop.

Budget: first batch <=5 links, <=12 web operations, one Luna-low scout, <=5 minutes scout, no paid API, no model benchmark campaign. Current quota telemetry reports percentages only; remaining tokens UNKNOWN. Implement 12k pause / 10k reserve only for reliable integer token telemetry. No repeated fetching for inaccessible links in this batch.

- [x] 1. Qualify four-family registry and bounded discovery state | gate: python3 -m pytest -q tests/test_discovery_cycle.py tests/test_routing.py tests/test_procedure_preparation.py
      2026-10-28T14:19:26Z exit 0 in 7s [8ffa4c0f] — ..........................................                               [100%] / 42 passed in 7.01s
- [x] 2. Verify source integration and document activation limits | needs: 1 | gate: bash scripts/check.sh
      2026-10-28T14:26:25Z exit 0 in 418s [180619a0] — DEMO: PASS / CHECK: PASS / agent-harness guard blocked this: rm -r on ~ (the home directory). If it is really intended, ask the human to run it themselves.

Next release work remains distinct: independently reviewed host scheduler activation, sandboxed proposal evaluation, evidence-backed promotion/rollback integration, broader source triage, matched quality/token evals. This bounded plan does not mark those complete.

## Authorized continuation

The owner clarification includes a nonprivileged read-only daily source timer, with actual activation/readback/disable. Initial full check passed 1455 tests before later review repairs; that is retained historical evidence, not qualification of the subsequent scheduler diff.

- [x] 3. Qualify fetch deadline fixes and reversible scheduler lifecycle | needs: 2 | gate: python3 -m pytest -q tests/test_discovery_cycle.py tests/test_daily_schedule.py tests/test_routing.py tests/test_procedure_independence.py
      2026-10-28T14:37:29Z exit 0 in 6s [863714e8] — ................................................                         [100%] / 48 passed in 6.26s
      2026-10-28T14:45:25Z exit 0 in 10s [5b858482] — ..................................................                       [100%] / 50 passed in 6.29s
      2026-10-28T15:04:09Z exit 0 in 6s [54e9a2d8] — .....................................................                    [100%] / 53 passed in 6.62s
- [x] 4. Qualify final source after review | needs: 3 | gate: bash scripts/check.sh
      2026-10-28T14:44:24Z exit 0 in 414s [b135495c] — DEMO: PASS / CHECK: PASS / agent-harness guard blocked this: rm -r on ~ (the home directory). If it is really intended, ask the human to run it themselves.
      2026-10-28T14:52:21Z exit 0 in 415s [99333f11] — DEMO: PASS / CHECK: PASS / agent-harness guard blocked this: rm -r on ~ (the home directory). If it is really intended, ask the human to run it themselves.
      2026-10-28T15:11:03Z exit 0 in 413s [add95c31] — DEMO: PASS / CHECK: PASS / agent-harness guard blocked this: rm -r on ~ (the home directory). If it is really intended, ask the human to run it themselves.

- [x] 5. Read back current scheduled runner after refresh and reversible lifecycle | needs: 4 | gate: python3.11 "${HARNESS_V11_LOCAL_VERIFY:?local readback script is required}"
      2026-10-28T15:12:31Z exit 0 in 0s [8fbc9a1d] — RUNTIME PASS: current source and rotation match active pinned runner; native exit0, daily86400, audit retained

Local native gate needs the retained read-only host verification script via HARNESS_V11_LOCAL_VERIFY; missing evidence fails. This is host qualification, not a portable CI requirement or all-device rollout.
