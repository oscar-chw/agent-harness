# Docs sync v0 — verdict note

Plan `plan/v3-docs-sync.md`, 2026-11-11. (Authored before this plan's node 6/7
gates run, so the session bridge's references resolve at gate time; gates are
described, not claimed — the claim lands when node 7 exits 0.)

## Verdict

**ADOPTED as specified — v0 ships in the tree behind its gates.** The docs now
match the built system, and a fail-closed gate keeps them that way.

## What shipped

- **Architecture as-built**: `docs/v3/architecture-v3-draft.md` gained §7, a
  dated as-built addendum (the planned §1–§6 text is unchanged — the draft is
  a planning record and stays one; the addendum records as-built truth).
  Per component of the §2 map and per phase of the §4 roadmap: planned →
  what shipped, with real verdicts and pointers — including the honest
  negatives (the learned-ranking line closed by disconfirmation;
  orchestration separation not built; the dreaming line dormant).
- **Session bridge**: `docs/v3/session-bridge-20261111.md` — a new dated
  doc (the 2026-11-10 bridge stands untouched). Full state for
  Codex/Claude sessions: the 10-track verdict ledger with one-line key
  numbers, pipeline state, dev9 staging with the exact owner command, the
  six-item owner-decision queue (DQ1–DQ6), the 28 legacy settlement findings
  with their three classes and the era-handling question (DQ5), and the
  conventions recap.
- **Consistency gate**: `.harness-work/v3-docs-sync/check_docs_sync.py` +
  the hash-bound evidence manifest
  `.harness-work/v3-docs-sync/bindings-20261111.json`, re-runnable:
  `/usr/bin/python3 .harness-work/v3-docs-sync/check_docs_sync.py`.

## The consistency gate's checks

1. **Verdict-class equality** — both docs (architecture §7 ledger, session
   bridge ledger) must state every one of the 10 NEEDLE tracks with the same
   verdict CLASS as `docs/v3/outcome-table-20261111.json` (CONFIRMED /
   DISCONFIRMED / SPLIT / OPEN, the leading token of the table's verdict).
   Completeness is enforced both ways: a track missing from a doc's ledger
   fails; a ledger id unknown to the table fails.
2. **Binding verification** — every entry in `bindings-20261111.json` (the
   outcome table md/json, the frozen registry, the per-track verdict docs,
   the three 2026-11-11 workstream verdicts, the plugin registry, this
   verdict note) must exist and hash-match its current bytes. Amending a
   bound doc without updating the manifest is drift and fails — that is the
   point; amendments take the dated, deliberate path.
3. **Referenced-path existence** — every backtick-quoted repo-relative path
   under docs/, plan/, .harness-work/, src/, scripts/, tests/, content/ in
   both docs must exist (directories for trailing-slash refs, files
   otherwise; placeholder tokens with `<…>` are skipped by design).
4. **Owner command** — the dev9 apply script must exist on disk AND the
   bridge must state the exact command.
5. **Decision-queue completeness** — DQ1–DQ6 must all appear in the bridge.

Exit 0 = consistent; 1 = drift, named; 2 = usage/internal. Controls proving
the gate fails when it must live in
`.harness-work/v3-docs-sync/check_docs_sync_controls.py`: a flipped verdict
class in a tmp bridge copy, a flipped binding hash, a deleted ledger line,
a mutated referenced path, and a missing owner-command path each exit 1
with the drift named.

## Drift the gate caught

During authoring, three real inconsistencies surfaced: (1) the renumbering
between the draft's sweep-1 H-numbering and the executed track ids (draft
"H4 unlearning" shipped as h5; draft "H5 RL data" stayed deferred) — the
addendum carries an explicit renumbering note rather than letting readers
map silently; (2) the dev9 connection: the installed MCP plan server
predating the recording-hygiene fix is the root cause of the gate-record
path leaks the settlement checker's inverse-redaction mode works around —
both docs record that applying dev9 retires the cause, which put DQ2 in the
queue with that consequence attached; (3) a second facet of the same dev8
recorder era, caught when the settlement scan failed node 6 closed: the
recorder stores `output.strip()` as the record body but signs the raw blob,
so a gate whose first output line leads with whitespace (this gate's nested
`OK` lines) stores a receipt whose signature cannot re-derive —
inverse-redaction covers path tokens, not whitespace. Resolution: the gate
now prints an indent-free header line first (same checks, same exit
contract, the controls still refuse by name) and node 6 was re-gated; the
divergent first attempt stays in the record as history. DQ2's consequence
list gains a second retired defect. Post-gate drift: none — the gate exited
0 at the node-6 gate and the controls refused each injected drift by name
(see the node record).

## What v1 adds

- Wire the consistency gate into the push tier (like `--settle`, an opt-in
  flag, or folded into the settlement scan) so docs drift blocks pushes
  without a wrapper remembering to run it.
- Extend verdict-class checking to key-number spot checks (the numbers are
  in the table's machine-readable `key_numbers`; a quoted-number check would
  catch numeric drift, at the cost of brittleness — deliberately not v0).
- The era-handling decision (DQ5) may add a settlement verification mode;
  that belongs to the settlement workstream's v1, not this gate.
