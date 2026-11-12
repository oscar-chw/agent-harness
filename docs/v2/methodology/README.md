# Procedures selected by evidence

Development contract, 2 November 2026. This directory is a bounded methodology
input to `plan/v2-completion.md`, not a new installed skill or a v2 acceptance
receipt. Existing task requirements, permissions and independent gates win.

Use the smallest action that resolves the next consequential uncertainty or
produces a checkable result. The actions below are alternatives and feedback
destinations, not stages every task must visit.

| Next action | Evidence that warrants it | Concrete result and next check |
|---|---|---|
| Direct | Known answer, sufficient current evidence, no consequential unresolved choice | Answer the question; check its arithmetic or source only as needed. No persisted plan for a simple calculation. |
| Investigate | A missing fact can change the answer or repair; an artifact exists but is ungraded | Inspect the authorized local source first, or run one discriminating probe. Obtain current external evidence only for the missing unstable fact. Verify the existing artifact before restarting it. |
| Plan | Real prerequisites, multiple write owners, costly rework or continuation need coordination | Record outputs, owners, dependencies, budgets and gates in the existing graph. Independent valid branches can proceed; the parent still needs integration. |
| Implement | Requirements, causal surface and acceptance are sufficiently known; action is authorized and reversible | Make the smallest change or draft. Run the frozen outcome check and affected regression checks. A draft is not completion. |
| Diagnose | An observed result fails acceptance or misses the user's objective | Compare intended and observed outcomes; distinguish requirement, evidence, implementation, environment, integration and evaluator causes. Choose a check that separates plausible causes; repair the causal surface and rerun acceptance. |
| Replan | A probe disproves an assumption, a bounded attempt produces no usable artifact, or a dependency/authority changes | Change the approach, inputs or scheduling within scope; preserve useful artifacts and failures. Hold only the blocked effect. Ask only when intent, acceptance, scope or authority needs an owner decision. |

Stop the current attempt when its stated bound is reached. Two identical failures
are a reason to change the diagnostic approach, not to retry with a new label.
An unavailable tool or refusal is evidence about that boundary; it does not grant
permission to obtain the same effect through another route. A technically
discoverable fact is the agent's work, not a question for the user.

For example, a known empty-input parser defect with a failing reproduction can
go straight to a small repair. A stack trace with two plausible causes needs a
probe first. A receipt that says TIMEOUT with no artifact warrants a changed
bounded method; the same receipt with a draft warrants inspection and grading
of that draft. A failed research task-fit check requires reconciling the actual
question and missing evidence, not merely extending the prose.

A demonstrably faulty check is itself a diagnosis target. Preserve the original
failure, establish intended behavior from the requirement or independent source,
make the smallest check correction, prove a genuinely invalid input still fails,
then rerun the original gate and affected checks. If the intended requirement is
unresolved, hold that decision rather than guessing or weakening acceptance.

## What the existing helper actually implements

[`method_control.decide`](../../../src/agent_harness/method_control.py) is advisory.
Its precedence is consequential uncertainty → failed gate → passing gate →
artifact exists → native timeout/output limit → native failure → multiple
dependencies → direct. It does not infer domain uncertainty from task text.
`dependencies` and `uncertainty` are caller-supplied classifications.

`DIRECT` permits a single known implementation as well as a direct answer; it
does not certify that no investigation is necessary. `VERIFY_ARTIFACT` is the
inspection/grading route. `REVISE_ARTIFACT` with diagnostic checks is the repair
route. `CHANGE_METHOD` is a bounded replanning signal. There are no current
`INVESTIGATE` or `IMPLEMENT` runtime enums. Do not rename narrative preferences
into purported runtime capabilities.

The helper validates artifact hashes and current request/context/memory receipt
bindings. A `PASS` receipt suppresses old failure diagnosis, but the helper does
not authenticate who wrote that receipt or whether its check was adequate.
`gate_unchanged` and `authority_unchanged` are promises of advisory scope, not an
OS sandbox or an independent quality judgment. Plan size is not a quality metric.

## Cases and proof boundaries

[`cases.json`](cases.json) contains synthetic, visible development cases for
coding, research, debugging, daily work and learning. Each has concrete inputs,
an expected next decision, a failure, a constraint-changing counterexample and
observable acceptance criteria. They are authored applications of existing
sources, not historical user outcomes or secret held-out tasks.

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 docs/v2/methodology/replay_cases.py`
checks pack structure and replays the cases with `probe_kind: method` against
the actual helper using disposable local fixtures. `contract_only` cases retain
domain/learning acceptance requirements that the helper does not enforce.
The replay cannot establish that a native model chose a good method, answered
correctly, learned, or saved tokens. Its receipt names those limits.

[`evaluation.md`](evaluation.md) fixes the baseline, split, outcome checks and
total-token accounting, and maps each condition to an existing enforcing check
or explicit gap. [`native-promotion.md`](native-promotion.md) explains why
promotion remains held and the smallest credible qualification sequence.

## Existing material checked

`existing:` repository `content/skills/work-loop/{SKILL.md,recovery.md,reasoning.md}`;
the loaded `standards`, `production-code`, `session-memory` and
`problem-solving-harness` skills; `bin/harness`; `method_control.py`, `launch.py`,
`procedures.py`, `improve.py`; method, procedure, learning-arm, legacy-promotion
and quality-eval tests; `content/templates/learning-review.md`; v1 acceptance
matrix; v2 second-brain contract, root graph and dev2 handoff. No new framework,
plugin, global instruction, hook or model campaign was needed. No external web
facts are adopted by this packet.
