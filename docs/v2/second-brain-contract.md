# General second brain: target and present boundary

Updated 2 November 2026. Status: clarified target; implementation partial.

## What the owner expects

The framework is general-purpose. SWE/full-stack/operations is the first
priority specialization, not the boundary of the architecture. The same core
supports everyday questions, research, learning, finance and other decisions:
understand the desired outcome, distinguish facts from assumptions, reason from
relevant principles, compare alternatives, verify material claims and retain
useful evidence. Domain knowledge and checks adapt to the task; they do not
create separate competing harnesses or authorize cross-project data access.

Scale effort to uncertainty, consequence and reversibility. A simple daily
question may need only a direct answer and one reason; do not force a plan,
research campaign, diagram or multiple agents. A consequential financial
decision needs its objective, time horizon, risk/liquidity constraints,
assumptions and scenarios made explicit, with current evidence where needed.
First-principles reasoning complements domain evidence; it cannot manufacture
missing facts or replace applicable professional constraints. Other domains
must receive their own relevant acceptance cases before broad quality claims.

Support designing, building, explaining and operating a whole application or
system. The local corpus must contain substantial engineering knowledge,
decision criteria, worked system designs, implementation examples, failure cases
and operational playbooks. Introductory notes and URL lists alone do not meet
this requirement. Learning and updating remain necessary.

Local-first means use the existing authorized local knowledge before new web
research. Reuse established knowledge without re-researching it on every task.
If a version, security fact, live price/service contract or project requirement
is missing or stale, disclose the gap and acquire only that evidence. Never
replace an unknown with a guessed fact to maintain an offline claim.

## Design judgment

The owner also expects the principles and judgment behind professional work,
not only a catalogue of methods. Use the relevant perspective, not a mandatory
committee of role-playing agents:

| Perspective | The question it contributes |
|---|---|
| Product and UX | What human outcome matters, what is confusing, how can an error be prevented/recovered? |
| Frontend | What should the user see and control through loading, success and failure? |
| Backend and data | What must remain true, where is state authoritative, what is the transaction boundary? |
| System architecture | Where should responsibility sit; which coupling, delay and failure boundaries matter? |
| Security | What is trusted, who may do what, and how does the design limit a mistake's effect? |
| SWE and operations | Can people understand, test, change, observe and recover this system at its actual cost? |

For a consequential choice, state the outcome/constraints and invariants,
identify material unknowns, compare two or three credible alternatives, then
recommend with explicit assumptions and the evidence that would change the
choice. Avoid invented numerical scores and a universal "best architecture".
Ask the user only where missing intent changes the decision; provide a sensible
default and its consequences. Simple tasks need no design dissertation.

Case notes must retain context, alternatives, principle, chosen implementation,
failure scenario, result/evidence and a counterfactual that reverses the choice.
A hypothetical example stays hypothetical. Repeating an example is not evidence
of transfer: test new cases and changed constraints. Principles, practical
methods and skills complement one another; a role label does not train a model.

Primary foundations inspected 2 November 2026: Nielsen's
[usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/),
Saltzer/Reed/Clark's [end-to-end argument](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf),
Google SRE's [simplicity chapter](https://sre.google/sre-book/simplicity/), and
[NIST SP 800-160 Vol.1 Rev.1](https://csrc.nist.gov/pubs/sp/800/160/v1/r1/final)
landing page/abstract. These supply useful principles; this is not a complete
reading of NIST or proof of agent design-quality improvement. The role questions
and following example are authored applications, not verbatim source doctrine.

Example: a stock-reservation app needs one correct deduction and a recoverable
experience. A disabled button helps interaction but cannot enforce stock across
two clients. Put the invariant at the authoritative transaction boundary; show
pending/error state and retain input in the UI. A small local app may use one
database and simple business functions. A measured write-contention or independent
availability requirement can change that choice; imagined scale is insufficient.
Test concurrent requests, a lost response and a mid-operation failure. This is a
design exercise, not a deployed application or a measured performance result.

Additional cases for transfer, not universal prescriptions:

| Case | Compare and reason | What changes the recommendation? |
|---|---|---|
| A small internal business application | Modular single deployment versus independent services; weigh ownership, change coupling, operational load and actual failure-isolation needs | Measured contention, separate ownership or release/availability constraints justify revisiting the boundary |
| A local document assistant | Exact/lexical retrieval versus semantic/hybrid/graph routes; require scoped source provenance and honest absence first | Held-out paraphrase or multi-hop failures justify testing another retrieval route against the same cases and cost |
| An important UI write | Optimistic feedback versus waiting for authoritative confirmation; balance perceived latency with reversibility and truthful status | A reversible cosmetic preference differs from a consequential reservation or money movement |

Observed harness case: a connected reader saw an updated index pointer but could
not retrieve the new chapter. The invariant was discoverability within the
selected source scope. Reopening all paths on every query could change project
or private-source scope. The bounded fix refreshes only profile-directory
membership while retaining original project/configured roots and explicit
overrides. Source regressions first failed; the installed persistent process then
passed absence/addition/removal checks in both search modes. This demonstrates
that one repair, not general human-like judgment or cross-device completion.

## Architecture

Execution model: cooperating stateful activities, not a mandatory linear
pipeline. A decision tree is a restricted branching structure. A general
execution graph can include cycles, shared work, parallel branches and joins;
hierarchical statecharts add nested states and concurrent regions. References:
[W3C SCXML](https://www.w3.org/TR/scxml/) execution/state semantics,
[Stately parallel states](https://stately.ai/docs/parallel-states), and
[LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api),
inspected 2 November 2026. Reuse concepts; no framework installation is implied.

Model task, worker, artifact/evaluation and retrieval/source freshness as
distinct correlated state domains. Events/evidence can trigger a local retry,
further research, replanning, partial progress or a join. Correlation is explicit
through task/source/artifact identities and versions. A parent can compose
children, but child completion must not bypass the parent's integration check.
Avoid unlimited spawning or materializing every theoretical combined state.

The existing workgraph is a dependency DAG: cyclic prerequisites are refused.
Its nodes themselves change state and can return to pending after failed gates;
that is a control-state cycle, not a dependency cycle. OperationalState provides
project-scoped CAS, leases and events. These are useful existing pieces, not a
completed runtime for arbitrary communicating hierarchical statecharts. New
composition must earn its place through crash/replay/duplicate-event/stale-
evidence/join tests; preserve the original completion authority.

Example: frontend fails, backend passes, documentation depends only on backend.
Retain backend's valid result, let documentation proceed, diagnose frontend,
and hold the parent delivery until relevant branches and integration pass.
If the cause is a wrong requirement, revisit that decision rather than blindly
running the same coding loop. A simple daily answer can finish directly.

The four requested parts form one design: framework/workflow owns execution and
recovery; methodology supplies relevant procedures; philosophy/first principles
guides choices; the local vault supplies source-backed knowledge and cases.
Memory/retrieval connects them. Load relevant pieces rather than imposing all
procedures and roles on every task. Integration must be judged on complete tasks;
selecting strong components separately does not demonstrate the best combination.

1. Thin application/provider adapters preserve native identity and permissions.
2. Task routing selects the smallest appropriate workflow and relevant skills.
3. Project contracts hold requirements, constraints, decisions and ownership.
4. Shared local knowledge holds source-backed explanations, patterns, tradeoffs,
   worked examples and playbooks. Retrieve small relevant sections.
5. Task state holds plans, execution evidence, checkpoints and handoffs.
6. Execution and verification iterate at the boundary actually being claimed.
7. Learning proposes reusable lessons from observed outcomes/corrections;
   independent checks decide promotion, retention and rollback.

Original sources remain authoritative; summaries, search indexes and any future
graph are derived views. Facts, proposed designs, current project state and
tentative lessons have different authority and must not be mixed.

## Memory choice: RAG first, with minimal structured operational state

Recommended architecture direction, not a new deployed retrieval capability:

- Preserve authorized original documents/history with stable source spans,
  timestamps and scope. Derived notes never become the only recovery route.
- Use exact current-state/decision lookup where a typed authoritative record
  exists. Use retrieval for evidence and history; a similar old passage does not
  override current task state or grant tool authority.
- Establish a strong raw-source RAG baseline: lexical/exact retrieval plus a
  separately measured semantic/reranking route when useful. Bound excerpt size,
  duplicate handling and context expansion. Current code has lexical/FTS5
  retrieval; semantic embeddings/reranking are not thereby implemented.
- Treat human-readable summaries, principles, cases and candidate lessons as
  source-linked views. Curate and invalidate stale advice; preserve contradictory
  history rather than silently rewriting it into a model-invented fact.
- Add automatic consolidation, graph expansion, learned query routing or new
  embedding models only after their incremental contribution is measured.
  Keep indexes rebuildable and embedding spaces version-isolated.
- Preserve existing permissions, user-authorized retention and device boundaries.
  Do not bulk-ingest private chats, credentials or another project merely because
  raw retrieval is a promising baseline. Local storage does not imply a remote
  model/embedding service is authorized.

Fresh primary-source review, 2 November 2026:
[RAW-RAG](https://arxiv.org/html/2610.30755v1), method section3 and limitations6.1,
preserves source windows and uses dense retrieval plus cross-encoder reranking.
It reports first place in six of seven compared benchmark/model settings, and
explicitly limits its evidence to offline conversational tasks. It does not
establish our SWE/dev-ops performance or an operational state/permission system.
[Memory Tax](https://arxiv.org/html/2610.34073v1), section6, tests retrieving
original history alongside transformed memory and jointly reranking; this
supports a source-recovery path, not a universal requirement for our own graph.
[Memory portability](https://arxiv.org/abs/2609.05339), abstract only reviewed,
reports writer/model and mixed-embedding migration problems on48synthetic
histories with two small open models. Generalization remains unproven.

Compare current retrieval, improved raw-source RAG, and that RAG plus our derived
views on the same frozen cases and reader. Include exact/paraphrased recall,
multi-source decisions, corrections, contradictory sources, no evidence,
cross-project exclusion, cold task recovery and new system-design cases.
Record supported answers/useful task completion, false memories, source scope,
total ingestion/maintenance/answer tokens, latency, storage and human corrections.
Use the standing quality-at-least-baseline AND aggregate-tokens-at-most-baseline
gate for improvement claims. No benchmark campaign or superiority result was
produced by this review; structural safety/state requirements remain mandatory.

## Present evidence

| Capability | Present boundary |
|---|---|
| Task graph, command gates and scoped workflow | Implemented; local tests and bounded native receipts exist |
| Shared local SWE/AI notes | Four authored pages, 45,899 bytes, installed on both established Macs |
| Section retrieval | Fresh installed processes passed 20 representative section checks on each device |
| Existing connected client | New AI section lookup failed on 2 November; reconnect/direct-file fallback remains necessary |
| Whole-system design/example library | Partial; the current notes are not that complete library |
| Knowledge graph | No demonstrated populated operational whole-corpus graph |
| Continuous cross-device synchronization | Not established; current source transfer is on-demand with conflict preservation |
| Automatic learning and measured improvement | Mechanics/held proposals exist; end-to-end efficacy and universal adoption are not established |

## Whole-application acceptance

Small-version qualification order: dev1 adaptive general guidance, expert
self-diagnosis and the concrete persistent-KB repair; dev2 a measured stronger
raw-source retrieval baseline and correction/recovery cases; subsequent
increments expand worked system designs/domain cases and evaluated learning.
These are work increments, not predeclared successful releases. Keep development
versus stable, source checks versus installed behavior, and canary versus broad
efficacy separate. V3 needs a demonstrated new capability; no breakthrough claim
or architectural rewrite is justified by a version number alone.

Use frozen local-only design tasks: a small CRUD app, a multi-tenant business
system, a retrieval assistant, a background-job/data pipeline and a failure/
recovery incident. Include missing-evidence and simple-task controls.

Each relevant design must resolve requirements and data flow, API/data models,
authorization, failure/concurrency behavior, tests, deployment/observability,
recovery and real tradeoffs. No mandatory distributed architecture for a small
app. Cite retrieved evidence and distinguish proposal from measured behavior.
Building and operating a system require executable verification beyond design.

Compare useful outcomes and total tokens with the current baseline. Test cold
recovery, correction/staleness, source scope and both-device delivery. Missing
coverage stays missing; one successful toy task is not broad qualification.
