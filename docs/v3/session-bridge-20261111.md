# Cross-session bridge — Kimi Work harness session, 2026-11-11

Purpose: the system is centralized. This record lets Codex/Claude sessions see the full
v3 state as of 2026-11-11, where the evidence lives, and what decisions are open. It is
ADDITIVE: the 2026-11-10 bridge (`docs/v3/session-bridge-20261110.md`) stays as the record
of that day; this one supersedes nothing. Everything listed is in this repo (docs/, plan/,
.harness-work/) or in the harness memory store (tags: agent-harness, v3). Conventions
unchanged: /usr/bin/python3 for pytest gates, no commits without owner request, zero
network, zero native/model calls in workstream scope, additive receipts only, live memory
corpus read-only, plan-record self-redaction after every gate, tamper attestation for new
test files, push tier green to close a workstream.

The verdict ledger and the referenced paths in this doc are machine-checked by
`.harness-work/v3-docs-sync/check_docs_sync.py` (re-runnable; drift exits 1 with the
drift named). The architecture draft's as-built state is §7 of
`docs/v3/architecture-v3-draft.md`.

## Track verdicts (machine-checked ledger)

Source of truth: `docs/v3/outcome-table-20261111.md` / `.json` (registry
`docs/v3/outcome-tracks-20261111.json`; every row's evidence hash-verified at
generation time; regenerate with `scripts/build_outcome_table.py --check`).

- h1 — CONFIRMED (as amended) — model-free consolidation: 26/26 checks, 5/5 mutation controls, recall@5 0.9333 unchanged; value = graph hygiene + reranker substrate
- h2 — DISCONFIRMED — pure semantic rerank, both arms: recall@5 0.9333 → 0.6000 / 0.6667; do not integrate
- h3a — DISCONFIRMED — bounded semantic boost: the dominance trilemma closes the pure-rerank line (no δ lifts b1 without breaking A/D; ADD needs w > 6.3)
- h3b — SPLIT — rule L disconfirmed (false negatives b1/b3/e1); rule L2 confirmed once on the frozen 18 (f1+f3 suppressed, zero false negatives)
- h4 — DISCONFIRMED (v0) — dreaming control loop safe but not selective: orphan P 0.6071, edge P 0.3636; DC2/DC4/DC5 hold
- h5 — CONFIRMED — certified unlearning in boundary: D1–D6 none triggered, 8/8 probes zero hits, 17/17 non-target unchanged, 42/42 checks
- h6a — CONFIRMED — L2 production candidacy in envelope: 6/6 legs, p95 0.040 ms vs 100 ms budget; ships `HARNESS_KB_HONESTY`, default OFF
- h6b — CONFIRMED — backflow guard in boundary: 0 blocking false positives over 133 candidates, 7.7 ms per admission, relearn re-admits
- h6c — DISCONFIRMED overall — dreaming v1: edge arm fixed (P 0.80 / R 1.0), orphan ceiling ≈ 0.60 holds; line dormant pending a model-based stance check
- v2-node4 — OPEN / NOT_QUALIFIED — 16-case gate still exit 1 (4 partial); overlap-window arm rejected at +21.17% tokens (38,970 vs 32,162); DQ1

## Pipeline state

Six tiers in fixed order (push → unit → integration → e2e → perf → ship), fail-fast,
one hash-bound receipt per run, `scripts/pipeline.py verify <receipt>` re-checks it.
Push tier = tamper guard (first; every accepted test-surface diff carries a sha256-bound
attestation — 87 entries in `.harness-work/tamper-attestations.json`) + ruff +
secret-scan. A partial run (`--tier push`) exits 2 with verdict INCOMPLETE and FAIL=0 —
that is the documented posture, so "push tier green" gates use a per-workstream wrapper
that asserts push PASS + all commands exit 0 + receipt verifies (see
`.harness-work/v3-docs-sync/check_push_tier.py` for the pattern). Settlement hooks are
wired opt-in: `scripts/pipeline.py --tier push --settle plan/<slug>.md` appends the
settlement scan (an action is not done until its receipt closes) to the push tier for
that run only; the default registry is byte-identical without the flag.

## dev9 deploy: STAGED, fenced behind one owner command

`plan/v3-dev9-deploy-prep.md` 11/11 gated: immutable hash-bound offline bundle, disposable
install + transaction rehearsal + pre-install audit all PASS
(PASS_DEV9_PREINSTALL_AUDIT_ONLY), live installed tree verifiably still dev8, real
install fenced. Why dev9 matters beyond the version bump: the installed MCP plan server
predates the repo's recording-hygiene fix, so gate records can leak absolute paths that
the per-gate self-redaction then rewrites post-signing — the settlement checker's
inverse-redaction mode exists because of it; applying dev9 retires the cause for new
records.

Owner command (from the repository root):

    /usr/bin/python3 .harness-work/deploy-20261111-dev9/owner_apply_dev9.py --owner-approved

It re-runs the full pre-install audit, then stage + transactional deploy with backup,
then whole-tree byte verification against the frozen inputs. The MCP server restart and
the cold readback afterwards are the owner's.

## Owner-decision queue

- DQ1 — v2-completion nodes 5–8 (carried from the 2026-11-10 bridge; node 4 TERMINAL):
  (a) accept the annotated confounded measurement and re-derive node 4's gate semantics;
  (b) leave 4 red / 5–8 blocked and treat the measurement as the v3-justifying evidence
  it was designed to be; (c) re-measure if the ambient confound becomes pinnable.
- DQ2 — dev9: run the owner command above (plus the MCP restart + cold readback after).
- DQ3 — H6a L2 first live enable: the honesty rule ships default OFF; the verdict's own
  honesty limits say the first live enable is a canary. Enable it, and when?
- DQ4 — dreaming dormancy: h4/h6c are dormant until a model-based stance check is
  authorized (the measured orphan ceiling is model-free; edges are fixed). Authorize the
  model-based track, or keep the line dormant?
- DQ5 — legacy settlement findings era-handling: the observational scan of the ten
  pre-sweep v3 plans found 28 done-nodes whose receipts do not close under the settlement
  checker, in three classes — 3 pre-convention done-marks with no gate note at all
  (v3-h1-consolidation nodes 1–3); 12 redaction-era tail divergences where the gate
  signature still verifies (v3-dev9-deploy-prep, v3-eval-pipeline); 13 pre-hygiene-fix
  signatures not re-derivable from the stored bytes (v3-eval-pipeline and the final
  mutation/summary nodes of h1–h6c). Options: an era-tolerant verification mode, a
  one-time receipt-repair pass, or attest-and-accept with this listing as the record.
  None is silently settled today. Detail: `docs/v3/settlement-plugin-loop-v0-verdict-20261111.md`.
- DQ6 — decision-layer v1 scheduling: the JEV substrate shipped (records, validator,
  admission loop); deferred to v1 are the policy engine on `routing.next_decision`, the
  `rea_check`/`jev_check` MCP tools, the registry amendment cadence, and any
  model-filled decision records (blocked until calibration is locally measured).
  Schedule any of these, or hold?

## Workstreams landed on 2026-11-11 (all 7/7 gated)

- REA support (`plan/v3-rea-support.md`): `harness.rea-record/v1` — lawful, pinned,
  evidence-bound source-analysis records; observed/inferred separation enforced;
  Lever record at `docs/v3/rea/lever-20261105.json`. Verdict:
  `docs/v3/rea-support-v0-verdict-20261111.md`.
- JEV + NEEDLE (`plan/v3-jev-needle.md`): `harness.jev-decision/v1` typed-decision
  records (fail-closed; authority required; hash-bound inputs) + the outcome table
  above. Verdict: `docs/v3/jev-needle-v0-verdict-20261111.md`.
- Settlement hooks + plugin admission loop (`plan/v3-settlement-plugin-loop.md`):
  settlement records + checker + `pipeline.py --settle`; the admission loop
  (REA qualification → JEV adoption decision → fail-closed admission) with registry
  `docs/v3/plugin-registry-20261111.json` (first entry:
  lever-experiment-contract-pattern, admitted). Verdict:
  `docs/v3/settlement-plugin-loop-v0-verdict-20261111.md`.
- Docs sync (`plan/v3-docs-sync.md`, this slice): architecture §7 as-built addendum,
  this bridge, and the consistency gate `.harness-work/v3-docs-sync/check_docs_sync.py`.
  Verdict: `docs/v3/docs-sync-v0-verdict-20261111.md`.

## Where the evidence lives

Verdict docs per track under `docs/v3/` (h2/h3/h4/h5/h6a/h6b/h6c verdicts; h1's evidence
in `.harness-work/v3-h1-consolidation/`); receipts per workstream under
`.harness-work/v3-*/`; pipeline run receipts under
`.harness-work/eval-pipeline-20261110/runs/`; tamper attestations
`.harness-work/tamper-attestations.json`; settlement document
`.harness-work/v3-settlement-plugin-loop/settlement-20261111.json`; docs-sync bindings
`.harness-work/v3-docs-sync/bindings-20261111.json`. Session findings persist in the
harness memory store (mem_add, scope user, tags agent-harness/v3/…).
