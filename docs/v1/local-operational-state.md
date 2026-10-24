# Local operational state (development slice)

This ledger gives Claude Code, Codex, and another MCP client connected to the
same local project and harness home a common task-coordination interface. The
host derives the project from its working directory; an MCP caller cannot pick
another project with a model-supplied label. `harness task`, the lower-level
`harness op`, and the opt-in MCP `op_state`
tool use the same SQLite database under `<HARNESS_HOME>/operational/`, keyed by
the full SHA-256 digest of the resolved project path. Distinct local paths do
not share a ledger merely because their short legacy project keys collide.
The CLI is available directly. The MCP definition is opt-in with
`HARNESS_ENABLE=op_state`; advertising it by default exceeded the existing
4,600-byte tool-definition budget. This is a development switch, not a claim
that its overhead or usefulness has cleared the release A/B gate.

The repository's generated Codex `SessionStart` hook and Claude Code's new
`_hook-op` `SessionStart` hook read the local ledger on startup, resume, and
compaction. When it exists, they emit a bounded current task summary and
cursor; stale memory-linked tasks appear first without their old stage text.
An absent ledger is quiet. An unreadable ledger reports unavailable, never a
fresh empty state. This describes candidate configuration; no live IDE
settings were changed by this development slice.

The ledger owns bounded task summaries, versions, leases and an ordered event
cursor. It does **not** own sourced facts. Conflicting claims remain separate
records in `ProjectMemory`, each with a source receipt. A task may link one
current memory receipt; snapshots revalidate it. A withdrawn, corrected, or
unreadable dependency appears as `memory_status: stale`, and `changes` reports
the affected task in `memory_invalidations` even if the operational cursor did
not move. A stale dependency blocks new claims and renewals; a current holder
can still release its lease. No old fact is silently made
current. This is advisory within one OS user, not an access-control service.

New `ProjectMemory` claims labelled `verified` retain that label only when the
whole cited source span matches the assertion verbatim. A proposed paraphrase
is stored as `pending`: ordinary search returns a receipt-only omission,
recovery holds it, and an explicit scoped read marks it unusable for current
decisions. This checks source correspondence, not real-world truth or conflicts
between separate exact quotations. Existing historical `verified` records are
not retroactively reclassified; review them before relying on the label.

The event, task projection, and request-id replay record commit in one SQLite
transaction. `expected` is the version from a snapshot. A stale version fails
closed; the caller reads `changes` from its prior cursor, then takes a new
snapshot before deciding whether to retry. Reusing a request ID with the exact
same inputs replays the original result, including a claim token; changing the
inputs conflicts. A replay is evidence of the earlier commit, not proof that a
linked memory receipt is still current; revalidate before using it. The token
and increasing `fence` identify the current lease.
After a crashed client, a later claim can take over after expiry and the old
token/fence cannot release it. Lease duration is 1–3600 seconds. `withdraw` is
terminal for a task ID. The event cap is 10,000; reaching it refuses new work
without silently discarding history.

The normal human entrypoint is `harness task`; MCP callers use the corresponding
`op_state` actions `status`, `checkpoint`, `stop`, `resume`, and `evidence`.
Both reach the same project-scoped ledger and report its current version and
activity. CLI mutations read the latest version when `--expected` is omitted;
the same CAS check still refuses a concurrent change. MCP mutations require an
explicit expected version and request ID. Neither surface creates another plan.

```sh
harness task checkpoint release --goal 'Qualify release' --checkpoint plan/release.md --next 'Run the gate'
harness task status release
harness task stop release --reason 'Independent receipt missing'
harness task resume release
harness task evidence release
```

`stop` prevents new claims; it does not kill a running worker and refuses to
claim it has stopped one with an active lease. `resume` clears a block only
while the checkpoint, pinned evidence (if supplied), and linked memory remain
current. Checkpoint, stop, and resume retain an existing source-memory receipt;
none silently clears a stale dependency. The optional `--evidence` file is bound to a SHA-256 digest, is limited
to 1 MiB inside the project, and becomes stale when it changes. Its status is
**reference only**: even a file containing `PASS` cannot mark a graph node done.
Run `plan gate` to establish completion. `--json` exposes the same status to a
script; `harness op` remains available for exact cursors and lease fencing.

CLI reads mutation fields as JSON from stdin, and returns one JSON result:

```sh
harness op snapshot
printf '%s\n' '{"task":"build","value":{"stage":"test"},"expected":0,"request_id":"create-1"}' | harness op put
harness op changes --cursor 0
printf '%s\n' '{"task":"build","expected":1,"request_id":"claim-1","ttl":300}' | harness op claim
```

Pass the returned `token`, `fence`, and latest `version` to `renew` or `release`.
The MCP tool takes the same fields with an `action`. Tokens are local lease
capabilities; avoid logging or displaying them unnecessarily. Neither a lease
release nor an operational summary marks code complete: the existing workgraph
node is done only when its independent gate passes.

Scope and limits: this slice coordinates processes sharing a local harness home
and the same resolved project path. A separate worktree path is a separate
ledger; the workgraph's own claims remain the source of truth for graph nodes.
Claim and renewal are the task actions this slice preflights automatically.
It does not intercept arbitrary IDE edits, Bash commands, native model turns,
or remote workers before they act. A hook summary is advisory, not action
authorization; consumers must refresh an older cursor before acting.
It has no authenticated cross-device service, remote replication, same-user
process isolation, automatic offline write queue, or transaction spanning
SQLite and ProjectMemory's source files. Memory receipt validity is checked on
read/claim/renew, so a cross-store change between a check and a commit is
detected at the next read, not prevented atomically. Clients must revalidate
before a sensitive action. It is not v1 release qualification.

## Cold owner recovery

For a goal that may outlive a chat, save `goal`, `checkpoint`, `next`, and, while
waiting on an independent prerequisite, `blocked_on`. `checkpoint` is a
project-relative file such as `plan/release.md`; that file should hold the
executable gate and its dated results. The ledger checks that the file is
present inside the project. Presence does **not** mean the gate passed.

```sh
printf '%s\n' '{"task":"release","value":{"goal":"Qualify release","checkpoint":"plan/release.md","next":"Inspect the held node and run its gate","blocked_on":"Independent evaluator receipt missing"},"expected":0,"request_id":"release-1"}' | harness op put
harness op snapshot
```

`snapshot` and `task status` are cold-session recovery views. Its `activity` says `blocked`,
`idle_ready`, `idle_unprepared`, `checkpoint_missing`, `stale_memory`,
`evidence_stale`, `leased_unverified`, `expired_reclaimable`, or `withdrawn`. A lease is a claim,
not evidence that a model is still running; an expired lease permits a fenced
takeover. `blocked_on` and a missing checkpoint prevent a new claim. After the
prerequisite is resolved, use a versioned `put` without `blocked_on`, then
re-read the snapshot. The bounded SessionStart brief carries the goal,
checkpoint, next step, and block reason where space permits; omitted tasks are
counted and can be read with `harness op snapshot`.

This is durable local state, not a scheduler. An idle Codex or Claude chat does
not wake itself or execute a ready node. The existing workgraph remains the
authority for node marks and gate evidence. No unattended dispatch, platform
heartbeat, or cross-device wakeup is enabled by this view.
