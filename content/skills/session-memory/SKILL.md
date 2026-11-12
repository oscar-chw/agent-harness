---
name: session-memory
description: Inspect shared task handoffs and maintain evidence-backed memory during multi-step work.
---

# Inspection-first session memory

Use for continuing, coordinating or checkpointing material work. A short answer
does not require a handoff. This protocol adds no access or messaging authority.

## Read before contacting another session
1. Resolve the authorized project root. Inspect its current graph and node records.
   With multiple requests/interruptions, keep `requests.md` beside that task's
   handoff: source pointer, intent, task/amendment/question/reference/stop, parent,
   acceptance and status. New steering does not silently cancel unfinished work.
2. `harness handoff --task <task>` reads local packets; large tasks: add `--list`,
   then `--packet <session>.md`; or read `handoffs/<task>/<session>.md`. Optional registered
   checkpoints: `harness task status --json` in the project. Use the default MCP
   `op_state status` before material work; if explicitly disabled, use CLI/project files.
3. Recheck source revisions, gates and artifact pointers. A handoff is advisory;
   `done` text, an expired lease or a quiet session proves neither PASS nor liveness.
4. Missing detail: use scoped `mem_search`, KB or targeted `session_search`.
   Prefer supported read-only chat inspection to raw transcript files. Never
   reopen excluded/private records or infer access to another user's projects.
5. Inspect shared status at task boundaries. Message only for urgent intervention
   or newly authorized work; no routine confirmations or model heartbeat polling.
   Idle sessions stop, not busy-wait. A task never authorizes duplicate work.

## Write while working
- For material work, create one project-local packet per task/session using the
  `${HARNESS_HOME:-$HOME/.agent-harness}/content/templates/handoff.md`. Use an observed session ID; otherwise record
  UNKNOWN and a unique local file name. Never overwrite a peer's packet.
- Update at decisions, milestones, failures, blockers, corrections and before
  compaction/end; do not wait to be asked. A crash before writing is unrecoverable.
- Usually 1–2 KiB: current goal/owner/revision, result, next step and held actions;
  link exact checks/results and source spans. Keep FAIL/BLOCKED/NOT_RUN, relevant
  constraints and unknowns explicit. Never shrink away correctness or copy a narrative.
- When permitted, register with `harness task checkpoint <task> --goal "..."
  --checkpoint handoffs/<task>/<session>.md --next "..."` from the project.
  Use the version returned by status with `--expected` when updating; a conflict
  means reread, not overwrite. The graph gate alone establishes completion.
  If the registry is unavailable, mark NOT_REGISTERED; keep the local packet
  discoverable through `harness handoff`. Never broaden access or bypass a guard.
- Save stable user-stated facts/preferences with scoped `mem_add`; record the
  source in the text, never pin without an explicit request. Observed project
  facts belong in evidence-linked KB/project memory, not user-fact assertions.
  Explicit user statements differ from inferred intent. Verified corrections
  and fail-to-pass evidence may become lesson candidates. Never treat uncertain
  inferences as confirmed preferences or promote generated skills automatically.
- Keep durable documentation in the shared KB/vault, task state in the graph/
  packet, and reusable methods in the candidate lifecycle. Link originals; avoid
  copying whole conversations, secrets, personal data or hidden reasoning.
- `state_save` is a small continuation fallback, not a shared multi-writer task
  ledger. `state_load` restores it after compaction; revalidate before acting.

## Bounds
Inspect only the needed project/task and disclose missing or stale evidence.
No polling messages, mandatory whole-history injection, background model calls,
automatic sharing across users/projects, purging history or weakened gates.
Tested file/CLI mechanics do not guarantee every model follows this protocol.
