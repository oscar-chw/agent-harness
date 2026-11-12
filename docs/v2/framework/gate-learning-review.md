# Final correction review — 2 November 2026

Current verdict: **P2 ADDRESSED; no additional concrete correctness finding in
this bounded static review.** This replaces the earlier CHANGES_REQUESTED verdict
for the inspected correction only. The original finding and source identities
remain below as history. No tests, runtime edits, installs or model calls were
performed by this reviewer. This is not release/native/learning-efficacy
certification; root retains acceptance and integration authority.

## Why the original finding is addressed

- `plan.py:411` now derives learning identity from existing node definition,
  graph policy, declared check-file fingerprints and non-owned input requirement
  fingerprints. Owned implementation/output bytes are excluded from the
  acceptance identity, so the repair itself need not change the judge identity.
- `current_learning_acceptance` supplies that same identity for context lookup;
  `cmd_gate` compares it before observation even for a failed execution. An
  acceptance change during execution makes the observation ineligible; conflict,
  NOT_RUN, permission and rejected successful-publication exclusions remain.
- `gate_learning.py:61` keys a declared sequence by that supplied identity and
  clears other definitions' pending failures. Legacy/no-declared-check sequences
  explicitly carry `COMMAND_ONLY_NOT_CHECK_EQUIVALENCE`; readback/context no
  longer represent them as unchanged check implementation evidence.
- The changed test source covers an easier oracle, changed graph policy, changed
  node requirement and changed non-owned requirement-file bytes under the same
  command, plus an implementation-only positive repair with duplicate-PASS
  control, the legacy disclosure, and mid-run judge drift during a failed gate.
  These assertions directly target the reported defect instead of simply
  changing the command string. They were inspected, not executed by this worker.

The binding remains limited to declared files/requirements and current ownership
metadata. It does not discover undeclared oracle dependencies or establish
causality/benefit. Existing OBSERVED_ONLY/promotion NOT_RUN disclosures remain
appropriate. No new engine, native permission change or silent promotion was
added by this correction.

## Main-owned evidence inspected

`plan/v2-completion/03-qualify-automatic-local-learning-observation-wit.md`
contains the original gate result `15 passed in 1.84s`.
`.harness-work/v2-completion/integrated-gate-round2.log` ends with `DEMO: PASS`,
`CHECK: PASS` and `PASS 9 (exit 0, 433s)`. These are retained main-owned results,
not a reviewer rerun. The assignment also reports the failing-first reproduction,
58 affected passes and Ruff PASS; those reports are not independently certified
by this review.

Current inspected identities (shared working tree, not a frozen release):

- `src/agent_harness/workgraph/plan.py`: `38ed0c51beb5adf58390f11af163ddb0c92e052437c237a67aa0a18896be820d`
- `src/agent_harness/workgraph/gate_learning.py`: `a07958a6e78e99ee829d9eb20c679aef6c019a867db4970681bf9e5cd420eb0d`
- `tests/test_gate_learning.py`: `12a122244f03c6c57276397c18e216a95e6738e571f5a5408074ca2e80bc6abe`
- `content/skills/session-memory/SKILL.md`: `d2862eb473e58bf8eb2e134588331f4519820a8737773f1910eaf108aaf013cc`

---

## Historical first review, preserved

# Gate-learning increment: bounded code review

Historical verdict: **CHANGES_REQUESTED — one P2 correctness finding.** Static review only;
no tests, model calls, installs or runtime edits. Root owns reproduction, original
acceptance, integration and any correction. Review is not certification.

Reviewed 2 November 2026 under
`handoffs/v2-completion/framework-review-assignment.md`. Base revision:
`60735e2b35088c0e458e78e8a3fe3f1574c2d970`, shared dirty working tree.

## P2: Bind the acceptance definition, not only its shell command

Location: `src/agent_harness/workgraph/gate_learning.py:61` (and the calls from
`src/agent_harness/workgraph/plan.py:1556` / `:1567`).

`definition_sha256 = digest(gate)` makes different acceptance checks share one
pending failure whenever the command text stays the same. For example, node1
uses `gate: python3 check.py`; an actual execution fails, then the assertions or
requirements of `check.py` change while that exact command remains. A later
accepted PASS increments the original row's count and is advertised in
`plan context` as an observed fail-to-pass learning candidate. No repair of the
judged artifact is required: an easier or different oracle produces the same
result. The assertion that a new definition cannot borrow an old acceptance
failure (gate_learning.py:68) is therefore false for this ordinary check layout.
This also applies to a changed node requirement/policy under the same command.

Versioned graph checks already distinguish the declared check-file contents
and node/policy definitions in their bindings. The learning hook receives only
the command string, so that distinction is lost even after both executions have
been correctly accepted under their respective graph revisions. Current
`test_changed_gate_or_forged_markdown_failure_does_not_create_a_repair` and
`test_changed_definition_cannot_reactivate_an_old_pending_failure` change the
command string; neither covers changed check bytes or requirement/definition
under an unchanged command.

Action: carry a stable acceptance identity into observation and context lookup
using the existing definition/policy/declared-check bindings where available.
Invalidate pending pairing on an acceptance-identity change. Keep the artifact
being repaired outside that immutable identity so a real implementation fix
still forms a pair. For legacy graphs, either supply an explicit acceptance
identity or expose the weaker command-only observation honestly rather than
calling it same-definition evidence.

Required root reproduction/control (specified, **NOT_RUN** here): fail an
unchanged command against one check revision, change only the check assertions
or a bound requirement, then pass; no same-definition pair should be produced.
Control: retain check/requirements, repair only the judged output, fail then
pass; produce exactly one pair, and another PASS must not duplicate it. Rerun
the original observation gate and affected versioned regressions after the fix.

Impact is limited to inaccurate learning-candidate provenance/counting; this
finding does not claim the observer changes gate authority or promotes a rule.

## Other reviewed boundaries

No additional concrete defect found in this bounded reading. The hook is after
the graph's moved/conflict return and excludes explicit NOT_RUN, permission
refusal and rejected successful version publication. SQLite `BEGIN IMMEDIATE`
serializes observation mutations; a pending failure is consumed by a PASS, so
an immediately repeated PASS does not increase count. This is a code-reading
assessment, not an independent concurrency or deduplication test result.

Existing `.harness-work/.gitignore` is preserved on FileExistsError; output and
gate command are hashed rather than stored verbatim in observations. Readback
returns OBSERVED_ONLY and promotion NOT_RUN with cause/benefit explicitly
unverified. These choices do not establish global privacy, native compliance
or useful learned methods. The coordination edit remains within file-first,
no-routine-message/no-model-heartbeat policy and adds no promotion/dispatch
mechanism.

Root-reported 8 observation tests, 51 affected checks, 37 guidance checks plus
one existing skip, Ruff and full candidate results were not rerun or certified
by this worker. New observation code/guidance installation remains outside
this review's scope.

## Inspected file identities

Hashes observed at review publication (not a frozen integration snapshot):

- `src/agent_harness/workgraph/plan.py`: `e3a81cac815cc3c2823cfdf23052101254f3660208ea5d2aef93c73ff248e1fc`
- `src/agent_harness/workgraph/gate_learning.py`: `6db1fd2e7755ba63c488d6b20393d3730f5a802e898566cc194036f3cb78fdbe`
- `tests/test_gate_learning.py`: `bd7e6101b90509f5c990448a84c93e6e031726633ea050c9e8cd214cf64a257e`
- `content/skills/session-memory/SKILL.md`: `d2862eb473e58bf8eb2e134588331f4519820a8737773f1910eaf108aaf013cc`
