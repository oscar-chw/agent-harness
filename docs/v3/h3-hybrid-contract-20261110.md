# H3 hybrid contract — pre-registered before any H3 results

2026-11-10. Design + pass-rule freeze for plan/v3-h3-hybrid nodes 5–8. No H3
eval has been run at the time of writing. Every number cited comes from the
pre-existing hash-bound artifacts baseline-20261110.json and
eval-h2-arm1-20261110.json. Same convention as the H1/H2 contracts: pass rules
fixed here; changes only by additive, evidence-cited amendment.

## Inputs (hash-bound, read-only, all reused — no new freeze)

- Corpus: `.harness-work/v3-h1-consolidation/frozen-corpus-20261110/`, 133
  pages, corpus sha256 `af6af281…`. Queries: the 18 frozen queries in
  `freeze-20261110.json` (sha e55ccdc2…). Baseline: `baseline-20261110.json`.
- H2 embedding cache `embeddings-cache-20261110.json` (GloVe 6B.100d,
  be4367dd…) and H2 arm-1 artifact (cosine cross-check source).
- NEW: `corpus-stats-20261110.json` — per-page token counts, token document
  frequencies, and per-page adjacent-raw-token bigram sets, built from the
  frozen corpus, each page entry bound to its freeze sha256.

## H3a — bounded hybrid scoring

Contract: candidates = the baseline-identical FTS5 k=10 hit list (verified
equal to the baseline artifact per query). Two pre-registered bounded forms:

- **BAND(δ = 0.10)**: maximal chains of hits whose consecutive lexical-score
  gaps are ≤ 0.10 form tie groups; within a group, order by
  (−cosine, baseline_rank); groups never interleave. A lexical lead > 0.10
  normalized-relevance points is structurally unbridgeable. δ = 0.10 chosen
  as a round bound at the scale of the baseline's own threshold granularity
  (min_score 0.15; typical adjacent-gap 0.02–0.06).
- **ADD(w = 0.15)**: score′ = lex + 0.15·cosine; order by
  (−score′, baseline_rank). Maximum semantic swing 0.15 score units —
  bounded by construction; semantic cosine spans [−1, 1] so no single page
  can gain more than 0.15 on another from semantics alone.

Pass (either form suffices for the form-level claim; H3a needs BOTH the
recovery and the safety legs in ONE form): b1 expected page top-5; A 3/3;
D 3/3; C 3/3; E 2/2; F no worse than baseline (f1 ≤ 7 reported, f3 ≤ 10,
f2 = 0). Latency p95 ≤ 100 ms; determinism required.

### Dominance trilemma (design analysis over recorded numbers — the pre-registered prediction)

For b1, recorded (baseline lex, arm1 cos): igsl-tenancy-project (0.44, 0.8819),
MEMORY.md (0.31, 0.8838), tenancy #2 (0.28, 0.8819) dominate the expected page
igsl-remote-machine (0.26, 0.8799) on BOTH signals; igsl-lan-hosts
(0.26, 0.8875) dominates it on cosine at equal lexical score. Top-5 therefore
requires remote-machine to overtake BOTH lex-0.37 pages (gap 0.11). But:

- any band with δ ≥ 0.11 also chains a1's candidates (max consecutive gap
  0.06) into one cosine-ordered group, where gpu-box (cos 0.9206) falls below
  nas-hardware (0.9375), data-work (0.9325), tenancy (0.9313), MEMORY (0.9288),
  resources (0.9216) → a1 rank ≈ 6 → A FAILS; and d1's gap-0.11 break point
  dissolves at δ ≥ 0.11, chaining ranks 2–10 into one group where
  self-certification (cos 0.7726) is LOWEST → d1 rank ≈ 10 → D FAILS.
- any additive w lifting remote-machine past the lex-0.35 pages needs
  w > 0.09 / (0.8799 − 0.8656) ≈ 6.3 — semantic-dominant, i.e. H2-arm1
  (A 1/3, D 0/3) with extra steps.

PREDICTION (pre-run): BAND(0.10) recovers b1 (rank 5) but fails a1 (rank ≈ 6)
and d1 (rank ≈ 10); ADD(0.15) preserves A 3/3, D 3/3, C 3/3, E 2/2 but leaves
b1 at rank ≈ 9. H3a is therefore expected to be DISCONFIRMED in both forms,
with the trilemma as the structural explanation: under lexical primacy, b1's
expected page cannot rise, because three pages beat it on both signals — its
H2-arm1 "recovery" required discarding lexical order entirely.

## H3b — lexical-evidence honesty rule

- content token: query token (lowercase `[a-z0-9]+`) not in the
  pre-registered stoplist (embedded in the stats artifact for audit) and
  length ≥ 2.
- content bigram: a pair of content tokens ADJACENT in the query's raw token
  stream, order preserved.
- **Rule L**: if NO content bigram appears (adjacent, order-preserved) in ANY
  candidate page's token stream, declare honest miss — suppress all reported
  hits regardless of scores. Inapplicable (no opinion) when the query yields
  zero content bigrams.
- **Rule L′** (diagnostic): L, but gated on weak lexical evidence — applies
  only when the top lexical score < 0.30.

Pass: f2 stays clean (0 hits); f1 AND f3 suppressed (or, per the plan brief,
measurably de-confidenced — recorded but not claimed as full success); and
ZERO false negatives: no A–E query may have its answer suppressed. The
18-query evidence matrix (per query: content bigrams, which appear in which
candidate, L/L′ outcomes) is recorded in full.

PRE-REGISTERED RISK (predictions, pre-run): f1's bigrams
(nas,rack),(rack,unit),(serial,number) and f3's (commit,identity) were
verified corpus-absent at freeze, so L should suppress both. But class B is
paraphrase-by-design: b1's bigrams (machine,hosts),(research,vms) and b2's
(network,settings) plausibly absent from the corpus (the corpus frames the
research VMs as "system containers"; b2's page says "network setting"
singular / "networking"). If L suppresses ANY A–E query, H3b as specified is
DISCONFIRMED and the boundary is mapped by the matrix. L′ would then spare
all answerable queries but fail to touch f3 (top lexical 0.56 ≥ 0.30) —
fixing f1 only.

## Disconfirmation criteria (before results)

H3a disconfirmed if neither form achieves b1-top-5 with A 3/3, D 3/3, C 3/3,
E 2/2, F no worse. H3b disconfirmed if L leaves f1 or f3 un-suppressed, or
suppresses any A–E query; partially confirmed findings (e.g. L′ fixing f1
only) reported as such. Latency over budget or non-determinism disconfirms
the engineering claim regardless of ranking outcomes.

## Mutation controls (node 8, pre-registered)

1. semantic-dominant settings — BAND(δ=∞) and ADD(w=6.5) — must REGRESS A/D
   while the bounded forms hold: the bound is load-bearing, both directions.
2. evidence rule disabled must flip f1/f3 back to their baseline false
   positives; enabled suppresses per the eval artifact. Both directions.
3. tampered corpus-stats index must refuse; intact verifies. Both directions.
