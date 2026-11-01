# Shared task handoff — advisory, inspect without messaging

Store at `handoffs/<task>/<session>.md` in the project; one writer per packet.
Inspect with `harness handoff --task <task>`; it needs no global task database.
Register through `harness task checkpoint` when permitted; otherwise record
NOT_REGISTERED and retain the project-local packet without expanding access.
Update at material milestones, blockers, corrections and before compaction/end.

- Task ID / owner / observed session ID (UNKNOWN if unavailable):
- Last updated / input revision / state (pending, running, blocked, done):
- Project / graph / current node:
- Intended outcome and preserved constraints:
- Source and code revisions actually used:
- Completed checks: command, result and evidence location:
- Failed or unrun checks and cause, if known:
- Changed files and integration dependencies:
- Existing task artifact index / final output / owned scratch; reuse locations rather than duplicating files:
- Current blocker / precise next action:
- Remaining worker, retry and usage budget:
- Held promotion, deployment or irreversible action:
- User-stated intent and source; inferred intent separately, with uncertainty:
- Durable memory/KB/lesson references; superseded or stale claims:

Reopen the graph and source receipts before acting. Recheck stale evidence;
do not convert this summary into a completion or authorization receipt. Retain
original records and link them instead of copying a whole conversation.
Inspect this file and current evidence for status/results. Contact another session
only to activate authorized work, not to ask it to repeat what is recorded here.
