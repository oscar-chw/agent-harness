# EMMA intake — candidate, not activated

Source: https://arxiv.org/html/2610.35966v1 (25 October 2026).

EMMA separates controller routing memory, inheriting specialist prompts and
per-step procedural skills. Reflection localizes a failure and proposes one
scope-owned edit; programmatic rules constrain admissibility and growth.
Overflow triggers finer decomposition with completed work preserved. Evaluation
uses frozen learned memory. Execution dispatches one step at a time; this does
not establish parallel orchestration performance.

Local design recommendation: retain immutable episode evidence; classify an
observed failure before drafting the smallest appropriate candidate. One-off
execution slips stay task-local. Require independent held-out evaluation,
versioned activation and rollback before using a learned procedure globally.
The paper acknowledges that accepted changes can survive unsuccessful task
chains, so its acceptance rule should not replace this project's promotion gate.

Disposition: design reference only. No upstream implementation was installed,
no EMMA benchmark was reproduced, and no local quality or token benefit is
claimed. Existing proposal-only lifecycle remains in force.

## Relevance to v3

Sections 3.2 and 3.3 make the failure owner explicit and freeze memory before
held-out evaluation. The paper reports first place in 17 of 20 settings across
five backbones. Its efficiency figure counts training executions. Our adoption
check instead counts observed tokens across development, preparation and both
trial arms. Compare both quality and total cost before adopting a change here.
[Method and results](https://arxiv.org/html/2610.35966v1#S5)

Appendix F illustrates a scope conflict worth testing. Its router selects one
continuous solver step, while the specialist prompt tells the solver to work
in phases with checkpoints. One dispatch can still contain multiple internal
phases. A valid learned procedure needs a replay that proves the boundaries
and preserved state, especially after an interrupted phase.
[Worked example](https://arxiv.org/html/2610.35966v1#A6)

Start with a failed episode and one reversible procedure draft. Leave isolated
execution slips with the task. Keep routing rules and role instructions outside
the procedure edit so a matched trial can attribute the result. The existing
controller replays frozen observations and complete cost before activation.
The latest dreaming replay only qualifies packing exact source evidence for
review. It supplies no new semantic judgments or promotion evidence.
[Procedure campaign](../../src/agent_harness/procedure_campaign.py),
[review payload replay](../../eval/results/v3-dream-review-payload-20261118.json)
