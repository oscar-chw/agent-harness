# Shared admission: what a returned call does and does not establish

Design analysis, 3 November 2026. **Source-inspected and proposed; no runtime
verification.** Scope is cooperating runners explicitly using
`plan run --shared-capacity N`, with one consistent capacity persisted in a
shared Admission SQLite store. Missing `writes` reserves the project root;
`writes: []` declares no product writes. No timer/dead-parent reclamation,
native installation change or sandbox enforcement follows from admission.

The source changed during this bounded investigation: the first read showed
the original runner; the later read included root's admission integration.
Findings below address the later observed snapshot, not an assertion about
the final integrated candidate. Source base is
60735e2b35088c0e458e78e8a3fe3f1574c2d970 plus uncommitted changes.

Inspected [plan.py](../../../src/agent_harness/workgraph/plan.py), SHA-256
5995fcdaf91cb8525288cd21b072064fd70634a8100a3eeb35edf7051a0c4c45:
`admission_store`/`declared_writes`; `_dispatch`/`_dispatch_codex`;
`_work_one`/`_work_one_unadmitted`; `cmd_run`; `cmd_gate`; `_kill_worker(s)`.
Also read [test_run_admission.py](../../../tests/test_run_admission.py), SHA-256
537cccbde76bdd620d754820597fdf9e01f1844b77c560359110ca77b2782a2a.
These test sources were not executed. The sibling admission module was not
present in the bounded source listing at inspection; its implementation is
the framework worker's responsibility, not reviewed by this note.

## The three distinct facts a scheduler must preserve

1. **Admission:** a durable reservation occupies one slot and its declared
   write region until explicitly settled. Capacity and write-conflict checks
   must decide the same acquisition, rather than each admitting against a
   different snapshot. A per-run `--workers` limit is a separate local bound.
2. **Task evidence:** a gate actually ran against the intended artifact and
   acceptance definition. Not obtaining capacity supplies no evidence about
   that artifact. A pending task, an admission wait and a failed gate are
   different facts, even if a CLI exits nonzero for unfinished work.
3. **Quiescence:** processes that could continue the admitted work have stopped.
   A timeout, dead parent, expired graph lease, returned Python function or
   successful kill request is not independently that fact. A reservation row
   is likewise not proof that a worker is alive.

The no-reclaim policy chooses conservative exclusion over automatic recovery
of availability when the third fact is unknown. That is coherent, provided
normal-return handling does not bypass it. Diagnostics should say “reservation
retained; worker/child state unknown,” not “child stopped” or “still running.”
An operator deciding how to settle an orphan needs evidence; deleting a row
because its owner PID disappeared would undo the stated policy.

## Six concrete failure traces

### F1. The owner crashes after reserving, before dispatch

**Trace.** Runner A acquires reservation H. Before it submits `_work_one`, it
crashes, perhaps between durable admission and writing the graph claim.
Runner B later sees a pending/expired graph node but H still exists. SQLite
admission and the Markdown graph are not one atomic transaction.

**Required outcome.** B does not infer that H is reclaimable from the graph's
state or A's dead PID. H continues to consume capacity/write ownership and is
shown diagnostically. No gate result is manufactured. This can block every
slot indefinitely; that is a deliberate liveness limit of no automatic reclaim,
not proof the task failed or work is safely stopped.

**Actionable distinction.** An abrupt crash differs from a still-live caller
catching an exception before any worker was submitted. The latter can prove
it has not dispatched this reservation and unwind its own acquisition. Root's
later snapshot acquires before `version_module().claim`, `set_node` and
`ensure_record`; failures there occur before the executor's cleanup region.
Do not fix such avoidable live-owner leaks by adding dead-owner reclamation.

**Main-owned countercase.** Inject failure immediately after acquire, once as
an abrupt owner death and once as a caught pre-submit exception. Require
retention in the uncertain crash case and explicitly accounted rollback for
the proven-undispatched live case. Existing successful dry-run release does
not cover either exceptional path.

### F2. The worker times out, but a child may survive

**Trace.** A holds H and launches a worker. The deadline expires after work may
already have modified files. `_dispatch_codex` attempts process-group killing
and a bounded communicate; cleanup exceptions are swallowed. The other dispatch
branch kills only the direct process. Both can return `dispatch_failed`, and
both discard the tracked direct process in `finally`. A child that detached or
outlived uncertain cleanup may still act.

**Observed contradiction.** In the later snapshot, `_work_one_unadmitted`
returns that ordinary result without gating, then `_work_one` unconditionally
calls `admission.release(reservation)`. Its comment says an interrupted owner
cannot prove children stopped, but a timeout is converted into normal return
and bypasses that protection. Round cleanup cannot recover a process already
discarded from `_LIVE`. Releasing H can admit a conflicting writer while a
surviving child still writes. A normal worker exit with an untracked background
child is another version of the same uncertainty.

**Smallest policy repair to decide.** Either retain H on an outcome with unknown
descendant/cleanup state, carrying an explicit settlement distinction through
dispatch, or establish and verify the stronger lifecycle evidence before
release. Do not use `dispatch_failed` alone as the release predicate: it also
covers failure to create a process, which has different consequences. A claim
limited merely to returned wrapper calls must explicitly give up stronger
live-work/write-exclusion claims after those calls; prose cannot provide them.

**Task evidence.** Skipping the gate for incomplete dispatch is appropriate.
Report “dispatch did not establish completion; effects may exist,” rather than
the current broad comment that the worker never ran. Main should cover timeout
with uncertain children and a no-process-created control using disposable
stubs, not native models. This note runs neither.

### F3. The worker returns; the gate is still working or raises

**Trace.** The worker finishes, then `_work_one_unadmitted` starts the gate.
The gate generates a build artifact, or fails after partial output. Another
runner wants overlapping writes during this interval. Alternatively, an
exception escapes the wrapper before its explicit release statement.

**Required outcome.** Keep the reservation through worker execution **and the
gate's relevant work**, rather than releasing at `_dispatch` return. Root's
later wrapper already includes this interval on ordinary return. A genuine
gate failure remains a gate failure, not an admission wait. A pre-gate route
hold or process-creation failure is not an artifact failure.

**Exception boundary.** Do not replace the current wrapper with an unconditional
`finally: release`: that would free H after interrupted or uncertain work too.
Conversely, a known no-launch route failure need not become a permanent orphan.
Record whether invocation actually started and whether cleanup is known; use
that evidence to settle the specific H exactly once. A stale completion for
an old reservation must not release a newer attempt by the same node/PID label.

**Main-owned countercase.** Hold a gate on a disposable barrier and attempt an
overlapping reservation; it must remain excluded. Separately exercise a proven
pre-launch error, a caught gate exception, and interrupted cleanup. A gate's
own subprocess timeout can also leave uncertain descendant effects; returning
an exit code does not by itself solve F2.

### F4. Admission is blocked; the task has not failed

**Trace.** A holds the last slot, or owns an ancestor of B's declared write path.
B's node is otherwise ready. `acquire` declines B, and B starts no worker.

**Required outcome.** No gate execution, `exit 1` gate note, failed-attempt
signature, retry escalation or STUCK transition for that node. Keep it pending
and report the capacity/write-conflict reason. Other eligible frontier nodes
can be considered. If none can run, stop with incomplete work and a diagnostic;
do not burn the round budget retrying an unchanged orphan automatically.

**Observed integration.** Root's later `cmd_run` acquires before claiming, skips
declined candidates, and considers the rest of the pool. That ordering supports
this rule. However, its “no node admitted” branch breaks without clearing
`capped`; the final summary can consequently print “stopped at the 20-round cap”
after the first blocked round. Give this stop its actual reason or clear the
cap flag. The eventual nonzero CLI status for an unfinished graph is compatible
with **zero failed gates**; do not turn it into task-failure evidence.

**Main-owned countercase.** With the sole slot occupied, assert no worker/gate
side effect and unchanged failure history; release the real holder and retry.
That first wait must not contribute to a two-failures escalation.

### F5. Declarations are disjoint; actual writes are not

**Trace.** A declares `src/a.py`; B declares `src/b.py`. Both gates write
`dist/report.json`, or A's worker writes an undeclared shared file. Alternatively,
A declares `[]` but a tool creates a cache. Admission can consider declarations
compatible while actual operations collide.

**Required outcome and limit.** Include intended product/generated writes from
both worker and gate when declaring the reservation. Missing declaration means
the root fallback; explicit `[]` must stay distinct from missing/malformed data.
Bad declarations must not silently become `[]`. Parent/child paths conflict:
`src` overlaps `src/a.py`, while lexical prefix alone must not make `src` collide
with `src-old`. Use one canonical project/path interpretation across runners.
Aliases not covered by that interpretation remain a limitation, not isolation.

**Not a sandbox claim.** Admission neither prevents unexpected writes nor
proves that `[]` actually reads only. The inspected test stub itself appends
to a shared `calls` file outside its product declarations; those scheduling
tests cannot establish filesystem confinement. A no-write declaration also
does not promise a consistent read while another task writes. “Exclusive
project root” should mean conflicting declared writes are excluded; if it
means excluding readers too, write sets alone do not implement that meaning.

**Main-owned countercase.** Check missing versus `[]`, ancestor overlap,
component-boundary siblings, malformed lists and shared gate outputs. Preserve
the explicit unsupported statement for arbitrary writes; do not claim an
OS-enforced read-only worker from declaration tests.

### F6. Two runners disagree about capacity or participation

**Trace.** The store persists capacity 2. A second runner requests 3, hoping to
get another slot. Or a legacy runner omits `--shared-capacity`; or an invocation
uses a different `HARNESS_HOME`, producing a different admission domain.

**Required outcome.** A conflicting requested capacity must not silently resize
the shared domain, overwrite its policy or open a fresh store to bypass it.
Reject/diagnose the mismatch before new dispatch, without gate failure. Under
the stated persistence rule, matching configuration does not expire simply
because reservations become empty. Acquiring against capacity and conflicting
writes must be one consistent operation even when initialisers race.

**Claim boundary.** Opt-out runs and different stores are not counted, so this
is a bound on participating reservations sharing the canonical store, **not all
processes on the machine**. Root's `admission_store` resolves from HARNESS_HOME
and the CLI is explicit opt-in. Preserve those facts in reporting; there is no
native client-wide rollout or automatic adoption in this design. Stable
participation/configuration is an input to the guarantee, not a measured fact.

**Main-owned countercase.** Two processes sharing one disposable store must
respect the persisted value and capacity/write atomicity. A mismatched N starts
no worker. Legacy-mode success without creating the store is a compatibility
control, not evidence of global throttling. No module test was run here.

## Decisions to carry into integration

The immediate contradiction is F2: returned timeout/uncertain cleanup currently
releases the reservation despite the conservative orphan policy. Resolve the
release predicate and the claim it supports before presenting admission as
continued-work/write exclusion. F1's live pre-submit unwind and F4's false cap
summary are smaller, concrete integration corrections; neither warrants a new
orchestration framework or automatic dead-parent reclaim.

Capacity admission, graph ownership, artifact acceptance and process state
remain separate records. A graph lease can expire while an admission hold stays;
an admitted task can fail its real gate; a declined admission can leave a valid
task untouched. Do not copy a transition from one record into another without
its own evidence. Persistent orphan blocking is an explicitly accepted recovery
limit, not permission to say the children were killed.

Checks above are **PROPOSED / NOT_RUN**. Root owns integration and all tests;
the framework worker owns the admission module. This worker changed only this
note and its handoff, ran no worker/native/model/process-lifecycle experiment,
and makes no installation, enforcement, performance or v2-completion claim.
