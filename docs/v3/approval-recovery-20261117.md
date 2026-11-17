# Recover an approved operation

The guard rule now directs agents to use a documented approval path for the
exact user-approved action. Unresolved actions remain held. This removes an
ambiguity that made a model treat every guard refusal as permanent.

## What an agent must do

1. Identify the rejecting component and preserve its exact refusal.
2. Inspect its documented approval interface and the current human grant.
3. Bind the invocation to the approved targets, effect and source revision.
4. Keep preflight, rollback and actual postchecks. Consume a scoped grant once.
5. Continue independent work when a separate native policy still refuses.

The owning transport must actually consume the approval. A chat statement alone
cannot supply a missing native grant. A global disable or a different executor
requires separate review. Existing destructive-command protections retain their
own checks.

## Qualification

An owner-operated administration wrapper already implemented a per-call approval interface.
An isolated fake-transport check verified refusal by default, consumption of
that interface, and refusal again on the next unapproved call. The live wrapper
and dangerous-command hook hashes were retained.

The owning operations chat completed its expressly approved installation. Independent
native readback then verified an allowed same-UID operation, refusal of root,
root-group and unlisted-shell attempts, and active SSH and thermal services.
The later app-level chat-resume refusal remains separate evidence. A personal
fresh SSH/editor session remains untested. This case establishes one working
approval consumer and its checked native outcome.

## Client compatibility

An approval response must be supported by the current client. Official Codex
PreToolUse documentation currently states that `permissionDecision: "ask"` is
unsupported and can fail the hook while execution continues. Verify protocol
support before adding a hook-level approval response. [Official hook documentation](https://learn.chatgpt.com/docs/hooks#pretooluse)

## Related context experiment

The optional `task_context` evaluation profile compares native automatic memory
injection with explicit shared project retrieval preserved. Both arms use the
same prompt and disable native memory generation for the trial. Effective
configuration and cold shared-memory reads passed without model generation.
Actual adherence, prompt size, token savings and adoption remain NOT_RUN.
The existing [negative continuation result](continuation-read-policy-20261117.md)
and its exact producing source remain independently replayable.
