# H2 rerank contract — pre-registered before any eval results

2026-11-10. Design + pass-rule freeze for plan/v3-h2-reranking nodes 5–8. No
eval has been run at the time of writing; the only measurements cited are the
pre-existing hash-bound artifacts baseline-20261110.json (H1 node 6) and the
v2 PoC results.json. Authored under the same convention as
docs/v3/h1-eval-query-design-20261110.md: pass rules are fixed here and may
only change by additive, evidence-cited amendment.

## Inputs (all hash-bound, all read-only)

- Corpus: `.harness-work/v3-h1-consolidation/frozen-corpus-20261110/` — 133
  pages, corpus sha256 `af6af2815cadc84b2b7ba589ef02a9b3e9d61937755b39106f7cbbe920a68781`.
  REUSED UNCHANGED from H1; no re-freeze, no edits.
- Queries: the 18 frozen queries in
  `.harness-work/v3-h1-consolidation/freeze-20261110.json` (classes A–F,
  per-query text sha256). Unchanged.
- Baseline: `.harness-work/v3-h1-consolidation/baseline-20261110.json`
  (in-process `agent_harness.mcp.kb.KB`, FTS5 porter unicode61, min_score
  0.15, k=10, over the same frozen corpus).
- Embeddings: GloVe 6B.100d at
  `.harness-work/v2-completion/paraphrase-semantic-20261110/glove.6B.100d.txt`,
  sha256 `be4367dd257eb945217234f16307c5c74236b648a222cc0b4ffd0dda6a3350b6`
  (pin from the v2 freeze; re-verified 2026-11-10). Already local; zero
  network; zero model tokens.

## Pipeline contract (the ONLY ranking change vs baseline)

1. Candidates: the baseline-identical in-process FTS5 hit list per query
   (same KB class, same backend, min_score 0.15, k=10, same frozen corpus).
   The reranker never adds or removes candidates before scoring; candidate
   membership of every expected page is asserted per query (audit: all 15
   answerable expected pages are inside the baseline k=10 pool, worst b1
   rank 9, so no full-corpus scan is part of the gated path).
2. Scoring: each candidate hit inherits its PAGE's cosine similarity
   `cos(meanpool(tokens(query)), meanpool(tokens(page)))`.
   - tokens: lowercase `[a-z0-9]+` (identical to the v2 PoC).
   - OOV tokens skipped and counted per text; a text with zero in-vocab
     tokens scores 0.0.
   - page vectors come from the hash-bound cache
     (`.harness-work/v3-h2-reranking/embeddings-cache-20261110.json`: per
     page — path, page sha256, text sha256, GloVe sha256, 100-dim vector
     rounded to 6 decimal places); query vectors are pooled at eval time
     from the same hash-verified GloVe file.
3. Final order: hits sorted by `(-cosine, baseline_rank)` — deterministic
   tie-break on the baseline rank; page rank = rank of the page's first
   occurrence. Rerank scores are reported alongside, never mixed with,
   lexical scores (different units; no numeric cross-comparison).
4. Honest-miss rule (pre-registered): if the top page cosine `< TAU = 0.50`,
   the eval path reports a MISS — zero hits. TAU is the v2 freeze's
   `a1_miss_rule` threshold, adopted BEFORE this eval; it is not tuned on
   H2 data. (v2 PoC evidence: true-pair cosines 0.75–1.00; the v2 negative
   control's top cosine stayed below 0.50.)

## Pass rules (pre-registered; baseline values cited from baseline-20261110.json)

- B1 recovery (the paraphrase fix): b1 expected page `igsl-remote-machine`
  rank ≤ 5 post-rerank (baseline rank 9, the only B miss).
- F improvement (the false-positive fix): for each of f1, f3 — post-rerank
  reported hits = 0 (miss rule fires), OR (reported hits < baseline count
  AND the baseline top-1 trap page is demoted from rank 1). Baselines: f1 =
  7 hits, top `igsl-gpu-box-hardware-state` @0.23; f3 = 10 hits, top
  `commit-a-sweeps-parallel-work` @0.56. f2 must stay at 0 hits. No F query
  may report MORE hits than its baseline count.
- A/C/D/E non-regression: every query passing at baseline still passes its
  frozen class rule post-rerank — A (a1,a2,a3) expected page top-3; B
  (b2,b3,b4) top-5; C (c1,c2,c3) top-5; D (d1,d2,d3) top-3; E (e1,e2)
  successor above superseded within top-10. Rank deltas are recorded per
  query; movement inside the passing window is allowed (the reranker exists
  to reorder), leaving the window is not.
- Latency budget: rerank stage (query tokenize + pool + cosine over
  candidates + sort + miss rule) p95 ≤ 100 ms per query, warm cache,
  measured over 18 queries × 7 repetitions on this machine under managed
  python3. One-time costs (GloVe parse, cache build, cache load) recorded
  separately, not gated.
- Determinism: two independent eval runs produce byte-identical per-query
  ranked lists (page order + rounded cosines).
- Usage: 0 model tokens, 0 native calls, 0 network.

## Disconfirmation criteria (written BEFORE results)

H2 is DISCONFIRMED if any of: b1 not top-5 post-rerank; OR f1 or f3 not
improved per the F rule AND the recorded cosine distributions offer no
honest explanation; OR any baseline-passing A/C/D/E query leaves its passing
window; OR p95 latency > 100 ms; OR repeated runs differ. Partial
disconfirmation is reported as such (e.g. b1 recovered but TAU cannot
separate F traps on this corpus → the miss-rule arm is disconfirmed while
the rerank arm stands — both stated with numbers).

## Pre-registered diagnostics (measurement, not gate)

- Separation: min top-cosine over answerable (A–E) expected pages vs max
  top-cosine over F queries; whether any threshold separates them.
- OOV rate per query/page (PoC convention).
- Candidate-pool membership of every expected page (asserted, recorded).
- Rank deltas per query vs baseline; recall@5 / precision@5 / MRR vs the
  baseline values 0.9333 / 0.2133 / 0.8185.

## Known limits (honest bounds, from the v2 PoC)

Static, non-contextual, English-centric embeddings; weak on code/CJK;
uncentered GloVe mean-pools share a common direction (arbitrary-pair cosines
~0.6), so TAU=0.50 may under-separate F traps here — a valid negative
result if it occurs, reported with distributions. This arm is a lower bound
on semantic retrieval, which is the correct conservative shape for the gate.

## Mutation controls (node 8, pre-registered)

1. Shuffled embedding weights (global permutation of all weight values,
   seed 20261110 — the PoC-proven method) must FAIL the b1 top-5 recovery
   criterion (red), real weights must pass it (green).
2. Wrong GloVe sha256 in the binding must make the pipeline REFUSE to run
   (red); the correct hash runs (green).
