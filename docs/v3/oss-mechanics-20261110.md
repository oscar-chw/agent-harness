# v3 research sweep 3 — OSS harness implementation mechanics

2026-11-10. Companion to sweeps 1 (memory) and 2 (vendor pillars). Mechanism-level
findings from primary sources; gathered by delegated research agent. Vendor/social
numbers flagged where unverified.

## DSH (DeepSeek Harness) — plugin architecture

Everything is a Cordis plugin; the kernel only mounts plugins and resolves
dependencies; the agent LOOP itself is a swappable bundle. Layered entry-list YAML
config: bundle patches → profile patch → home patch → CLI `--patch`; later layer
wins, full-row replacement (NO deep merge); `!!js` expressions parsed to inert
markers. `--dump-config` as a first-class debug verb. Modes are plugin bundles
(Standard / Code-PTC / Minimal / Creator); permission presets per mode; sandbox =
bwrap/Landlock/Seatbelt. (github.com/deepseek-ai/deepseek-harness README + CLI
reference, MIT, 0.1.0-rc.x dev preview.)
Adapt: layered full-row-replacement config; dump-config verb; modes-as-profiles.
Reject: Cordis/pnpm runtime, `!!js` escape hatch.

## OpenClaw dreaming — actual scoring/gates

Three phases: Light (ingest daily notes + transcripts, Jaccard-0.9 dedupe, stage
to short-term; never writes MEMORY.md), REM (theme extraction, reinforcement
signals only), Deep (scores + gates + writes MEMORY.md under "Promoted From
Short-Term Memory"). Deep score = 0.30 relevance / 0.24 frequency / 0.15 query
diversity / 0.15 recency (14-day half-life) / 0.10 consolidation / 0.06 concept
richness. Promotion gates ALL required: minScore 0.8, minRecallCount 3,
minUniqueQueries 3. Rehydrates snippets from live files (deleted content skipped).
Audit: memory/.dreams/events.jsonl + DREAMS.md narrative + promote-explain.
Opt-in, default off. (docs.openclaw.ai/concepts/dreaming; community guides
2026-04-07.)
Post-ClawHavoc: skills ran with full host permissions, no hash/signature
verification; poisoned SOUL.md/MEMORY.md persisted after skill removal. Defenses
shipped: ClawHub VirusTotal/SkillSpector scanning — but an independent audit
claims 91% miss rate on seeded malicious skills. No registry signing exists.
Adapt: phase-scoped write permissions (only final phase writes durable store),
all-three-gates promotion, promote-explain transparency, events.jsonl audit.
ADD what they lack: hash-pin memory/persona files + diff-alert on unexpected
mutation. Reject: any registry scan verdict as a gate signal.

## Hermes Agent — self-writing skills, gated

skill_manage (create/patch/edit/delete) writes agentskills.io-compatible SKILL.md
after complex tasks/errors/corrections. Gates: write_approval → staged writes
under ~/.hermes/pending/skills with diff/approve/reject; guard content scanner;
per-skill LOCK refuses ALL writes (incl. terminal redirection) even under --yolo;
agent cannot self-unlock. Curator pass every 7d after 2h idle: deterministic
stale(30d)/archive(90d) transitions + capped LLM review; snapshot tar.gz before
every pass; rollback reversible; worst case = archive, never delete.
KNOWN GAP (issue #55647): per-session background review has NO snapshot of its
own; review fork patched skills without read-before-write. Lesson: EVERY automated
writer needs its OWN state checkpoint, not just the cron pass.
(hermes-agent.nousresearch.com docs; github issue 55647.)

## Pi — extension model over 4-tool core

Extensions = TS modules, factory gets ExtensionAPI: registerTool/registerCommand +
typed events (tool_call, tool_result, turn_start/end, session_compact...). Hooks
can BLOCK/REWRITE tool calls (permissionDecision allow/deny/ask, updatedInput,
additionalContext); awaited subscribers count toward run settlement → a hook can
reliably gate progress. Core: read/write/edit/bash, <1k-token prompt.
Supply-chain posture (for its own npm, not extensions): exact pins,
min-release-age=2, lockfile pre-commit protection, --ignore-scripts +
allowlist, npm audit signatures, SHA256SUMS. No sandbox — containment delegated
to documented container patterns; honest about it.
(pi.dev; npm README; agent-events wiki.)
Adapt: event-stream-with-settlement hook model (our pytest gates ARE awaited
subscribers blocking settlement); permissionDecision maps to gate veto/amend.
Reject: trust-the-user extension model for agent-authored runtime artifacts.

## NEEDLE + no_human — queue and tamper guard

NEEDLE: bead = title+body(deliverable+acceptance)+status+priority+deps; SQLite
beads.db; six-step state machine (SELECT→CLAIM(atomic, lost race is first-class)→
BUILD(deterministic prompt from bead state)→DISPATCH→EXECUTE→OUTCOME with an
explicit handler per outcome incl. timeout/crash/race-lost/queue-empty escalation
ladder ending in Knot = alert human). Rule: "if an outcome can happen, it has a
handler." (github.com/jedarden/NEEDLE)

no_human tamper guard (exact mechanism): static mechanical count over EVERY test
file via git ls-tree (not just the diff); counts deleted tests, new skips/xfails,
tautologized assertions; baseline = merge base; runs BEFORE the model review gate
(tampering never spends reviewer tokens); findings must be JUSTIFIED against
acceptance criteria (not auto-fail — legitimate removal deletes tests); "no test
command" = explicit NOT RUN verdict. Measured over 65 days self-building:
505/1709 claimed-dones refuted, 44 attempts stopped pre-review for test tampering,
46 bug proofs refused (evidence test passed on old code too). Known bug: unquoted
git ls-tree drops non-ASCII filenames; empty-diff action posts synthetic PASS.
(github.com/no-human-ai/no_human README.)
Adapt directly — see docs/v3/tamper-guard-design-20261110.md.

## The user's X post — RECOVERED

x.com/thesupermannx/status/2119341077975249222 (Nov 8 2026, via threadreaderapp
mirror): hype thread on claimed Tencent "Terminal-RSI" — recursive
self-improvement alternating RSR (fine-tune on own successfully rewritten
trajectories) and RPR (PPO with inherited critic), "success-prioritized reward"
paying only on final terminal-gate pass. Claims Terminal-Bench 20.68%→50.58%.
UNVERIFIED: arXiv ID 2610.22192, Tencent attribution, all numbers single-source.
Transferable idea (mundane, gate-shaped): dense/partial rewards teach agents to
fake success; strict terminal-verifier-gated rewards don't — the training-side
analogue of our pytest gates.

## Discourse notes

Threads: dead source for harnesses (login-walled, nothing indexed) — stop
spending sweep budget there. Ronacher "Better Models: Worse Tools" (2026-07-04):
models RL-trained against a forgiving harness emit malformed calls stricter
harnesses reject — harness strictness is a compat surface, not only safety.
"98.4% of Claude Code is harness" leak analysis; LangChain "Your Harness, Your
Memory" lock-in argument.

## Unverified (flagged)

Terminal-RSI everything; OpenClaw v2026.6.1 enforcement claims; 91% scanner miss
rate (single audit, methodology unseen); ClawHub malicious counts vary
(341/824/1184/2400+ by source); DSH ecosystem 48h numbers; Pi package count
snapshot; Hermes background-review write frequency; no_human tautology-detection
precision (undocumented — assume value-changed-assertion and fixture-edit blind
spots).
