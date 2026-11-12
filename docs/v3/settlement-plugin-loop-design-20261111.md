# Settlement hooks + plugin admission loop — design v0

2026-11-11. Design for plan/v3-settlement-plugin-loop (node 4); v0 implements
nodes 5–6. Sources: docs/v3/oss-mechanics-20261110.md (Pi settlement, DSH
plugin architecture), docs/v3/jev-decision-records-20261111.md +
src/agent_harness/jev.py (typed decisions), docs/v3/rea-support-design-20261111.md
+ src/agent_harness/rea.py (qualification records), src/agent_harness/workgraph/
plan.py (the workgraph surface the hooks scan), scripts/pipeline.py (wiring).

## 1. What this unifies

The harness already records DECISIONS (JEV, `harness.jev-decision/v1`) and
OUTCOMES (the NEEDLE table) — but "done" itself is only asserted, never
proven, at both ends of the loop:

- **Work end.** A plan node flips to `[x]` the moment its gate exits 0.
  Nothing later checks that the receipt chain (graph note + node record +
  gate signature) still closes. A hand-edited mark is indistinguishable from
  a gated one — today.
- **Capability end.** External capabilities enter as adapted patterns or
  adapters justified by sweeps and REA records, but nothing enforces the
  intake discipline per capability: no record → no admission is a
  convention, not a mechanism.

Pi (sweep 3): awaited hook subscribers count toward run settlement, so a
hook can reliably gate progress — our pytest gates already ARE those
awaited subscribers; v0 makes settlement itself auditable: **an action is
not done until its settlement receipt closes**. DSH (sweep 3): everything
is a plugin the kernel mounts — v0 adopts the ADMISSION discipline for
external capabilities (discovery → qualification → typed decision →
fail-closed admission), not the Cordis/pnpm runtime (rejected per the
sweep).

## 2. Settlement — schema `harness.settlement-record/v1`

One record per scanned action, emitted by the checker as a JSON document
(`{schema, checked_at, records: [...]}`). Exact fields, fail-closed, the
rea.py/jev.py idiom.

| field | rule |
|---|---|
| `plan` | `{ref}` — the plan file scanned, repo-relative |
| `action` | `{node, title, mark}` — the workgraph node identity |
| `expected_receipts` | non-empty list: `graph-note`, `node-record` |
| `status` | `open` / `settled` / `failed` — see semantics below |
| `settled_by` | null unless settled: `{note_sha256, record_sha256, gate_signature, verification}` where verification ∈ `direct` / `inverse-redacted` |
| `detail` | one sentence: why settled/open/failed |

Status semantics: **open** = the node claims no done-mark (listed, never a
failure); **settled** = done-mark AND every expected receipt verified;
**failed** = a done-mark whose receipts are missing or unverifiable
(fabricated or tampered). UNKNOWN is never zero: the checker emits exactly
one record per parsed node; a done node it cannot classify is failed, never
omitted. Checker exit: 0 when no record is failed, 1 otherwise, 2 internal
error (fail-closed).

## 3. The receipt chain and signature re-derivation

For a done (`[x]`) node, the closing chain, all required:

1. **Graph note**: a note line under the node matching NOTE_RE with
   `exit 0` carrying an 8-hex `[sig]`. A sig-less exit-0 note cannot be
   hash-verified → failed (fail-closed, even for legacy plans).
2. **Node record**: `plan/<slug>/NN-*.md` exists → missing is failed.
3. **Attempt consistency**: the last fenced `## Attempt … exit N` block
   (falling back past blocks marked `NOT APPLIED`, which never settle a
   mark) must be exit 0; a newer applied failure under an `[x]` mark is an
   inconsistency → failed. The note's `in Ns` must equal the attempt
   heading's `Ns` (both derive from one `secs`).
4. **Signature**: `gate_signature` = sha1 over the normalised WHOLE output,
   8 hex, computed by the tool over the redacted-but-UNSTRIPPED blob while
   the record file stores `blob.strip()` — so the checker recomputes over
   the candidate set `{body, body+"\n"}`. A match is verification `direct`.
   (Probed 2026-11-11 against all seven v3-jev-needle nodes: `body+"\n"`
   reproduces every signature whose gate output carried no absolute path.)
5. **Post-signing redaction** (the honest case for a mismatch): when a
   gate's output carried absolute paths and the plan records were
   hygiene-redacted AFTER the gate (owner convention), the stored bytes
   differ from the signed bytes. The checker then tries inverse-redaction
   candidates: apply the documented token map — the literal tokens
   `/Users/me`, `redacted-host`, `agent@` mapped to the LIVE home,
   hostname and user from the runtime environment, never stored literals —
   then re-run the candidate set. A match is verification
   `inverse-redacted`: the stored body is proven authentic up to exactly
   the known hygiene tokens. No candidate matches → failed (tampered or
   corrupted receipt).
6. **Tail cross-check**: rebuild the note tail from the stored body (last
   three non-empty lines, stripped, ` / `-joined, 400-char cap) and compare
   to the note's tail — both in stored (post-redaction) space, so this
   binds note ↔ record even when the signature needs inverse redaction.

Two documented properties. **Machine-local by construction**: inverse
redaction binds verification to the machine that ran the gates; a relocated
repo reports failed/unverifiable, never silently settled. **8-hex sha1 is a
drift and hygiene control, not a security boundary** — the same posture the
tool's own STUCK detector takes with the same signature. **The signed
surface is the fenced Attempt body** (the gate output); bytes outside the
fences (e.g. Summary sections the tool appends legitimately) are not
signature-covered, but every settlement record pins the whole record file's
sha256 at scan time, so outside-fence drift is detectable against the last
emitted document — and a tampered attempt body fails the chain outright.

**Finding carried to v1 (not fixed here)**: `redact_machine_paths` does not
fire under MCP-mediated gates (root/home resolution in the server process),
so gate-record lines can carry absolute paths that the post-gate hygiene
redaction then rewrites post-signing — case 5 exists because of this.
Changing signature inputs repo-wide is its own workstream; see the verdict
note.

## 4. Pipeline wiring — opt-in, documented judgment

Decision: `scripts/pipeline.py --settle plan/<slug>.md` (repeatable)
appends one command `[python, scripts/check_settlement.py, --plan, …]` to
the PUSH tier for that run only. `default_registry()` is untouched, default
runs are byte-identical, and tests injecting stub registries are
unaffected. The wrapper `.harness-work/v3-settlement-plugin-loop/check_push_tier.py`
exercises this flag against the three v3 plans.

Why not a new tier: the receipt schema `harness.pipeline-receipt/v1` pins
`TIER_ORDER` (push → ship, six names) and `verify()` requires the exact
tuple with strict NOT_RUN semantics — a seventh tier would invalidate the
verification contract of every historical receipt and change INCOMPLETE
meaning for every caller. Why the push tier: settlement is tree hygiene
like the tamper guard and secret-scan — fast, runs no tests, belongs in
the tier that guards the tree. **Without the flag, nothing changes.**

`scripts/check_settlement.py`: `--plan PATH` repeatable, at least one
required, a missing path is exit 2 (fail-closed). Emits the settlement
document next to the workstream's receipts
(`.harness-work/v3-settlement-plugin-loop/settlement-<date>.json`) and
prints one line per action plus a verdict.

## 5. Plugin admission loop — schemas `harness.plugin-candidate/v1` + `harness.plugin-registry/v1`

Four stages (NEEDLE: if an outcome can happen, it has a handler — every
stage's refusal is a named, recorded outcome):

1. **Discovery** — a candidate descriptor at
   `docs/v3/plugin-candidates/<name>-<date>.json`: exact fields `{schema,
   name, kind, rea, jev, admit_verdict}`; kind ∈ plugin / skill / adapter /
   pattern; `rea` and `jev` are `{ref, sha256}` bindings; `admit_verdict`
   names the exact JEV option that admits.
2. **Qualification** — the REA record (`harness.rea-record/v1`) is REQUIRED:
   load, `rea.validate`, `rea.verify_bindings` against disk, and the
   candidate's declared sha256 must equal the file's current bytes. No REA
   record → refuse. (An external capability without a lawful, pinned,
   evidence-bound analysis is not admittable — the bootstrap rule from
   rea-support §7.)
3. **Typed decision** — the JEV record is REQUIRED: load, `jev.validate`,
   `jev.verify_bindings`; `domain` MUST be `adoption`; `subject.name` MUST
   equal the candidate name; the declared sha256 must match the bytes. No
   JEV adoption decision → refuse.
4. **Admission** — the verdict must equal `admit_verdict` exactly, else
   refuse; confidence ordinal must be ≥ `policy.execute_at_or_above`
   (low < medium < high), else ESCALATE — refused with the escalation
   named, never auto-admitted.

Registry (`harness.plugin-registry/v1`): `{schema, entries: [...]}`; each
entry `{schema, name, kind, status, rea {ref, sha256}, jev {ref, sha256},
verdict, confidence, detail, admitted_at, promotion}` with status ∈
admitted / refused and promotion always NOT_GRANTED (admission is
repo-local residency, never authority). `scripts/admit_capability.py
--candidate <file> --registry <file>` verifies-then-writes atomically
(all-or-nothing, the outcome-table idiom); one entry per name, a duplicate
refuses — amendments are new dated registry files. Refusals are written to
the registry too: a refused admission is a first-class auditable outcome.

## 6. The Lever example (retroactive)

The one existing repo capability processed through the loop in v0:
candidate `lever-experiment-contract-pattern` (kind `pattern`). REA:
`docs/v3/rea/lever-20261105.json` — exists, verified on disk (pattern-only
decision, MIT, pinned commit). JEV: `docs/v3/jev/lever-pattern-adoption-20261111.json`
— new, domain adoption, options adopt-pattern-only / hold / reject, verdict
adopt-pattern-only, confidence high against a medium threshold, inputs
hash-bound to the REA record + the rea-support design and verdict docs +
the embodied artifact src/agent_harness/loop_contract.py, receipts pointing
at the v3-rea-support push-tier run receipt on disk. Admission emits the
registry's first entry, status admitted, hash-bound to both records.

## 7. Non-goals for v0

- No new pipeline tier (receipt-schema stability); no default behavior
  change anywhere.
- No workgraph/plan.py core change — the redaction-under-MCP finding is
  documented (§3), not fixed; signature inputs are repo-wide and changing
  them mid-flight breaks STUCK continuity.
- No live capability beyond the one retroactive Lever example; no registry
  daemon (the registry is emitted by a script, like the outcome table).
- No model-filled decisions (vendor calibration unverified); promotion
  NOT_GRANTED everywhere; zero network, zero native/model calls.
