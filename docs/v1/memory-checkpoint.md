# First v1 memory checkpoint — 26 October 2026

Development starts from `0774a11` (Studio 0.9.1.dev0 candidate). This worktree is
separate; the live package is unchanged. See [architecture](architecture.md),
[acceptance limits](ACCEPTANCE-MATRIX.md), and the work graph in
`plan/v1-memory-foundation.md`.

## Evidence, before and after

- **Scoped FTS relevance:** another project's cached documents changed a valid
  result from 0.48 to 0.40; at a fixed 0.45 threshold it disappeared. FTS document
  frequency and ranking now use current-scope evidence before top-k truncation.
- **Candidate truncation:** with 120 own-scope documents, adding unrelated-scope
  cache changed which 50 candidates survived. The fix streams matching scoped
  sections into a bounded result heap; foreign cache cannot change this set.
- **Peer correction:** without FTS, a reader reused its in-memory ranker after a
  peer had already indexed changed terms. It now invalidates on SQLite data
  version or live-scope changes. This is a same-backend connection test, not a
  claim of arbitrary client/runtime concurrency correctness.
- New regression/control suite plus existing MCP cases: **41 passed**. Cache
  inventory tests: **4 passed**. Combined MCP/cache/context checks: **52 passed**.
- Three isolated mutants restored global frequency counts, the global candidate
  cutoff, or stale fallback caching. Each failed its intended regression. The
  unmutated controls passed. See the machine-readable probe results in the plan.
- Independent bounded review found no actionable must-fix issue; its 9 focused
  tests and disposable WAL read-only probe passed. Main-loop verification remains
  the authority. Final full source gate: **1360 passed, 2 skipped, 2 xfailed**;
  privacy scan and isolated install demo passed. The original failures and rerun
  receipts remain in the plan. No live deployment is implied.

The first complete suite failed on two existing skip-policy checks because the
new test had introduced an unapproved FTS skip. The test now explicitly requires
FTS for its FTS-specific arm, consistent with the other new FTS regression; the
fallback arm still runs. Existing skip checks were not changed. Focused rerun:
11 passed, 99 deselected. The earlier collection error was fixed by explicitly
setting `PYTHONPATH=src` in the new plan gates; its failure is retained.

## Cost and limits

A deliberately broad 600-document query, seven warm repetitions, measured median
29.82 ms on the baseline and 100.85 ms on the candidate. Both returned five hits
and 1,600 serialized bytes. This is a latency regression from scoring the complete
scoped matching set rather than an unsafe shared-statistics prefilter. It is
recorded as a tradeoff, not a speed or token gain. The retained heap is bounded;
scoring time still grows with the number of matches. This one synthetic fixture
does not establish typical latency, actual model tokens, or task quality.

The cache inventory opens SQLite read-only, reports aggregate metadata, and never
prunes or prints source text. Current-scope cache, retained outside-discovery cache,
session rows, allocated pages and free pages are distinguished. Missing and
unreadable stores are different states. SQLite may maintain ordinary WAL reader
metadata. Outside-current-discovery entries may belong to other active clients;
the report is not an eviction permit.

The installed doctor's oversized-index failure remains. No live compaction,
retention change, cache purge, deployment, held-out model trial or skill promotion
was performed. Remaining work includes measured retrieval performance at larger
scales, mixed-backend cache coherence, strong source-change identity, safe cache
maintenance, actual cross-client recovery, and the native evaluation boundary.
