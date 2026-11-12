---
name: work-loop
description: Default loop for research, coding and dev-ops - analyse, research, plan, execute, test, loop back where the evidence points. Use for any task beyond a one-line change.
---

# Adaptive problem solving

Choose the next useful action from the current goal, evidence and constraints.
These are available actions, not a mandatory sequence. Simple answers stay direct.
Use relevant principles, counterevidence and alternatives; [reasoning.md](reasoning.md)
provides optional depth when a concrete uncertainty cannot be resolved directly.

## Prepare before task actions
- Material includes requested plans and research. Before the substantive answer,
  writes or delegation, emit **Task brief:** in a few sentences, then continue:
  outcome, scope/non-goals, constraints/authority, success check, sourced context,
  labelled assumptions/consequential gaps and next action. Preserve original intent.
- Recover available context before questions; use [task-brief.md](task-brief.md).
  Do not invent facts, expand authority or change acceptance to make work easier.
- Trivial requests stay direct, without a visible brief or compulsory research/plan.
  Do not chase prompt perfection; revisit only when evidence or requirements change.

## Understand and inspect
- Establish the intended outcome, constraints, facts, assumptions and success check.
- Inspect local knowledge, memory, task state and the project before asking for
  information already available. Research only the consequential evidence gap.
- Ask the user only for unrecoverable intent, authority or a real value tradeoff;
  give a recommended default and its consequences. Own technical diagnosis.

## Act and verify
- Choose a small reviewable action; coordinate independent work only when useful.
- Code: name a failing reproduction and affected checks. Research: define the
  hypothesis, evidence, baseline and disconfirmation before judging the result.
- Data: tiny input, representative sample, full run. Record commands, inputs,
  seeds and outputs where they matter. Reuse the current task's artifact home.
- Run the actual check; compare with the intended outcome and baseline. Preserve
  failures, unrun steps and uncertainty. Never weaken a valid test to get green.
- Optional optimization assessment: [feedback-loop.md](feedback-loop.md).
- Full-stack/interview work: load [full-stack.md](full-stack.md). Explain useful
  tradeoffs and use an appropriate visual when it reduces understanding effort.

## Respond to evidence
- A weak or failed result: reconcile intent with what was actually achieved;
  identify the gap, competing causes and a discriminating check before patching.
- Return to analysis, research, design, implementation or verification as needed.
  Repeat neither the same failed approach nor a full routine without a reason.
- Dependency branches can proceed independently and join at an integration check.
  Parent completion requires current child evidence and its own outcome check.
- Persist task state/checkpoints for dependencies, recovery or cross-session work.
  `plan context` rebuilds the briefing; `plan gate` records completion evidence.
  A failed gate returns its node to pending. Never hand-edit completion marks.
- Blocked effect: follow [recovery.md](recovery.md); continue independent work.
- Report the outcome, evidence and material limits concisely. Verified corrections
  and fail-to-pass lessons are candidates, not automatically promoted standards.
