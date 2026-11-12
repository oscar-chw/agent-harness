# Shared cooperating-runner admission — 3 November 2026

Implementation handoff: `src/agent_harness/workgraph/admission.py`.
Root owns `plan.py` integration, independent module/runner acceptance, remaining
integration corrections and any activation. This is a bounded scheduling
component, not security/authentication, filesystem isolation, native permission,
process-liveness detection or a measured throughput/quality improvement.

## Public surface and persistence

- `Admission(home: Path, capacity: int)` opens/initializes
  `home/admission/reservations.sqlite`. Capacity is persisted once per canonical
  home. A different requested capacity raises ValueError even after every
  reservation is released. Separate projects using this home compete together.
- `acquire(root, writes, owner, task)` returns
  `{admitted: true, reason: "admitted", reservation: opaque_id}` after commit,
  or `{admitted: false, reason: "capacity" | "write_overlap"}` without a
  reservation/mutation. Invalid input/storage raises explicitly. Root must not
  equate a denial with an executed artifact gate failure.
- `release(reservation)` deletes exactly that reservation only if the same
  Admission instance acquired it. An unknown/foreign/already released ID returns
  false; malformed unbounded input raises. A new instance can inspect retained
  state, but cannot release IDs copied from inspection. This prevents accidental
  unrelated cleanup by a cooperating runner; it is not OS-user authentication.
- `inspect()` returns a deterministic list of records with `id`, `owner`, `task`
  and canonical absolute `writes`. No extra secret/token is stored or exposed.
  These labels and paths are operational metadata and must not contain secrets.

Each reservation consumes one slot, irrespective of write-path count. Capacity
and all path conflicts are checked in the same SQLite BEGIN IMMEDIATE
transaction as insertion. Readers/first-use schema/config checks also serialize;
failed transactions close/roll back rather than partially reserving paths.
A lost return after commit can leave a reservation; acquisition is intentionally
not an idempotent retry API. Do not infer an absent response means no mutation.

## Graph and canonical-path semantics

The existing graph field is **write_scope:**, JSON array or the supported legacy
comma-separated syntax parsed by root's runner. There is no duplicate writes
field. `ctx` is read context and is not a write set. The module's Python
parameter remains `writes` as requested.

- No write_scope / writes=None means the canonical project root is the write
  scope, conflicting with every writer below that root, including nested roots.
- Explicit `[]` means read-only: one capacity slot, no write conflict. It can
  coexist with a writer, including an exclusive-root writer; this is not a
  consistent-read lock or database transaction isolation guarantee.
- Explicit paths reserve all requested targets atomically, including missing
  files/directories without creating them. Equality and ancestor/descendant
  containment conflict in both directions; `a` and `ab` are distinct.
- Project-root aliases resolve to their canonical root; separate projects and
  nested roots compare actual absolute target paths, not just project labels.
- Admission-time canonicalization is an observation. Cooperating callers must
  not retarget symlinks/rename reserved directory boundaries during execution.
  This module does not intercept arbitrary edits or defeat a same-user attacker.

**Root clarification/remaining integration correction:** final graph writes are
relative-only; safe symlink aliases resolving inside the project must canonicalize
and conflict with their target. Escaping/outside targets remain refused. The
worker's initial source accepted absolute-inside paths and rejected all write-
path symlinks conservatively. Root explicitly took ownership of these corrections
at the file-close boundary; they are not claimed corrected/tested by this worker.
The earlier local alias-rejection check is therefore historical, not the final
inside-alias acceptance oracle. Do not weaken outside-escape negatives to fix it.

## Bounds and private store

Initial module bounds: capacity integer1..256 (not bool); at most64 write paths;
owner/task each256UTF-8 bytes, nonempty and no control characters; input/canonical
paths at most4096UTF-8 bytes; encoded scope at most64KiB; DB at most32MiB,
4096-byte pages/8192-page ceiling. Inspect refuses malformed/over-capacity stored
records rather than defaulting to empty state.

Following OperationalState's filesystem pattern: dedicated directory0700 and
SQLite file0600; reject redirected/nonregular paths, nonprivate dedicated
store/files, hard-linked database files and oversized files. Open with
O_NOFOLLOW/O_NONBLOCK and fstat before SQLite; trusted_schema disabled. The
application ID/version and settings identify this store. Existing unrelated
schema or unsupported identity/version fails rather than being overwritten;
SQLite exception reports include error class, not private row text. Existing
owner files/permissions are not silently repaired. This is local same-user
cooperation, with the same filesystem observation/race limits as that model.

No TTL, age/PID cleanup, destructor release, background sweeper or capacity
reset exists. A dead orchestrator can leave living children. Normal-return
release must follow worker **and gate** completion/cleanup, using only the
runner's own returned reservation. Exception/interruption with unknown child
state retains the reservation. Retained state requires explicit operator
investigation under original authority; inspect is not permission to purge it.

## Evidence and exact qualification boundary

Focused local script (outside root tests):
`python3 /Users/me/Documents/Codex/2026-11-02/agent-harness-framework/work/admission_focused.py`.

- First result exit1: explicit assertion that the missing Admission component
  could not implement shared capacity/write-conflict behavior.
- First implementation attempt exit1: Python3.9 annotation evaluation rejected
  `list[str] | None`. Added deferred annotations; no test/criterion loosened.
- Rerun exit0: canonical containment/missing paths, read-only/exclusive scopes,
  component-prefix distinction, owned/idempotent release, persisted-capacity
  conflict, invalid inputs/private store and six-process capacity/overlap races.
  Processes exited without releasing, and fresh instances retained their slots.
- `python3 -m ruff check --select E,F,B src/agent_harness/workgraph/admission.py`
  initially exit1 for14E501 formatting issues. `python3 -m ruff format` then
  reformatted only the owned module. Root took source ownership before another
  worker lint/test run; no post-format/current-root PASS claim is made here.

Main owns independent `tests/test_shared_admission.py` and
`tests/test_run_admission.py`, root graph node14 and its original gate. Worker
read node14 context but did not run/close it or edit those tests. Root's
clarification preserves acquiring-instance-only release; a contrary new test
expectation/import path is being corrected by the test owner, not changed here.
No broad suite, native/model call, install, config/guard change, release,
publication or promotion was performed by this worker. Source safety/behavior,
runner integration, installed readback and useful outcomes remain separate.
