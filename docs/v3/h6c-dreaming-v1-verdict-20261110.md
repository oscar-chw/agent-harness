# H6c dreaming v1 — verdict

2026-11-10. plan/v3-h6c-dreaming-v1 node 10. All numbers re-derived from the
hash-bound artifacts by `.harness-work/v3-h6c-dreaming-v1/check_h6c.py` (exit 0,
15/15 integrity checks). Artifacts: `eval-h6c-20261110.json` (sha 6d6fac2f…),
`mutation-controls-h6c-20261110.json` (sha db426e3f…),
`dominance-analysis-20261110.json` (sha a561f305…), v1 apply receipt (sha
4ccb55c5…), dreamed-v1 corpus root 7895f5e7…, v1 module sha f6479491…, contract
(sha a94bdf69…, pre-registered + amendment 1, both pre-eval). All bound to H1
freeze e55ccdc2… / corpus af6af281… / baseline 286a988c… / H1 apply receipt
d2726339… / H4 labels 4ac7032f… / H4 apply receipt b9711f6d…. Zero model tokens,
zero native calls, zero network; live corpus never touched; v0 module bytes
untouched (sha e7134338… verified in check B3).

## H6c verdict: DISCONFIRMED overall — DC1 fires on the orphan arm; split outcome: the edge-arm fixes WORK (ceiling refuted there), the orphan-arm ceiling HOLDS

v1 = literal-local ±8-token idf-weighted context windows + two-sided stance
gates (edge arm), BM25 idf recalibration + log-scaled authority (both arms),
pre-registered in `docs/v3/h6c-dreaming-v1-contract-20261110.md` before any v1
scoring run.

| criterion (pre-registered) | result | pass? |
|---|---|---|
| DC1 orphan-link v1 P ≥ 0.80 AND ≥ v0 + 0.10 | **0.6034** (v0 0.6071; apply-all 0.4940) | NO — fires |
| DC2 orphan-link v1 recall ≥ 0.50 | 0.8537 (v0 0.8293) | YES |
| DC3 edge v1 P ≥ 0.75 AND R ≥ 0.75 | **P 0.80, R 1.0** (v0 0.3636 / 1.0) | YES |
| DC4 no invariant violation | no fact loss; MEMORY.md byte-identical; no archive/; all 58 writes guard-receipted orphan-link appends with valid frozen→dreamed hash chains terminating live; trigger bootstrap-fired; dry-run pure | YES |
| DC5 retrieval non-regression | 18/18 queries non-regressed; recall@5 0.9333, precision@5 0.2133, MRR 0.8185 — identical to baseline | YES |
| DC6 dormancy clause (edge P in [0.36, 0.60] ⇒ ceiling confirmed) | edge P = 0.80 — OUTSIDE the band | ceiling REFUTED for edges |

Per-arm scoreboard vs the frozen labels (13 edges / 4 true; 83 links / 41 true):

| arm | v0 promoted | v0 P / R | v1 promoted | v1 P / R | v1 TP/FP/FN |
|---|---|---|---|---|---|
| supersedes edges | 11/13 | 0.3636 / 1.0 | 5/13 | **0.80 / 1.0** | 4 / 1 / 0 |
| orphan links | 56/83 | 0.6071 / 0.8293 | 58/83 | **0.6034 / 0.8537** | 35 / 23 / 6 |

Hygiene (unchanged in kind from v0): orphans 34 → 8 (26 integrated), in-degree
hist {0:34, 1-2:51, 3-4:27, ≥5:20} → {0:8, 1-2:64, 3-4:40, ≥5:20}.

## Edge arm — the fixes worked, with the predicted single residual

Literal-local windows + idf mass + the two-sided stance requirement demoted 6
of v0's 7 false promotions and kept all 4 true ones:

- The four zero-context FPs (18-storage, config-declares via `10000`,
  gpu-box→tenancy, lan-hosts) died on G-CtxLocal (mass 0.00).
- The generic-overlap FPs died on idf mass exactly as designed:
  nas-hw→remote-machine {sudo} mass 2.46 and nas-hw→polymarket {live, data}
  mass 2.73 — both below the 3.0 bar (s_ctx_local < 0.5).
- True edges carried distinctive local vocabulary: {intel, x710} mass 7.04,
  {2500, 5000, linked} 10.94, {surfshark, tunnel} 4.98, and the predicted
  recall risk 10g→remote-machine cleared the bar on {linked} alone (mass 3.65,
  s_ctx_local 0.608 ≥ 0.5).
- The one surviving FP is exactly the contract's pre-registered residual:
  tenancy→config-declares, the two pages that record the SAME vacuous-gate
  lesson in near-identical words ({network, passed, vacuously, while}, mass
  8.41, stanceA present). Agreement restatement is the model-free boundary —
  the residual is the predicted one, not a new failure mode.

Caveat, restated from contract §7: n=13 (4 true); the signals were designed
from H4's frozen FP evidence on this same corpus — this is mechanism-level
evidence that the gates separate THESE cases, not a generalization proof. The
node-9 controls show the gates bite on planted unseen data both directions.

## Orphan arm — the ceiling holds, and the dominance question is answered

The H4 verdict's hope ("the orphan arm could plausibly reach ~0.8 precision at
recall cost") is dead, on two independent evidences:

1. **Re-thresholding cannot do it** (node-5 dominance analysis, v0 scores ×
   labels): the v0 envelope reaches P ≥ 0.80 only at recall ≤ 0.4878.
2. **Re-scaling cannot do it either** (v1 measured): BM25-idf + log-auth did
   not improve the ranking — the v1 envelope is WORSE at the P ≥ 0.80 frontier
   (8 thresholds, max recall 0.3171) than v0's (19 thresholds, 0.4878), and at
   the frozen 0.55 gate precision is unchanged (0.6034 vs 0.6071) while recall
   rose slightly (0.8537 vs 0.8293). The residual FPs share genuinely rare
   vocabulary with their sources (project names, machine roles) — rarity is
   not the discriminator; topical relatedness without warrant is the failure
   mode, and it is semantic, not lexical.

Model-free orphan-link ceiling on this corpus: ≈ 0.60 at high recall,
≈ 0.80 only at recall ≤ 0.49. Both scoring variants agree.

## Mutation controls (node 9, both directions, exit 0)

| control | green | red |
|---|---|---|
| bad_candidate_rejected | planted nonce pair demoted at contract thresholds (G-Score 0.505 < 0.55) | promoted under maliciously lowered thresholds, receipted loudly |
| stance_gate_bite | stance-free successor marker → G-StanceA demotes; already-corrected target window → G-StanceB demotes | both promote with edge_require_stance=False, receipted loudly |
| phase_scope_guard | all 6 out-of-scope writes raise PhaseScopeError | stubbed guard lets everything through (incl. MEMORY.md append) |
| trigger_fail_closed | below-threshold: ValueError before any write | cooldown refuses a hot state; sessions=5 fires and writes |
| freeze_drift | intact copy verifies (corpus af6af281…) | one byte of drift refuses dry-run AND apply before writing |

## Engineering findings that stand regardless of the verdict

- The literal-window extractor + BM25 idf + log-auth are deterministic,
  bounded, stdlib-only, and unit-tested (20 tests; v0's 17 still pass, v0
  module bytes unchanged — additive amendment held).
- The dreaming control loop (trigger, phases, PhaseGuard, receipts,
  determinism, dry-run purity, fail-closed) held for a second consecutive
  track — 15/15 integrity checks, zero guard refusals needed in the real run.
- The dominance-analysis artifact (v0 PR envelopes) is reusable for any future
  scoring variant; the corrected v1 envelope is recorded in this verdict.
- The labels artifact (96 candidates, adjudicated blind to scores) has now
  supported two full hypothesis cycles.

## What follows — dormant-or-continue recommendation

1. **Orphan arm: dormant.** Two model-free scoring variants plateau at ≈ 0.60
   precision at the pre-registered gate, and the envelope evidence shows no
   threshold rescues it. Do not iterate further model-free here; a semantic
   (model-based) warrant check is the only plausible next signal and is
   explicitly unauthorized.
2. **Edge arm: validated at mechanism level — keep, but do not wire live.** If
   a future track connects dreaming to a live path, the v1 edge gates
   (G-StrongLit + G-CtxLocal + G-StanceA/B + G-Score) are the recommended
   promotion rule, WITH the documented residual failure mode: agreement
   restatement (two pages recording the same lesson) is indistinguishable from
   supersession without semantics. Ledger-only promotion remains the right
   surface.
3. **The dreaming line as a whole: dormant until a model-based stance/warrant
   check is explicitly authorized.** That is the one signal both arms' residual
   failures point to.

## Amendment — 2026-11-11 (additive): v0-module hash binding amended after lint hygiene

Same hygiene edit as the H4 verdict amendment of the same date: v0 module
`src/agent_harness/memory_dreaming.py` dropped dead `hashlib` import and dead
`source` local (and `tests/test_memory_dreaming_v1.py` dropped dead `math`
import). v0 module sha `e7134338…` → `9d61a247…`; this check's B3 binding now
asserts `V0_MODULE_SHA256_AMENDED_20261111` with the original constant
retained as the frozen 2026-11-10 record (H1 amendment precedent). Both
master checks and both full suites (37 tests) re-run green; integrity 15/15;
DC1–DC6 outcomes unchanged (overall DISCONFIRMED stands). The eval reports
change sha on every regeneration: the `6d6fac2f…` citation above is the
2026-11-10 verdict-time copy; the current regeneration is `b6efb83a…`. All
other cited bindings (freeze, corpus, dominance analysis, receipts, contract,
v1 module) unchanged and re-verified.
