# H3 verdict — hybrid retrieval: bounded semantic boost + lexical-evidence honesty rule

2026-11-10. Plan `plan/v3-h3-hybrid`, nodes 1–9. All numbers re-derived by
`check_h3.py` (evidence-integrity gate) and `mutation_controls.py` (3
controls, both directions) over the hash-bound artifact
`eval-h3-20261110.json` (sha256 `18d4fe09…`), itself bound to freeze
`e55ccdc2…`, corpus `af6af281…`, contract `43a33a65…`, amendment 1,
corpus-stats `ca3ee265…`, H2 cache and H2 arm-1 `0a46fd1c…`. Controls receipt
`mutation-controls-h3-20261110.json` (sha256 `319787aa…`). Usage across the
whole plan: 0 model tokens, 0 native calls, 0 network.

## Verdict summary

| sub-hypothesis | form | verdict |
|---|---|---|
| **H3a** bounded semantic boost under lexical primacy | BAND(δ=0.10) | **DISCONFIRMED** — b1 recovered (rank 5) but A 2/3, D 0/3 |
| | ADD(w=0.15) | **DISCONFIRMED** — A/C/D/E held, F no worse, but b1 rank 10 (baseline 9) |
| **H3b** lexical-evidence honesty | rule L (as pre-registered) | **DISCONFIRMED** — false negatives b1, b3, e1 |
| | rule L′ (diagnostic) | partial — suppresses f1 only; f3 untouched (top lex 0.56 ≥ 0.30) |
| | **rule L2 (amendment 1)** | **CONFIRMED** — f1+f3 suppressed, f2 clean, zero false negatives |

Per-class pass counts (frozen 18):

| pipeline | A | B | C | D | E | F |
|---|---|---|---|---|---|---|
| baseline (BM25+supersedes) | 3/3 | 3/4 | 3/3 | 3/3 | 2/2 | 1/3 |
| H2 arm1 (pure cosine) | 1/3 | 3/4 | 3/3 | 0/3 | 2/2 | 1/3 |
| h3a BAND(0.10) | 2/3 | 3/4 | 3/3 | 0/3 | 2/2 | 1/3 |
| h3a ADD(0.15) | 3/3 | 3/4 | 3/3 | 3/3 | 2/2 | 1/3 |
| h3b baseline+L | 3/3 | 2/4 | 3/3 | 3/3 | 1/2 | 3/3 |
| **h3b2 baseline+L2** | **3/3** | **3/4** | **3/3** | **3/3** | **2/2** | **3/3** |

## H3a — disconfirmed, with the dominance trilemma as the structural explanation

The pre-registered prediction (contract, written before any H3 run) matched
the observed outcome: BAND predicted b1 rank 5, a1 ≈ 6, d1 ≈ 10 — observed
exactly (5, 6, 10). ADD predicted b1 ≈ 9 — observed 10.

The trilemma, measured (mutation control 1, recomputed from the artifact):

| BAND δ | b1 rank | A | D |
|---|---|---|---|
| 0.03 | 9 | 3/3 | 3/3 |
| 0.10 | **5** | 2/3 | 0/3 |
| ∞ (semantic-dominant) | 5 | 1/3 | 0/3 |

No bound lifts b1 without breaking A/D, because b1's expected page
(igsl-remote-machine, lex 0.26, cos 0.8799) is dominated on BOTH signals by
igsl-tenancy-project (0.44, 0.8819), MEMORY.md (0.31, 0.8838) and
tenancy#2 (0.28, 0.8819), and on cosine at equal lex by igsl-lan-hosts
(0.26, 0.8875). A band wide enough to bridge the 0.11 lexical lead chains
a1's and d1's candidates into cosine-ordered groups where their expected
pages lose. The additive route needs w > 6.3 (semantic-dominant — measured
at w = 6.5: D drops to 2/3, i.e. H2-arm1's failure mode returns). Under
lexical primacy, b1's H2-style "recovery" is structurally unavailable.
**The pure-rerank line closes here: semantics can reorder a frozen lexical
candidate set only by overriding the lexical evidence that makes the baseline
good.**

## H3b — rule L disconfirmed as specified; pre-registered refinement L2 confirmed

Rule L (no query content-bigram in any candidate → honest miss) suppressed
all three negative controls but also b1, b3, e1 — all paraphrase-class
queries whose answer page contains every query content token but not the
query's compound phrasing (the corpus says "system containers", not
"research VMs"). Zero-false-negative leg breached → disconfirmed as
specified, exactly as the contract's pre-registered risk anticipated.

The 18-query evidence matrix exposed a structural separator — best candidate
content-token coverage:

| query | L fires | coverage | interpretation |
|---|---|---|---|
| b1, b3, e1 | yes (false negative) | **1.00** | paraphrase: unigram-complete, bigram-absent |
| f1 | yes (correct) | 0.60 | `rack` is corpus-absent |
| f3 | yes (correct) | 0.50 | `commit` present, `identity` absent |
| f2 | yes (correct) | 0.00 | no candidates at all |

Amendment 1 (pre-registered after L's failure, before any L2 run, citing
snapshot `eval-h3-ruleL-20261110.json` sha256 `3b11a55e…`) fixed
**L2 = L ∧ (best candidate content-token coverage < 1.0)** — a lexically
complete candidate overrides the missing-bigram signal. Measured: L2 fires
on f1, f2, f3 only; zero A–E suppression; f1/f3 suppressed; f2 clean.
All pre-registered L2 legs pass. The separation margin is structural
(1.00 vs ≤ 0.60), not a tuned threshold.

## Engineering claims (all verified, both directions)

- Determinism: two passes byte-identical (canonical ranking hashes recorded
  and re-derived).
- Latency: hybrid stage p95 0.183 ms against the 100 ms budget (7 warm reps
  × 18 queries; candidate fetch excluded, p95 40.7 ms, unchanged from
  baseline path).
- Mutation controls (receipt `319787aa…`): (i) semantic-dominant settings
  regress A/D while bounded forms hold — the bound is load-bearing;
  (ii) rule disabled → f1 back to 7 hits and f3 to 10 with the trap pages at
  rank 1, enabled → suppressed per the artifact; (iii) tampered stats
  (page hash, page set, stoplist) and tampered rule flags are all caught;
  intact verifies clean.
- `check_h3.py` re-derives from the frozen inputs: candidates vs baseline,
  cosines vs H2 arm-1, both boost forms exactly, evidence matrix
  completeness, L/L′/L2 outcomes, all 7 pipeline verdicts, determinism,
  latency, usage. Hypothesis criteria are re-derived and reported, never
  gated.

## What follows (ranked)

1. **Adopt L2 as a production-candidacy honesty layer — in a separate gated
   plan.** BM25+supersedes stays the retriever untouched; L2 would sit
   between retrieval and answer generation as a "no-evidence" declaration.
   Candidacy requires fresh queries (L2 was validated once, on the frozen 18
   it was refined on) and a production binding design (per-page token sets at
   index time).
2. **Query-class routing**: negative-control-style queries are detectable
   pre-retrieval (coverage + bigram evidence); route them to the honesty
   path instead of ranking.
3. **Field-aware scoring**: title/frontmatter vs body weighting — the one
   lexical-side improvement the evidence still leaves open (b1's gap is a
   titling problem: the answer page never says "research VMs").
4. **Exact-tie-only semantic tiebreak**: the only dominance-free boost
   (cosine orders only exact lexical ties). Safe by construction; small
   effect — worth one bounded test if the ranking line ever reopens.
5. **Contextual embeddings** (local runtime) — parked; static GloVe pooling
   is now measured twice as insufficient (H2, H3a).

## Honesty limits

- L2 was designed after rule L's failure was observed — the plan brief's
  single authorized refinement, validated exactly once on the same frozen
  18 queries. Its confirmation is evidence for the structural claim
  (lexical completeness overrides phrase absence), not proof of generality.
- H3a used one frozen candidate set (k=10) and one embedding model; the
  trilemma is a statement about this corpus and these signals, supported by
  pre-registered prediction matching observed outcomes exactly.
- The coverage statistic reads the frozen corpus read-only; no hash-bound
  input was modified by the amendment.
