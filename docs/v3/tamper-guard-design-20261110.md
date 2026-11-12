# Tamper guard — design for the plan/gate spine

2026-11-10. DESIGN — not implemented. Adapts no_human's mechanism (sweep 3,
docs/v3/oss-mechanics-20261110.md) onto our workgraph. Evidence base: 44 attempts
stopped pre-review for test tampering in 65 days of no_human self-building;
Anthropic/OpenAI both treat test integrity as mechanical, not prompted.

## What it is

A static, model-free check that runs BEFORE any gate whose result could be
weakened by reducing tests. It compares the working tree's test surface against
a recorded baseline and stops the run when the surface shrank without a
justification on record.

## Mechanism (adapted, with their bug fixed)

1. **Test surface inventory**: enumerate every test file via
   `git ls-tree -r -z HEAD -- tests/ eval/` PLUS untracked test files (our repo
   carries untracked test files in the working tree — ls-tree alone would miss
   them; use `-z` quoting so non-ASCII names cannot escape the comparison —
   no_human's disclosed bug).
2. **Count mechanically, no model**: per file — test functions (def test_*),
   skip/xfail markers, and assertion density. Surface = (files, functions,
   skips, assertions) tuple per path.
3. **Baseline**: the last gate-passing commit's surface, stored as
   `.harness-work/tamper-baseline.json` refreshed ONLY on gate PASS. (no_human
   uses merge-base; our linear plan/gate flow has no branches — last-green is
   the honest baseline.)
4. **Trip conditions**: net function count drop; any file deleted; new skip/xfail
   added; assertion density drops >20% in a touched file; "no test command found"
   recorded as explicit NOT_RUN verdict, never blank.
5. **Justification path, not auto-fail**: a trip stops the gate and requires a
   `tamper-justification:` line in the plan node record referencing the
   acceptance criterion that legitimately removes coverage. The justification is
   recorded, auditable, and itself evidence. Legitimate feature removal deletes
   tests — numeric auto-fail would be wrong.
6. **Ordering**: runs before any model-consuming review/eval step — tampering
   must never spend reviewer budget.

## Where it hooks our spine

- `plan gate <slug> <id>` runner (src/agent_harness/workgraph/plan.py): the
  tamper check executes first; a trip returns exit 2 with the finding list and
  does not run the node's gate command.
- Baseline refresh happens only inside the PASS path of the same runner, so a
  weakened tree can never become the new baseline.

## Known blind spots (carried from no_human + Skylos notes, accepted for v0)

- Value-changed assertions (same shape, different expected value) and fixture
  edits evade static detection → covered instead by our existing mutation
  controls on critical suites.
- Detection precision for "tautologized" assertions is heuristic; v0 counts
  assertion density only.

## Qualification path (when approved)

New plan node with gate: fixture repo where (a) a test deletion trips the guard,
(b) a justified removal passes with the record, (c) a non-ASCII test filename
trip is caught (regression for their bug), (d) a PASS refreshes the baseline.
Estimated: ~150 lines + tests; zero new dependencies; zero tokens.
