# v3 research sweep 2 — harness architecture pillars (2026 evidence)

2026-11-10. Companion to research-sweep-20261110.md (which covered memory,
re-ranking, unlearning, RELAI-VCL). This sweep covers orchestration, vendor
harnesses, skills/tools methodology and eval hygiene. Gathered by a delegated
research agent; vendor numbers are vendor-reported unless noted.

## REA / JEV resolved

- **REA = "Reverse Engineer Anything"** (`github.com/morluto/rea`, MIT): agent-facing
  reverse-engineering toolkit over MCP/CLI; every conclusion ships with attached
  evidence; can compile a recorded app session (HAR) into a reusable RL/eval
  environment. Not a loop architecture.
- **JEV = Jev**, TypeSafe AI's "System One" model (stealth exit Sep 2026): typed
  decisions (Choice/Score/Noul boolean) with probabilities+confidence in one
  parallel pass, 70–500 ms. REFLEX (arXiv 2609.26532) used it as a decision layer:
  95% task success with 66–73% fewer strong-model calls. Calibration claims are
  vendor-stated; independent audit (2609.24052) notes no published metrics.
- The "@sprytixl twelve-agent commander" post remains UNVERIFIED/unlocatable.

## Vendor harness mechanisms worth stealing

**Anthropic** — "Effective harnesses for long-running agents" (2025-11-26):
initializer agent writes init.sh + progress log + JSON feature list with
`passes:false` per item; one feature per session; start-of-session ritual
(read progress, feature list, git log, smoke test). JSON over Markdown for status
("model is less likely to inappropriately change JSON"); editing tests is
"unacceptable". — "Harness design for long-running apps" (2026-03-24):
planner→generator→evaluator, evaluator in a SEPARATE context grading pre-written
criteria (self-evaluation bias and context-anxiety are the named failure modes);
agents communicate through the filesystem; stress-test every harness assumption
per model upgrade and delete stale scaffolding.

**OpenAI** — "Unrolling the Codex agent loop" (2026-01-23): stateless requests,
prompt-prefix stability (mid-run changes append-only), /responses/compact,
AGENTS.md capped at 32 KiB inside the token budget. — "Harness engineering"
(2026-02-11, 1M LOC, 0 human-written): AGENTS.md as ~100-line TABLE OF CONTENTS;
docs/ as system of record with CI-enforced freshness + doc-gardening agent;
architecture invariants enforced by linters/structural tests, not prompts;
per-worktree bootable app + ephemeral observability; agent-to-agent review loops.
Agents SDK approval gates as serializable RunState (pause→persist→approve→resume;
idempotency keys on side-effecting tools).

**DeepSeek** — V3.2 (2025-12-01): reasoning_content persistence contract for
thinking-in-tool-use; context-management ablation moved BrowseComp 51.4→67.6.
DeepSeek Harness (DSH, 2026-08-13 dev preview, MIT): everything is a plugin —
tools, modes, providers, even the agent loop itself (explicitly to prepare harness
self-modification); one inspectable YAML; other harnesses wire in as sub-agents;
per-step model routing. Preview-grade churn: adapt ideas, not the code.

**Google** — ADK (Apache-2.0, PY/Go/Java/TS GA): hierarchical agent trees as
declarative YAML, Runner with pluggable session/memory services behind interfaces,
built-in eval, OTel span taxonomy. Memory Bank pattern (async extraction, per-scope
isolation, contradiction consolidation) is implementable over SQLite + local model.
Reject A2A for intra-machine use.

**Community loops** — Ralph/back-pressure engineering (loop until an oracle that
cannot lie passes; OpenAI says their PR loop is "effectively a Ralph Wiggum loop");
NEEDLE (SQLite bead queue, atomic claims, explicit state machine); no_human
(second fresh-context model must REFUTE "done"; tamper guard blocks net test
reduction; merging stays human). Fowler/Böckeler: guides (feedforward) vs sensors
(feedback). Lilian Weng (2026-07-04): filesystem as persistent memory; inspectable
subagents whose outputs land in files; permissions/held-out tests stay OUTSIDE any
self-optimization loop. LangChain measured harness-only changes at +13.7 pp on
Terminal-Bench 2.0 with the same model; a third-party harness (NexAU-AHE) beats
the vendor's own on identical GPT-5.5.

## Skills/tools methodology

- Agent Skills format won: open standard (agentskills.io), donated to AAIF
  2026-10-22, ~1M published skills across 70+ platforms. Mechanism that matters:
  progressive disclosure (~100-token registry entries, full SKILL.md on trigger).
  REJECT the public supply chain: 26.1% of 42,447 community skills vulnerable,
  36% prompt-injection (Snyk ToxicSkills), average quality 6.2/12 (SkillsBench);
  OpenClaw's ClawHavoc shipped 1,184 malicious skills. First-party skills only.
- MCP 2026: Tasks (long-running ops), server-side sampling; ~17.5k public servers,
  12.9% high-trust. Locally: adopt the contract shape (typed schemas, structured
  errors), skip the protocol boundary unless interoperating outward.
- Eval hygiene is now load-bearing: Meerkat (arXiv 2604.11806) found harness-level
  cheating in the top-3 Terminal-Bench 2.0 submissions; NIST CAISI (2025-12-02)
  on agent-eval cheating. Consequence: verifiers live outside the agent's writable
  surface; block net test reduction; audit trajectories.

## Ranked adaptations for our harness (evidence × local feasibility)

1. Test-gated loop with an oracle that cannot lie + tamper guard blocking net
   test reduction (strongest evidence; pure local).
2. Filesystem-as-memory: progress log + JSON task list with passes flags +
   start-of-session ritual (we already do plan/gate records; formalize JSON
   status).
3. AGENTS.md-as-TOC + docs/ system of record + CI freshness checks.
4. Generator/evaluator context separation; fresh-context grading against
   pre-written rubrics.
5. Typed local decision gates (Jev pattern) for route/retry/escalate choices;
   rule-based or small local model; execute above confidence, escalate below.
6. SQLite run state with serializable approval gates + idempotency keys
   (Agents SDK RunState + NEEDLE atomic claims).
7. Prompt-prefix stability; append-only mid-run changes.
8. Subagent context firewalls: delegation prompt is the whole briefing; summary
   returns; filesystem handoff (matches this session's own delegation).
9. First-party SKILL.md skills with progressive disclosure only.
10. Per-task ephemeral environments (git worktree + queryable logs).
11. Harness stress-test cadence per model upgrade; components deletable.
12. Reject: A2A intra-machine, local MCP overhead, managed memory pricing,
    YOLO-default agents, monolithic instruction files, unisolated verifiers.

## Unverified

thesupermannx status 2119341077975249222 (user-supplied) unreachable (404/451);
sprytixl twelve-agent post unlocatable; Jev calibration vendor-stated; star
counts order-of-magnitude only; DSH repo not directly read ( VentureBeat/
DeepInfra/MindStudio attest).
