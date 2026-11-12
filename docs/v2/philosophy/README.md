# Design judgment: choose from the actual constraints

Use these references when a task contains a real design choice: competing
outcomes, an uncertain result, a responsibility boundary, or costly recovery.
For a routine direct answer, answer directly. These are optional references,
not an extra mandatory workflow or a new runtime capability.

- [Decision references](decision-references.md): what must remain true, where
  responsibility belongs, and when an apparently simpler choice costs more.
- [Worked cases](worked-cases.md): five SWE cases, one daily choice and one
  consequential personal decision, each with a recommendation and reversal.
- [Transfer prompts](transfer-prompts.md): changed situations without suggested
  answers. Give only this file to a proposed evaluation's responding agent.
- [Reviewer notes](reviewer-notes.md): acceptable reasoning, dangerous shortcuts,
  and changes of constraint that should change a recommendation.

Start with the case nearest the current uncertainty. Read its evidence and
limits before transferring its recommendation. A case about safe retries does
not establish that the current API implements the required contract.

## Evidence boundary

Prepared 2 November 2026. **Documented** means attributed source content;
**inferred** means an authored application; **hypothetical** marks invented
scenario inputs; **measured** requires an actual observation and receipt.
All worked cases here are hypothetical/inferred. No application was built,
restored, deployed or benchmarked for these cases. Local artifact checks can
measure link/coverage integrity; they cannot measure design competence.

The existing [engineering case sidecar](../engineering-cases-20261102.md) is
the source for Shopify, Amazon, overload and Stripe applications. Its researcher
reports focused primary-source reading; this worker read the sidecar and did
not repeat that campaign. The [second-brain contract](../second-brain-contract.md)
supplies scope and known capability limits. Three primary additions were read
directly, with their gaps and read depth recorded in the decision references.
No other external source is asserted as newly read here.

These public development prompts and their review notes are **not held-out**
evidence. Exposure makes them unsuitable for a later held-out improvement
claim. The orchestrator owns independent review, paired evaluation, original
graph gates and integration. Better answers, lower total tokens, stable v2,
native procedure adoption and device parity remain unestablished by this pack.
