# Settlement era-handling — decision brief (DQ5)

2026-11-11. Informs owner decision DQ5 of `docs/v3/session-bridge-20261111.md`.
Findings source: `docs/v3/settlement-plugin-loop-v0-verdict-20261111.md`
(observational scan of the ten pre-sweep v3 plans: 75 settled, 28 failed,
0 open at scan time; the three sweep-era plans settle 100%). This brief is
analysis only — it decides nothing and changes nothing.

## Re-measurement (2026-11-11, this brief)

The scan was re-run for this brief (`scripts/check_settlement.py --plan` over
the same ten plans). Current: **104 nodes, 75 settled, 29 failed, 0 open —
class A 3 / B 13 / C 13**. The +1 vs the verdict is `v3-eval-pipeline` node
19 (tool resolution), added and gated at 15:50 local, AFTER the verdict's
scan — plan evolution under the same pre-fix recorder era, not a settled
node flipping. All 13 verdict-named class-C nodes are still unverifiable;
none recovered, none newly settled. The decision should use these numbers.

## The three era classes (29 nodes, re-measured)

- **Class A — 3 nodes** (v3-h1-consolidation 1–3): done-marks with no exit-0
  gate note at all. Pre-dates gate records as the convention. Supporting
  evidence exists unhashed under `.harness-work/v3-h1-consolidation/`.
- **Class B — 13 nodes** (v3-dev9-deploy-prep 5/6/9/11; v3-eval-pipeline
  5/6/9/10/13/15/17/18/19): the note tail diverges from the stored record
  body (raw-path vs tool-redacted `<repo>` form) while the gate signature
  **still verifies direct** against the stored body. Era divergence in the
  stored receipts, not forged output.
- **Class C — 13 nodes** (v3-eval-pipeline 8/11/12/14/16, plus the final
  mutation/summary nodes of h1–h6c): the gate signature is not re-derivable
  from the stored bytes. The pre-recording-hygiene-fix server signed output
  whose stored form can no longer reproduce the signed bytes. Genuinely
  unverifiable; the raw signed bytes are gone.

## Options

### 1. Era-tolerant verification mode — recommended AGAINST

A standing tolerance keyed on plan/era is a permanent hole: any FUTURE
genuine failure in those ten plans would settle under the tolerance and
never surface. Fail-closed must keep meaning fail-closed for everything
after the decision date. Every acceptable option below keeps the checker
exactly as strict as today for anything not individually excepted.

### 2. One-time receipt-repair pass — feasible for Class B only

- **Class B: feasible and honest.** The note tail is a *derived view* of the
  record body (last 3 non-empty lines, 400 chars — `_tail_of` in
  `src/agent_harness/settlement.py`); the gate signature covers the record
  body, not the note text. Realigning the tail to the stored body fabricates
  nothing: the signed evidence bytes are untouched. Shape: a scripted
  one-time pass editing ONLY the tail field of each affected note line
  (exit/secs/signature fields untouched), recording before/after sha256 of
  each plan file as a receipt, then a re-scan that must settle all 13
  direct. Feasibility against every note-line consumer is VERIFIED — see
  the addendum below; the one implementation-time recheck is the
  secret-scan exemption list (some entries exist because of the raw-path
  tails this pass removes).
- **Class A: impossible as repair** — no signed bytes exist. The nearest
  honest equivalent, re-running those gates today, verifies TODAY's tree,
  not the era's work. Legitimate as current-state verification, not as era
  closure.
- **Class C: impossible** — the signed raw bytes were never stored by that
  era's recorder.

### 3. Attest-and-accept — feasible for all classes

A dated, class-scoped attestation ledger, mirroring the tamper-attestation
pattern (schema-bound, evidence sha256-bound, non-empty dated reason).
The checker gains a narrow `--attestations FILE` flag: a failed (plan, node)
pair matching a ledger entry reports a NEW status `settled-by-attestation`
— never `settled` — so attested nodes stay distinguishable forever.
Ledger entries that match nothing raise (no stale holes); a malformed
ledger is an ERROR (fail-closed); every unmatched failure stays failed.

## Recommendation: hybrid by class

| Class | Nodes | Handling |
|---|---|---|
| B (signature verifies) | 13 | Receipt-repair: scripted tail realignment + receipt + re-scan |
| A (no gate note) | 3 | Attest-and-accept, entries citing a sha256-pinned listing of `.harness-work/v3-h1-consolidation/` |
| C (signature unrecoverable) | 13 | Attest-and-accept, entries citing each node's verdict doc / plan |

End state: 88 settled (75 today + 13 repaired), 16 settled-by-attestation,
0 failed, 0 open — every node accounted for, no standing tolerance, and the
distinction between cryptographically settled and owner-attested is
preserved in the data forever.

Simpler fallback: attest-and-accept all 29 (skips the repair; acceptable,
but wastes Class B evidence that still verifies and leaves a stored
divergence in place forever).

## The cost of doing nothing

The findings block nothing today — they are observational and the sweep-era
plans settle clean. But every future `--settle` scan of those ten plans
will report 29 failed, forever. A scan that always reports failures trains
its reader to ignore failures; that is exactly the signal the settlement
hook exists to protect. Doing nothing quietly degrades the control.

## Addendum: class-B repair feasibility, verified pre-decision (2026-11-11)

The repair edits note-line tails in historical plan files, so every consumer
of plan note lines was checked for an integrity constraint the edit would
trip. None exists that applies between tool operations:

1. **Note format** — `workgraph/plan.py:109` `NOTE_RE` captures the tail as
   free text (`— (.*)$`); nothing validates it at load.
2. **Signature** — `gate_signature(blob)` (`plan.py:564`) signs the gate
   output blob only; the note's tail field is never an input, so the edit
   leaves the `[8-hex]` signature valid (settlement re-derives it from the
   stored record body, which the repair does not touch).
3. **Workgraph tamper repair** — the snapshot/restore guard
   (`plan.py:3186–3227`, `3394–3406`) builds `snapNoteLines` from
   `load(slug)` at the START of each operation, in memory only. It catches
   a worker rewriting history DURING a dispatch round; it persists no hash
   of note lines, so a receipted edit made between operations simply
   becomes the next operation's baseline.
4. **Settlement checker** — `settled_by.note_sha256` binds the note line,
   but only for records settled AFTER the edit; the 13 class-B nodes are
   failed (never settled) and the only persisted settlement documents cover
   the sweep-era plans.
5. **Docs-sync bindings** — `.harness-work/v3-docs-sync/bindings-20261111.json`:
   15 bindings, zero reference `plan/` files.
6. **Tamper guard** — surface is `tests/` + `eval/` only (eval-pipeline
   design doc, Amendment 3/4 discussion); `plan/` is not covered.
7. **Pipeline artifact-pinning** — default tiers pin invoked files; plan
   files enter runs only via opt-in `--settle`, whose historical receipts
   are not re-verified when plans change.

One implementation-time recheck remains: `scripts/secret-scan.sh`'s scoped
exemption list includes entries motivated by the raw-path tails this pass
removes — after realignment, confirm no exemption is load-bearing in the
other direction (a scan that errors on unused exemptions would need the
list pruned in the same change).

## Implementation sketch (only after the owner picks)

- Ledger: `.harness-work/settlement-attestations.json`, schema
  `harness.settlement-attestations/v1`; entries {plan, node, class,
  evidence: [{path, sha256}], reason, date}.
- `settlement.py`: new status value; `check_settlement.py`: `--attestations`
  flag; tests for: attested failure reports settled-by-attestation / stale
  entry raises / unmatched failure stays failed / malformed ledger is an
  ERROR. New test file carries a tamper attestation per convention.
- One gated workstream (~4 nodes), push tier green to close.

## Standing prevention (already tracked, not part of this decision)

New instances stop when dev9 deploys (DQ2 ships the recording-hygiene fix);
the redaction-under-MCP root fix (root/home resolution in the server
process) is v1 per the verdict note's "What v1 adds" #1.
