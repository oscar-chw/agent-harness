# H4 dreaming — verdict

2026-11-10. plan/v3-h4-dreaming node 9. All numbers re-derived from the
hash-bound artifacts by `.harness-work/v3-h4-dreaming/check_h4.py` (exit 0,
15/15 checks) and `mutation_controls.py` (exit 0). Artifacts:
`eval-h4-20261110.json` (sha 64f83b2f…), `mutation-controls-h4-20261110.json`
(sha 795919d4…), `h4-inputs-20261110.json` (sha 4ac7032f…), apply receipt
(sha b9711f6d…), dreamed corpus root b41ae049…, all bound to freeze
e55ccdc2… / corpus af6af281… / baseline 286a988c… / H1 apply receipt
d2726339… / contract fbf9756b… (pre-registered
`docs/v3/h4-dreaming-contract-20261110.md`). Zero model tokens, zero network;
the live memory corpus was never touched (all runs on the frozen H1 snapshot
or fresh copies of it).

## H4 verdict: DISCONFIRMED (v0 as specified) — DC1 and DC3 fire; DC2, DC4, DC5 hold

The hypothesis — a deterministic, model-free control loop (trigger → Light
candidate staging → REM scoring → all-required promotion gates → phase-scoped
Deep writes) can promote H1's consolidation candidates at high precision
without touching retrieval — fails on both quality arms. The safety and
hygiene arms all hold; the loop is safe but not selective enough.

| criterion (pre-registered) | result | pass? |
|---|---|---|
| DC1 orphan-link precision ≥ 0.80 AND ≥ apply-all + 0.20 | 0.6071 (apply-all 0.4940, +0.113) | NO — fires |
| DC2 promoted links integrate ≥ 15 orphans | 26 integrated (orphans 34 → 8) | YES |
| DC3 edge precision ≥ 0.75 AND recall ≥ 0.75 | precision 0.3636, recall 1.0 (apply-all 0.3077) | NO — fires |
| DC4 no invariant violation (fact loss / MEMORY.md / freeze / dry-run purity / promotion without trigger / archive-or-delete) | no fact loss; MEMORY.md byte-identical; no archive/ created; all 56 writes guard-receipted orphan-link appends with valid frozen→dreamed hash chains | YES |
| DC5 retrieval non-regression (amended H1 rules) | 18/18 queries non-regressed, ranks identical to baseline; recall@5 0.9333, precision@5 0.2133, MRR 0.8185 — unchanged (prediction P3 confirmed) | YES |

Promotion scoreboard vs adjudicated labels (96 candidates, labelled blind to
scores): orphan links promoted 56/83 → TP 34 / FP 22 / FN 7, precision 0.6071,
recall 0.8293. Supersedes edges promoted 11/13 → TP 4 / FP 7 / FN 0, precision
0.3636, recall 1.0. The 2 demoted edges are exactly the weak-literal ones
(`ptcg-top-episode-bias → baidu-netdisk-access` 0.261 and
`ptcg-top-episode-bias → ptcg-model-spec` 0.379, both matched only the dotted
suffix `.08`): G-StrongLit works as designed.

## Why it failed (evidence, not speculation)

1. Paragraph-level `s_ctx` is agreement-blind — exactly the boundary contract
   prediction P2 registered. Pages that AGREE with a correction share more
   vocabulary than the page carrying the stale claim. The worst FP edge scored
   a perfect 1.000: `igsl-tenancy-project → config-declares-kernel-disagrees`
   (strong literal "cannot reach the NAS", 20 shared context tokens, same-month
   dates) — the tenancy page *discusses* the same problem; nothing supersedes
   anything. Likewise `igsl-nas-hardware-state → igsl-lan-hosts` 0.971 (ctx=8)
   and `→ igsl-remote-machine` 0.957 (ctx=13): hardware-state pages genuinely
   coexist with host pages, sharing vocabulary precisely because they agree.
2. `s_auth` = 1.0 for hub pages adds a flat +0.20 (edges) / +0.15 (orphans,
   via the 0.20 weight at full authority) to anything a hub touches. Four of
   the seven FP edges have `s_auth` ≥ 0.5; three have 1.0. Authority measures
   citation centrality, not supersession likelihood, and at these weights it
   overrides the absence of a stance signal.
3. idf saturates at N = 133 pages: 4–9 moderately generic shared tokens are
   enough to max `s_ctx` / `s_lex`, so the lexical legs cannot separate
   "same topic, both true" from "new fact replaces old fact". The orphan arm's
   22 FPs are the same phenomenon at page level (e.g. hub pages absorbing
   orphans on shared project vocabulary — full `fp_keys` in
   `eval-h4-20261110.json`).
4. What the gates DID catch confirms the design intent: G-StrongLit removed
   both `.08`-only edges (H1 would have applied them), and G-Support/G-Score
   removed 27/83 orphan proposals including all planted-nonsense controls.
   The failure is concentrated where no model-free signal exists: stance.

## Mutation controls (node 8, both directions, exit 0)

| control | green | red |
|---|---|---|
| bad_candidate_rejected — planted nonsense pair | demoted at contract thresholds (G-Score 0.480 < 0.55) | promoted when thresholds maliciously lowered; override receipted loudly |
| phase_scope_guard | all 6 out-of-scope writes raise PhaseScopeError | stubbed guard lets everything through, incl. MEMORY.md append |
| trigger_fail_closed | below-threshold state: ValueError before any write | cooldown refuses a hot state; sessions=5 fires and writes |
| planted_true_pair | genuinely topical orphan promoted, facts preserved (independent recompute) | deleting the promoted source page from the output IS caught by the independent verifier |
| freeze_drift | intact copy verifies against manifest (corpus af6af281…) | one byte of drift refuses dry-run AND apply before writing |

Control-harness note, honestly recorded: the independent verifier originally
checked hash-accounting only (a receipted hash vouches for a missing page),
which made the deletion red-case undetectable. It was strengthened to require
each receipted mutation chain to terminate live on disk (last after_sha256 ==
live page hash, adjacent links chained — the same semantics as gate-7 check
B8d). The shipped module is unchanged (module sha e7134338… throughout); only
the control harness gained the stricter independence property.

## Engineering findings that stand regardless of the verdict

- The trigger model (bootstrap OR sessions ≥ 5 OR pages_changed ≥ 10, with
  same-session cooldown) is fail-closed and was proven so in both directions.
- PhaseGuard (Light = stage receipts only, REM = score receipts only, Deep =
  only orphan-link appends under dst, never MEMORY.md/archive/) held with
  zero refusals needed in the real run and six caught violations under test.
- Determinism: two dry-runs byte-identical modulo created_utc; dry-run purity
  (no mutations, no output root, no dst) verified.
- Hygiene gain is real even under disconfirmation: orphans 34 → 8, in-degree
  histogram {0:34, 1-2:51, 3-4:27, ≥5:20} → {0:8, 1-2:66, 3-4:38, ≥5:20},
  with zero retrieval regression — the loop's writes are structurally safe.
- The labels artifact (13 edges / 83 orphan links, adjudicated blind to
  scores, hash-bound) is reusable for any H4 successor scoring variant.

## What follows (ranked by expected value)

1. Literal-local context windows (±8 tokens around the matched literal) plus a
   target-side stance/negation signal — the measured failure is paragraph-level
   agreement-blindness; narrow the window and require disagreement evidence.
2. Log-scaled `s_auth` and idf recalibration (sublinear tf, document-length
   normalisation) so hub authority cannot add a flat bonus to everything.
3. Edges stay ledger-only until a model-based stance check exists — the
   measured model-free edge ceiling (0.3636 at recall 1.0, with the best
   gates we could pre-register) suggests ≈ 0.4–0.6 precision is the realistic
   band without semantics.
4. The orphan arm could plausibly reach ~0.8 precision by raising
   min_score/min_support at a recall cost — but only after a dominance-style
   pre-analysis of the precision/recall trade-off on the labels artifact, not
   by ad-hoc threshold tuning.

Recommendation: do NOT promote dreaming v0 to any live path. The control loop
(trigger, phases, guards, receipts) is sound infrastructure and stays in the
tree behind its gates; the scoring model does not discriminate agreement from
supersession and must not gate real corpus writes.

## Amendment — 2026-11-11 (additive): eval report regenerated after v0-module lint hygiene

`src/agent_harness/memory_dreaming.py` lost three dead names (F401 `hashlib`
import, F841 `source` local in `score_orphan_link`; the third finding, F401
`math`, was in `tests/test_memory_dreaming_v1.py`) — behavior-preserving:
both full dreaming suites (37 tests) and both master checks re-run green on
the edited bytes, integrity 15/15, verdict unchanged (DISCONFIRMED). v0
module sha `e7134338…` → `9d61a247…`; H6c's B3 binding was updated by dated
amendment in `check_h6c.py` (`V0_MODULE_SHA256_AMENDED_20261111`, original
retained). The eval reports embed their generation context, so every re-run
changes their sha: the `64f83b2f…` citation above is the 2026-11-10
verdict-time copy; the current regeneration is `8ad71f1f…`. Every other
binding cited above (freeze, corpus, labels, receipts, contract) is unchanged
and re-verified by the re-run.
