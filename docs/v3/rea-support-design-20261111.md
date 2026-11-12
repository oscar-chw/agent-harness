# REA support for agent-harness — design v0

2026-11-11. Design for plan/v3-rea-support (node 4); v0 implements nodes 5–6.
Sources: docs/v3/harness-pillars-20261110.md ("REA / JEV resolved"; ranked
adaptations), docs/v3/oss-mechanics-20261110.md (NEEDLE/no_human), sweep 1
(docs/v3/research-sweep-20261110.md, SBU evidence log), the v2 precedent
docs/v2/references/lever-20261105.md, and docs/v3/architecture-v3-draft.md
(§1 inherited principles: gate-first, fail-closed, plain records, promotion
only through gates).

## 1. What REA support means for this harness

REA = "Reverse Engineer Anything" (sweep 2): an agent-facing reverse-
engineering toolkit whose load-bearing idea is that **every conclusion ships
with attached evidence**. The owner directed: "it should also support rea and
those useful tools."

For THIS harness, REA support concretely means: a **structured, lawful source-
analysis record** that an agent produces when it studies an upstream library
or tool to support a dependency decision — **reuse, adapter, fork,
pattern-only, or independent build** — plus a fail-closed validator that
refuses records whose evidence discipline is broken, and plan/workgraph
integration so a dependency decision can cite the record that justifies it.

Two deliberate scopings:

- **We adopt the discipline, not the toolkit.** Installing upstream REA as a
  dependency would itself be a reuse decision requiring an REA record (the
  bootstrap rule, §7). v0 is a first-party plain JSON record + validator;
  zero network, zero new dependencies, stdlib only.
- **Lawful sources only.** The intake contract (§2) refuses anything we are
  not authorized to read. "Reverse engineering" here means reading published
  source and documentation we may lawfully read — never circumvention,
  credential misuse, or decompilation of proprietary binaries.

Why this earns its place: sweep 1 rejected adopting Mem0/Letta/OpenClaw
wholesale — "borrow mechanisms only". Until now nothing enforced HOW a
borrowed mechanism gets justified. The REA record is that intake valve: every
adapted mechanism in docs/v3/architecture-v3-draft.md §4 cites sweeps; from
now on, any plan node that reuses upstream work can cite a hash-bound record
whose claims are separated into observed, inferred and unknown.

## 2. REA intake contract — what may be analyzed

An analysis may start only when ALL intake fields are present; the validator
refuses otherwise (fail-closed):

| field | requirement |
|---|---|
| `subject.name` | upstream project/library name |
| `subject.source_locator` | repo URL or local path |
| `subject.version_pin` | commit/tag digest pinning exactly what was read — an unpinned ("latest main") analysis is refused: conclusions must be replayable against the same bytes |
| `license` | `spdx` id + `holder` + `evidence` (a pinned license-file URL carried by a hash-bound local doc, or a local license-file sha256). **A missing license refuses the record** — no license, no analysis-derived decision |
| `lawfulness` | `basis` (why reading this source is authorized: public license-bearing repo, owner-held source, published documentation) — leaked code, credentialed areas beyond authorization, circumvention of access controls, and sweep-2-style "unverified/unlocatable" sources are not analyzable input |
| `reading_scope` | explicit `read` and `not_read` lists — the Lever note's "Other skills, linked anecdotes, automation recipes, dependencies and runtime behavior were not audited" is the model; undeclared scope refuses |

## 3. Analysis-record schema — `harness.rea-record/v1`

One JSON file per record at `docs/v3/rea/<subject>-<date>.json` (plain
records; public-safe: no deployment specifics, so secret-scan stays green).

- **Hash binding.** `evidence_bindings`: a list of `{ref, sha256, role}`.
  `ref` is a repo-relative path (the local evidence doc) or a logical name
  for the pinned upstream source. The on-disk check layer re-hashes every
  local `ref` and refuses on mismatch; the `version_pin` binds the upstream
  version. A record whose source is not hash-bound is refused.
- **Claim separation.** `claims`: `{id, statement, basis, observation_class,
  evidence[]}`. `basis` is `observed` or `inferred`. Observed claims carry an
  `observation_class` from the v2 convention: `documented` (upstream docs
  say), `source-observed` (read in source, not executed), `measured`
  (executed locally, receipt-bound). An observed claim MUST cite at least one
  evidence entry whose sha256 appears in `evidence_bindings` — an "observed"
  claim without bound evidence is **inference presented as observed** and the
  record is refused. Inferred claims carry `reasoning` and no evidence
  binding requirement; they are labeled and cannot silently upgrade.
- **UNKNOWN is never zero.** `unknowns` is a non-empty list. Bounded reading
  never yields total understanding; a record claiming zero unknowns is
  refused as dishonest by construction.
- **Promotion.** `promotion` is always `NOT_GRANTED` (the
  src/agent_harness/loop_contract.py precedent): a record is evidence for a
  human/plan decision, never an activation authority.

## 4. The five decision types and their evidence requirements

`decision.type` is one of five values; each carries mechanical requirements
the validator enforces, plus `decision.evidence` listing claim ids that must
all exist:

| decision | required fields (all fail-closed) |
|---|---|
| `reuse` | `license_compatible: true`; `used_surface` non-empty; for each used-surface element at least one `source-observed` or `measured` claim; `integration_cost` note |
| `adapter` | all `reuse` requirements + `boundary_map` non-empty: what the adapter translates and where the boundary sits (thin adapters preserve upstream identity — v2 contract principle) |
| `fork` | `license_permits_fork: true`; `fork_reason` (why upstream-as-is fails us); `maintenance_budget` statement — a fork is an ongoing obligation, not an import |
| `pattern-only` | `paraphrase_only: true`; `code_copied: false`; `reading_scope.read` non-empty — the Lever decision's exact shape ("paraphrases design ideas and includes no upstream implementation or substantial prose") |
| `independent build` | `prior_exposure` declaration (what was read before designing) + `rationale` that the design is independently derivable |

## 5. Integration with plan / workgraph / pipeline

- **Plan/workgraph (v0, additive — no engine change):** a plan node cites a
  record in its `ctx:` field (e.g. `ctx: docs/v3/rea/lever-20261105.json`);
  any gate script may call `rea.verify_record(path, root)` and fail the node
  when the cited record is invalid — fail-closed at the spine, per
  architecture-v3-draft §1. The workgraph engine itself is untouched.
- **Pipeline/tamper guard:** records and the design doc live under `docs/`,
  outside the test surface the tamper guard watches (`tests/`, `eval/`), so
  they need no attestation; the validator's own test suite DOES (one
  attestation entry, plan node 7). Push-tier secret-scan covers the records
  (tree-only mode).
- **v1 surface (recorded, not built):** a `rea_check` MCP tool validating a
  cited record inside `plan gate`; REA-record intake for the upstream REA
  toolkit itself (the bootstrap rule).

## 6. "Those useful tools" — support surface per the pillars doc

The useful-tool list is sweep 2's 12 ranked adaptations plus the vendor
mechanisms behind them. Status reflects this repo TODAY (sibling v3
workstreams have shipped since the architecture draft): each gets a minimal
support surface or a recorded deferral reason.

| # | adaptation (sweep 2) | status | minimal support surface / deferral |
|---|---|---|---|
| 1 | test-gated loop, oracle that cannot lie + tamper guard | **shipped** | `scripts/tamper_guard.py` v1 in the push tier with fail-closed attestation (plan v3-eval-pipeline node 17); REA v0 reuses its attestation discipline |
| 2 | filesystem-as-memory: progress log + JSON task list with `passes` flags + session ritual | exists / partial | workgraph plan files + node records already are the progress log; formal JSON status deferred to the v3.x phase (architecture-v3-draft §4 phase 5) — v0 REA records are themselves plain JSON, same posture |
| 3 | AGENTS.md-as-TOC + docs/ system of record + CI freshness | partial | AGENTS.md 60-line cap exists; TOC reshaping and CI freshness deferred (phase 5) — REA records join docs/ as the system of record for dependency decisions |
| 4 | generator/evaluator context separation | designed | architecture-v3-draft §2.3 phase 3; REA records give the separated evaluator pre-written criteria to grade against (a reuse claim's bound evidence) |
| 5 | typed local decision gates; execute above confidence, escalate below | designed | architecture-v3-draft §2.4 phase 4; REA decisions are a new typed verdict the decision layer may route on (invalid record → escalate, never execute) |
| 6 | serializable run state, approval gates, idempotency keys | designed | phase 3; no REA v0 dependency |
| 7 | prompt-prefix stability, append-only mid-run | exists / partial | append-only plan records exist; prefix-stability measurement deferred to phase 2 companion |
| 8 | subagent context firewalls, filesystem handoff | exists | handoff template + bounded subagent orchestrator; REA records are filesystem-handoff-native by construction |
| 9 | first-party SKILL.md skills, progressive disclosure only | **exists** | `content/skills/` already; a `source-analysis` skill teaching this record format is the v1 candidate |
| 10 | per-task ephemeral environments (git worktree + logs) | deferred | phase 5; needs owner appetite for worktree churn |
| 11 | harness stress-test cadence per model upgrade | deferred | phase 5; no model upgrade has occurred since the cadence was designed |
| 12 | rejections: A2A intra-machine, local MCP overhead, managed memory pricing, YOLO-default, monolithic instructions, unisolated verifiers | **adopted** | all remain rejected; REA intake contract adds "unverified sources" to the rejected-input list |

Vendor mechanisms behind the list, settled the same way: Anthropic's
initializer/progress-log/feature-list (covered by #2), OpenAI's approval
gates as serializable RunState (#6) and AGENTS.md TOC (#3), DeepSeek's
reasoning-content persistence (deferred — provider-specific, no local
surface), Google's ADK memory-bank pattern (covered by the H1/H4 memory
workstreams, not REA), Ralph/no_human oracle + tamper stance (#1, shipped),
NEEDLE beads (our workgraph nodes already are beads with gates).

## 7. Non-goals for v0

- No upstream REA toolkit install or vendoring — adopting it is itself a
  reuse decision that requires an REA record first (bootstrap rule).
- No network access, no crawling; analysis input is local evidence docs and
  already-pinned references.
- No binary, protocol, or runtime reverse engineering.
- No HAR/session compilation into eval environments (REA's other feature;
  no local recorded-session surface exists).
- No record ever grants promotion, activation, or merge authority.
- No workgraph engine or pipeline changes (additive amendments only).
