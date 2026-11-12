# Retrieval and cold-checkpoint runtime seam

3 November 2026. Source inspection only; runtime/native verification **NOT_RUN**.
Root owns node4, freezing, execution and grading. No runtime/config/test edits.

## Smallest existing seam

Use `handoffs/<task>/<session>.md` as the producer's project artifact; a fresh
native process reads it and its current source spans. The installed guide
already describes this protocol. Root selects real content from the vault
reconciliation; no new architecture or actor answer is needed.

Give the producer a material continuation task and permission for its own named
checkpoint. It must write during its native turn. CLI final-output capture,
a receipt's `answer`, and root-written files are different observations. Bind
native write events to resulting bytes; "saved" prose does not prove a write.

The cold reader can use `harness handoff --task TASK --list`, then `--packet
NAME.md`, or the same scoped file directly. It should recover a source-supported
answer and useful next action, preserving pending/failed/unrun/held states.
Do not supply the complete producer answer. Freeze/disclose pointer assistance;
do not message the producer or resume its thread to demonstrate cold pickup.

## Inspected consumers and assumptions

- Active local guide: `/Users/me/.agents/skills/session-memory/SKILL.md`.
  Bytes match installed
  `/Users/me/.agent-harness/content/skills/session-memory/SKILL.md` and
  repo `content/skills/session-memory/SKILL.md` (SHA-256
  `d438a606e6a0033fe9c15fad731ba0e65c698cb85891fc724829a9f60dd2ab0c`).
  `/Users/me/.codex/skills/session-memory` was absent in
  the path inventory. Presence under `.agents` does not prove a particular
  Codex CLI version discovers or follows it. If root supplies the guide
  explicitly, record explicit exposure; do not claim automatic skill loading.
- `handoff.inspect` is read-only and advisory: 16 KiB/file, 64 KiB aggregate,
  100 entries, exact Markdown packet names and link/nonregular-file refusal.
  It returns path/hash/text; oversized or changed files can refuse. Listing
  and selecting avoids full-task injection, not the individual file bound.
- `mcp.state.project_root` walks to an ancestor `.git`, else uses the directory.
  A pilot nested inside this repo may therefore resolve handoffs at the repo
  root rather than its apparent subdirectory. Freeze the canonical project
  root and run both clients there; do not assume a new folder is isolation.
- `harness task checkpoint` is optional registration in the host/project
  OperationalState store. It needs an existing local file, goal and next
  action; updates use CAS. Status checks presence, not checkpoint correctness.
  If unavailable or outside the frozen write scope, retain the file and
  `NOT_REGISTERED`; never enable MCP/global storage for the pilot. No registry
  record is needed for `harness handoff` discovery.
- `SourceVault.resolve` checks project/source receipts, snapshot integrity,
  current original bytes and exact line ranges; historical reads are explicit.
  `ProjectMemory.recover` checks scope/current sources and follows latest
  revisions, returning CANDIDATE/HOLD/REFUSE_WITHDRAWN as applicable. Correction
  cannot change ownership/access and withdrawal is terminal for that identity.
  Verified paraphrases can become pending unless exactly source-supported.
- KB reads/search locate notes; rank/visibility prove neither entailment nor
  authority. Reopen original spans rather than trusting a summary's label.
- `launch.prepare` accepts 1–8 named ProjectMemory receipts, not arbitrary
  handoff paths; it requires current CANDIDATE dependencies and a complete
  512–32768-byte context budget. It is not a general checkpoint loader.
  Injecting the target answer as a memory dependency would change this pilot.
- `launch.execute` uses Codex on PATH, project cwd/`-C`, fresh `exec` unless
  explicitly resumed, default read-only or explicit workspace-write, POSIX
  cleanup and timeout <=300 s. Thus its default cannot produce a project
  checkpoint. It records thread/request/context/prompt identities, status and
  usage, but COMPLETED_UNGRADED never establishes task quality. It retains
  stdout/stderr hashes and bounded event summaries, not the original raw
  streams; root must choose capture that preserves required raw evidence
  without changing runtime/config. Native availability, actual executable,
  effective permissions/model and skill exposure remain unverified here.

## Targeted controls for root's frozen pilot

1. Producer: predeclare permitted writes, source pins, budget and grader; bind
   tool-write events to the new packet's hash. Distinguish legitimate project
   writes from final-output capture and reject fabricated checks or approval.
2. Correction: retain the old source/receipt as historical, acquire the current
   permitted revision, and require corrected advice with source span support.
   Old context must not silently become current; withdrawn advice must not be
   restored by copying it into a handoff. Correction grants no new permission.
3. Cold reader: distinct fresh thread identity, no resume/history transcript,
   same authorized project files; record exact input and assistance. Bind its
   answer/next action to observed current spans rather than packet wording alone.
4. Absence/scope: a forbidden tempting match must not expand access; an absent
   original remains UNKNOWN, not "never existed". Missing checkpoint, oversize
   or stale source must remain visible, with no manufactured substitute.
5. Preserve every attempt, original input/output/events and usage uncertainty.
   A blocked write, missing client, timeout or unavailable native execution is
   FAIL/NOT_RUN for the appropriate axis, never repaired by a root-authored
   checkpoint. No silent extra probes beyond the two authorized stages.

Existing two-process tests use a Python-written packet, not a native producer.
All sixteen acceptance cases remain requirements; this development pilot cannot
qualify unrepresented cases, automatic learning or comparative efficacy.
