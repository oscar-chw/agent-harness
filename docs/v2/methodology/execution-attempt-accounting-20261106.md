# Execution attempts retain their usage

This is a source-only accounting correction, not accepting learning or an
efficiency result. No installation, native inference or promotion is performed
by this change. Original node 42 remains open.

The controller previously started each run's execution totals from zero. A new
run could therefore forget a failed earlier trial. A received native response
could also fail a source/boundary/answer check before its usage was recorded.

The controller now commits a consumed attempt in its database before invoking
the native client. On return, it retains the native receipt and commits its hash
before grading or checking whether the candidate and sources are still current.
Final grading and usage accounting are separate: a wrong answer or rejected
model boundary does not erase otherwise complete provider-reported usage.

## What is counted

- A series is project-local and identified by the sorted development input
  hashes. Renaming a candidate or case, changing a retry's model or moving the
  suite does not reset it. Distinct canonical inputs are a different series.
- Current candidate calls plus known preparation cost form the current cost.
  All known earlier trial arms in that series are conservatively charged as
  candidate-selection/retry overhead. They never inflate the current paired
  baseline allowance. This is a conservative accounting policy, not a measured
  comparison between harnesses.
- Prepared but unconsumed runs are not charged. Consumed runs without complete
  usage stay explicitly unknown. Cached input is included in total input.
- Pinned receipts and completed results are checked against the controller's
  database. Altered evidence prevents another invocation. Legacy runs use their
  original database-bound observations; absent ungraded usage stays unknown.
- The database journal survives a missing final result. There is an unavoidable
  crash interval between receiving/writing a response and committing its hash.
  A file left in that interval is retained but **unbound**, so it remains unknown;
  accepting its bytes as proof would remove the integrity check.

`usage_complete` stays false and `promotion` stays `NOT_GRANTED`. Wider root,
review, orchestration and maintenance costs remain unqualified. This journal
does not replace the separate native counter-window reader or close the complete
campaign accounting boundary.

## Checks and limits

The initial accounting suite reproduced 11 failures. The corrected controller
passed the 63-case initial affected set, then the 139-case broader set. Added
review/edge controls bring the dedicated accounting suite to 15 passing tests.
Six broken copied implementations were rejected with an unchanged-source
positive control (14 tests at that snapshot). These are deterministic protocol
fixtures, not native effectiveness or token-savings measurements.

The independent source reviewer identified the receipt-to-journal crash interval.
The root reproduced it and checked that it remains unknown and blocks completion;
the suggestion to trust an unpinned receipt was deliberately not adopted.

One new distinct-series fixture initially reused stale task hashes. Existing
validation correctly refused it. The fixture now explicitly prepares the new
inputs before correction; the original stale-input refusal tests remain intact.

The first full run had 2,355 passes and one malformed-packet test failure (plus
two skips and two expected failures). Its fixture receipt was a `TIMEOUT`, not
an accepted packet. A controlled 2.2-second startup delay reproduced the false
failure with the old two-second allowance. That test now allows five seconds;
the same delayed malformed packet still raises at protocol stage 1 before
account access. All rejection assertions remain. The separate real-timeout
test keeps its 0.15-second deadline. The full failed report is retained; the
original pytest temporary receipt expired during later pytest cleanup. The
controlled before/after receipts and affected 89-test pass are retained.

The corrected full gate was rerun with the compatible installed wheel builder:
**2,357 passed, 2 skipped, 2 expected failures**, with six pre-existing marker
warnings retained. Its 2,361 case identities match the current collected suite.
Root qualification is `PASS_SOURCE_EXECUTION_ACCOUNTING_ONLY` in
`.harness-work/execution-accounting-20261106/root-review.json`.

Evidence: `.harness-work/execution-accounting-20261106/` contains original failure
reports, affected checks, copied-mutation logs and the root qualification receipt.
No full-v2, publication, cross-device, official-benchmark or superiority claim
follows from these checks.
