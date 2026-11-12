# Admission inspection and file handoff — 3 November 2026

Design contract for root's explicit `--shared-capacity N` opt-in. This document
adds no runtime, command, MCP surface, database, hook or automatic wiring. Only
participating invocations using the same local HARNESS_HOME/store are covered;
an absent row says nothing about unrelated interactive chats or another device.
The original graph gate remains completion authority.

## Existing interfaces and the important separation

Inspected `src/agent_harness/operational_state.py`: project-scoped SQLite,
version/CAS, events, checkpoints, source/evidence freshness and fenced TTL leases.
`snapshot()` reports `project`, `cursor`, task `version/status/fence/until`,
checkpoint/evidence/memory state and derived `activity`. `leased_unverified` and
`expired_reclaimable` are task-ledger interpretations, not process observations.
The claim TTL is 1..3600 seconds; graph leases are separately configurable and
default four hours. Neither proves a worker stopped or its writes are safe.

OperationalState `_db()` creates the directory/database if absent, opens it
read/write, starts `BEGIN IMMEDIATE` and can create schema even for a snapshot.
Reuse its *versioning concepts*, not that access path, for strict read-only
admission inspection. Do not extend its bounded string-only VALUE_FIELDS with
nested admission/process arrays or put reservations into sourced project facts.

`handoff.py:inspect` reads project Markdown packets, hashes bytes, rejects
redirected/nonregular/changing packets and applies caps: 16 KiB per packet,
64 KiB aggregate and 100 entries. It grants no liveness or action authority.
The existing template supplies task/session, source revision, graph/node,
commands/results, blocker, next action, budget and held actions. Add only the
small admission reference below; do not copy an entire shared database.

The inspected `plan.py` slices eligible graph work by `--workers` and dispatches
a pool. `ctx:` is source/context metadata, not declared write ownership or an OS
sandbox. A graph claim, a task lease, a handoff and a source receipt cannot
substitute for an admission reservation bound to an actual invocation.

## Proposed store and reservation semantics

Root's opt-in store lives under `HARNESS_HOME/admission/`; its concrete database
name/schema are implementation choices, not an already installed interface.
Bind the namespace to the resolved local harness home/device and a persistent
store identity/epoch. It spans participating projects in that namespace, while
OperationalState remains separately project-scoped. Do not silently connect to
another harness home or device to make a reservation disappear.

- `--shared-capacity N` declares a positive capacity for this store. All concurrent
  participants must agree with its recorded capacity/configuration revision;
  a conflicting N produces `CONFIG_MISMATCH`, never an automatic increase.
  Omitted opt-in means `NOT_ENABLED`, not evidence of free shared capacity.
- Reserve atomically **before each real worker invocation**; charge every
  unreleased reservation, including reserved-before-spawn and unresolved child
  state. Correlate it with a unique invocation ID. A graph node can have several
  historical attempts; only currently unreleased invocation rows occupy slots.
  A coordinator or graph lease is not itself a worker slot. Nested cooperating
  dispatch must reserve each additional invocation, without double-counting one.
- `writes: null` (Python None, including an omitted declaration resolved to this
  default) means exclusive write coverage of the canonical project root.
  `writes: []` declares read-only work: it holds no write paths but still consumes
  invocation capacity. A nonempty list declares explicit canonical write targets.
  Record raw and effective forms; never infer `[]` from an empty/missing `ctx:`.
- Compare actual canonical targets and ancestor/descendant overlap, including
  shared generated files/lockfiles and aliases. Task labels, graph node IDs or
  different worktree names do not establish disjoint writes. Unresolvable paths
  are an admission error/hold, not an empty scope. Read-only work has no write
  conflict, but does not gain a stable source snapshot while another writer runs;
  retain/revalidate its source revisions separately.
- No TTL, dead-parent, idle-chat, missing heartbeat or expired graph/operational
  lease automatically frees a reservation. Parent exit can leave children alive.
  Until reconciled, unknown child state retains its capacity and write coverage.
  Reservation bookkeeping is not filesystem enforcement or a native permission
  grant; nonparticipating/direct writes remain outside this mechanism.

## Read-only inspect contract

Proposed request fields: host-resolved project identity; task/graph/node reference;
request/invocation correlation; requested slot count; explicit N/opt-in; raw and
effective `writes`. Source/context receipts may be attached as separate advisory
references. Inspection computes a view only; it never reserves or clears a row.

Use an existing-database, read-only, bounded SQLite transaction. No create,
migration, schema initialization, lease renewal, event append, repair, pruning or
new journal/WAL/shared-memory file is permitted. If the selected SQLite access
cannot read the current committed state without such writes, report unavailable.
Do not use an immutable shortcut on a live changing WAL database to fabricate a
consistent view. Root must qualify the actual SQLite behavior on fixtures.

| Inspect field group | Minimum fields and meaning |
|---|---|
| Snapshot binding | schema; store ID/epoch; capacity-config revision; event head/transaction version; observation time; consistency boundary |
| Availability | `NOT_ENABLED`, `UNINITIALIZED`, `UNAVAILABLE`, `UNSUPPORTED_SCHEMA` or `OBSERVED`; missing/unreadable/corrupt store is not zero occupancy |
| Request | task/graph/node; invocation ID if already assigned; slots requested; project root or authorized opaque identity; raw/effective writes |
| Capacity | configured N; unreleased slot sum; available slots; whether this request fits; unknown-child reservations included |
| Reservations | ID/revision; invocation/owner/session correlation; project identity; slot charge; lifecycle state; effective write coverage; last observed event |
| Child observation | `NOT_STARTED_CONFIRMED`, `RUNNING_OBSERVED`, `EXITED_CLEANUP_CONFIRMED` or `UNKNOWN`; observed-at; adapter/host; PID plus birth identity/group where available; evidence reference |
| Blockers | reservation IDs/revisions; `CAPACITY`, `WRITE_OVERLAP`, `UNKNOWN_CHILD`, `CONFIG_MISMATCH` or unavailable-state reason; exact overlapping targets only within authorized visibility |
| Release evidence | retained explicit release/reconciliation event, actor, prior row revision and evidence digest, or null; never a fabricated expiry time |
| Advisory links | graph lease owner/expiry, OperationalState task version/cursor/activity, source/ctx pins and packet hash, each separately labeled |
| Decision limit | `BLOCKED`, `UNAVAILABLE`, `NOT_ENABLED` or `CAN_ATTEMPT_ATOMIC_ADMISSION`; the last is not a reservation or launch grant |

A point-in-time free slot can be taken immediately by another participant. The
later reserve operation must atomically recheck capacity, write overlaps,
configuration and expected state. Do not treat an inspect hash as a durable
admission token. A changed store epoch invalidates a cursor/reference; do not
silently accept a replacement empty database.

Scope before emitting: retain enough opaque owner/reservation IDs to explain a
capacity blocker without revealing another project's prompts, source snippets or
private paths. Expose exact write paths only where authorized. Never emit lease
tokens, credentials, complete worker commands/prompts or another user's records.
Bound rows/bytes with visible omissions; an incomplete blocker list cannot yield
an all-clear. Read failure stays visible rather than falling back to an old
handoff's occupancy figure.

### Illustrative view, not observed state or an existing API

```json
{
  "schema": "proposed.admission-inspect/v1",
  "store": {"id": "local-store-A", "epoch": "epoch-A", "head": 17},
  "availability": "OBSERVED",
  "request": {
    "task": "delivery", "graph_node": 4, "slots": 1,
    "project": "project-A", "writes": null,
    "effective_writes": {"mode": "PROJECT_ROOT_EXCLUSIVE", "root": "project-A"}
  },
  "capacity": {"configured": 2, "occupied_unreleased": 2, "available": 0},
  "reservations": [
    {
      "id": "reservation-A", "revision": 2, "invocation": "attempt-A",
      "owner_session": "session-A", "project": "project-A", "slots": 1,
      "lifecycle": "UNRELEASED", "child_state": "RUNNING_OBSERVED",
      "effective_writes": ["project-A/src/f.py"], "release_evidence": null
    },
    {
      "id": "reservation-B", "revision": 1, "invocation": "attempt-B",
      "owner_session": "session-B", "project": "project-B", "slots": 1,
      "lifecycle": "UNRELEASED", "child_state": "UNKNOWN",
      "effective_writes": {"mode": "PROJECT_ROOT_EXCLUSIVE", "root": "project-B"},
      "release_evidence": null
    }
  ],
  "blockers": [
    {"reason": "CAPACITY", "reservations": ["reservation-A", "reservation-B"]},
    {"reason": "WRITE_OVERLAP", "reservations": ["reservation-A"]},
    {"reason": "UNKNOWN_CHILD", "reservations": ["reservation-B"]}
  ],
  "advisory": {"graph_lease_B": "EXPIRED", "ctx": ["src/f.py"]},
  "decision": "BLOCKED"
}
```

If the same request declares `writes: []`, its write blocker disappears but both
slot charges remain. An expired graph lease B changes neither charge. A source
ctx hit alone creates no write claim. These are countercases for root's tests.

## Small project handoff and recovery

Add these bounded fields to the task's existing single-writer packet:

`admission: opt-in N; store ID/epoch; inspect head/time/status; own invocation and
reservation ID/revision; requested/effective writes; blocker IDs/reasons; child
state and observation evidence; next owner action; held scope; NOT_REGISTERED if
unregistered.` Link the source-revision/graph/evaluation evidence already present.
A packet stores the last observation, not current free capacity.

For an already authorized OperationalState checkpoint, reuse bounded strings:
`resource` holds the admission ID/reference, `blocked_on` the concise reason/IDs,
and `checkpoint` the project-local packet. If root publishes a separate bounded
project-local observation file, its `evidence/evidence_sha256` can bind those bytes.
Do not place the global database path in a field expecting project-local evidence,
store secrets in a packet, or register/mutate state merely by reading inspection.
No automatic CLI/MCP/checkpoint adapter is claimed here.

1. On start/resume or before dependent dispatch, read the assigned packet and graph,
   then obtain a fresh read-only view for the same store epoch/configuration.
   Revalidate source/ctx pins separately. No chat or model heartbeat is needed.
2. Capacity/write conflict: preserve IDs, versions and unknown state in the packet.
   Continue genuinely independent admitted work, or stop with a precise dependency.
   A quiet owner, stale packet, completed graph gate or expired lease cannot clear it.
3. Reconcile through root's authorized execution adapter/owner: distinguish proven
   never-spawned, still running, confirmed exit with descendant/group cleanup, and
   unknown. PID absence/reuse, parent death or remote unobservability alone is not
   proof of cleanup. Unknown remains occupied; do not launch a duplicate writer.
4. Only an explicit authorized, version-checked release transaction can free the
   reservation after supported no-spawn/cleanup evidence. Preserve the original
   reservation, prior unknown state, evidence, actor and event history. This is a
   proposed operation, not an existing release command; never delete SQLite rows
   or force-clear by age to resolve a conflict. On CAS conflict, reread and reconcile.
5. Reinspect and atomically attempt admission again if still authorized. Original
   graph gates, task ownership, guard holds and source-freshness checks still apply.
   Successful process cleanup frees occupancy; it does not make the task pass.

## Qualification boundary for root

Required focused controls: two simultaneous contenders for the last slot; parent/
child path overlap across labels; None versus explicit [] versus omitted writes;
ctx-only scope; expired graph and operational leases with a live/unknown child;
parent exit with surviving descendants; unsupported/missing/corrupt/replaced store;
inspection creating no DB/schema/sidecars or events; stale/CAS-conflicting release;
bounded/redacted blocker output; config mismatch; preserved original failed gates.
No runtime/admission/native or broad checks were run by this document worker.
