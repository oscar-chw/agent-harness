## goal: V1 checkpoint — reliable scoped retrieval and observable cache ownership

Done-condition: `bash scripts/check.sh` exits 0 on this source, the scoped-retrieval negative/control tests are sensitive, and the architecture/evidence map preserves all unqualified claims. This is a bounded development checkpoint, not v1 release acceptance.

## analysis

Parent work is harness-v05 node 10 (vault/retrieval), with node 20 (scoped task responsibility) retained as a separate requirement. The historical parent gate names a missing test in another checkout and cannot establish this slice. Do not mark that parent complete from these tests. The deployed 0.9.1.dev0 package and its source checkout remain unchanged; work is in a separate v1 worktree.

Observed: shared FTS cache statistics include documents outside the current KB roots. Adding a different project's documents changed an unchanged scoped result from score 0.48 to 0.40. This can suppress a valid result at threshold 0.45. The live index also remains over budget; do not purge original evidence, compact the live database, raise a cap, or claim disk health fixed by retrieval repair.

## research

existing: KB's per-connection kb_live table already filters returned rows; fallback BM25 already uses only live rows. The FTS document-frequency counts and initial rank still use shared-table corpus statistics. Existing memory placement, source receipts, procedure hold gates, client adapters, source-evidence graph and acceptance matrix remain the foundation. New upstream links are candidates weighted by requirement relevance, evidence, marginal benefit, overlap, cost and dependencies; popularity is not evidence.

## plan

1. Freeze regression/control tests for cross-scope result stability, FTS candidate cutoffs and fallback behavior; repair only the retrieval seam.
2. Add a read-only cache inventory with synthetic tests distinguishing active KB, retained other-scope cache, session data and free pages. No source text, credentials, deletion or live compaction.
3. Reconcile architecture decisions and run affected/full source checks plus independent review. Keep actual client discovery, held-out quality/total-token gates, automatic learning and v1 rollout distinct.

Context note: the CLI is 66 KB; the node briefing keeps the small inventory module rather than injecting the entire CLI. The CLI changes only register cache-status and print its result.

Bounds: local CPU development and synthetic fixtures, one substantive checkpoint in roughly one hour. No additional model-evaluation campaign, native configuration change, deployment, main merge, server work or production data change. Failure twice with the same cause changes the approach.

- [x] 1. Make scoped retrieval independent of other cached projects | ctx: src/agent_harness/mcp/kb.py | gate: PYTHONPATH=src python3 -m pytest -q tests/test_kb_scope.py tests/test_mcp.py
      2026-10-26T08:05:58Z exit 2 in 0s [b754ffbc] — ERROR tests/test_kb_scope.py / !!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!! / 1 error in 0.24s
      2026-10-26T08:08:02Z exit 0 in 2s [1caf45c8] — .......................................                                  [100%] / 39 passed in 2.21s
      2026-10-26T08:10:33Z exit 0 in 2s [616b845e] — .........................................                                [100%] / 41 passed in 2.22s
      2026-10-26T08:25:32Z exit 0 in 2s [616b845e] — .........................................                                [100%] / 41 passed in 2.22s
- [x] 2. Report cache inventory without mutating source or database | ctx: src/agent_harness/cache_status.py | gate: PYTHONPATH=src python3 -m pytest -q tests/test_cache_status.py
      2026-10-26T08:14:40Z exit 0 in 0s [d19dd4a0] — ....                                                                     [100%] / 4 passed in 0.24s
      2026-10-26T08:25:32Z exit 0 in 0s [d19dd4a0] — ....                                                                     [100%] / 4 passed in 0.18s
- [x] 3. Run complete source verification on the integrated checkpoint | needs: 1,2 | gate: bash scripts/check.sh
      2026-10-26T08:31:51Z exit 1 in 379s [495e84b7] — FAILED tests/test_harness_best.py::TestV041::test_every_skip_in_the_suite_is_environmental / FAILED tests/test_harness_best.py::TestV041b::test_every_skip_names_an_environmental_reason / 2 failed, 1358 passed, 2 skipped, 2 xfailed in 378.84s (0:06:18)
      2026-10-26T08:40:43Z exit 0 in 387s [8699aaec] — DEMO: PASS / CHECK: PASS / agent-harness guard blocked this: rm -r on ~ (the home directory). If it is really intended, ask the human to run it themselves.
