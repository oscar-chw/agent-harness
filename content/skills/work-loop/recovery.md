# Keep the goal; isolate the blocked action

The user supplies the outcome and material clarifications. Own the research, plan,
execution, checks and recovery within that scope. Use existing skills and tools;
do not ask the user to choose routine implementation details. Scale the process
to the risk and uncertainty. Autonomy does not guarantee a successful outcome.

## Before executing

Understand the intended effect and targets. Prefer a bounded, reversible operation
that meets the goal: exact files over broad globs, a dry run before a bulk change,
and a recoverable move over permanent deletion when retention is acceptable.
Do not silently substitute archiving for a requested security purge, or change
scope, acceptance criteria or authority to make a command run.

## When an action is refused

1. Preserve the goal, completed evidence, exact rejecting layer and next step in
   the node's record/handoff. Link to the native refusal without copying secrets.
2. Do not repeat the denied effect through another command, tool, agent or account.
   Do not disable its guard. Diagnostic inspection must itself be permitted.
3. Hold the affected unfinished node. Keep its dependants waiting; continue ready
   independent nodes. A shared broken runtime, lost authentication, user stop or
   graph-integrity failure can require stopping the whole drain.
4. If the rejecting layer supports approval for this action, use that mechanism
   once with the exact target, effect and risk. Reuse a valid unconsumed grant;
   do not treat chat approval as a native grant when no consumer exists.
5. If there is no supported approval path, name the boundary and required owner
   action. Keep the checkpoint resumable instead of claiming the task is done.

Fix a false-positive rule only through an authorized maintenance path, with the
innocent case and a genuinely invalid case checked. A proposed rule fix is not
permission to execute the rejected action.

## What the development runner enforces

`hold: permission` is scheduling metadata, not an approval. A guard-refused gate
is recorded as `NOT_RUN` and held. A worker reporting structured denials is held
if completion was not established; an independent passing gate can accept work
despite an incidental denial. Other branches can finish. A new runner, `resume`, `--force`
or `--attended` does not clear the hold.

After an authorised guard repair, use `plan recover <slug> <id>
--gate-sha256 <original-sha256> --reason "resolution and evidence"`. This clears
only a pending guard-origin hold bound to that exact gate, after the current
guard accepts it. It executes nothing and preserves the original denial. A
changed gate, live lease, disabled/missing guard or unknown/native/worker origin
stays held. This is scheduler repair, not consent or a native approval token.
Native/worker denials need their original authority path and explicit operator
resolution; never relabel them as guard holds or retry through another route.
The runner does not authenticate human consent or auto-repair native policies.
Worker-denial reporting currently uses Claude's structured `permission_denials`;
Codex does not expose an equivalent through this adapter. Do not infer that signal
from arbitrary result text. Gate-guard holds apply with either worker backend.

## Privileged-command preference

Read `sudo_policy` from the current rules. `harness privileges --mode
deny|ask|adaptive|scoped` changes this instruction preference; omit the mode to
inspect. It grants no OS capability and changes no native permission setting.

- `deny`: no sudo. The user may change mode; independent work continues.
- `ask`: approve each privileged operation or an explicitly described batch;
  do not ask again for an operation already covered by valid approval.
- `adaptive` (default): judge the effect in its current context, not the word
  sudo. Authorized low-risk actions proceed. Ask only for an unsafe effect that
  is not already covered by approval, or consequential uncertainty about safety.
- `scoped`: execute within the user's established administrative task scope
  without per-command prompts. Missing scope is not unlimited authority.

Consider the actual target, resolved paths, affected users/services, blast radius,
reversibility, data sensitivity and current machine state. A read-only service
diagnostic differs from deleting its data; a disposable fixture differs from a
shared production database. Read-only access to credentials is still unsafe.
Bulk deletion, new exposure, destructive migrations and privilege/security changes
need the corresponding authority. Never infer it merely from broad goal approval.

Reuse approval within its stated purpose, targets, effects and end condition;
ask only for a material expansion. If uncertain, inspect safely or try a bounded
non-mutating preview. Do not change native/organization restrictions or work around
a guard. Do not collect passwords, pipe them to sudo or log secrets.

Learn from explicit user corrections and independently verified effects through
existing scoped lessons/decision records. Retain context, rationale, evidence,
exceptions and a counterexample with the same command in an unsafe context.
Success/exit0 alone is not a safety label. Learned cases advise future judgments;
they never grant approval, create global allowlists or silently weaken a guard.
Revalidate state and authority when context changes; contradictory evidence makes
the old case uncertain. No model-weight training or proven safety-classifier
improvement is implied by recording a lesson.
