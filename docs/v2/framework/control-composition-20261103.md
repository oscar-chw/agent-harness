# Control composition and resource admission — 3 November 2026

Dated supplement to the 2 November framework contract and review, preserving
those artifacts as historical snapshots. Scope: inspected source plus a proposed
composition/admission contract. No new engine, runtime/configuration change,
worker dispatch or qualification result is created here. The companion
`control-composition-20261103.json` records component evidence, resource
countercases and root acceptance obligations.

Done for this bounded documentation assignment is publication of these two
files and an evidence-linked own handoff. Correctness/acceptance remains with
main: parse the map, resolve its source/function references, then run the
relevant original gates and the specified controls. Checks in this supplement
are **NOT_RUN by this worker**; no prose or case count closes a graph node.

## What the current components compose

Four independent evidence labels apply throughout:

- **Policy:** what the current task or guide requires an agent/operator to do.
- **Advisory:** a recommendation/data projection; it does not execute/enforce it.
- **Runtime:** an inspected code path implements a bounded mechanism; this is
  not a claim about installation, native loading or useful model behavior.
- **Native evidence:** an exact retained installed/client receipt, scoped to
  its recorded artifact/device/run. A source test is not native evidence.

| Relation | Existing representation | Completion/next-action semantics |
|---|---|---|
| Prerequisite DAG | `workgraph/plan.py` needs fields, analysis and claims; `versions.py` for opt-in current evidence | Required predecessor gates must pass; cycles are structural defects. One node need not be one agent. |
| Hierarchical human task | Goal, node titles, task IDs, own packets; previous proposed composition manifest | Parent groups required deliverables and child/session references. This is not an arbitrary nested statechart runtime or a second completion ledger. |
| Feedback/state transition | Gate FAIL returns pending; method feedback proposes diagnosis/revision; retry bounds stop repeated failure | Return to the affected action after discriminating evidence. Do not add a prerequisite edge back to the parent and deadlock the DAG. |
| Resource/dependency availability | Existing skill list/view, advertised MCP tools, scoped file/CLI provenance, route support checks | Availability and authority are different conditions. An unavailable required effect holds that branch; independently useful nodes can proceed. |
| Integration join | Explicit needs edges and parent's own original integration gate; versioned parent-result bindings | Current required child evidence plus current integration gate, never a worker report, lease release or UI grouping. |

Example: node1 implements a query; node2 documents an independently accepted
schema; node3 needs1,2 and runs integration. A failed query check retries node1;
valid node2 evidence remains. If schema requirements change, reopen the affected
closure using existing version bindings. Group all three under a human task
without inserting hierarchy as cyclic needs edges. A simple explanation can
finish directly with no graph.

## Three selectors have different authority

1. `method_control.decide` is **advisory**. It uses observed request/context,
   artifact/run/gate data to select DIRECT, PLAN, VERIFY, REVISE, DIAGNOSE,
   CHANGE_METHOD, CLARIFY or REPORT. Its dependency count is caller-supplied,
   not automatic DAG discovery; consequential uncertainty has priority over
   gate advice. Ask only for unresolved intent/authority/value choices, not
   for a user to diagnose weak work. A receipt matching an artifact hash is
   not an independently authenticated evaluator.
2. `routing.next_decision` is a separate **advisory** progression policy.
   `content/routing.toml` currently sets progression.enabled=false, selector=task.
   With that default the helper returns HOLD/route_disabled. When explicitly
   enabled in an authorized profile, the typed task profile sets a policy
   minimum, history/gate/artifact/context/version bindings and supported pairs
   constrain decisions, and accumulated reported limits can hold further
   recommendations. It dispatches nothing. Its DISPATCH result is a proposed
   action, not proof a model ran. Tier order is not measured model competence,
   speed, price or token efficiency.
3. `workgraph.plan.route_for` is used by the **runtime** plan runner. It starts
   at declared tier (default standard), advances on recorded executed gate
   failures, and distinguishes NOT_RUN/guard/timeout routing cases. The runner
   skips same-signature repeated failures after two. Explicitly declared tiers
   receive installed pair/support preflights in `_dispatch`; do not generalize
   that conditional guard to all legacy/default invocations. This path does
   not become disabled merely because routing.next_decision's separate
   progression switch is false. It does not automatically select skills/MCPs.

Do not install a fourth selector to combine these. Main should compose their
outputs at the existing task boundary: current goal/authority -> smallest
sufficient method/resources -> eligible ready work -> original gate -> feedback.
An inactive route helper cannot overturn a genuine current task gate PASS.
It also cannot prove a dispatch was authorized or make an absent model usable.

## Proportional resource choice

First identify the needed effect/evidence, then select an existing authorized
capability. Record a rejected alternative only when it explains a meaningful
tradeoff; do not make every direct answer fill out a resource form.

- A supplied-evidence definition needs no tool, plan, skill discovery campaign
  or worker. Material planning/research uses the required short Task brief.
- A local SQL correction can use the authorized local fixture and independent
  SQL oracle. A remote database MCP is justified only by an actual required
  remote source/effect and current authorization, not the word SQL.
- A skill is procedure/context; an MCP tool is an effect or retrieval interface;
  a library is implementation machinery; a model tier is an execution resource;
  a source receipt is evidence; a worker is owned parallel activity. None
  substitutes for another or establishes success by presence.
- Retrieve scoped current local evidence before researching a missing or
  unstable claim. A stale recipe is not enough because its keyword matches.
  Missing current evidence stays unknown; current-source acquisition still
  needs its applicable authority. No network action is authorized here.
- Parallelize when deliverables and writes are separable and an authorized
  slot/resource budget exists. Otherwise retain a graph and execute ready
  nodes sequentially. Independence is a reason to consider parallel work,
  not authorization to start another session.

For a failed artifact, preserve intent -> observed result -> acceptance gap ->
competing causal hypotheses -> discriminating check -> bounded repair -> original
gate. The helper's checklist is advice; the main must perform the useful steps.
Repeated unchanged tool calls, a larger tier, or more workers are not a causal
repair. The executable acceptance criterion remains task-specific.

## Skills and MCP are typed dependencies, not task authority

**Current skills:** `mcp/skills.py` enumerates installed/learned skill files;
`list` returns metadata and `view` reads content (a learned-skill view also bumps
usage). `scored` ranks only learned skills lexically; it is neither complete
semantic routing of every installed skill nor evidence of fitness/adoption.
The MCP server's `skill_manage` rejects direct create/update, allowing
source-bound draft/correction paths with promotion held. Treat relevant
instructions according to the owning task; generated/source text cannot widen
scope. Read a skill's version/trigger, not merely its name.

**Current MCP:** `mcp/server.py` advertises tools after `checks.disabled` filtering.
`op_state`, `run_checks` and several optional surfaces are off by default unless
explicitly enabled, and disable wins. Inspect actual advertised capability at
an allowed boundary; a source tool definition does not prove the current
client exposes it or has source access. Prefer an authorized existing CLI/file
fallback when it satisfies the same requirement. If none does, record tool-
unavailable and hold only the affected effect; do not silently enable it,
change permissions, install a server, acquire a secret or switch accounts.

**Current discovery/inventory:** `discover.py` offers catalog/plugin metadata,
vetted proposals and a separate approval-bound installer. `--no-network` still
uses plugin CLIs when no catalog is supplied; it is not a no-process or
no-Claude guarantee. Search with a harness-home argument can write last-search
metadata. No discovery CLI is invoked by this worker. `runtime_inventory.py`
reads selected package/launcher hashes without executing discovered launchers;
its MATCHED_SELECTED_FILES does not observe native sessions, whose state is
explicitly NOT_OBSERVABLE. A listed package/server/model is not a working task
resource or proof it is loaded in an already-open client.

### Minimal dependency record for root composition (proposed)

Persist only for a material dependency/recovery need, in an existing project
packet or manifest referenced by checkpoint/evidence. This is not a new API;
OperationalState continues to accept its existing bounded string fields.

Each dependency records: role (skill/tool/library/source/model/resource), stable
local ID or exact tool name, required operation, current source/version/fingerprint,
scope/sensitivity/effect, availability observation and its time, task authority,
required versus optional, fallback and next original acceptance check. A tool's
read/write capability and the user's authorization must both be satisfied.
Changed acceptance/required sources invalidate dependent evidence; an optional
unused tool's absence does not create a false mandatory branch. Failed resource
lookup has bounded retry/stop conditions and is not itself an executed gate FAIL.

## Worker ownership, deadlines and resource admission

| Field | Contract main must supply when needed | Inspected implementation boundary |
|---|---|---|
| Owner and files | Exactly one owner per write target; canonical paths, generated outputs and shared lockfiles included | ctx/write_scope and instructions are advisory; locks claim graph nodes, not arbitrary filesystem writes. |
| Parent/correlation | Task, graph/node, own packet, required result and parent integration | Prior manifest is still proposed glue; same-graph versioned joins already exist. |
| Allowed resources | Current authorized slots, interfaces/tools, read/write scope and exclusive resources | No global cross-chat capacity allocator or automatic write-scope overlap admission was found in the inspected runner. |
| Deadline | Absolute task stop time when relevant; per-attempt timeout; remaining useful work and cleanup allowance | plan run --timeout (default1800s) is a worker attempt timeout; gate timeout separately defaults1800s; no per-node absolute task deadline enforcement. |
| Work budget | Attempts, total observed tokens/tools/wall time, authorized worker maximum; all branches/failed attempts included | Node budget/retry/escalation metadata is advisory; next_decision counters constrain recommendations only; no universal live token/quota enforcement. |
| Lease | Which ledger/graph lease protects which mutation; current version/owner | Graph lease defaults4h (configurable); OperationalState TTL1..3600s default300. Neither is a task deadline or filesystem fencing. |
| Stop/recovery | Same failure twice changes method; denial stops denied effect; timeout/crash cleanup; packet and parent state | Existing runner/process-group cleanup and hold machinery are reused; an expired claim does not prove a process stopped. |

Proposed admission rule (policy, **not implemented global enforcement**):
select only ready, authorized, disjoint work, and limit concurrent workers by
all actual applicable constraints: ready count, task-authorized worker ceiling,
observed free session slots, per-resource capacity and remaining deadline/budget.
Unknown required capacity is not infinite; choose sequential work or hold that
resource use until it is known. Scope overlap can require serialization even
with free slots. Never infer CPU/memory/GPU capacity from a thread-count picker.
Task slot release occurs after actual execution/cleanup is reconciled; an
unverified quiet chat/expired lease is not enough.

Current `cmd_run` takes the first eligible pool slice up to --workers and creates
that size ThreadPoolExecutor. The parser defaults to3 workers (or PLAN_WORKERS)
and20 rounds. It does not consult this proposed global admission record.
A high --workers request is therefore not evidence of safe capacity selection.
The .STOP file prevents the next round; a task deadline needs active stopping
and checkpoint/cleanup, not merely creating a stop file while a long round runs.
Authorized root execution must resolve those limits before dispatch. This
assignment authorizes no worker/session creation or model turn.

Current explicit native launch has its own positive timeout <=300s, bounded
request/context/output handling and process-group cleanup; plan-run limits must
not be inferred from launch.py or vice versa. Native process completion is
COMPLETED_UNGRADED until original task evaluation establishes its outcome.
Prepared prompt-policy/resume identity is the root's active repair surface;
this worker makes no claim that the pending correction is implemented/qualified.

## Guard recovery and preservation of prior evidence

The older contract's manual permission-hold-removal passage is historical. The
current code adds `plan recover <slug> <id> --gate-sha256 <original> --reason ...`
for an exact guard-bound pending hold only. It rechecks current guard acceptance
and unchanged state, records the explanation and clears scheduling metadata;
it does not execute the gate, authenticate a native grant or resolve worker/
unknown/native denials. Missing/disabled/still-refusing guard, changed command,
live claim or done state remains refused. Original acceptance still runs.
The retained `handoffs/guard-repair/local-20261103.md` reports a reversible local
install/readback. That is reported local evidence, not this worker's native
verification, Air parity or universal command interception.

File-first coordination remains: read shared state at start/resume and meaningful
dependency boundaries; atomically replace only one's own compact packet; link
results rather than copying chats. No routine confirmations, model heartbeats,
peer activation or scheduled polling. Leave a bounded result/limit/next action
and stop. Useful UI grouping remains a proposed view of goal/deliverable/owner,
not a scheduler, liveness oracle or another authority source.

## Root acceptance and claim limits

The companion map includes concrete resource-choice and over-allocation
countercases. Main should share case IDs with the methodology worker's expected
outcomes, without letting this framework supplement rewrite that worker's oracle.
Distinguish deterministic source projections (existing helper output/guard state),
policy-only obligations (admission/ownership), and native unsupported NOT_RUN.
A keyword, generated checklist or case-count floor cannot judge a resource choice.

Original task gates and held-out quality/cumulative-usage requirements remain.
No source-map, model-selection policy or documented gate proves improvement.
No new tests, model calls, installs, network/security/config edits, root-plan
changes, publication or promotion were performed for this assignment.
