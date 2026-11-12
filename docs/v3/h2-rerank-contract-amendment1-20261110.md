# H2 rerank contract — Amendment 1 (post-arm-1, pre-arm-2): common-direction correction

2026-11-10. ADDITIVE amendment to docs/v3/h2-rerank-contract-20261110.md. The
original contract is byte-unchanged (sha256 ffa56b11…, still bound in the
inputs receipt); where this amendment and the original disagree, THIS document
governs plan/v3-h2-reranking nodes 7–8. It is written AFTER arm 1's run and
BEFORE arm 2 exists in any form, and cites only the arm-1 artifact plus the
pre-existing v2 PoC record.

## Arm-1 result (recorded, disconfirmed as contracted)

Artifact: `.harness-work/v3-h2-reranking/eval-h2-arm1-20261110.json`
(sha256 `0a46fd1c02abf4489ec226ac12932e8b26164bf05dc21edaea94b7f0952e436a`),
hash-bound to freeze e55ccdc2… / corpus af6af281… / GloVe be4367dd… /
contract ffa56b11…, deterministic across two passes, usage zero.

- b1 RECOVERED: rank 9 → 5 (top-5 criterion met). The semantic signal exists.
- But six baseline-passing queries regressed out of their windows: a1 2→6,
  a2 1→9, b3 3→7, d1 3→9, d2 1→4, d3 1→8. Class pass rates: A 3/3→1/3,
  D 3/3→0/3, B 3/4→3/4, C 3/3, E 2/2.
- Aggregates: recall@5 0.9333→0.6000, MRR 0.8185→0.4249, precision@5
  0.2133→0.1200.
- F unchanged: f1 top cosine 0.9225, f3 0.9178 — both far ABOVE tau=0.50, so
  the miss rule never fires; 7 and 10 hits still reported; false positives
  still 2.
- Root cause, recorded in the artifact's pre-registered separation
  diagnostic: every top cosine is compressed into [0.798, 0.969];
  max F top cosine (0.9225) EXCEEDS the min answerable top cosine (0.7982);
  `separable_at_some_threshold: false`. The v2 PoC documented this exact
  failure mode: uncentered GloVe mean-pools share a large common direction,
  so raw cosines cannot discriminate on this corpus.
- Latency was fine (rerank-stage p95 0.132 ms ≪ 100 ms; total p95 38.7 ms)
  and determinism held — the failure is the raw-cosine scoring function,
  not the engineering.

Verdict on arm 1 (pure raw-cosine rerank + tau=0.50): DISCONFIRMED as
contracted. This is a recorded experimental result, not a gate failure to
rerun.

## Arm 2 (pre-registered before its first run): common-direction-corrected cosine

Identical pipeline to arm 1 with ONE change, aimed at the diagnosed cause:
both query and page vectors are centered by subtracting the SAME corpus mean
vector m = mean of the 133 hash-bound cached page vectors (rounded to 6dp,
recorded in the arm-2 artifact). No other change: same candidates (FTS5 k=10,
baseline-identical), same tokenizer, same ordering (-cosine, baseline_rank),
same determinism and latency requirements. No new inputs; the cache is
reused unchanged (centering is a deterministic eval-time transform of it).

Arm-2 pass rules (fixed here, before any arm-2 numbers exist):

- Ranking: b1 expected page rank ≤ 5; every baseline-passing A/C/D/E query
  still passes its frozen class rule; E successor above superseded;
  determinism across two passes; rerank-stage p95 ≤ 100 ms.
- Miss rule: NO numeric threshold is pre-set (centering rescales cosines;
  the v2 prior 0.50 applies to raw cosine only). The pre-registered RULE is:
    * Let maxF = max top-cosine over the F queries and minAE = min top-cosine
      over the 15 answerable queries (top cosine = cosine of the rerank
      rank-1 page), all computed BEFORE any miss rule is applied.
    * Separability criterion (falsifiable): gap = minAE − maxF must be
      STRICTLY positive. If gap ≤ 0, arm 2's miss-rule arm is DISCONFIRMED
      and reported with both distributions — no post-hoc rescue.
    * If gap > 0: TAU2 = round((maxF + minAE) / 2, 6), recorded in the
      artifact. With TAU2 applied: f1 and f3 must report 0 hits, f2 must
      stay at 0, and no answerable query may be suppressed.
  The threshold is a data-derived EVAL finding by a fixed rule (its
  production selection, with proper validation, is deferred to H3); the
  GATE is the existence of the gap, which cannot be fudged.
- F ranking diagnostics (trap-page rerank ranks) recorded either way.

If arm 2 fails its ranking rules, H2's rerank family (page-level mean-pool
GloVe cosine, raw or centered) is disconfirmed with two arms of evidence and
the summary says so.
