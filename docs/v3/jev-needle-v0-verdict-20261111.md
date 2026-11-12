# JEV + NEEDLE v0 — verdict and amendment note

Plan `plan/v3-jev-needle.md`, 2026-11-11. Design: `docs/v3/jev-decision-records-20261111.md`.

## Verdict

**ADOPTED as specified — v0 ships in the tree behind its gates.** Both surfaces
are built, every acceptance test written before implementation is green, and
every control fails in the direction it must. No amendments to v0 scope were
needed; v0 stands as designed.

## What shipped

JEV typed-decision records v0:

- `src/agent_harness/jev.py` — schema `harness.jev-decision/v1`: exact fields;
  kind ∈ choice/score/boolean; domain ∈ dependency/hypothesis/adoption/
  promotion/routing/escalation; verdict enum fail-closed per kind; confidence
  {level high/medium/low, basis}; policy {execute_at_or_above, below escalate}
  recorded as data; scope; reversibility ∈ reversible/reversible-with-receipt/
  irreversible; authority required; inputs non-empty hash-bound bindings;
  receipts must exist on disk; unknowns non-empty; promotion NOT_GRANTED.
- `tests/test_jev_decisions.py` — 23 tests, green under pytest and unittest:
  every fail-closed rule proven both directions, REA-expressibility (the Lever
  pattern-only decision as domain=dependency kind=choice), the real H6a record
  verified on disk.
- `docs/v3/jev/h6a-l2-candidacy-20261111.json` — one real retrofit record:
  the H6a adoption decision, inputs hash-bound to its verdict doc and
  contract, receipts bound to the eval and mutation-control artifacts.

NEEDLE outcome table v0:

- `docs/v3/outcome-tracks-20261111.json` — frozen registry: 10 tracks
  (h1, h2, h3a, h3b, h4, h5, h6a, h6b, h6c, v2-node4), 32 bound files, every
  sha256 computed from disk at authoring time.
- `scripts/build_outcome_table.py` — generator: verify-then-emit, atomic
  all-or-nothing writes, `--check` mode (verify + regenerate + byte-compare,
  writes nothing), row-completeness assert so an absent row is impossible.
- `docs/v3/outcome-table-20261111.md` / `.json` — the emitted table; every
  row's verdict doc and receipts re-hashed and verified at generation time.
- `tests/test_outcome_table.py` — 9 tests over fixture registries in tmp
  roots (deliberately not the live tree: verdict docs get legitimately
  amended), green under pytest and unittest.

## What the two unify

One typed decision envelope at decision time, one hash-bound outcome surface
at outcome time — the same binding discipline at both ends. A JEV record
binds its evidence as sha256-pinned inputs verified on disk; a NEEDLE row
binds its verdict doc and receipts the same way. Both fail closed: a record
that does not validate cannot be written; a table whose bindings drift or go
missing cannot be generated, and no row is ever skipped silently. The
hypothesis program's decisions (h1–h6c, v2-node4) and its outcomes are now
one continuous, auditable evidence chain.

## Acceptance evidence

- Nodes 1–3 phase gates (analysis / research / plan): PASS, exit 0.
- Node 4 design gate: PASS, exit 0 (24 required elements).
- Node 5 JEV gate: PASS, exit 0 (23 passed).
- Node 6 NEEDLE gate: PASS, exit 0 (9 passed + 4-check master: real `--check`
  byte-identical; intact skeleton 10 rows; tampered verdict doc refused with
  DRIFT, nothing emitted; missing receipt refused with MISSING, no silent
  row skip).
- Node 7 hygiene gate: push-tier wrapper (tamper guard + ruff + secret-scan
  on the hash-bound receipt, receipt verified).

## Amendments to v0

None. The v0 scope held: no model pass, no routing-engine change, no edits
to any verdict doc or receipt, convention-only ctx citations.

## What v1 adds (explicitly out of v0)

1. **Policy engine on `routing.next_decision`** — the recorded
   execute_at_or_above / escalate-below policy becomes a live switch
   (architecture-v3-draft §2.4 phase 4); v0 records are its substrate.
2. **`rea_check` / `jev_check` as MCP tools** — validation exposed through
   the server with the same fail-closed rules, so records are checkable at
   authoring time, not only in pytest.
3. **Registry amendment cadence** — today the outcome registry is amended by
   dated additive amendment with no rhythm; v1 defines who amends, on what
   evidence, and at what cadence (per workstream close, per freeze).
4. **Model-filled decisions stay out** until calibration is locally measured —
   the Jev model's calibration is vendor-stated and unaudited; any model fill
   requires a local calibration track first. v0 records are filled by gates
   and humans only.
