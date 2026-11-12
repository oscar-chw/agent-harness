# Independent shared-admission acceptance cases

3 November 2026. Source: the orchestrator's activation of this existing
Methodology & Evaluation helper. This assignment supersedes the earlier
documentation-only write scope **only** for the new
[`tests/test_shared_admission.py`](../../../tests/test_shared_admission.py),
this case document and the existing methodology handoff. Main owns execution,
runtime integration and final verification. No original gate/test is changed.

## Frozen subject and interface

The oracle is the supplied interface and admission semantics, not the concurrent
implementation. No admission module was found in the initial file inventory.
Main subsequently clarified the canonical module path as
`agent_harness.workgraph.admission`, and the import now uses that path. The
initial `shared_admission` module-name assumption was corrected in this new test
file; there is no import fallback, skip or synthetic implementation.

```python
Admission(home: Path, capacity: int)
acquire(root: Path, writes: list[str] | None, owner: str, task: str) -> dict
release(reservation: str) -> bool
inspect() -> list[dict]
```

An admitted result has `admitted is True`, a diagnostic `reason` string and a
nonempty `reservation` string. A refusal has `admitted is False`, a reason and
no usable reservation. Extra result/record fields and record ordering are not
the oracle. Snapshots compare unordered serialized records instead of private
table names or a chosen persistence backend.

`None` reserves exclusive root writes; `[]` reserves no write paths while still
consuming capacity. Explicit relative writes are canonicalized. Actual path
equality or component containment conflicts, including directory and project-root
symlink aliases. Mere string prefixes do not conflict. Capacity persists in one
home and is shared by projects and independent processes; a different declared
capacity is refused even after all reservations were released. Reservations
persist when their acquiring process exits. Main clarified that explicit release
is **acquiring-instance-only**: a reopened instance or another process cannot
release a known reservation, even if inspect exposes its ID. No live-PID check,
timer, cold inspect or possession of that ID transfers release authority.

Input interpretation used in these cases: invalid capacities and invalid/escaping
write declarations raise `ValueError` (type errors may also use `TypeError`);
ordinary capacity/write conflicts return a refusal dict. Empty path strings are
invalid; `.` is the explicit relative root-write spelling. Internal `..` that
normalizes inside the root is allowed; resolved outside paths and all absolute
write declarations are rejected. These choices follow the relative-canonical-path
and exception/no-entry request; main should resolve any contrary intended API
requirement rather than silently weaken a valid case. Read-only versus an
exclusive-root reservation is not tested because the supplied contract did not
define read/write conflict semantics; no read set or shared context becomes a
write declaration in these tests.

## Cases, controls and failure discrimination

| Family / test name | Sound control and named defect rejected |
|---|---|
| `test_disjoint_outputs_sharing_context_can_enter_without_a_project_wide_lock` | Two owners write different outputs while using the same `ctx.md`; both enter. A project-wide mutex or treating shared context text as a write conflict fails. Admission must not create declared output files. |
| `test_read_only_requests_consume_capacity_without_claiming_write_paths` | Two read-only requests plus an unrelated writer fill capacity 3. A fourth reader is denied without a new row; treating `[]` as root ownership, or making readers free capacity, fails. |
| `test_exclusive_root_and_parent_child_scopes_conflict_in_both_directions` | Parametrized `None`/root, `.`/root and `src`/descendant containment in both acquisition orders. Same-files-only checking, asymmetric ancestor checks or a denied-request slot leak fail. |
| `test_component_prefix_is_not_path_containment` | `src/a`, `src/ab` and `src/a-other/file.py` coexist with three available slots. Raw `startswith` overlap checks fail this positive control. |
| `test_internal_normalization_and_missing_output_components_use_one_identity` | Nonexistent `new/../new/output.json` conflicts with `new/./output.json` without creating files. Lexical-only equality or requiring outputs to exist fails. |
| `test_symlink_alias_of_an_inside_directory_conflicts_with_its_target` | An in-root directory alias and its target name one output; only one enters. Ignoring symlinks fails. |
| `test_symlink_alias_of_project_root_cannot_evade_existing_write_ownership` | Alias of the project root conflicts with the real root's output. Root-string partitioning fails. |
| `test_nested_project_roots_compare_actual_output_paths` | Outer `nested/result.txt` conflicts with inner `result.txt`, but inner `other.txt` enters. Project identity alone cannot separate actual overlapping writes. |
| `test_invalid_or_escaping_write_raises_and_preserves_existing_entries` | Reject traversal outside, absolute-inside/absolute-outside, external symlink and empty path. A prior valid entry remains; a valid earlier path in the same invalid request is not partially reserved. |
| `test_malformed_write_collection_does_not_create_an_entry` | A string treated as characters, a non-string member or a mapping must fail instead of silently reserving unintended paths. |
| `test_multi_output_request_reserves_one_slot_and_all_paths_atomically` | Two output paths consume one slot; a later request with one conflicting member must not retain its earlier free member. A subsequent request for that free path enters. |
| `test_capacity_is_shared_between_projects_and_denial_does_not_leak_a_slot` | Capacity 1 occupied in project A blocks project B under the same home; a cold instance cannot release it. Only the acquiring instance's release permits B; both handles see the current reservation. Per-project counters or hidden reset fail. |
| `test_reopen_retains_reservations_and_release_is_exact_and_idempotent` | Reopen sees both owners but cannot release even known IDs. The acquiring instance rejects altered/unknown IDs, releases its exact reservation once and leaves the other path owned. Token-prefix deletion, cold-instance release, blanket reset and duplicate-release success fail. |
| `test_invalid_capacity_cannot_initialize_a_new_shared_home` | Zero, negative, bools, fractional, string and None fail on a fresh home. Merely relying on capacity mismatch against an existing home cannot pass this case. A valid initialization after refusal remains empty. |
| `test_invalid_capacity_fails_without_resetting_existing_state` | The same invalid values cannot erase or replace a valid persisted reservation. |
| `test_capacity_mismatch_is_refused_and_does_not_reset_even_after_release` | Capacity 2 refuses reopens at 1 or 3 with and without an occupied slot; original state/capacity remain available. |
| `test_actual_process_race_caps_all_projects_and_retains_exited_owners` | Six spawned independent processes, distinct projects and disjoint writes start acquiring at a common barrier. Exactly the shared capacity (1 or 2) enters, not one per process/project. Child exit does not free capacity, and the parent cannot release the child's known ID or obtain the occupied slot. |
| `test_actual_process_race_rejects_alias_overlaps_even_with_spare_capacity` | Six simultaneous contenders use canonical aliases of one output with capacity 6. Exactly one enters; a later unrelated output enters. Thus overlap, not the capacity limit or a permanently closed gate, determines the refusal. |
| `test_actual_process_race_allows_disjoint_writers_in_one_project` | Four processes with four disjoint files and capacity 4 all enter. This rejects an implementation that makes the overlap race pass by locking the whole root or always refusing contenders. |

## Actual concurrency and cleanup

The race helper uses multiprocessing's **spawn** context, separate `Admission`
objects and a common process barrier after each opens the shared ledger.
Requests are not serialized through the parent and no sleep/retry selects the
winner. All accepted reservations remain persisted while the parent evaluates
the results. No ordering of winning owners is assumed.

Test deadlines bound barrier/result waiting and cleanup only; they are not
reservation TTLs or production reclamation rules. A missing result, nonzero child
exit or surviving child fails. `finally` terminates and joins only the fixture
processes, escalating to `kill` if necessary; no model, shell worker tree or
external service is started. A failed test must not leave its children running.

The exited-owner test directly checks no dead-PID auto-reclaim. These bounded
tests do not simulate an arbitrarily long wall-clock interval; absence of any
time-based reclamation also requires main's source review or a separately
controlled-time test. No hours-long sleep is added to manufacture that claim.

## Clarified requirement and narrow correction

Before root qualification, main corrected two previously unspecified interface
details: canonical module `agent_harness.workgraph.admission` and
acquiring-instance-only release. The original newly authored cases allowed a
cold handle to release known IDs; that expectation was invalid under the clarified
ownership contract. Only the new import and those release expectations changed.
The cold-release refusal is now an explicit negative, while acquiring-instance
release, duplicate-release refusal, persistent reopen and exited-owner capacity
controls remain. No original test/gate, capacity threshold, overlap or escape
assertion was weakened. Root owns actual execution of the corrected cases.

Root also clarified that runner integration uses the existing `write_scope`
field; the admission API argument remains `writes`. This standalone API suite
does not rename or implement runner fields. The current implementation's safe
internal-symlink gap remains a valid failing case for main to repair; external
symlink escape refusal and absolute-inside rejection are preserved.

## Main-owned commands and evidence policy

From the repository root, main should preserve the original missing-module or
behavioral failures and then run against the integrated implementation:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider tests/test_shared_admission.py
PYTHONDONTWRITEBYTECODE=1 python3 -m ruff check tests/test_shared_admission.py
```

Worker test execution: **NOT_RUN**, as assigned. Source-wide/runner/native/model
verification: **NOT_RUN**. The documented module absence is an observed initial
prerequisite, not a fabricated test-exit receipt. Missing-module import fails
collection rather than being skipped or counted as passing acceptance.

Before qualification, main should prove the acceptance instrument rejects actual
implementation defects: remove atomic shared capacity checking, remove canonical
overlap checking, use string-prefix containment, clear rows on reopen, or reclaim
dead owners. Each relevant negative must turn red while its stated positive
control stays green. This worker neither mutates nor implements the concurrent
module, and does not grade a framework worker's report as runtime evidence.

Claim class: local behavioral acceptance of this narrow admission API. Authority:
test failures inform/block main's qualification decision under the unchanged root
gates. Scope excludes native write fencing, proof that declared writes match real
worker writes, authenticated owners, task scheduling, OS isolation, resource
optimality, model efficacy, token savings, deployment and release.

`existing:` current standards/production-code/work-loop/session-memory guidance;
shared README and own/framework packets; existing operational-state independent
process tests, workgraph concurrency fixture cleanup and tests/conftest.py. Their
interfaces are distinct from admission and were not reused as fake implementation.
