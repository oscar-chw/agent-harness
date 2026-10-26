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
