# REA support v0 — verdict

2026-11-11. Verdict for plan/v3-rea-support. Design:
docs/v3/rea-support-design-20261111.md. All gates run via the plan tool;
pytest gates on /usr/bin/python3 (3.9.6, pytest 8.4.2); zero network, zero
native/model calls, no commits, additive only.

## What shipped

| artifact | role |
|---|---|
| `docs/v3/rea-support-design-20261111.md` | intake contract, schema, five decision types, plan/workgraph/pipeline integration, useful-tools support surface |
| `src/agent_harness/rea.py` | `harness.rea-record/v1` schema, fail-closed `validate`, on-disk `verify_bindings` / `verify_record` |
| `tests/test_rea_support.py` | 33 tests, both directions per rule; runs under pytest and unittest |
| `docs/v3/rea/lever-20261105.json` | real retroactive record from the documented Lever decision |
| `.harness-work/v3-rea-support/check_design.py` | node 4 structural gate (35 required elements) |
| `.harness-work/v3-rea-support/check_rea_v0.py` | node 6 master control check (8 checks) |

## Gate exits

| node | gate | exit |
|---|---|---|
| 1 analyse | `phase-check v3-rea-support analysis` | 0 |
| 2 research | `phase-check v3-rea-support research` | 0 |
| 3 plan | `phase-check v3-rea-support plan` | 0 |
| 4 DESIGN | `check_design.py` | 0 (after two recorded failures: root-resolution bug, case-sensitive phrase — both fixed in the check, not the doc) |
| 5 IMPLEMENTATION | `/usr/bin/python3 -m pytest -q tests/test_rea_support.py` | 0 (33 passed) |
| 6 CONTROLS | `check_rea_v0.py` | 0 (8/8) |
| 7 hygiene | `/usr/bin/python3 scripts/pipeline.py --tier push` | see plan record |

## Controls matrix (check_rea_v0.py, 2026-11-11)

| control | direction | result |
|---|---|---|
| real record | intact validates + bindings verify on disk | OK |
| C1 license absent | refused: `invalid license spdx` | OK |
| C2 source unpinned | refused: `unpinned source version` | OK |
| C3 inference as observed | refused: `observed claim c6 cites no bound evidence` | OK |
| C4 bound evidence mutated | refused: `hash mismatch` (tmp-tree mutation) | OK |
| C5 unknowns emptied | refused: `invalid unknowns list` | OK |
| C6 pin/binding inconsistent | refused: `upstream-pin digest must equal the version pin` | OK |
| intact re-pass | still passes after all mutations | OK |

## The example record

`docs/v3/rea/lever-20261105.json` — retroactive record of the 2026-11-05
Lever decision (docs/v2/references/lever-20261105.md, sha256 6bcb18ea…):
subject github/lever pinned at e9c4befa…, license MIT (GitHub, Inc.) evidenced
via the bound doc, reading scope copied from the note's own declaration,
4 observed claims (documented ×4 incl. the NOT_RUN declaration) + 1
source-observed local-fit claim + 1 explicitly inferred claim, 4 unknowns,
decision **pattern-only** (`paraphrase_only: true`, `code_copied: false`),
promotion NOT_GRANTED. The unit suite re-verifies this record on every run, so
a mutated evidence doc fails CI, not just the one-off control.

## Known limits (honest boundaries of v0)

- Zero-network v0: upstream bytes are bound by commit pin only, not hashed
  locally; the record's honesty rests on the bound local evidence doc.
- The validator checks STRUCTURE (license present, claims bound, per-type
  fields); it cannot judge whether a statement is true — that remains
  review's job (phase_check.py's own lesson: presence of a THING, never a
  judgement about meaning).
- `measured` observation claims have no receipt-channel integration yet, so
  v0 records carry documented/source-observed claims only.
- Plan `ctx:` citation of a record is convention in v0; no engine enforcement.

## What v1 would add

1. A `rea_check` MCP tool so `plan gate` can validate a cited record inline
   (workgraph surface, additive).
2. An REA record for the upstream REA toolkit itself before any adoption —
   the bootstrap rule from the design doc (§7).
3. A first-party `source-analysis` SKILL.md teaching the record format
   (ranked adaptation #9 surface).
4. Receipt-channel integration for `measured` claims (pipeline evidence_file
   channel precedent).
5. HAR/session-to-eval-environment compilation — deferred: no local
   recorded-session surface exists.
