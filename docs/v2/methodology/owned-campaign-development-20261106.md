# Freeze the comparison before learning from it

**Status: implemented in source for development collection only.** This does not
activate a method, finish the learning controller, or qualify full V2.

The old drafting/trial entry points could bind supplied episode files, but that
did not prove the controller had collected those experiences before choosing a
candidate. The new campaign starts earlier:

1. Freeze every development and held-out task, original answer, split, model,
   effort, timeout and controller source revision before any call.
2. Run each development task through the existing isolated native boundary.
   Persist the consumed attempt before invocation and the returned receipt before
   checking sources or grading. A failed call stays consumed; no automatic retry.
3. Grade the actual answer against the original frozen answer. Only successful
   source-bound experiences enter the result. Keep completed actors under the
   denied evaluator directory before starting the next one.

The public source CLI separates the model-free freeze from explicit execution.
From the source checkout (these commands are not in the installed dev8 yet):

```sh
PYTHONPATH=src python3 bin/harness improve --project "$PROJECT" --prepare-campaign "$SUITE" --oracle-root "$ORACLE"
PYTHONPATH=src python3 bin/harness improve --project "$PROJECT" --collect-campaign-development "$CAMPAIGN_ID"
```

The second command consumes included native quota. Its result is development
evidence, **not** an activated skill. The supported tasks are bounded exact-JSON
answers; this is not a general coding-quality grader. Caller scores and episode
claims cannot replace these executions. Same-host owner/controller integrity is
assumed; this is not adversarial host attestation.

A bounded native smoke collected **two real development answers**, both correct,
in distinct fresh threads. Root replay matched the frozen answers, request and
receipt hashes, controller database and empty owned process groups. It reported
46,142 native input-plus-output tokens, not certified complete workflow cost.
This used the existing built-in provider, not the separate temporary configuration
below. No method was drafted or activated, and no held-out comparison was run.

## What still prevents promotion

Controller-owned drafting from these new records, paired held-out execution,
complete usage across preparation/review/maintenance and prior attempts, and the
accepting correction/rollback consumer still need integration. The current result
keeps `usage_complete=false` and `promotion=NOT_GRANTED`. Reported native counts
are not certified full provider or campaign cost. The original node-42 gate and
the original 16-case V2 acceptance remain unchanged.

## Native configuration admission

A separate **model-free** native check read back a fresh per-process provider
with ChatGPT-login-only account admission and both configured retry counts zero.
It observed the existing command/direct-file denials and empty MCP surface, and
sent no `turn/start`. No installed settings or default provider changed.

An initial check falsely rejected serialized unset/default fields. The correction
accepts only known `null` optionals and the two default-`false` capability flags,
as shown in the pinned [provider definition](https://github.com/openai/codex/blob/ddd1812a51f4aded35c3ec5446672474d5cb546b/codex-rs/model-provider-info/src/lib.rs#L146-L235).
Nonempty credentials/routes, changed retry/auth values and unknown fields still
fail. Original failures and before/after controls are retained.

Configured zero retries is **not proof of every runtime retry path**, backend
inference routing or complete token accounting: no generation occurred. The earlier
direct-usage notification probe remains unqualified. Evidence and qualification
receipts are under `.harness-work/provider-admission-20261106/`.
