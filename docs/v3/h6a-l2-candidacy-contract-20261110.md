# H6a contract — L2 production candidacy, pre-registered before any validation run

2026-11-10. Pass/fail rules for plan/v3-h6a-l2-candidacy, written AFTER the
fresh query set was fixed and BEFORE any validation run. Same convention as
H1/H2/H3: rules fixed here; changes only by additive, evidence-cited
amendment. This contract does not modify any H1/H2/H3 artifact.

## Inputs (hash-bound, read-only)

- Fresh query set: `fresh-queries-20261110.json`, sha256
  `2f4b00f4d2243697d4f39a169199e16852f94395f9440d53bd21ec262abb5ea9` —
  15 queries (N5 P5 V2 X3), each probe-verified against page bytes, negative
  controls forbidden-pattern-verified corpus-absent, baseline candidates
  recorded (k=10, production kb path over the frozen-corpus copy).
- Frozen corpus copy: `.harness-work/v3-h6a-l2-candidacy/frozen-corpus/`,
  verified byte-equal to the H1 freeze record (corpus `af6af281…`, 133 pages).
  H1's snapshot itself is never touched; the live corpus is never read.
- L2 provenance: H3 contract `43a33a65…`, amendment 1 `f6c1a39f…`, H3 eval
  artifact `18d4fe09…` (the stability oracle), hybrid_scorer.py `5060a9b1…`
  → byte-copied into `l2_rule.py` (`4a395400…`; copy fidelity is
  pytest-enforced per object).

## The frozen rule (no changes authorized)

L2 fires (honest miss) iff: (a) rule L fires — NO query content bigram
(adjacent both-content raw-token pair, `[a-z0-9]+` lowercase, length ≥ 2, H3
stoplist) appears in ANY candidate page's token stream; AND (b) the best
candidate content-token coverage — |Q ∩ P| / |Q| over DISTINCT query content
tokens, max over the top-10 candidate sections' distinct pages, 0.0 if none —
is < 1.0. Any change to tokenizer, stoplist, bigram adjacency, coverage
statistic, threshold, or window is a new hypothesis, not a refinement.

## Pass rule (validation, node 7)

H6a CONFIRMED iff ALL of:

1. **N leg** — all 5 N-class queries suppressed (0 reported hits).
2. **P/V leg** — zero P/V-class queries suppressed, and each expected page in
   the reported top-5.
3. **X leg** — each X-class outcome equals its pre-registered
   `boundary_expectation` (recorded in the query-set artifact): x1 suppressed
   (the false-negative hole: answerable, coverage 0.75, bigrams absent), x2
   NOT suppressed (coverage 1.00 override via the index page despite the fact
   being absent), x3 NOT suppressed (bigram leg blind spot: (zfs pool)
   present).
4. **Stability leg** — the original frozen 18 reproduce the H3 artifact's L2
   outcomes exactly (fires on f1/f2/f3, silent elsewhere).
5. Engineering — determinism byte-identical across two passes; hybrid stage
   p95 ≤ 100 ms; usage zero.

## Disconfirmation criteria (before results)

H6a DISCONFIRMED if any N query escapes suppression, any P/V query is
suppressed or loses its top-5 rank, any X query contradicts its registered
expectation, any stability outcome differs from the H3 artifact, or latency /
determinism / usage budgets break. On disconfirmation: record which leg fell
and STOP before integration — the verdict doc then maps the boundary instead
of recommending adoption.

## Honesty notes (design process disclosure)

- All 15 designed queries are in the artifact; none were dropped for their
  L2 outcome. Two queries designed as negative controls measured as
  boundary cases (x2: coverage exactly 1.00 via MEMORY.md; x3: bigram
  (zfs pool) present) and were CLASSIFIED X with their mechanisms recorded —
  classification disclosed here, never silent dropping. One designed N
  candidate ("megacli firmware revision") was dropped for a weak trap (1
  baseline hit at 0.16, marginal above the 0.15 threshold) — a trap-strength
  reason, not an outcome reason.
- X1 is a deliberately constructed false negative: genuinely answerable
  (probes verified), suppressed by design expectation. If validation confirms
  the pre-registered expectations, the verdict must state plainly that L2's
  safety envelope is "no false negative when some candidate is
  unigram-complete on the query's content tokens" — NOT "no false negatives"
  — and that x1 demonstrates the hole at coverage 0.75.
- Design-time measurements were computed with the frozen rule over the frozen
  copy; validation re-derives everything from scratch on a fresh index.

## Integration design (pre-registered; conditional on CONFIRMED)

- Flag: `HARNESS_KB_HONESTY` env var (off unless set to 1/true/yes), matching
  kb.py's existing env-flag convention. Default OFF = the honesty block is
  skipped entirely (byte-identical behavior, proven against recorded
  candidates).
- Flag ON: at refresh(), per-page content-token sets and adjacent
  both-content bigram sets are built from indexed section bodies joined in
  ord order; at search(), L2 (frozen parameters, embedded in kb.py — eval
  tooling is never imported) is evaluated over the distinct pages of the
  top-10 scored sections (the exact validated window); on fire, search
  returns []. Non-firing queries return the identical list as flag OFF.
- Fidelity between section-reassembled page sets and the eval's raw-page sets
  is PROVEN by reproducing the recorded L2 outcomes on all 33 queries (15
  fresh + 18 frozen) against the frozen-corpus copy, not assumed.
