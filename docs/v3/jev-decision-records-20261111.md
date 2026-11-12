# JEV typed-decision records + NEEDLE outcome table — design v0

2026-11-11. Design for plan/v3-jev-needle (node 4). Sources:
docs/v3/harness-pillars-20261110.md ("REA / JEV resolved"; ranked adaptation
#5), docs/v3/oss-mechanics-20261110.md (NEEDLE outcome handlers), and the
sibling schema conventions of harness.rea-record/v1
(docs/v3/rea-support-design-20261111.md, src/agent_harness/rea.py).

## 1. What this unifies

The harness already MAKES typed decisions and records each kind differently:
workgraph gate verdicts (exit 0 in a node record), `routing.next_decision`
verdicts (tier or HOLD), REA dependency decisions (the five types of
harness.rea-record/v1), hypothesis verdicts (CONFIRMED/DISCONFIRMED across
the H1–H6c docs), promotion holds (NOT_GRANTED). Nothing links them: no
common envelope for confidence, scope, reversibility, authority, or the
evidence a decision binds.

JEV v0 is that common envelope: ONE typed decision record,
`harness.jev-decision/v1`. Jev itself (TypeSafe AI's "System One" model —
typed Choice/Score/boolean verdicts with confidence in one pass) contributes
the SHAPE. We adopt the record, **not the model**: its calibration is
vendor-stated and unaudited (sweep 2, "Unverified"), and this track makes
zero model calls — v0 records are filled by gates and humans, and the
execute-above-confidence / escalate-below rule is recorded as POLICY, not
enforced by an engine (the engine is architecture-v3-draft §2.4 phase 4;
this is its substrate).

## 2. Schema — `harness.jev-decision/v1`

Exact fields everywhere (the rea.py discipline); validation raises on the
first defect; filesystem checks live in one separate verifier.

| field | rule |
|---|---|
| `schema` | the literal id |
| `record_id`, `created` | non-empty text |
| `subject` | `{name, question}` — what is being decided |
| `kind` | one of `choice`, `score`, `boolean` (the Jev primitives) |
| `domain` | one of `dependency`, `hypothesis`, `adoption`, `promotion`, `routing`, `escalation` |
| `options` | choice: non-empty list, verdict must be a member; boolean: must be empty, verdict ∈ {YES, NO}; score: `score_range {min,max}` required, verdict must parse as a number inside it |
| `verdict` | per kind above — **a verdict outside its enum refuses** |
| `confidence` | `{level: high\|medium\|low, basis}` — basis names the evidence, not a vibe |
| `policy` | `{execute_at_or_above: high\|medium\|low, below: "escalate"}` — ranked adaptation #5 as data: execute above confidence, escalate below; `below` is fixed to escalate (fail-closed) |
| `scope` | the envelope text — every confirmation in this repo is bounded; the record must say where it holds |
| `reversibility` | `reversible` \| `reversible-with-receipt` \| `irreversible` (mirrors the workgraph's `risk: irreversible`) |
| `authority` | who/what decided — a plan node gate, the owner, a check script. **Missing authority refuses**: an authority-free decision is a rumor |
| `inputs` | non-empty evidence bindings `{ref, kind, role, digest}` (local-file sha256 re-hashed on disk by the verifier). **Unbound inputs refuse** |
| `receipts` | repo-relative receipt paths; the verifier requires each to exist |
| `unknowns` | non-empty — the UNKNOWN is never zero doctrine carried from harness.rea-record/v1 |
| `promotion` | always `NOT_GRANTED` — a decision record is evidence, never authority |

## 3. REA consistency

A harness.rea-record/v1 decision IS expressible as a JEV record: domain
`dependency`, kind `choice`, options = the five REA types (reuse, adapter,
fork, pattern-only, independent build), verdict e.g. `pattern-only`, inputs
= the REA record's own evidence bindings. The mapping is unit-tested against
the real Lever record (docs/v3/rea/lever-20261105.json). The reverse is not
required: REA keeps its richer per-type evidence requirements; JEV is the
envelope.

## 4. The retrofit example: H6a

The real v0 record (docs/v3/jev/h6a-l2-candidacy-20261111.json) retrofits the
H6a ship decision: domain `adoption`, kind `choice`, options
{ship-opt-in-default-off, ship-default-on, do-not-ship}, verdict
**ship-opt-in-default-off** — L2 ships in kb.py as `HARNESS_KB_HONESTY`,
default OFF. Confidence high (basis: all six pre-registered legs green on the
fresh 15 plus 18/18 stability), scope = the documented envelope (the x1
thin-worded false-negative hole), reversibility = reversible (flag off is
byte-identical), authority = plan v3-h6a-l2-candidacy's gated nodes plus the
contract's "no parameter change is licensed" posture, inputs bound to the
verdict doc + eval/controls artifacts by sha256, receipts pointing at the
same artifacts.

## 5. NEEDLE outcome table

NEEDLE's rule — "if an outcome can happen, it has a handler" — applied to
hypothesis outcomes: the outcome table is the harness's single
machine-readable answer to "what did each v3 track conclude, and where is
the evidence?"

- **Registry**: `docs/v3/outcome-tracks-20261111.json` — one entry per track:
  H1, H2, H3a, H3b, H4, H5, H6a, H6b, H6c, and the v2 node-4 campaign. Each
  entry: hypothesis, pre-registered criteria, observed key numbers, verdict,
  and bindings = `{path, sha256}` of the verdict doc(s) and receipt(s) the
  entry claims to summarize.
- **Generator**: `scripts/build_outcome_table.py` re-hashes every bound file
  and emits `docs/v3/outcome-table-20261111.md` + `.json`. A mutated verdict
  doc FAILS generation (hash mismatch); a missing receipt refuses (no
  silently-skipped rows — **absent rows are impossible**: the emitted table
  must contain exactly the registry's tracks or generation fails). Writes are
  all-or-nothing.
- **Amendment semantics**: the registry binds doc BYTES as of 2026-11-11.
  Verdict docs do get amended (the H4/H6c dated-amendment precedent); a later
  legitimate amendment takes the same path — a dated, additive registry
  amendment — never a silent re-bind. The generator never updates the
  registry itself.
- **--check mode**: verify bindings + regenerate + byte-compare with the
  emitted docs; drift exits nonzero. This is the node 6 gate's core.

## 6. Non-goals for v0

- No Jev-model or any model pass (vendor calibration unverified; zero model
  calls in scope) — the record shape only.
- No routing-engine change: `routing.next_decision` stays advisory and
  untouched; the policy field is data for the phase-4 engine, not a live
  switch.
- No edits to any verdict doc or receipt; the live corpus untouched.
- No engine enforcement of ctx citations (convention only, as in REA v0).
