# Runtime contract: reuse the DAG, correlate evidence, preserve authority

2 November 2026. Source boundary: working tree based on
`60735e2b35088c0e458e78e8a3fe3f1574c2d970`; exact inspected files are bound in
`verification.json`. CURRENT means source behavior, not installed/native proof.
REQUIRED means normative acceptance; PROPOSED means root integration work.

## 1. Authorities and independent state domains

| Domain | Current owner and truth | Must not imply |
|---|---|---|
| Dependency and acceptance | `plan/<slug>.md`, node records, actual `plan gate`; opt-in `workgraph/versions.py` receipts | A packet, lease, model output or operational summary can set done |
| Operational activity | `OperationalState`, one local resolved project path and harness home; CAS versions, events, leases | Source fact truth, process liveness, filesystem isolation or authorization |
| Artifact/evaluation | Exact output/check/input bytes, execution result and receipt provenance | A file saying PASS proves the evaluated behavior |
| Sources/retrieval | Original sources and current scoped receipts, derived retrieval views | Old similar text overrides current requirements or permits wider access |
| Method choice | `method_control.decide` advisory decision with current request/context/artifact bindings | Executes a tool, validates arbitrary gate provenance or changes acceptance |
| Handoff | Project-local bounded packet and its inspection hash | Freshness, activity, grant, acceptance or automatic resumption |
| Native permission | Actual host/tool/guard boundary and scoped resolution evidence | A graph field, model suggestion or chat label supplies a native grant |

CURRENT operational row statuses are `open`, `leased`, `withdrawn`, not
`done`. Derived activity can be `blocked`, `idle_ready`, `idle_unprepared`,
`checkpoint_missing`, `stale_memory`, `evidence_stale`, `leased_unverified`,
`expired_reclaimable` or `withdrawn`. These are not additional graph marks.
Lease activity is unverified even before expiry. Separate evidence status
must remain visible: activity chooses one priority label and can hide another
concurrent issue. A stale-memory read can occur without a new operational event.

CURRENT graph marks are pending `[ ]`, running `[>]`, done `[x]`. A failed
gate records failure and returns pending; there is no persistent failed mark.
`ready`, `blocked`, `held` and version `stale` are derived scheduling/evidence
states. `hold: permission` is a retained boundary, not an approval.

## 2. Admission and bounded control cycles

REQUIRED: simple supplied-evidence answers can terminate directly. Use a graph
for real prerequisites, shared ownership, recovery or continuation; do not
materialize a mandatory set of phases or workers. Consequence and uncertainty
choose evidence strength independently of answer length.

CURRENT dependency edges `needs:` form a DAG. Cyclic prerequisites are rejected;
a retry or changing pending/running/done state is a control cycle, not a cyclic
dependency. A parent task groups work but is not an additional `needs:` edge.
A node can be a unit of work without a separate agent.

REQUIRED bounded repair cycle: observe failure -> classify failed requirement,
source, artifact, environment, permission or evaluator -> choose a discriminating
check -> change the smallest causal surface -> rerun original acceptance.
When the same signature repeats twice, change the approach or record the
surviving blocker; no unbounded drain. Requirements/acceptance changes are
explicit, evidenced and invalidate affected results. A demonstrably wrong
check may be corrected within current authority with retained failure, a
valid control and an invalid control; this is not permission to loosen it.

CURRENT `method_control` selects (in priority order): consequential uncertainty
`CLARIFY`; bound FAIL `REVISE_ARTIFACT`; bound PASS `REPORT_GATE_RECEIPT`;
existing artifact `VERIFY_ARTIFACT`; timeout/output-limit without artifact
`CHANGE_METHOD`; failed run `DIAGNOSE`; multiple dependencies `PLAN`; else
`DIRECT`. Diagnosis checklists adapt to failure categories; PASS suppresses
prior failure diagnosis. `CLARIFY` is advisory, and does not replace inspection
of recoverable intent or create a routine question to the user. Its gate-result
JSON is hash-bound to an artifact but not an independently authenticated oracle.
The caller still checks original gate execution/provenance before completion.

## 3. Explicit correlation without another state engine

CURRENT: OperationalState values accept only bounded strings in `goal`, `stage`,
`summary`, `next`, `resource`, `checkpoint`, `blocked_on`, `evidence`,
`evidence_sha256`. Do not insert nested child/task arrays into this API. Graph
nodes already accept advisory `write_scope`, `budget`, `retry`, `escalation`
and `evidence`; these do not configure enforcement.

PROPOSED minimal integration record: a project-relative, atomically replaced
JSON manifest linked by existing checkpoint/evidence fields. It is a derived
cross-reference, not a second completion ledger. No parser/enforcement for this
record exists today. The following is its field contract, not a new CLI API:

```json
{
  "schema": "harness.task-composition/v1",
  "task_id": "delivery",
  "generation": 1,
  "parent_task_id": null,
  "graph": "plan/delivery.md",
  "required_nodes": [1, 2, 3],
  "integration_node": 4,
  "members": [
    {
      "node_id": 1,
      "child_task_id": "delivery.frontend",
      "session_id": "UNKNOWN",
      "packet": "handoffs/delivery/frontend.md",
      "write_scope": ["frontend/"],
      "result_receipt": null
    }
  ],
  "view": {"group": "delivery", "label": "Application delivery"}
}
```

REQUIRED validation: resolve `graph`, `packet` and every manifest path inside
the owning project; reject escape/redirected paths, duplicate members/required
IDs, unknown required/integration nodes, mismatched graph ownership and cyclic
parent ancestry. A manifest can be partial while in progress; it cannot be
used to accept a join until all required members resolve to current receipts.
`required_nodes` are this task's terminal deliverables, not every transitive
node; the graph carries their prerequisite closure. The integration node
must depend on every required terminal node and pass its own original gate.
Optional members cannot silently replace required ones. Generation increases
on a membership/ownership/goal mapping change and invalidates this task's join.
The generation must be a bound input if used for acceptance.

REQUIRED acceptance bindings reuse existing versioned node receipts: graph
node identity; definition and policy hashes; declared inputs/checks; parent
result identities; output hashes/modes; run ID/time and exit status. No invented
receipt format replaces `plan.result/v1`. Correlate a child to that receipt via
its graph/node and project identity. A session ID is only navigation metadata;
UNKNOWN is valid, a guessed ID is not. Operational row version/fence/request ID
identify a ledger mutation, not an artifact evaluation. Remote/worktree paths
must not be collapsed into the same ledger by reusing a human task name.

## 4. Join, invalidation and unaffected work

CURRENT opt-in `## versions: v1` supports content-addressed receipts and binds
`inputs`, `checks`, `outputs`, definition/policy and `needs:` parent receipts.
`plan versions <slug>` inspects freshness without rewriting. `plan refresh
<slug>` persists invalidation of stale completed nodes while retaining sources,
old receipts and live leases. Missing/corrupt receipts are held, not accepted
from prose. Undeclared files and environment changes are outside that binding.
Legacy graphs remain unversioned; done marks alone have no automatic freshness
guarantee. The current `v2-completion` graph has no versions marker.

REQUIRED join predicate: every required terminal node has a current valid gate
receipt, required sources/checks/outputs match, no relevant unresolved hold,
and the parent integration gate passes on those exact receipts. Declare the
manifest as an integration input and acceptance-relevant check files in
`checks:`. For environment-sensitive work, bind an environment fingerprint
artifact as a declared input; CURRENT code does not discover one automatically.
A hash proves correspondence to observed bytes, not authenticity against an
OS user who can rewrite both code and evidence, and not a global atomic snapshot.
Revalidate immediately before consequential use.

Example DAG: 1 frontend; 2 backend; 3 docs `needs: 2`; 4 integration
`needs: 1,3`. Backend PASS permits docs while frontend fails. Hold integration;
preserve backend/docs receipts. A changed frontend output invalidates frontend
and dependent integration, not backend/docs. A changed backend result invalidates
docs and integration. A new frontend PASS with identical output but a new result
identity still invalidates an old parent join. A removed required branch or
changed gate/requirement must invalidate the join, never make it cheaper to pass.
An initial frontend failure may never have a prior success receipt; it is still
pending and blocks integration normally.

PROPOSED correlation manifest extends this existing model to separately named
child tasks/handoffs. Same-graph joins are already implemented. Arbitrary
cross-graph receipt traversal, all-or-nothing acceptance across files/SQLite,
nested concurrent statechart regions and automatic join transactions are not.
For current bounded work, one root graph with explicit terminal dependencies
avoids those gaps. Do not install a new engine without a case this cannot model.

## 5. CAS, replay and recovery

CURRENT OperationalState writes task projection, event and request replay in
one SQLite transaction. Supply the observed `expected` version and a unique
request ID. Exact same-ID/same-input retry replays the original result; same
ID/different inputs conflicts. A fresh mutation increments version. Replayed
claim output may be expired: it is not a fresh lease or refreshed source check.
On conflict, read changes from the previous cursor, take a fresh snapshot and
reconcile intent; do not repeatedly force old state.

CURRENT operational lease TTL is 1..3600 seconds (default 300), fenced by token
and increasing fence; graph running leases are a separate four-hour mechanism.
Never interchange them. The ledger cannot prevent a previously running process
from editing files after its lease expires. A takeover requires inspection of
actual worker activity and ownership; fenced ledger operations alone do not
make dual file writes safe. Do not display lease tokens in packets/UI.

CURRENT claim checks blocked-on, missing/invalid checkpoint, evidence and linked
memory freshness; renew checks owner/fence/expiry plus evidence and memory.
Renew does not independently recheck checkpoint presence. Release permits stale
evidence/memory but still requires current unexpired ownership. `stop` refuses
to pretend it killed an active worker. `withdraw` is terminal for that task ID.
`checkpoint`, `stop`, `resume` preserve existing memory links; low-level `put`
with omitted memory receipt clears that link. REQUIREMENT: consumers must not
use `put` casually to clear a stale dependency; retain/revalidate receipts or
use preserving checkpoint operations. The source guard is not automatic here.

REQUIRED cold recovery sequence:

1. Read `handoffs/<task>/` and graph context; verify source revision and current
   gates. Missing packet means unknown, never done. No registry is required.
2. Read `harness task status --json` / operational snapshot when available;
   distinguish unavailable/corrupt from fresh empty state. Preserve local file
   fallback when MCP `op_state` is disabled; do not enable it silently.
3. Revalidate linked memory/evidence even if cursor is unchanged; inspect current
   graph versions. Preserve failure history and independent valid branches.
4. Reconcile claims, actual process activity, write scope and native authority.
   Only an authorized executor resumes useful ready work. No automatic model
   wakeup is implied by a lease, checkpoint, file update or idle chat.
5. Rerun affected original checks, then integration; checkpoint atomically.

There is no transaction spanning graph files, the operational DB, source files
and memory. Recover a crash between graph acceptance and optional checkpoint
by rebuilding the operational view from current graph receipts; never rebuild
acceptance from an operational summary. After claim-commit/lost-response, exact
request replay recovers the old response without dispatching duplicate work;
revalidate lease and process state before continuing. A failed mutation leaves
no event/replay commit. Event cap (10,000) refuses writes rather than pruning.

## 6. Permission recovery without duplicate denied effects

CURRENT graph gate refusal is `NOT_RUN`, not an executed FAIL; it sets
`hold: permission` and does not consume a diagnostic gate attempt. Structured
worker denial plus unfinished work holds only that branch. Independent PASS
can settle already-completed work despite incidental worker denial. Guard
holds apply to either backend; structured worker-denial reporting currently
uses the Claude adapter signal and has no equivalent Codex signal in this
adapter. Arbitrary result text is not a trusted denial detector.

REQUIRED packet: preserved goal; exact rejected effect/target and rejecting
layer; native refusal evidence; affected node/dependants; safe independent work;
smallest supported owner action; next original gate. Do not copy secrets.
A different tool/agent/account must not repeat the denied effect. A new runner,
`resume`, `--force` or `--attended` does not resolve the hold. Use a real
supported approval mechanism only when one exists and current authority permits.
After the underlying boundary is resolved, root records scoped resolution and
removes only that permission hold through the authorized graph maintenance
path; root resumes original checks. Graph metadata never edits native policy.
When no supported path exists, retain BLOCKED and stop bounded work.

## 7. Disjoint write ownership and shared checkout

REQUIRED each worker gets exact owned files/directories, read scope, original
gate, dependencies, stop conditions and packet. `ctx:` is context/declared
editable artifact metadata, not an OS sandbox. `write_scope:` is currently
advisory; no source enforcement is claimed. Check overlaps before dispatch,
including parent/child directories, symlink aliases, shared generated output,
formatters/lockfiles and root-plan/evaluator ownership. A packet writer owns
only its packet; never update a peer's status or stage/commit unrelated files.

CURRENT this campaign's scopes are fixed in `handoffs/v2-completion/README.md`.
Root owns runtime integration, root plan and independent final checks. For
worker additions or boundary changes, read current shared state before editing
an interface. Serialize an overlapping file or use root-authorized isolated
worktrees with root merge/integration; isolation does not prove semantic
compatibility. Separate worktrees have separate operational ledgers; the explicit
`PLAN_DIR` override can share one plan directory. Without it, worktrees may
claim different copies of the graph. Do not assume every worktree lease or task
registry is globally coordinated.

## 8. Useful grouping and file-first coordination

CURRENT grouping: one goal/root graph, per-node records, one handoff directory
and one packet per worker. Existing `plan status`, `ready`, `context`, `versions`
and `harness handoff --task` are sufficient read views. Native app UI grouping
and bidirectional task-state sync are not implemented by these modules.

PROPOSED UI projection: group by human goal, then required deliverable/owner;
show pending/running/held/current/stale separately from gate PASS/FAIL/NOT_RUN,
receipt/source revision and last observed activity. Keep backend/docs visible
as valid during frontend repair; show one actionable parent hold and dependency
reason. Expose original gate/packet links and evidence age. Never call a quiet
session live, show a stale receipt green, or place raw tokens/source bodies in
a sidebar. Grouping is navigational and must not mutate acceptance/permissions.

REQUIRED file-first policy: read README, own packet and relevant shared evidence
at start/resume and meaningful dependency boundaries. Atomically replace only
one's own packet after a material result, failed check, blocker or next-action
change. Keep packet <=16 KiB (current reader), link larger evidence. Current
reader also caps task entries at 100 and aggregate packet text at 64 KiB; exceeding
limits fails explicitly. Keep all packets compact enough for aggregate reads.
Handoff inspection hashes bytes and refuses nonregular/redirected/oversized
packets; it does not parse or trust their claims.

No routine messages, confirmations, model heartbeats, peer activation, scheduled
polling or mandatory conversation copies. Messages are only for separately
authorized activation/intervention. Idle work stays idle; completion of a packet
does not dispatch a model. When a bounded assignment is complete or genuinely
blocked after independent work, leave evidence, next action and held actions,
then stop. Root's final integration is an independent gate, not a vote among
worker reports.
