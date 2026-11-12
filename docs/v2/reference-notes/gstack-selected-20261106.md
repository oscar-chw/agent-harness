# Gstack selected source review — 6 November 2026

## Scope and pin

**D.** This closes the selected-source gap for `garrytan/gstack`; it does not install, copy, activate, or review the whole framework. The narrow question was whether its evidence-bound review of a changed implementation suggests a useful mechanism for V2.

**D.** Reviewed upstream commit [`4b1a1152844abf3e0562fb72767856dcdd5ba331`](https://github.com/garrytan/gstack/commit/4b1a1152844abf3e0562fb72767856dcdd5ba331), current `main` at retrieval (commit timestamp 2026-11-06T07:02:54Z). The actual pinned [`LICENSE`](https://github.com/garrytan/gstack/blob/4b1a1152844abf3e0562fb72767856dcdd5ba331/LICENSE) is MIT, copyright 2026 Garry Tan. No upstream code is copied into our shipped implementation; selected unmodified analysis snapshots are retained privately with that licence.

## Observed mechanism

**C.** [`lib/ship-recheck.ts` lines 33–69](https://github.com/garrytan/gstack/blob/4b1a1152844abf3e0562fb72767856dcdd5ba331/lib/ship-recheck.ts#L33-L69) accepts a scoped re-review only for a bounded product-change carry on linear history against the same base. It refuses rewritten history, retargeted or legacy receipts, incomplete/unnamed paths, binary changes, missing or oversized moved-context sections, failed/empty range-diffs, and packets over 400 lines or 64 KiB. It hashes the exact review packet; `readRecheck` requires a clean record naming reader, original head, current head, packet hash, and (when context was composed) `range_base`.

**C.** [`bin/gstack-ship-receipt` lines 843–866](https://github.com/garrytan/gstack/blob/4b1a1152844abf3e0562fb72767856dcdd5ba331/bin/gstack-ship-receipt#L843-L866) constructs that packet from the range-diff, changed product-path diff, and any moved-base-context sections. It still refuses carry on deeper review depth or changed risk class (lines 895–906), and preserves full `/ship` as the route for blocking findings. [`lib/ship-patch.ts` lines 112–160](https://github.com/garrytan/gstack/blob/4b1a1152844abf3e0562fb72767856dcdd5ba331/lib/ship-patch.ts#L112-L160) classifies a path as context only where the branch's hunks are retained at the base-adjusted location; moved-context hunks enter the scoped packet and require a reader. This is evidence binding and bounded review, not automatic truth or source-authority transfer.

**C.** `test/ship-recheck.test.ts` covers eligibility refusals, byte/line caps, exact-record binding and stale hashes, end-to-end carry, changed risk class, and a mixed changed-path plus moved-context reproduction. The test itself points to `test/ship-receipt-carry-mixed.test.ts` for additional GST-1561 coverage; that file was outside this four-file review slice and is not represented as inspected.

**NOT_RUN.** No upstream test command or upstream code was executed. No comparative model-quality or efficiency experiment was run.

**M, source identity only.** The root fetched these four files and the licence independently at the pinned commit, reconstructed Git's blob hashes from their complete bytes, and matched all five returned identities. This verifies the selected material, not its behavior. Research-model overhead was not measured and is not treated as zero.

**C, boundary limit.** `readRecheck` checks that a nonempty reader name and clean verdict match the packet/head coordinates. That binds a record to inputs; it does not authenticate that the named model actually performed the review. Our learning controller must keep invocation provenance and full accounting checks rather than treating this record as promotion authority.

## Fit to the V2 contract and disposition

**C.** The useful mechanism to consider is a single bounded review packet whose digest and source/head coordinates are carried into a machine-checked reviewer record, with explicit refusal when the packet is incomplete, too large, or the risk class changes. It makes the review input auditable and prevents a clean verdict for one input from being reused for another.

**D.** V2's acceptance remains stricter: quality must be at least baseline **and** all-token use at most baseline, with full overhead counted. Gstack's local caps and hashes establish neither quality nor token savings. Its one-reader record is not a substitute for our independent machine-checkable gate or for authority in source files. Gstack's reviewed-worktree/base model also does not establish our file-first coordination or shared graph ownership.

**Decision — adapt as a design pattern only, deferred from implementation.** If a concrete V2 review handoff needs this seam, consider binding a bounded, complete evidence packet to its exact file/source revision and recording the reviewer result against that digest; retain our graph/file authority and refusal semantics. Adoption would require a paired check against the current workflow showing quality >= baseline and all-token <= baseline, plus negative controls for stale digest, missing packet parts, cap overflow, and changed risk/authority. Until then, no activation, skill promotion, or behavior change is authorized by this review.

## Selected primary files

Receipts and upstream file blob hashes are in `.harness-work/reference-gstack-20261106/`; it records the exact commit, license, selected paths, and retrieved blob hashes. Source line links above and below are pinned to that commit.

- [`lib/ship-recheck.ts`](https://github.com/garrytan/gstack/blob/4b1a1152844abf3e0562fb72767856dcdd5ba331/lib/ship-recheck.ts)
- [`lib/ship-patch.ts`](https://github.com/garrytan/gstack/blob/4b1a1152844abf3e0562fb72767856dcdd5ba331/lib/ship-patch.ts)
- [`bin/gstack-ship-receipt`](https://github.com/garrytan/gstack/blob/4b1a1152844abf3e0562fb72767856dcdd5ba331/bin/gstack-ship-receipt)
- [`test/ship-recheck.test.ts`](https://github.com/garrytan/gstack/blob/4b1a1152844abf3e0562fb72767856dcdd5ba331/test/ship-recheck.test.ts)
