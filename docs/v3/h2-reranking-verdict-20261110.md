# H2 reranking — verdict

2026-11-10. plan/v3-h2-reranking node 9. All numbers re-derived from the
hash-bound artifacts by `.harness-work/v3-h2-reranking/check_h2.py` (exit 0);
artifacts: `eval-h2-arm1-20261110.json` (sha 0a46fd1c…), `eval-h2-arm2-20261110.json`,
`mutation-controls-h2-20261110.json`, `inputs-20261110.json`, all bound to
freeze e55ccdc2… / corpus af6af281… / GloVe be4367dd… / contract ffa56b11…
(+ amendment1 for arm 2). Zero model tokens, zero native calls, zero network.

## H2 verdict: DISCONFIRMED — on both pre-registered arms

The hypothesis — a bounded, offline, deterministic semantic rerank over the
FTS5 k=10 candidates improves paraphrase recall AND reduces negative-control
false positives WITHOUT regressing A/C/D/E — fails under both scoring
variants. Each arm satisfied at most one of the three legs:

| criterion (pre-registered) | arm1: raw cosine, tau=0.50 | arm2: centered cosine, separability rule |
|---|---|---|
| b1 recovered to top-5 (baseline rank 9) | YES (rank 5, cos 0.8875) | NO (rank 6) |
| f1 false positive reduced (baseline 7 hits, trap rank 1) | NO (7 hits; trap rank 4) | NO (7 hits; trap rank 3) |
| f3 false positive reduced (baseline 10 hits, trap rank 1) | NO (10 hits; trap rank 2) | NO (10 hits; trap rank 3) |
| f2 stays clean | YES (0 hits) | YES (0 hits) |
| A/C/D/E non-regression | NO — a1, a2, b3, d1, d2, d3 leave their windows | NO — same six queries |
| determinism (two passes byte-identical) | YES | YES |
| rerank-stage p95 ≤ 100 ms | YES (0.13 ms) | YES (0.62 ms) |

Per-class pass rates (baseline → arm1 → arm2):
A 3/3 → 1/3 → 1/3 · B 3/4 → 3/4 → 2/4 · C 3/3 → 3/3 → 3/3 ·
D 3/3 → 0/3 → 0/3 · E 2/2 → 2/2 → 2/2 · F 1/3 → 1/3 → 1/3.
Aggregates: recall@5 0.9333 → 0.6000 → 0.6667; MRR 0.8185 → 0.4249 → 0.3924;
precision@5 0.2133 → 0.1200 → 0.1333; F false positives 2 → 2 → 2.

## Why it failed (evidence, not speculation)

1. Whole-page mean-pooled GloVe cosine has almost no ranking discrimination on
   this corpus. Arm 1 compressed every top cosine into [0.798, 0.969] — the
   uncentered common direction the v2 PoC documented. Arm 2 (subtracting the
   corpus mean, amendment 1, pre-registered before it ran) spread scores to
   [0.25, 0.65] but did not make them *discriminate*: the same six queries
   regressed, and b1 fell back out (rank 6).
2. No honest-miss threshold exists in either arm. Arm 1: max F top cosine
   0.9225 > min answerable top cosine 0.7982. Arm 2: gap = −0.391 (f3 top
   0.6419 vs a1 top 0.2507), so the pre-registered separability rule yielded
   no TAU2 at all. The F traps are semantically *genuine* near-neighbours —
   gpu-box really is about hardware serials; commit-a-sweeps really is about
   commits. Topical similarity cannot express "this specific fact is absent".
3. The lexical signal carries real fact-level information that pure semantic
   ordering discards: class D (doctrine pages, distinctive vocabulary) went
   3/3 → 0/3 in both arms; class A 3/3 → 1/3. C (orphans) and E (supersedes)
   survived both arms — their pages are topically dominated by the query
   subject, where mean-pooling works.
4. The semantic signal is real but weak: arm 1 recovered b1 9 → 5, and the
   controls prove the recovery depends on the actual embeddings (shuffled
   weights: top cosine 0.417, miss fires, recovery gone; query-side variant
   rank 7, cosine −0.081).

## Engineering findings that stand regardless of the verdict

- Deterministic rerank eval path: two full passes byte-identical in both arms.
- Latency is a non-issue at this corpus size: rerank stage p95 0.13 ms (arm1)
  / 0.62 ms (arm2) vs the 100 ms budget; total per-query p95 ≈ 39 ms, dominated
  by the FTS5 candidate fetch (~24 ms p50), not embeddings. One-time GloVe
  load ≈ 5 s; cache build ≈ 0.8 s.
- The fixtures are the durable deliverable: hash-bound embedding cache
  (133 pages), two-arm eval runner, stdlib master check that re-derives every
  verdict, 25 unit tests, and 3 both-directions mutation controls (shuffled
  weights / wrong hash / tampered artifact) — all reusable for H3.

## What follows — H3 candidates (ranked by expected value)

1. H3-hybrid: lexical score primary with a bounded semantic tie-break/boost
   (or convex combination with a pre-registered weight). Arm-1 evidence says
   the semantic signal rescues b1 (9→5); the baseline says lexical ordering
   carries A/D. Combining them targets exactly the failure observed: neither
   signal alone suffices. H2's fixtures make this cheap to test honestly.
2. H3-granularity: section/snippet-level pooling instead of whole-page
   mean-pooling — doctrine pages (D) are diluted by page-level averaging.
3. H3-weighting: IDF/SIF-weighted pooling or top-principal-component removal
   (stronger common-component correction than the corpus mean).
4. F-class honesty is likely NOT a similarity problem at all — consider
   lexical evidence rules (top-score + margin) for miss detection; semantic
   similarity structurally cannot see absence.
5. Contextual embeddings only if a local runtime (torch/ollama) ever lands;
   out of scope today.

Recommendation: do NOT integrate this reranker into production kb.py; the
baseline lexical path stands. Proceed to H3-hybrid with these fixtures.
