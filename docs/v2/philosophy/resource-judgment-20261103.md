# Choose resources for the uncertainty they resolve

This round extends the earlier [decision references](decision-references.md).
It addresses dependency selection, retrieval/research, parallel/direct work,
memory/procedure and confidence. Every case is **hypothetical**; its proposed
decision and check are **inferred**, not measured results. None requires a
framework recital. The right choice changes when the constraints change.

## Evidence reused, with its limits

The [source bindings](source-bindings-20261103.json) record local input identities,
selected retained primary-read receipts and case-to-source links. Canonical
reference packs live outside this repository; their recorded paths are local
evidence routes, not bundled dependencies. This round fetched no upstream source
and installed nothing. A prior researcher's documented reading is attributed to
that receipt; it is not a new full read by this worker.

- **S1 — prior foundation reading.** The earlier decision references record
  primary reading of [Google SRE Simplicity](https://sre.google/sre-book/simplicity/)
  and the [end-to-end argument](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf).
  Their application here is to compare continuing complexity and check the
  actual claimed outcome, rather than treating a tool's presence as sufficient.
- **S2 — retained library cases.** The canonical LIBRARY-PACKS guide records
  limited official-doc reading and local-runtime observations separately.
  ENGINEERING-CASES distinguishes staff CRUD from public product UX, using the
  [Django admin tutorial](https://docs.djangoproject.com/en/5.2/intro/tutorial02/),
  and notes the single simultaneous writer in
  [SQLite's transaction documentation](https://www.sqlite.org/lang_transaction.html).
  Those are the prior audit's source-backed distinctions. Its runtime inventory
  is dated evidence about inspected locations, not current universal availability.
- **S3 — project contract.** The [second-brain contract](../second-brain-contract.md)
  separates original sources, current operational state and derived views; it
  recommends scoped retrieval before acquiring missing/fresh facts. This is a
  project design/authority constraint, not a measured retrieval advantage.
- **S4 — source policy versus execution.**
  [reasoning.md](../../../content/skills/work-loop/reasoning.md) assigns diagnosis
  of inadequate work to the agent. Source inspection of
  [method_control.decide](../../../src/agent_harness/method_control.py) shows
  advisory checks for intent-gap failures; its module explicitly does not grade
  artifacts or execute tools. Source inspection of
  [routing.next_decision](../../../src/agent_harness/routing.py) likewise shows
  an advisory resolver, not model dispatch. No native adherence was tested here.
- **S5 — candidate learning boundary.** The existing
  [learning-review template](../../../content/templates/learning-review.md)
  calls for source/task binding, independent held-out evaluation, complete cost
  and rollback. The retained EVAL-INTERVIEW guide distinguishes missing runtime,
  wrong oracle and wrong candidate. These are procedural requirements/proposals;
  their presence does not establish automatic learning or improvement.

## J1. Library or framework: a local reconciliation becomes staff CRUD

**Intent and constraints.** A supplied project already has a small Python/SQLite
script. The required outcome is one reproducible discrepancy report from local
synthetic data. No HTTP endpoint, interactive UI or multi-user writer is needed.

**Choice.** Reuse the existing library-level path, comparing its output with an
independent expected report. Adding a web framework creates setup and operation
without resolving a stated need. This is a task-fit inference from S1/S2, not
a claim that stdlib always beats a framework or that this script passed.

**Counterfactual.** The task becomes a sustained staff data-entry workflow in an
existing Django project with working models and permission conventions. Reusing
its admin may avoid bespoke staff CRUD. If the audience becomes public users
with a multi-step journey, admin's staff purpose no longer fits that outcome;
keep the established stack where practical and design the appropriate public
interface. A typed API requirement may justify another API path; it does not
automatically justify replacing the existing application or installing two stacks.

**Discriminating check and unknowns.** Check the actual required journey:
report correctness in the first version; persistence plus staff/non-staff direct
access in the second. Read project runtime/lockfile and dependency compatibility
before following a versioned recipe. Where required framework execution is
unavailable, record NOT_RUN; do not infer compatibility from a fetched tutorial.
Measured concurrent-write needs could also reverse the database choice; merely
calling the app “business software” cannot resolve that decision. Sources: S1/S2.

## J2. Retrieve or research: distinguish a missing source from a stale answer

**Intent and constraints.** Explain a project's recorded reason for a schema
choice. Its authorised local decision record contains the exact question,
source span and applicable revision. Retrieve that record first, then answer
within its scope. Browsing generic opinions would not establish what this
project decided. Sources: S3 and [worked case C4](worked-cases.md).

**Counterfactual.** The question asks whether that choice works with a newly
specified provider version. The old decision is context, not current evidence
of compatibility. Inspect the local runtime/configuration, then acquire only
the missing version-specific primary evidence if access is authorised. If
research is unavailable, state precisely which compatibility claim is unknown;
offer a bounded conditional design or hold the dependent action.

**Discriminating check and cost.** Establish whether the source is absent from
the allowed corpus, not ingested, retrieved badly or simply inapplicable. An
indexing defect needs an ingestion check; a version gap needs the relevant new
evidence. Changing ranking cannot recover an unacquired source. Stop gathering
when the remaining unknown would not change the decision or acceptance check.
Local-first does not mean treating stale notes as current truth or widening
source scope to avoid admitting absence. No retrieval method was compared here.

## J3. Parallelise or work directly: independence must pay for coordination

**Intent and constraints.** Explain a single short query from a known local
schema. The answer and its relevant check fit in one context. Work directly:
splitting it adds a briefing and join without removing an actual dependency.
This is a proportional design judgment, not a measured token or latency result.

**Counterfactual.** An authorised task needs two substantial investigations:
API compatibility against a pinned contract, and an unrelated fixture audit.
Their inputs are stable, outputs disjoint and each result can be checked at
integration. Parallel investigation can now be sensible within the existing
worker/resource limits. State each owner, output, deadline and stop condition.
The parent still owns the integrated claim; two favourable reports cannot
substitute for its check.

**Reversal and discriminating check.** If both branches must change the same
schema, or the compatibility result determines which fixtures are valid,
sequence the dependent work or first freeze a shared interface. If workers
compete for a scarce resource, inspect capacity/queueing rather than assuming
more workers help. Measure total work, join corrections and useful completion
before claiming a benefit. A route suggestion is not permission to dispatch,
and this case activates no workers. Sources: S1, S3/S4 and the
[existing coordination policy](../../../handoffs/v2-completion/README.md).

## J4. Memory or procedure: an episode is evidence, not an instruction

**Intent and constraints.** A task failed because a package was absent in its
specific virtual environment. Preserve the observed command/result, environment,
source and eventual resolution as a scoped episode. Retrieving that episode may
explain a recurrence. It does not justify “always install globally,” changing
another project's environment, or promoting a new active recipe. Sources: S3/S5.

**Counterfactual.** Several independently supported episodes suggest a reusable
environment check with a clear trigger and exclusions. Draft a dormant procedure
candidate: applicability, smallest existing alternative, version constraints,
negative cases, evidence links and rollback. Repetition is a reason to evaluate,
not a promotion receipt. A procedure that works on one project can still harm
an unrelated task by creating unnecessary setup or crossing authority boundaries.

**Discriminating check and correction.** Compare the candidate with unchanged
workflow on new relevant and irrelevant tasks under the frozen evaluation
contract. If the original failure was actually a wrong interpreter selection,
repair the episode's interpretation and invalidate dependent advice while
preserving the original observation. A current task instruction or authoritative
state record outranks a similar old passage. No procedure was promoted or tested
in this round, and a saved file does not prove future use.

## J5. Confidence belongs to claims, not to the whole answer

**Intent and constraints.** Recommend how to prepare a migration. The scenario
supplies the source schema and required invariants, but destination version,
backup usability and acceptable data loss are unknown. Be specific about what
is supported: the invariant is known; compatibility and recoverability are not.
Do not convert fluent explanation, many matching sources or a route score into
a numerical probability of safe execution. Sources: S1/S3/S5.

**Choice and counterfactual.** Proceed with a reversible design comparison and
identify the unknown that controls execution. Read discoverable technical facts
from authorised local state; test a recovery copy when permitted. Ask the human
only for the unrecoverable business constraint, such as acceptable loss, not
which diagnostic command to choose. If exact version and exercised recovery
evidence later become available, narrow those uncertainties and reassess the
dependent action. That evidence would not grant production authority by itself.

**Discriminating check.** Bind every claimed result to the artifact, input,
version and environment it actually tested. A successful startup cannot alone
settle data reconciliation. If conflicting receipts cannot be ordered by scope
or revision, retain the conflict and hold the affected conclusion. More reading
cannot resolve an unknown stakeholder value; a missing runtime remains NOT_RUN.

## J6. A failed artifact: diagnose the gap without outsourcing it to the user

**Hypothetical failure inputs.** The accepted requirement is one row per customer,
including customers with no sales, with invoice revenue counted once. A synthetic
fixture has one invoice for 100, two invoice lines, two payment records and a
second customer with no invoice. The submitted query inner-joins both child
tables and groups by customer. The supplied failed result is revenue 400 and
no row for the second customer. This is an authored example, not executed SQL.

**Intent → result → gap.** Recover the requirement and artifact from task records.
Compare the supplied output with invoice grain and required customer coverage.
The gap is duplicated contribution plus missing customers; “the query ran” or
“the syntax check passed” does not answer the accepted task.

**Causal hypotheses.** One explanation is many-to-many join fanout plus inner-join
exclusion. Another is duplicate invoices in the source. A third is an incorrect
fixture/oracle. Keep these as rival hypotheses until the check separates them;
do not assert a source-data defect because the total is wrong.

**Discriminating check.** Count source invoices by identifier before the joins;
then trace invoice contribution and customer membership after each join. Compare
the source rows with an independently constructed expected report. One source
invoice becoming four joined rows supports fanout; duplicate identifiers already
present before joining supports a different cause. A known-good and deliberately
wrong report test whether the oracle can distinguish 100 from 400 and preserve
the zero-sales customer. If the oracle is faulty, preserve that failure and
correct only the demonstrated error, then rerun the original check.

**Repair decision and reversal.** For fanout, aggregate child data to the required
grain before combining and preserve the required customer domain; rerun the
original report check plus relevant regressions. For a source duplicate, resolve
its actual identity policy instead of hiding it with DISTINCT. If the recovered
requirement instead meant received payments, the revenue definition must be
resolved against that requirement, not silently switched to make an answer pass.
Ask the human only if that intent genuinely cannot be recovered. S4 assigns this
diagnosis to the agent; its advisory code does not perform this investigation.

## Proposed acceptance, owned by the orchestrator

The separate [transfer prompts](resource-transfer-20261103.md) change the decisive
constraint. Review outcomes, consequences and evidence fit, including the fluent
but wrong alternatives above. Do not score labels such as “counterfactual” or
the presence of all five diagnosis headings: an agent can recite them and still
fix the wrong problem. These are exposed development cases, not held-out tasks.

Semantic/source-correspondence review, executable SQL checks, paired agent
evaluation, runtime/native adherence and performance comparison are **NOT_RUN**
in this worker round. Main owns acceptance and all verification. This document
neither executes a tool nor makes prose a grant, procedure, grader or expertise.
