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

After the underlying boundary is actually resolved, record the scoped resolution
and evidence in the node record. The authorized operator may then remove only
`hold: permission` from the node's fields and resume the original checks. This
does not remove native restrictions; if they still refuse, the hold returns.
The runner does not authenticate human consent or auto-repair native policies.
Worker-denial reporting currently uses Claude's structured `permission_denials`;
Codex does not expose an equivalent through this adapter. Do not infer that signal
from arbitrary result text. Gate-guard holds apply with either worker backend.
