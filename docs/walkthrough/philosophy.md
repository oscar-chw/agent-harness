# Philosophy and first principles

Use a thinking method because it resolves the task's uncertainty. A familiar framework name alone provides no evidence that the answer is sound.

## Mechanism

The authored reasoning guide offers several lenses. The model selects the amount of reasoning and relevant domain knowledge for the request.

| Lens | Useful question | Expected output |
|---|---|---|
| First principles | What outcome, constraint and invariant does the design have to satisfy? | A consequence derived from stated premises, with a counterexample check |
| Critical thinking | What is supported, inferred or contradicted? | A claim with source support and material uncertainty |
| Causal reasoning | Which competing cause explains the observation? | A small experiment or comparison that separates explanations |
| Systems thinking | Which actors, state changes, dependencies and feedback matter? | A trace of behavior across boundaries and failure effects |
| Decision reasoning | Which option fits the constraints and what would reverse the choice? | A recommendation, credible alternative, decisive reason and assumption |
| Design judgment | How do human needs, correctness, trust and operations interact? | A coherent design with explicit tradeoffs |
| Socratic teaching | Which prerequisite or assumption should the learner test next? | One useful question, example or direct explanation, followed by a changed-case check |

This is authored guidance. Task evidence establishes whether the selected reasoning was useful.

Typed decision records retain choices, confidence, input bindings and authority metadata. Their validator checks the declared contract. A decision model's quality requires its own evidence.

## Example

An illustrative user asks whether the system needs a knowledge graph. Start with the actual failure, such as a missed cross-document relationship. Specify the required relationship and a retrieval case that can expose the miss. Compare a simpler scoped lexical path with a graph-supported candidate on those cases, including update cost and source correctness. Prefer the option that meets the requirement with the supported tradeoff.

The recommendation can change when the task needs relationships that the simpler path repeatedly misses. That changed constraint becomes a reusable decision case, retaining the original evidence and alternatives.

For interview practice, ask the learner to predict what happens when two writers read the same task version. If the prerequisite is missing, explain the transaction with the 3→4 example, then check a changed case. An urgent operational request may need direct action and concise rationale.

## Diagnose weak work

Recover the original intent and acceptance, state what was actually achieved, identify the precise gap and compare plausible causes. A weak research result might reflect the wrong question, missing sources, an invalid premise, an inadequate method or a faulty evaluator. Choose a check that distinguishes those causes before repairing the affected part.

The learner's stated preference, the model's inference and demonstrated understanding remain different evidence. A successful explanation on one example leaves transfer to a new example unmeasured.

## Tradeoffs

- First-principles reasoning still needs reliable premises and domain constraints.
- Additional questioning can improve diagnosis or waste time. Match teaching depth to purpose and urgency.
- Repeated cases can propose a lesson. They do not automatically justify a universal rule.
- A sophisticated explanation can still have a wrong conclusion. Independent outcomes matter.

## Evidence and limits

Eight authored calibration cases cover direct/guided requests, prerequisites, urgency and uncertainty. Adding the full selected reasoning guide increased observed tokens by 3.38% and produced a 92-word response against a 90-word limit. That treatment remains unadopted. Learner follow-up, transfer and broad teaching efficacy remain unmeasured.

## Implementation

[Reasoning and Socratic guidance](../../content/skills/work-loop/reasoning.md) · [Decision cases](../v2/check_decision_cases.py) · [Decision records](../../src/agent_harness/jev.py) · [Authored-case checks](../../tests/test_v3_philosophy_cases.py) · [Calibration and source references](../v3/qualification-20261113.md#philosophy-calibration)
