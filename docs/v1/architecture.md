# v1 architecture and evidence contract

26 October 2026. The aim is reliable coding, research and general project work across
supported clients, with local evidence and recoverable state. This is a development
architecture, not a claim that v1 is released, every client is equivalent, memory
is lossless, or an agent can solve any task. The deployed 0.9.1.dev0 candidate is
kept separate from this development work.

## One integrated system

A request enters through a native client adapter. A project/task contract identifies
the intended outcome, authority, allowed sources, acceptance check and budget. Scoped
retrieval supplies a small source-bound context packet. The coordinator chooses a
single worker or a bounded dependency graph; evidence can send any node back to
research, planning or implementation. Independent task checks settle completion.
Verified outcomes and explicit corrections can create local learning candidates;
promotion requires a separate held-out comparison and can be rolled back.

| Boundary | Existing foundation | v1 requirement and remaining evidence |
|---|---|---|
| Client and provider | Claude Code, Codex, Copilot and other adapters; MCP/CLI entry points | Detect capabilities and actually observe fresh and existing-client loading. Native subscription login and an API model provider are distinct paths. Unsupported capabilities must be named; no universal-provider claim from an adapter list. |
| Project identity and state | Stable project IDs, source-bound records, CAS updates, task ownership and graph leases | Preserve user/project/tenant separation across clients, concurrent corrections, reassignment, restart and stale writers. A lease is not proof a model is running. Cross-device sync requires its own conflict and privacy checks. |
| Local knowledge | Source vault, document sections, original evidence, source citations and conversation search | Retain source identity/revision/status; distinguish facts, documents, history, task state and inferred lessons. Retrieval indexes are derived caches, never the authority. Withdrawals and unavailable evidence must survive retrieval and summarisation. |
| Research and source intake | Source vault, document readers, source/evidence graph and client search/browser tools | Acquire relevant field information lawfully; deduplicate social pointers and resolve primary sources. Keep access failures, dates, source versions and claim-support links. Shared API/wiki/environment knowledge obeys the same project/tenant permissions; retrieved text never grants execution authority. |
| Context and intent | Scoped facts, source receipts, bounded packets and explicit task profiles | Explicit preferences may be saved; inferred intent remains a scoped candidate and cannot grant authority. Retrieve only material context, keep stable prefixes where practical, and measure cache hits and total usage rather than promise savings. |
| Planning and execution | Dependency graph, independent gates, bounded native launch, stop/retry and signal cleanup | Route by actual task needs and available model/effort pairs; isolate parallel writes. Enforce worker, time, retry and usage budgets. Quota exhaustion, unavailable tools and failed acceptance are different outcomes. Verify cold recovery and final integration, not only each worker. |
| Evaluation and review | Test tiers, source checks, code review, artifact bindings and negative controls | Completion requires task-specific evidence. A real citation must also support its adjacent claim. Freeze held-out cases, actor/evaluator boundaries, effective model identity and all overhead. Require quality at least baseline and aggregate tokens no greater than baseline; preserve failures. |
| Governed learning | Dormant procedure drafts, source episodes, correction/withdrawal links and rollback | Never promote from an agent's own scores or repeated wording alone. Independent source episodes and held-out native evidence are required. Current promotion remains held where answer isolation, effective model and grader provenance are unproved. |
| Skills and extensions | Task skills, discover/vet flow, installer records and rollback | Reuse existing capabilities before adding dependencies. Verify source, license, version, supported installer and actual installed result; preserve action-specific authority. New plugins or learned procedures are optional until their marginal task benefit is measured. |
| Diagnostics and release | Runtime/status, doctor, manifests, reversible installation and CI | Report installed revision, active client discovery, phase/node state, scope/retention coverage and errors separately. Progress comes from completed acceptance checks, not a fabricated confidence percentage. One versioned core with explicit machine profiles and reversible, CI-qualified updates is the target; cross-device consistency needs actual readback. Source tests, model performance, release and rollout are distinct gates. Default rules must justify their context/maintenance cost. |

## Memory placement and cache policy

Use the [placement map](memory-placement.md). Original documents and transcripts
stay with their owners. Compact facts, project records, plans and task checkpoints
carry explicit provenance and scope. A correction supersedes an old claim rather
than silently deleting its history. Local search can expose retained evidence;
it cannot recover data a provider never exported or a retention policy removed.

The first v1 checkpoint repairs two actual retrieval defects: shared FTS statistics
could suppress a valid scoped answer, and a fallback reader could miss terms a peer
had already indexed. `cache-status` is a read-only inventory, not a purge command.
Its outside-current-discovery rows may belong to another active client and are not
authorised for eviction. Free pages, KB cache and session-search storage are
reported separately. Compaction, retention-policy changes and live rebuilds remain
separate operations; no source history is disposable to make doctor green.

## How source references influence decisions

Start from a requirement or observed failure. For each source ask:

- Does it address that problem, and at the relevant client/runtime boundary?
- Is the support a measured result, a reproducible mechanism, practitioner advice,
  an upstream claim, or an unread social pointer?
- What benefit remains after accounting for existing components and overlapping sources?
- What are the conflicts, dependencies, permissions, token/latency and maintenance costs?
- What is the smallest falsifiable local comparison, and what would make us reject it?

Use **adopt, complement, validate, defer or reject**, with reasons and provenance.
Do not sum invented precision scores or rank by stars. A source with weak efficacy
evidence can still suggest a useful experiment; it cannot establish performance.
Deduplicate reposts by their underlying method or repository.

| Source and inspected coverage | Decision for this architecture | What would change the decision |
|---|---|---|
| [SQLite FTS5 documentation, bm25 section](https://www.sqlite.org/fts5.html#the_bm25_function): corpus averages and document frequencies belong to the whole FTS table. | **Adopt the mechanism explanation.** It directly explains the reproduced scope-ranking defect; fix the existing retrieval seam, not the storage stack. | Regression/control and bounded latency evidence on the changed implementation. |
| [Felix Rieseberg's outcome-level task-design essay](https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/), article read. | **Complement.** Useful framing for outcome contracts, appropriate reproduction tools and external judges; mostly overlaps the existing work loop. Practitioner advice, not evidence of autonomous self-learning or unlimited capability. No new default prompt. | A missing task-design behavior demonstrated on held-out work, then a paired improvement without extra total tokens. |
| [OpenHeart README](https://github.com/AhmadHassan-BTed/OpenHeart), overview/features inspected; code and benchmarks not audited. | **Defer adoption; validate only for a concrete code-navigation gap.** A program graph could complement source retrieval. The README's memory-compression claim is not a demonstrated reduction in LLM tokens, and no local performance gain is established. It does not replace provenance, history or project scope. | Pinned implementation, license review, representative language/repository coverage, source round-trip checks and matched retrieval/task cost results. |
| [blader/humanizer](https://github.com/blader/humanizer), prior inspected editing reference and [local pilot](humanizer-candidate/RESULT.md). | **Reject redundant default activation for this candidate.** The control already passed the case; added instructions showed no observed gain and higher usage. Reposts are the same lead, not new evidence. Keep the [optional source-check workflow](source-check-workflow.md). | New held-out cases demonstrating a meaningful quality or token gain under the same acceptance rule. |
| Raw-RAG, TextFold, Praxist and other retained leads in the [source/evidence graph](source-evidence-graph.md). | **Validate/defer per requirement**, preserving the recorded limits. Do not install one framework per link. | The specific frozen comparison in each existing row; no popularity-based promotion. |
| Unread/new social posts | **Defer.** Unknown content cannot define a feature or become a factual premise. | Lawful readable primary material and a requirement-level reason to investigate. |

Python and SQLite remain the implementation baseline. Rust is an option for a
measured hot path, not a prerequisite for reliable memory or a reason to rewrite
working components. A code graph, reranker or alternative agent loop is optional
until it beats the simpler baseline on the same work and full cost.

## Next qualification steps

1. Finish this memory correctness/diagnostic checkpoint with sensitive controls,
   source tests and independent review; preserve the live index failure.
2. Freeze a small authorized cross-client recovery set: saved fact, changed source,
   correction, inaccessible evidence, compaction, concurrency and stale ownership.
3. Observe effective native discovery and evaluator isolation before allocating a
   separately bounded real-task comparison. No unit-test count substitutes for it.
4. Expand learning/routing/orchestration only where those results identify a gap.
   Merge, deployment and new model-call budgets retain their own authority.

## Readiness before work — design requirement, not yet a qualified feature

Use risk-adaptive, evidence-backed readiness. A small read or local edit needs a
small check; a shared schema change or irreversible operation needs stronger
evidence. Readiness covers the goal and acceptance, uncertain assumptions and
source currency, actual capabilities/environment/authority, ownership and
interface/schema conflicts, resource budgets, executable verification and recovery.
It is not a universal long checklist or a substitute for runtime checks.

Bind readiness to the relevant source revisions, dependencies, scope and shared
state. When those change, invalidate affected readiness and recheck before the
dependent action. Compare actual changed files and observed actions against the
declared operation where signals exist. A declared intent or advisory claim cannot
prove what a worker actually did. Missing signals remain unknown.

Qualification must include a stale plan, a missing environment dependency,
competing interface/schema changes in disjoint files, an undeclared edit and a
clean cheap task. Measure prevented failures, false blocks, latency and total
token overhead against the current workflow. This requirement adds no default
prompt, new daemon or dependency until that comparison succeeds.

### Complementary source intake

- [Foremerge](https://github.com/naw103/foremerge), README inspected: declared
  semantic scopes, advisory claims and validation tied to candidate fingerprints
  are useful coordination references. Its claims are nonexclusive, its local
  state is not distributed consensus, and validation is not an OS sandbox.
  **Complement/validate**, not automatic adoption. We have not audited its code
  or established local productivity gains; declaration-versus-edit coverage needs
  explicit qualification before relying on it.
- [LangChain harness-engineering report](https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering),
  primary article read: it reports fixed GPT-5.2-Codex improving from 52.8 to 66.5
  on Terminal Bench 2.0 after harness changes. **Complement** trace-based failure
  analysis and external verification. This benchmark-specific result does not
  isolate memory's causal effect, establish universal gains, or justify adding
  its framework to this harness. Existing tracing/eval/recovery is the first reuse
  target; test marginal benefit before adding overlapping infrastructure.
- [Anthropic's agent-pattern guidance](https://www.anthropic.com/research/building-effective-agents),
  primary article read: start with the simplest adequate solution and weigh
  increased complexity against latency and cost. **Complement** execution choice;
  responder, router, tool use, multiagent and generator/verifier are alternatives,
  not a mandatory maturity ladder. The article itself warns its tooling landscape
  has changed since publication.

The related social graphics remain secondary pointers. Closed-loop verification,
recovery, observable traces/evals and execution authority are core requirements;
MCP is a complementary interface, multiagent use requires task evidence, and a
gateway is conditional on provider needs. Pricing ratios depend on actual models
and usage. No dependency was installed from these references.

[Chroma's Context Rot report](https://www.trychroma.com/research/context-rot),
primary report inspected, measures nonuniform degradation as context grows across
its tested models and controlled tasks. **Complement** focused context and durable,
source-bearing state; it does not prove this harness improves a task. The supplied
IG `DeBl1GmsVLJ` brief identifies its 3/6-to-6/6 and 94%-to-25% figures as simulated;
they are not empirical acceptance evidence. Selective subagents and on-demand
skills remain optional mechanisms. Any promotion comparison must count the whole
system's tokens, retries and quality, not merely a smaller coordinator window.

## 31 October candidate: shared local control and proportionate execution

The owner's latest direction is a shared system for tasks, memory, knowledge and
execution across client applications, with less manual coordination. This is an
architecture amendment, not a claim of deployed central session control.

### Task admission

Choose direct answer, bounded task, exploratory investigation or rigorous
execution using scope, uncertainty, consequences, reversibility and coordination
needs. Reasoning depth, research breadth, workflow machinery and verification
strength are separate controls. Keep simple work implicit where adequate.
Admission should not require a separate LLM call, persistent plan, worker or
memory search for every prompt. Existing mandatory checks and access boundaries
still apply. See the [bounded trigger review](../v2/adaptive-execution-review-20261031.md).

For the proposed Codex adapter, interpret the owner's suggestion to route simple
tasks to "chat" as a direct-answer task policy inside Codex. It is not an asserted
native setting, automatic model switch or authorized transfer to a different
ChatGPT conversation. Such a separate destination needs its own explicit adapter,
supported access and task/context contract.

### Shared state and client boundaries

Use a local control service with a durable project/task registry, scoped source
vault, memory/retrieval, execution queue and result/evidence store. Managed workers
use supported native adapters; independently opened clients can cooperate through
MCP/CLI and source-bound project state. Native conversations and hidden runtime
state remain client-owned unless a supported interface exposes them.

The target is that changing a compatible frontend preserves project state and
useful context. App changes may also change tools, permissions, sandbox, context
handling and capabilities, so they cannot be represented as only a model change.
Scope access separately from a client's identity. Never forward an unrelated
project or reuse credentials as a shortcut to provider interoperability.

The [Codex app-server interface](https://learn.chatgpt.com/docs/app-server#start-or-resume-a-thread)
is a candidate supported Codex backend for thread creation/resumption and paginated
history. It reports loaded instruction sources and session identities. This audit
did not launch it or qualify a new controller against the installed runtime.

### Concurrency and resource admission

Represent many tasks in the queue and admit bounded workers based on actual
independence, native capabilities/limits, account quota, memory/CPU and integration
capacity. Requested worker count is demand, not a promise of simultaneous work.
Use per-task and account-wide limits and ownership fencing; do not create extra
primary sessions to evade a native or provider concurrency boundary.

[Current Codex documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents#global-settings)
exposes `agents.max_concurrent_threads_per_session`, excluding the primary; the
default is chosen by Codex when unset, and `agents.max_threads` is a legacy alias.
This documents a configuration surface, not the current effective limit on this
host or permission to exceed a hard runtime cap. No configuration was read or
changed for this proposal. Cross-client worker admission needs actual readback.

### Useful outcomes without user-authored handoffs

After material work, adapters should persist compact structured outcomes: task
identity and scope, relevant input/output revisions, changes, result, acceptance
receipts, unresolved assumptions, blockers and next permitted action. Preserve
contradiction, supersession and withdrawal rather than blending them into a
summary. Trivial answers need not create a task packet merely to satisfy a form.

At resume or the next stateful action, build a small scoped context packet from
canonical records and relevant deltas. Track its revision/watermark; revalidate
stale dependencies before consequential work. A non-live client can catch up on
read. Snapshot/packet generation is the system's responsibility, not a manual
handoff the user must compose. Critical required context being unavailable must
be distinguished from an optional memory service being unavailable.

Adapter registration or an installed guide does not establish that a model used
the packet. Qualification must observe actual cold-client reads, correct task
continuation, current corrections, missing evidence, concurrent ownership and
disconnect recovery. Information never persisted before a crash remains missing;
raw conversation injection is not a remedy for that gap.

### Qualification and authority

Before activation, freeze cases for: direct answers without orchestration,
required fresh-source checks, one-line consequential changes, cold recovery,
stale corrections, disconnected clients, duplicate dispatch, crash-after-side-
effect, queued work beyond available capacity and final integration. Count all
model calls, context, retries and synchronization overhead. Preserve the strict
quality/token rule and test task classes individually.

This amendment starts no controller, scheduler, worker or background model job.
It changes no native hooks, permissions, quotas, effort or concurrency settings.

## Outcome-first interface and shared capability management

Owner requirement, 31 October: the user should normally state the desired outcome,
not supply a methodology, research instruction, repository/skill selection or a
manual cross-session handoff. The controller should infer a proportionate method
from current project requirements, verified state, capabilities and constraints.
Material uncertainty must remain explicit; inferred intent cannot grant authority.

For routine implementation decisions, choose a default and proceed within scope.
When a user decision changes the outcome, acceptance, authority or meaningful
cost/risk, offer two or three concrete options with consequences, a recommendation,
its brief evidence-based rationale and the default. Do not expose a questionnaire
about internal tools or require the user to design the workflow. Rationale means
inspectable evidence and tradeoffs, not a hidden reasoning transcript.

Research is conditional on a decision-relevant gap, current-source requirement or
observed failure. The user need not explicitly request it, but every task must not
pay for an external search, full knowledge scan or skill-discovery stage.

### Capability registry and lifecycle

Maintain a local capability registry for skills, MCP servers, repositories and
other tools: identity, location, source/revision, license, declared capabilities,
trigger scope, dependencies, installation/registration/enabled state, actual
availability evidence, evaluation status, context/resource cost and rollback.
A downloaded directory, configured server and working capability are different
states. Refresh deterministic metadata on relevant changes; do not load every
skill body or re-audit every repository for each request.

Resolve task needs against this registry first and disclose only relevant tool
definitions/instructions. An unmet need can trigger bounded primary-source or
marketplace research without a separate user reminder. Vet and pin candidates;
keep external content untrusted and preserve installation/access authority.
Missing credentials or permissions cannot be synthesized from a skill's README.

Observe skill use, failures, corrections and outcomes. Draft the smallest useful
update, evaluate trigger precision as well as task quality against a no-candidate
baseline, and version qualified changes with rollback. Do not promote skills
merely because they recur in conversation, have many stars or have been downloaded.
Avoid installing overlapping capabilities without a measured or concrete need.

### Cross-session progress without conversation relays

For authorized shared projects, use one discoverable task/outcome interface, with
stable project/task/session IDs and explicit access scope. Each material outcome
records owner, state, relevant revisions, artifact references, verification result,
blocker/dependency and next permitted action. A done mark needs the required
evidence; a running lease does not prove liveness. Keep historical records distinct
from the latest verified state.

Adapters should publish material progress and outcomes atomically with an
acknowledged revision. Readers fetch a compact dependency/result view, then only
the evidence needed for their work. Use change notifications where supported and
revision/watermark checks on the next read otherwise. Track disconnected or stale
adapters; do not claim instant cross-device visibility without a measured boundary.
Crash recovery must reconcile effects that happened before their record was saved.

Messages are for authorized activation/resumption, a real decision or conflict
that shared state cannot resolve. Ordinary status discovery reads the task system;
it should not repeatedly wake peers, request their summaries or import whole chats.
The user does not compose handoff text. This is automatic structured outcome
capture, not a promise that unsaved conversation content can be recovered.

Example acceptance: given a task to continue QTs work, a fresh authorized reader
discovers which dependencies passed, what remains blocked, the relevant current
artifact revisions and the next permitted action from shared records. It does not
ask the user to repeat the method or message a peer for already recorded progress.
An outdated pass, missing receipt, unrelated project and disconnected writer must
produce the appropriate stale/unknown/denied outcome instead of invented readiness.

Qualify this alongside the simple-task control: a supplied-text rewrite must not
trigger registry-wide discovery, research, workers or mandatory progress records.
These requirements amend the target design; native enforcement, automated registry
refresh and universal client adherence are not established by writing them here.

## Approval continuity for an owner away from the machine

Owner requirement: approval may arrive asynchronously while the owner is away.
Once valid approval has been received, do not ask again for equivalent consent
merely because the session changed, compacted, waited or failed to resume. First
determine whether the remaining obstacle is authorization, execution capability,
budget, a technical failure or a policy boundary that owner consent cannot change.

Represent an approval request as a durable, scoped action record: task/action ID,
plain-language effect, relevant artifact revisions, access scope, risk/budget,
rollback where applicable, authenticated grant source and the permitted use count
or validity conditions. Never store credentials or turn arbitrary retrieved text,
a peer's claim or a model-generated "APPROVED" string into user consent. Reuse
existing direct authorization when the authorized effect/scope remains valid;
require new consent only when a material change actually needs it.

Keep owner consent separate from native execution permission and actual outcome.
Useful states include REQUESTED, OWNER_APPROVED, READY_TO_EXECUTE, RUNNING,
COMPLETED, BLOCKED_TECHNICAL, BLOCKED_POLICY, EXPIRED and REVOKED. A task may be
owner-approved yet blocked by another layer. Do not collapse that into REQUESTED,
mark it complete, or claim a stronger grant than the runtime actually accepts.

Use each client's supported approval interface and access checks. Before asking
the owner to approve, establish whether that action has an actual supported
approval consumer. A hard deny or missing approval interface requires an honest
blocker report and supported maintenance/operator path, not another identical
question, a forged receipt, an alternate execution route or a guard bypass.

Where the client supports asynchronous grants and wakeups, an accepted grant
should enqueue/resume the existing action under its recorded owner. Revalidate
the relevant revisions, scope, dependencies and resource budget, acquire the
execution lease atomically and reconcile prior attempts before retrying. Grant
delivery, acknowledgement, work resumption and successful completion need distinct
receipts. Unsupported wakeups must remain visible; an approval is not proof that
a dormant session woke or an operation ran.

Remote presentation should show the proposed effect, recommendation, grant scope
and a concise progress/result receipt. Notify again only for a meaningful changed
action, failure, missing prerequisite or decision; do not repeatedly ask the owner
to approve an unchanged action that is already authorized. Native session trust,
tool permission, task consent and release approval are different authorities.

Qualification cases: approval during idle/disconnect, compaction and restart;
duplicate delivery; unchanged-action reuse; materially changed scope; revoked or
expired grant; delivery to the wrong task; forged peer/retrieved approval; missing
approval consumer; native policy denial after owner approval; quota exhaustion;
and crash after side effect but before completion receipt. Verify authorized
resumption and duplicate suppression, preserve valid negative controls and report
unavailable native interfaces explicitly. No approval bridge, wakeup mechanism or
hook/policy change is installed by this design amendment.

## User-controlled consequential actions and guard precision

Owner clarification: configurable harness policy should protect against an
agent inventing or performing consequential actions without authority, while
supporting an intentional owner-authorized action. Do not describe an approvable
action as permanently forbidden or request approval where no consumer exists.
This requirement does not override provider, organization, operating-system or
other higher-priority restrictions. No blocked command or hook is changed here.

| Decision | Intended treatment |
|---|---|
| Clearly authorized low-risk operation | Execute within scope; verify the result |
| Consequential action with a supported approval path | Present effect/targets, uncertainty, recovery options and approval scope; pause until the grant is accepted |
| Ambiguous target, excessive scope or inadequate recovery | Resolve the specific uncertainty or prepare a safer concrete proposal before asking |
| Suspected false positive | Keep the action unexecuted; retain a bounded refusal receipt and diagnose through a separately supported maintenance path |
| Non-overridable restriction or absent approval integration | Report the exact blocker and supported resolution; do not promise that another identical consent message will unblock it |

Deletion example: resolve the named target and boundaries, distinguish a file
from a tree, and describe irreversible effects. Prefer recoverable removal when
that satisfies the request. Ask only for consent actually required and not
already granted. Where supported, bind the grant to the action, target identity,
scope, relevant preconditions and validity/use conditions; recheck immediately
before execution so approval cannot be replayed against a replaced or expanded
target. Record the execution result. A broad directory, changed target or scope
expansion must not inherit a narrower approval.

Guard classification should use structured action/tool arguments and the actual
execution context where available. A word inside a quote, document, log or test
fixture is not by itself proof of execution; an interpreter or wrapper can still
carry executable effects. Do not repair overblocking by blanket-exempting an
interpreter, switching off protection, changing quoting to evade a refusal or
silently allowing anything after the user says yes.

Every confirmed false-positive correction needs a minimal reproduction, the
intended legitimate case, nearby harmful cases and wrapper/path/argument-boundary
controls. Run the original refusal case and affected regression suites against
the exact candidate revision, then qualify installed behavior through the
supported maintenance process. Preserve valid denials. Unknown classifications
remain explicitly uncertain; the policy may request approval only where the
runtime can actually enforce and consume it.

Evaluate false blocks, missed dangerous actions, legitimate approval completion,
unnecessary/repeated prompts, stale/forged/overbroad grants, result accuracy,
latency and total token overhead separately. Useful tests include an approved
single-file deletion, an unapproved deletion, an innocent textual mention, a
changed target after approval and a native-policy refusal after owner consent.
These are qualification requirements, not permission to execute a denied test or
weaken a live guard. Configurable harness rules and non-overridable boundaries
must be identified separately in diagnostics and approval wording.

## Source recovery and evaluated curation

The [31 October reference review](../v2/reference-review-20261031.md) distinguishes
two different Memory Tax papers, the trained Librarian Agents builder, Anthropic's
graph example, Karpathy's wiki/experiment patterns and TypeSafe's Jev API.
Their evidence supports a candidate design, not a new deployment claim.

Keep original evidence directly searchable alongside derived wiki/graph views;
summarization must not be the only access path. Qualify combined retrieval against
raw and existing lexical baselines with matched reader, evidence visibility and
total construction/maintenance/query costs. Check predicate direction and source
support as well as entity matching. Curate incrementally where reuse warrants it.
Use frozen independent checks and bounded experiments before promotion. Jev is an
optional remote decision service candidate; no routing gain, local inference or
included subscription access is implied by its typed API.
