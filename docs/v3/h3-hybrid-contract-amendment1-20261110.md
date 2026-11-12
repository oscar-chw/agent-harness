# H3 hybrid contract — amendment 1 (additive): rule L2 pre-registration

2026-11-10, second entry. This amendment ADDS one pre-registered refinement of
rule L. It does not modify the original contract
(`h3-hybrid-contract-20261110.md`, sha256 `43a33a65…`), does not touch H3a,
and does not alter the recorded L/L′ outcomes or their verdicts. Authority:
the plan brief granted ONE bounded refinement of rule L if the pre-registered
form failed, itself pre-registered before testing. This is that refinement —
written after rule L's failure was observed, BEFORE any L2 evaluation has run.

## Evidence base (hash-bound)

- Pre-refinement eval snapshot: `eval-h3-ruleL-20261110.json`, sha256
  `3b11a55ed9041317499a085e313e7729b57f8d2fb1daad93536709fe1ae48245` — the
  byte-identical copy of the first (post-bugfix) H3 eval, preserved so this
  amendment cites evidence that no later run can overwrite.
- Coverage matrix computed from the frozen corpus (read-only) under the
  contract's own content-token rule, over each query's baseline-identical
  candidate set recorded in that snapshot:

  | query | class | L fires | best candidate content-token coverage |
  |-------|-------|---------|----------------------------------------|
  | b1    | B     | YES (false negative) | 1.00 |
  | b3    | B     | YES (false negative) | 1.00 |
  | e1    | E     | YES (false negative) | 1.00 |
  | f1    | F     | yes (correct)        | 0.60 |
  | f2    | F     | yes (correct)        | 0.00 (no candidates) |
  | f3    | F     | yes (correct)        | 0.50 |
  | all other A–E | — | no    | 0.71–1.00 (rule silent) |

## The observed failure and the structural separator

Rule L as specified is DISCONFIRMED: it suppresses f1/f2/f3 correctly but also
suppresses b1, b3, e1 — three false negatives, breaching the zero-false-negative
pass rule.

The separator is structural, not tuned: every A–E false negative has a
candidate page containing ALL of the query's content tokens (coverage exactly
1.00 — the answer page is lexically complete on unigrams even though the
query's compound phrasing is paraphrased away, which is precisely why the
bigram test over-fires). Every true negative control has coverage at most
0.60: f1 = 0.60 (`rack` is corpus-absent), f3 = 0.50, f2 = 0.00. The margin
between the two populations is 1.00 vs ≤ 0.60 — a gap of 0.40 coverage
points, not a knife-edge threshold fitted to the outcome.

## Pre-registered refinement: rule L2

Definition (exact):

- content-token coverage of a candidate page = |Q ∩ P| / |Q|, where Q is the
  set of DISTINCT query content tokens (contract stoplist, length ≥ 2) and P
  is the candidate page's content-token set, both from the frozen corpus under
  the contract tokenizer. Best coverage = max over the query's candidate
  pages; 0.0 when the candidate set is empty.
- **Rule L2**: declare honest miss iff `rule_L(report)` holds AND the query's
  best candidate content-token coverage is < 1.0.

Equivalent reading: L2 is L with an override — if some candidate page is
lexically complete on the query's content tokens, the paraphrase explanation
for the missing bigrams is available and the rule stays silent.

## Pass / disconfirmation criteria for L2 (fixed before the L2 run)

H3b via L2 CONFIRMED iff, on the frozen 18 queries:

1. ZERO false negatives — no A–E query suppressed;
2. f1 AND f3 both suppressed;
3. f2 stays clean (0 reported hits).

Any A–E suppression, or f1/f3 un-suppressed, or f2 polluted, DISCONFIRMS L2,
and with it H3b in full — no further refinements are authorized; the boundary
will be reported as mapped. H3b's headline verdict is then: L disconfirmed as
specified, L2 disconfirmed, honesty-rule line closed.

## Honesty notes (required by the plan brief)

- L2 was designed AFTER rule L's failure was observed — it is the brief's
  single authorized refinement, not an a-priori form. It is validated exactly
  once, on this same frozen 18-query set; a pass is therefore evidence for
  the structural claim (lexical completeness overrides phrase absence), not
  proof of generality. Confirmation here licenses a production-candidacy
  evaluation under a separate gated plan, not direct adoption.
- The coverage statistic is computed from the frozen corpus read-only; the
  hash-bound corpus-stats artifact is UNCHANGED (this amendment adds no new
  inputs and breaks no existing binding).
- No H3a form was tuned; H3a's verdict stands on the original contract alone.
