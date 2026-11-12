# Source-backed answers still need the required context

3 November 2026. Candidate philosophy design under
handoffs/v2-completion/scope-qualification-20261103.md.
No runtime/default change, native call, test, new source acquisition, regrading
or acceptance change is performed or authorized by this document.

## The failure is omission, not necessarily fabrication

A sentence can follow from its cited source and still fail to answer the user's
question fully. Saying that an option is unavailable may be correct yet omit
when that observation was made, which conditions were checked, or what would
make the option usable. The user can then make an unsupported decision even
though each sentence the assistant actually wrote was defensible.

Claim support and answer completeness ask different questions. Support asks
whether a stated claim follows from the permitted evidence. Completeness asks
whether the answer preserves the meanings required by the task and the source
qualifications necessary to interpret them. Refusing an unsupported conclusion
can avoid a false assertion while leaving a required distinction unexplained.
That remains incomplete under a binding requirement; caution is not a substitute
for answering what the evidence does establish.

Root's report in docs/v2/memory-qualification-20261103.md records this pattern:
some answers retained the main limitation but omitted required historical
classification, the boundary between inventory and usable content, or prerequisites
for adoption. This motivates a hypothesis, not an independent regrade or proof
that the mechanism below repairs it. The original requirements remain binding.

Transport completeness is another layer. In the inspected
src/agent_harness/launch.py:238–312, _answer_fields retains a bounded preview
with complete-answer metadata/sidecar, while read_answer validates and returns
the retained answer. Its own docstring disclaims semantic truth and permission.
A full recovered body can omit a necessary meaning; a clipped preview can hide
a meaning that was present. Any later evaluation must first read the complete
retained answer, then assess its substance. A matching hash settles neither
substantive support nor useful coverage.

## Candidate: one brief requirement-to-answer pass

For a nontrivial source-backed answer, identify the distinct asks and explicit
binding requirements in the current task. Before finishing, associate each with
a supported answer sentence or an explicit, scoped unresolved gap; retain source
qualifications that change the conclusion or what the user may do next.

This is one short review of the draft, using the evidence already authorized and
available. It is not an extra agent, a new retrieval engine or a fixed list of
case answers. A compact working note can say:

> Required meaning -> answer location -> source span / unresolved evidence gap.

The association must carry the meaning, not merely a matching noun, citation,
status word or checklist mark. A sentence can cover several requirements when
it actually explains them. An unresolved requirement stays unresolved: writing
“unknown” cannot satisfy a requirement for an established fact or a demonstrated
result. Missing support should narrow the answer and state the consequential
gap, rather than create a fact to fill the row.

Review the source's relevant limits while making the association. Time, selected
population, read extent, exceptions and action authority matter when changing
them would change the answer or its use. Do not append every possible caveat to
every answer. A source's failure to mention something establishes a bounded
absence of support, not a universal negative.

When a required meaning is supported but omitted, revise the relevant sentence.
When evidence conflicts, explain the conflict and its decision consequence.
When evidence is insufficient, preserve the gap and any applicable hold.
If a binding requirement cannot fit the current output budget, do not silently
drop it or declare completion: disclose the incomplete scope and retain the
requirement for the accountable owner. Changing that requirement or budget needs
the existing authority; this proposal grants none.

Stop after this pass. Do not start an unbounded search for certainty, repeat
consumed calls, acquire excluded sources or add a standing workflow. A direct
definition, simple conversion or other trivial answer with no material evidence
qualification can finish directly. The trigger is task complexity and risk of
meaning loss, not the presence of a citation or a product-specific case ID.

## Why this is a general-purpose candidate

The mechanism starts with what the user needs to decide and what must remain
true, then asks what the evidence actually warrants. It can apply to planning,
explanation, a technical recommendation or a personal administrative question.
It does not encode a visible acceptance answer, inventory count, named source
or harness-specific taxonomy. Task, framework state, authored guidance and
original evidence still have different jobs; none should silently substitute
for another.

Existing source bindings, scoped retrieval and complete-answer retention are
useful seams. This proposal adds no assertion that any of them understands
meaning. The working note is temporary reasoning support, not a verified memory
record, new authoritative source or automatic skill. Persisting or activating
a reusable procedure remains a separate authorized, evaluated decision.

## Costs and plausible failure modes

The pass consumes attention and input/output tokens, particularly when source
qualifications require rereading. A working note can become a duplicate summary;
an exhaustive list of facts can crowd out the useful answer. Keep associations
brief and revise only meanings actually required or needed for interpretation.
No token saving or latency improvement is presumed.

The same assistant can misunderstand both the request and its self-check.
An incomplete obligation list can make a bad answer look complete. An irrelevant
source can make a well-filled list look supported. Independent evaluation must
check the answer against the frozen task and permitted original evidence, not
against the candidate's own list.

Another failure is ritualized caveating: repeating “historical” or “unknown”
without explaining which conclusion is limited. Overconservatism can also hide
useful supported facts behind a blanket refusal. A good answer states what is
known and what remains unresolved at the right scope. Unsupported permission,
contradiction, disclosure or advice is still unacceptable even if coverage rises.

Finally, a new correction can be omitted while an old requirement is copied
faithfully. Preserve the historical statement and explain the applicable current
correction; do not rewrite the record or choose whichever version makes the
answer easier. A source or handoff supplies evidence, not new task authority.

## Prospective held-out counterexample plan

This document and all examples already exposed in the project are development
material. They cannot become an unseen evaluation by renaming them. Root may
separately authorize an independent task author to freeze a fresh set of questions,
permitted source packets, required meanings, disallowed inferences and meaningful
unknowns before candidate responses. That author should not derive the answer
requirements from the candidate's working notes or observed responses.

Sample unfamiliar domains and task forms, with both straightforward and
misleading evidence. Counterexample families should include:

- A short factual answer whose evidence is sufficient: extra review or caveats
  should not make it less useful or needlessly expensive.
- A dated rule and a newer correction: the answer needs the applicable rule
  while preserving the historical status.
- A procedure with an unobvious exception or required permission: a correct main
  step cannot compensate for omitting the condition that changes whether to act.
- A faithful quotation paired with a misleading requested inference: provenance
  alone must not supply entailment.
- A partial record where a precise answer is unavailable: explicit bounded
  uncertainty should coexist with the useful facts that are supported.
- A source with several attractive but irrelevant facts: covering the request
  should not turn into reproducing the whole document.
- A genuinely conflicting pair of permitted sources and an excluded tempting
  source: completeness must not invite unauthorized evidence access or a
  fabricated resolution.

These families are public design suggestions, not themselves held-out cases.
Independent authors must supply unseen particulars, paraphrases and changed
conditions, including cases where the required detail reverses the recommendation.
Judge whether the user can make the intended bounded decision, not whether
preferred words occur.

A prospective matched comparison should preserve source visibility, task
requirements, reader/model settings, output budget and authority in both arms.
Freeze the candidate instruction before exposure; use separate fresh responding
sessions under root's existing approval and resource rules. No runs are granted
here. An independent reviewer should read the complete retained answers against
the original sources without accepting the candidate's self-check as grading.
Record claim support, omitted required meanings, useful supported content,
wrong actions/scope violations, unnecessary verbosity and complete resource use.

Count the review's overhead and failed attempts in whole-task usage, with
historical UNKNOWN debt still visible. Keep the existing no-per-case quality/
scope/correction regression AND aggregate-tokens-at-most-baseline requirement;
do not average a harmful case away or loosen it to reward better completeness.
If a requirement is irrelevant or disputed, resolve it independently before
running rather than changing it after seeing an answer.

The proposal is disconfirmed as an improvement if omissions persist, new false
claims or scope violations appear, trivial tasks degrade, or complete cost fails
the standing requirement. A positive result on this bounded set would still not
establish universal judgment, autonomous learning or stable readiness. Root owns
the actual freeze, execution, verification, interpretation and any activation.

## Inspected basis and status

- docs/v2/vault/acceptance-cases.json: original task, answer requirements,
  run_contract and absence policy; unchanged.
- docs/v2/memory-qualification-20261103.md: root's scoped omission/retention report;
  not re-executed or independently adjudicated here.
- src/agent_harness/launch.py:238–312: retention/readback mechanics, inspected only.
- docs/v2/second-brain-contract.md: quality/cost and general-purpose boundaries;
  docs/v2/philosophy/minimum-sufficient-checkpoint-20261103.md: preserve meaning,
  authority, failed attempts and unresolved usage.

Status: AUTHORED_CANDIDATE. Implementation, tests, semantic/native validation,
held-out comparison and efficacy: NOT_RUN by this worker. Only this assigned
design and the own compact packet/history are delivered.
