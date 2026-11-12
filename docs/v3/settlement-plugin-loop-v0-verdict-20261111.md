# Settlement hooks + plugin admission loop v0 — verdict note

Plan `plan/v3-settlement-plugin-loop.md`, 2026-11-11. Design:
`docs/v3/settlement-plugin-loop-design-20261111.md`.

## Verdict

**ADOPTED as specified — v0 ships in the tree behind its gates.** Both
mechanisms are built, every acceptance test written before implementation is
green, and every control fails in the direction it must. No amendments to v0
scope were needed.

## What shipped

Settlement hooks (Pi pattern — an action is not done until its settlement
receipt closes):

- `src/agent_harness/settlement.py` — schema `harness.settlement-record/v1`:
  one record per scanned node {plan, action, expected_receipts (graph-note +
  node-record), status open/settled/failed, settled_by hash-bound evidence
  (note sha256, record sha256, gate signature, verification mode), detail}.
  The receipt chain: exit-0 note WITH a signature; the node record file; the
  last applied Attempt exit-0 and duration agreeing with the note; the note
  tail rebuilt from the record body; the gate signature re-derived from the
  stored body — `direct`, or `inverse-redacted` when the post-gate hygiene
  redaction rewrote the bytes after signing (tokens resolved from the live
  environment, never stored). UNKNOWN is never zero: one record per parsed
  node; a done node it cannot classify is failed, never omitted.
- `scripts/check_settlement.py` — the CLI: explicit `--plan` set (an empty
  scan is a usage error), exit 0/1/2, atomic document emission.
- `scripts/pipeline.py --settle PLAN` — the opt-in wiring (see decisions).
- `tests/test_settlement.py` — 17 tests, green under pytest and unittest.
- Receipt: `.harness-work/v3-settlement-plugin-loop/settlement-20261111.json`.

Plugin admission loop (DSH pattern — no capability is repo-resident without
the loop):

- `src/agent_harness/plugin_loop.py` — schemas `harness.plugin-candidate/v1`
  and `harness.plugin-registry/v1` (entries `harness.plugin-admission/v1`).
  Stages: qualification (an REA record is REQUIRED; declared sha256 must
  equal the bytes, then rea.validate + verify_bindings on disk) → typed
  decision (a JEV domain=adoption record is REQUIRED, subject.name must
  equal the candidate name) → admission (verdict must equal admit_verdict;
  confidence must meet policy.execute_at_or_above; below threshold
  ESCALATES — refused, never auto-admitted). Refusals are registered,
  first-class outcomes; promotion is always NOT_GRANTED.
- `scripts/admit_capability.py` — the CLI; idempotent re-admission with
  identical bindings (gates re-run), any other duplicate name refuses.
- `tests/test_plugin_loop.py` — 14 tests, green under pytest and unittest.
- Registry: `docs/v3/plugin-registry-20261111.json`.

## The example run

`lever-experiment-contract-pattern` (kind pattern), retroactively processed:
discovery `docs/v3/plugin-candidates/lever-pattern-20261111.json` →
qualification by the EXISTING `docs/v3/rea/lever-20261105.json` (MIT, pinned
commit, pattern-only) → typed decision by the NEW
`docs/v3/jev/lever-pattern-adoption-20261111.json` (verdict
adopt-pattern-only, confidence high vs a medium threshold, inputs hash-bound
to the REA record and the rea-support design/verdict docs, receipt bound to
the v3-rea-support push-tier run) → ADMITTED, registry entry hash-bound to
both records. Re-running the admission is idempotent and re-verifies both
records on disk.

## Design decisions (the judgment calls, documented)

1. **Opt-in push-tier command, not a new tier.** The pipeline receipt schema
   pins TIER_ORDER (six tiers) and `verify()` requires the exact tuple; a
   seventh tier would invalidate every historical receipt's verification
   contract. `--settle` appends the settlement scan to the push tier for
   that run only; `default_registry()` is untouched and default runs are
   byte-identical (tests/test_pipeline_runner.py stays green). Settlement is
   tree hygiene — it sits with the tamper guard and secret-scan.
2. **Inverse-redaction is machine-local and token-only.** The post-gate
   hygiene redaction (owner convention) rewrites stored gate output after
   signing; verification reconstructs the signed bytes from LIVE home/host/
   user values mapped from the documented tokens — literals carry no real
   identifier, and a relocated repo reports failed rather than silently
   settling.
3. **The signed surface is the fenced Attempt body.** Bytes outside fences
   (legitimate Summary sections) are not signature-covered; the whole-file
   record sha256 pinned in every settlement record makes outside-fence
   drift detectable against the last emitted document.
4. **Refusals are registered.** A refused admission is written to the
   registry with its stage's named reason (NEEDLE: every outcome has a
   handler), so the loop's denials are as auditable as its admissions.
5. **Live source is referenced, not hash-bound.** The Lever record binds
   frozen dated artifacts; the embodied artifact (loop_contract.py) is named
   in the confidence basis text, so later source edits evolve the capability
   without falsely invalidating the decision record.

## Findings the hook exists to surface (observational, not gated)

An observational scan of the ten OTHER v3 plans (75 settled, 28 failed, 0
open) found three legacy classes, all pre-dating this sweep's receipt
convention:

- **3 nodes** (v3-h1-consolidation 1–3): done-marks with no exit-0 gate
  note at all — written notes only, from before gate records were the
  convention. Reported as "done-mark without an exit-0 gate note".
- **12 nodes** (v3-dev9-deploy-prep, v3-eval-pipeline): note tail diverges
  from the record body (raw path vs tool-redacted `<repo>` form) while the
  gate signature still verifies direct — era divergence in the stored
  receipts, not forged output; the record says so.
- **13 nodes** (v3-eval-pipeline 8/11/12/14/16, and the final mutation/
  summary nodes of h1–h6c): the signature is not re-derivable from the
  stored bytes — the pre-recording-hygiene-fix era signed output the stored
  form can no longer reproduce. Genuinely unverifiable; reported failed.

None of these is silently settled, and none blocks this workstream: the
three decision/evidence-layer plans built under the current convention
(v3-rea-support, v3-jev-needle, v3-settlement-plugin-loop) settle 100%
(18 settled at node-5 gate time, 21 by node 7, 0 failed). What to DO with
the legacy classes — an era-tolerant verification mode, a one-time
receipt-repair pass, or attest-and-accept — is a v1 decision for the owner.

**Redaction-under-MCP finding** (design doc §3, carried here):
`redact_machine_paths` does not fire under MCP-mediated gates, so gate
records can carry absolute paths that the post-gate hygiene redaction then
rewrites post-signing — the `inverse-redacted` verification mode exists
because of it. Fixing root/home resolution in the server process is v1
(signature inputs are repo-wide; changing them mid-flight breaks STUCK
continuity).

## Acceptance evidence

- Nodes 1–3 phase gates: PASS, exit 0.
- Node 4 design gate: PASS, exit 0 (32 required elements).
- Node 5 settlement gate: PASS, exit 0 (17 passed + 4-check master).
- Node 6 plugin-loop gate: PASS, exit 0 (14 passed + 5-check master).
- Node 7 hygiene gate: push-tier wrapper with `--settle` exercised against
  the three v3 plans (tamper guard + ruff + secret-scan + settlement scan
  all exit 0 on the hash-bound receipt; receipt verifies).

## Controls matrices (both directions)

Settlement (17 tests + 4-check master): intact settles direct /
inverse-redacted | fabricated done-mark without receipts fails | missing
record file fails | sig-less note fails unverifiable | tampered body fails
the signature check | tampered tail fails the tail check | newer applied
failure under a done-mark fails | re-claim NOT-APPLIED notes are benign |
duration mismatch fails | open nodes listed, never failed | unrecognized
node lines raise | empty scan refuses | the live tree stays at zero failed.

Plugin loop (14 tests + 5-check master): intact admits with full receipts |
missing REA record refuses at qualification | REA hash drift refuses |
internally-invalid REA refuses | missing JEV refuses | wrong JEV domain
refuses | subject mismatch refuses | verdict mismatch refuses |
below-threshold confidence ESCALATES and never auto-admits | threshold
equality admits | duplicate-with-changed-bindings refuses, identical is
idempotent | malformed candidate/registry raises | the real Lever candidate
re-admits against the live tree.

## What v1 adds (explicitly out of v0)

1. **Fix redaction-under-MCP at the source** (root/home resolution in the
   plan server process), retiring the need for inverse-redaction on new
   records; a signature-input change is its own gated workstream.
2. **Decide the legacy classes**: era-tolerant verification mode, one-time
   receipt repair, or attest-and-accept, per plan.
3. **Gate-time settlement emission**: the plan tool closes the receipt at
   gate time (Pi's actual hook model — the awaited subscriber writes the
   settlement record) instead of a scanner proving it after the fact.
4. **Admission as an MCP tool + registry amendment cadence**: who proposes
   candidates, on what evidence, at what rhythm (mirrors the outcome-table
   registry cadence item in the JEV/NEEDLE verdict note).
5. **Model-filled decisions stay out** until calibration is locally measured
   (carried unchanged from the JEV/NEEDLE verdict).

## How this closes the sweep-derived build-out

The sweep's Adapt lines are now all mechanism-backed, end to end: REA v0
(qualification: every conclusion ships with attached evidence) → JEV v0
(typed decisions with confidence and policy) → NEEDLE v0 (the hash-bound
outcome surface) → **settlement v0 (done means the receipt closes; unsettled
is enumerated, never assumed)** and the **admission loop v0 (no external
capability is repo-resident without REA qualification and a JEV adoption
decision)**. The two ends of "done" — work claimed done, capabilities
claimed resident — now both fail closed.
