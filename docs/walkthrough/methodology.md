# Methodology, templates and evaluation

Choose the next useful action from the user's outcome, the available evidence and the current constraints. The workflow can return to analysis, research, design, implementation or verification when a specific finding requires it.

## Mechanism

1. Refine consequential ambiguity and recover existing project context. A short direct task can remain short.
2. Define success with an observable acceptance check. Research names its question, evidence and what would disconfirm its conclusion.
3. Use the graph when dependencies, owners, recovery or costly rework justify it. Select only the relevant skills and source sections.
4. Make a small change and run its check. Preserve the original failure and inspect the cause before retrying. Retain sound independent work.
5. Review the diff and relevant user flow. A current gate, the review finding and the exact artifact each need their own evidence.
6. Checkpoint at milestones, material corrections, blockers and continuation boundaries. Reusable methods enter a candidate lifecycle.

## Example

The shipping demo defines the threshold with three tests. Its first gate must actually run those tests and report the two expected assertion failures. A guard refusal is recorded as an execution problem. The prepared fix must pass the same test file, whose hash stays unchanged. The graph's transition follows the gate outcome.

This distinction prevents an environment or permission failure from being presented as a reproduced code defect. Another check requires the expected version-conflict diagnostic before describing a stale writer as rejected.

## Templates and skills

| Starting structure | Purpose |
|---|---|
| task.md | Goal, scope, acceptance and continuation |
| worker.md | Bounded delegated work and evidence expectations |
| handoff.md | Recoverable status, decisions, sources and next action |
| source.json | Source identity and provenance |
| procedure.json | A sourced reusable-method candidate |
| learning-review.md | Evidence and decision about a proposed lesson |
| loop-contract.json | A bounded comparison's cases, metrics and acceptance |

The [catalogue](../CAPABILITIES.md) links each file and all nine skills. The [delivery guide](../DEVELOPMENT.md) adds ticket, PR and release examples plus stack-specific checks. A template helps preserve required information. Its presence alone settles no outcome.

## Evaluation and learning

The procedure controller freezes tasks, answer inputs, model/effort, runtime and budget. It records consumed attempts and replays artifacts, grades, source bindings and observed usage before adoption. The acceptance rule preserves every required per-case quality dimension and counts preparation, failed attempts and evaluation overhead. Unknown required usage holds adoption.

The generated-procedure trial remains held after candidate-charged 172,569 tokens against a 48,969-token baseline. Retaining the failed attempt makes the decision auditable. A qualified result would still have a bounded project and task scope, with correction and rollback paths. Weight training remains outside this implemented procedure-learning path.

## Tradeoffs

- Unit tests provide fast local feedback. Integration, property, end-to-end and task-quality evaluations address different failure modes.
- A frozen evaluator reduces outcome-driven acceptance changes. A demonstrably invalid check needs an independently justified correction and preserved valid negative controls.
- Cost-complete trials can reject a useful-looking method whose preparation and maintenance outweigh the measured gain.
- A complete pipeline is expensive. A relevant targeted check can be the right acceptance for a small change.

## Evidence and limits

The live demo uses real CLI/MCP processes and a scripted code repair. The native memory study is separate. A passing transport test establishes mechanics, while broad agent productivity and teaching transfer remain unqualified.

## Implementation

[Adaptive work loop](../../content/skills/work-loop/SKILL.md) · [Standards](../../content/skills/standards/SKILL.md) · [Templates](../../content/templates) · [Procedure controller](../../src/agent_harness/procedure_campaign.py) · [Adoption checks](../../src/agent_harness/procedures.py) · [Review gate](../../src/agent_harness/review.py) · [Feedback assessment](../../content/skills/work-loop/feedback-loop.md)
