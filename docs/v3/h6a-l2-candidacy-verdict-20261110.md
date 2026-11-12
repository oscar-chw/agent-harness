# H6a verdict — L2 production candidacy: CONFIRMED within a pre-registered envelope

2026-11-11. Plan `plan/v3-h6a-l2-candidacy`, nodes 1–10. All numbers re-derived
by `check_h6a.py` (evidence-integrity gate) and `mutation_controls.py` (3
controls, both directions) over the hash-bound artifact
`eval-h6a-20261110.json` (sha256 `0b8d1555…`), bound to the fresh query set
(`2f4b00f4…`), the H6a contract (`0c0a7c6c…`), the H1 freeze (`e55ccdc2…` /
corpus `af6af281…`), and the H3 provenance chain (contract `43a33a65…`,
amendment 1 `f6c1a39f…`, eval `18d4fe09…`, module `5060a9b1…`). Controls
receipt `mutation-controls-h6a-20261110.json` (sha256 `e1d236bb…`). Usage
across the whole plan: 0 model tokens, 0 native calls, 0 network.

## H6a verdict

**VALIDATION CONFIRMED — all six pre-registered legs green — and the
integration is done: L2 ships in `src/agent_harness/mcp/kb.py` as the opt-in
honesty layer `HARNESS_KB_HONESTY` (default OFF, byte-identical behavior when
off).** The confirmation carries an explicit envelope (below): L2 is validated
as "no false negative when some candidate is unigram-complete on the query's
content tokens" — NOT "no false negatives" — and the fresh set contains a
deliberate, pre-registered counterexample that fires exactly where H3's
separator said it would.

## Validation table (frozen rule, unchanged — no parameters tuned)

Fresh 15 (class × query × suppressed × best coverage × pass):

| id | class | suppressed | coverage | pass | note |
|----|-------|-----------|----------|------|------|
| n1 | N | yes | 0.67 | ✓ | hddpool pool GUID — absent fact, 10 baseline trap hits |
| n2 | N | yes | 0.50 | ✓ | Kaggle token rotation date — 10 trap hits |
| n3 | N | yes | 0.75 | ✓ | Surfshark renewal date — 3 trap hits |
| n4 | N | yes | 0.67 | ✓ | NVMe firmware revision — 3 trap hits |
| n5 | N | yes | 0.50 | ✓ | smartd SMTP relay — 4 trap hits |
| p1 | P | no | 1.00 | ✓ | b1-shape: bigram absent, coverage override silent |
| p2 | P | no | 1.00 | ✓ | b1-shape: both bigrams absent, override silent |
| p3 | P | no | 0.75 | ✓ | bigram (kaggle credential) present — bigram leg |
| p4 | P | no | 1.00 | ✓ | bigram leg; top-5 rank kept |
| p5 | P | no | 1.00 | ✓ | bigram leg; top-5 rank kept |
| v1 | V | no | 1.00 | ✓ | verbatim floor |
| v2 | V | no | 1.00 | ✓ | verbatim floor |
| x1 | X | **yes** | 0.75 | ✓ (expectation) | **the false-negative hole, firing as registered** |
| x2 | X | no | 1.00 | ✓ (expectation) | coverage override via MEMORY.md defeats suppression |
| x3 | X | no | 0.75 | ✓ (expectation) | bigram (zfs pool) present — bigram-leg blind spot |

Legs: N all suppressed ✓ · P/V zero false negatives, all expected pages top-5 ✓
· X all three match pre-registered expectations ✓ · **stability control: the
original frozen 18 reproduce the H3 artifact's L2 outcomes AND coverages
exactly (18/18)** ✓ · determinism byte-identical ✓ · stage p95 0.040 ms vs
100 ms budget ✓ · usage zero ✓.

## The boundary, mapped (the candidacy's real deliverable)

The X-class exists to find where L2 breaks, and it found exactly the
pre-registered edges:

- **x1 (answerable, suppressed):** "How often does smartd test the disks?" is
  genuinely answered by igsl-18-storage ("daily short and monthly long
  self-tests") — but the query token "often" is absent from every candidate,
  coverage lands at 0.75, no bigram exists, and L2 declares honest miss.
  **L2 can false-negative an answerable query whose wording is lexically thin
  against the corpus.** This is the envelope's lower edge: the coverage-1.0
  override protects paraphrases whose tokens all appear; it cannot protect
  ones that don't.
- **x2 (negative, escapes):** an index page (MEMORY.md) is unigram-complete
  on the query's tokens, so the override stays L2's hand even though the fact
  is absent. Index/overview pages are suppression-resistant by construction.
- **x3 (negative, escapes):** one corpus-common content bigram ("zfs pool")
  satisfies the bigram leg regardless of coverage. Queries that happen to
  contain a common compound escape suppression.

Adoption posture these edges support: L2 is safe to enable as an **honesty
layer** (it converts confident false positives into honest misses, and on 33
queries never took a real answer away except the deliberately constructed
edge case) — with the documented caveat that thin-worded answerable queries
can be suppressed. If that trade-off is unwanted for some surface, keep the
flag off there. No parameter change is licensed by this result; any change is
a new hypothesis.

## Integration status

`src/agent_harness/mcp/kb.py` (sha256 `7e03a928…`):

- `HARNESS_KB_HONESTY` env flag (`1`/`true`/`yes`), default OFF. Flag off:
  the honesty block is skipped entirely — results byte-identical to the
  recorded candidates on all 33 queries, and the evidence maps are never
  built (tested).
- Flag on: per-page content-token/bigram sets are built lazily from indexed
  section bodies joined in ord order (invalidated on index change); at
  search(), L2 evaluates the distinct pages of the top-10 scored sections —
  the exact validated window — and returns [] on fire. Non-firing queries
  return byte-identical results to flag-off (tested).
- The embedded rule is a frozen copy of the eval module; tests assert the
  stoplist, tokenizer, and window constants equal the H3/H6a originals.
- Fidelity of section-reassembled evidence vs raw-page evidence is proven by
  outcome reproduction on all 33 queries, including all three boundary cases.
- Gate: 97 tests green — 8 new (`tests/test_kb_honesty.py`) + 89 existing
  (`test_kb_*.py`, `test_mcp.py`, `test_context_budget.py`).

## Controls matrix (receipt `e1d236bb…`)

| control | green | red | verdict |
|---|---|---|---|
| flag_default | flag ON reproduces all 33 recorded outcomes | flag OFF: f1 7 hits, f3 10, n1 10 — the baseline false positives return | BOTH |
| embedded_rule_tampering | intact rule reproduces outcomes | stoplist-minus-"the" flips n2/n3/n4/f1; window=1 flips x2 (+b2/d1 — narrow windows false-negative) | BOTH |
| tampered_artifacts | intact eval verifies clean | flipped suppression flag caught; altered fresh query text caught | BOTH |

## Honesty limits

- The fresh set is 15 queries on ONE frozen 133-page corpus; the N and P/V
  legs were designed to construction invariants (fact absence, trap strength,
  answerability), and two designed negatives that measured on the boundary
  were classified X with their mechanisms disclosed — nothing was dropped for
  its outcome (one weak-trap N candidate was dropped for trap strength, and
  disclosed in the contract).
- x1's suppression is a real false negative, pre-registered as expected; the
  confirmation is "the boundary is where H3 measured it", not "L2 is
  universally safe".
- Production evidence maps are rebuilt from the live index on change; live
  behavior follows the same code path proven on the frozen copy, but the live
  corpus is larger and dynamic — the first live enable should be treated as a
  canary, watching for unexpected honest-miss rates.

## What follows (ranked)

1. **Enable deliberately, observe**: turn on `HARNESS_KB_HONESTY` for one
   real surface and log suppressions; the envelope says expect occasional
   x1-shaped false negatives on thin-worded answerable queries — if that
   rate is unacceptable, the next hypothesis is de-confidencing (report hits
   with an honesty annotation) instead of hard suppression. That is a NEW
   hypothesis needing its own gated plan.
2. **Retrieval-side enrichment for thin-worded queries** (x1's fix lives in
   retrieval, not in the rule): synonyms/expansion would raise coverage above
   1.0's protection — but that's the lexical pipeline's business, not L2's.
3. **Close the reranking line**: H2 + H3 + H6a together complete the arc —
   semantics can't reorder safely (H2), bounded hybrid boosts are empty (H3a),
   lexical evidence is the usable honesty signal (H3b-L2, H6a). BM25 +
   supersedes + opt-in L2 is the validated production shape.
