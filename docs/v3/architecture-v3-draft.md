# v3 target architecture (DRAFT)

**Status: DRAFT — 2026-11-10. Not approved. Not implemented. Nothing in this
document authorizes code changes; every mechanism below enters only through the
gated experiment path (§5) starting with `plan/v3-h1-consolidation.md`.**

**As-built status: see §7 (2026-11-11 addendum). The planned text of §1–§6 is
unchanged; §7 records what actually shipped, with real verdicts.**

Sources cited in this document:

- **sweep 1** = `docs/v3/research-sweep-20261110.md` (memory: consolidation,
  learned re-ranking, unlearning, regression-constrained self-modification;
  hypotheses H1–H5).
- **sweep 2** = `docs/v3/harness-pillars-20261110.md` (orchestration, vendor
  harness mechanisms, skills/tools methodology, 12 ranked adaptations).
- **v2 contract** = `docs/v2/second-brain-contract.md` and `docs/contract.md`.
- Current architecture = `README.md`, `docs/how-it-works.md`.

Section names and item numbers refer to those documents. Mechanisms composed in
a way neither sweep states directly are marked **[novel combination]** — ours,
not sourced.

## 1. Design principles inherited from v2 (unchanged)

These stay exactly as they are; v3 adds capability inside them, never around
them.

1. **Gate-first.** A node is done only when its gate command exits 0, run by the
   work graph after the guard has passed it. v3 inherits this wholesale
   (current: `src/agent_harness/workgraph`, `plan` MCP tool).
2. **Fail-closed.** Unparseable input, unknown route state, exhausted budget or
   a missing receipt returns BLOCKED/HOLD, never a best-effort proceed
   (current: `guard.py` fail-closed parse; `routing.next_decision` returns
   `HOLD` on unknown inputs).
3. **Plain records.** Markdown/SQLite/JSON files, human-readable, one small
   file per item, hash-bound where evidence matters; stores have caps and are
   archived, not deleted, past the cap (build contract; `docs/how-it-works.md`
   "Bounded on disk").
4. **Promotion only through gates.** Nothing learned, consolidated or
   re-ranked activates on a caller's say-so. The standing rule: no per-case
   quality regression, a measurable gain, aggregate tokens including overhead
   no greater than baseline (`docs/how-it-works.md` "Getting better, only
   where measured"). The `HOLD_UNVERIFIED_BOUNDARY` posture of
   `skill_manage`/`harness improve --apply` is the template for every v3
   promotion.
5. **Verifier outside the writable surface.** Held-out tests, frozen corpora,
   permission boundaries and the evaluator never live where the agent being
   judged can edit them (sweep 2, "Skills/tools methodology", eval hygiene:
   Meerkat/NIST CAISI; "Community loops", Lilian Weng: permissions/held-out
   tests stay OUTSIDE any self-optimization loop). v2 already enforces this for
   skill promotion; v3 extends it to memory consolidation and re-ranking.
6. **Local-first constraints carried from v2** (sweep 1, preamble): no paid
   APIs, no new runtime, standard-library-only default install, measured
   footprint caps.

## 2. Target component map

```
spine          plan / gate / oracle            (exists; harden)
memory         consolidation H1 · ranking H2/H3 · unlearning H4 · RL data H5
orchestration  planner/generator/evaluator separation · subagent firewalls
               · filesystem handoff
decision       typed local gates; execute above confidence, escalate below
tools/skills   first-party progressive-disclosure skills · contract-shaped tools
eval hygiene   tamper guard (net test reduction) · trajectory audit
```

### 2.1 Spine: plan / gate / oracle

**Target.** One work graph remains the only completion authority. Every v3
subsystem (consolidation, re-ranking, unlearning, promotion) is expressed as
gated plan nodes, not as background processes. The oracle is an executable
check that cannot lie: pytest gates, frozen-corpus hash verification, mutation
controls (sweep 2, "Community loops": loop until an oracle that cannot lie
passes; ranked adaptation #1). Mid-run state changes are append-only and the
prompt prefix stays stable across a run (sweep 2, "Vendor harness mechanisms",
OpenAI: prompt-prefix stability; ranked adaptation #7).

**Exists today.** The workgraph (`plan` tool, gate commands judged by the
guard, atomic claims with leases, failed gates return nodes to pending,
irreversible nodes held for a human) — on by default since v0.3.3
(`docs/how-it-works.md`). Hash-bound snapshot conventions from v2
(`plan/v3-h1-consolidation.md`, "Assets to reuse").

**Gap.** No tamper guard blocking net test reduction is active by default
(`check_guard` is installed but inert; `run_checks` is off by default).
Prompt-prefix stability is unmeasured in our stack. Oracle coverage is
per-plan, not yet a uniform property of every memory mutation (§2.2).

### 2.2 Memory subsystem

The v2 contract's memory choice stands: RAG-first over plain records, derived
views never the only recovery route, automatic consolidation/graph/learned
routing added only after incremental contribution is measured (v2 contract,
"Memory choice"). v3 is that measurement program.

#### 2.2.1 Consolidation (H1) — first experiment

A local, model-free-first dreaming pass over the existing memory store: exact/
near-duplicate merge, SUPERSEDES edges, conflict flagging, decay weighted by
load-bearing reference count instead of wall-clock recency (sweep 1, H1;
EngramRAG retention half-life by topological load; SUPERSEDES DAG for fact
mutation). Consolidation safety mechanisms come from arXiv 2603.17244 via
sweep 1: dry-run default, circuit breaker, cursor-based resumption, auditable
report, published-item protection. Runs on a copy; promotion into the live
store is a separate gated decision (`plan/v3-h1-consolidation.md` non-goals:
no deletion without archive, no live-store mutation). **[Novel combination]**:
driving the pass as workgraph nodes with hash-bound frozen corpora and
mutation controls as the oracle — the individual mechanisms are sourced, the
composition onto our Markdown/SQLite store under our gate spine is ours.

#### 2.2.2 Learned ranking (H2/H3)

Retrieval becomes a cascade behind `kb_search`/`mem_search`: cheap lexical/
structural candidate generation, then a learned reranker using stored outcome
signals (gate pass/fail, reuse counts, correction events) — zero LLM calls at
selection (sweep 1, H2; AgentMemRec 2610.34673). Cached query–memory relevance
scores in an online matrix, completed causally, cut repeat-retrieval cost
(sweep 1, H3; EARM 2608.22767). Retrieval experience is itself a memory, kept
in the same plain-records discipline. Frozen evaluation: the existing v2
retrieval case sets (`docs/v2/methodology/`) plus the node-4 gate corpus
(sweep 1, "Adaptation map").

**Gap.** Today: FTS5/BM25 scoped retrieval with `uses` counters and a wikilink
reference graph — the raw signals exist, the cascade, the reranker and the
score cache do not.

#### 2.2.3 Unlearning (H4)

Agent-level deletion protocol: blocklist + dependency-closure deletion with
reference counting over the Markdown/SQLite memory, recorded in a hash-chained
tamper-evident log (sweep 1, H4; SBU 2602.17692, memory pathway only).
Acceptance: the removed fact and its derived artifacts yield zero retrieval
hits after deletion, retained facts untouched, no backflow through plans or
summaries in a probe eval (sweep 1, H4 disconfirmation). **[Novel
combination]**: the audit log reuses our v2 hash-chain/snapshot conventions
rather than SBU's own store.

**Gap.** `mem_forget` is single-item deletion with no closure, no backflow
check, no tamper-evident log.

#### 2.2.4 Deferred RL (H5)

No local training budget is assumed. v3 collects the training signal — (query,
candidates, chosen, outcome) logged from v2-completion campaign runs — and
evaluates policies offline (sweep 1, H5 + "Adaptation map"; MemDream's
GRPO-chosen repair ops and PPRO's ranking priors noted as the shape of a
future policy, not a commitment). If the disconfirmation holds (no budget),
we ship the logged dataset and the offline evaluation, and we do not fake
learning (sweep 1, H5).

### 2.3 Orchestration

**Target.** Planner → generator → evaluator, with the evaluator in a SEPARATE
context grading pre-written criteria — self-evaluation bias and context
anxiety are the named failure modes (sweep 2, "Vendor harness mechanisms",
Anthropic 2026-03-24; ranked adaptation #4). Subagents get context firewalls:
the delegation prompt is the whole briefing, a summary returns, handoff is
through the filesystem (sweep 2, ranked adaptation #8). Agents communicate
through the filesystem, not shared context (same Anthropic source). Run state
is serializable: pause → persist → approve → resume, idempotency keys on
side-effecting tools (sweep 2, OpenAI Agents SDK RunState + NEEDLE atomic
claims; ranked adaptation #6).

**Exists today.** Tier routing (`content/routing.toml`, `harness-<tier>` agent
files, `plan run` passes model/effort explicitly); a bounded built-in-subagent
orchestrator on Kimi; the project-local handoff template and session-memory
protocol; workgraph atomic claims with leases.

**Gap.** No enforced generator/evaluator context separation — today the same
session usually writes and judges. Subagent firewalls are convention, not
mechanism. Run state is not serializable mid-node: approval gates pause the
human, not a resumable RunState. Per-task ephemeral environments (git worktree
+ queryable logs, ranked adaptation #10) do not exist.

### 2.4 Decision layer

**Target.** Typed local decisions for route/retry/escalate: a Choice/Score
verdict with an explicit confidence, made by rules or a small local model in
one cheap pass; execute above the confidence threshold, escalate below it
(sweep 2, "REA / JEV resolved": the Jev pattern as used by REFLEX; ranked
adaptation #5). This decides harness-level routing only — it never replaces a
gate's exit-0 authority.

**Exists today.** `routing.next_decision` (disabled by default): typed task
profile → minimum tier, `HOLD` on unknown inputs/stale context/exhausted
budgets; advisory, no measured advantage (`docs/how-it-works.md`).

**Gap.** No confidence semantics, no execute-above/escalate-below policy, no
outcome logging feeding back into routing (that feedback is H5's dataset).
Calibration claims in the sweep are vendor-stated and unaudited (sweep 2,
"REA / JEV resolved"; "Unverified") — so our confidence thresholds must be
set from our own logged outcomes, not imported numbers. **[Novel
combination]**: Jev-style typed verdicts driving workgraph tier selection
under our fail-closed HOLD discipline.

### 2.5 Tools and skills

**Target.** First-party skills only, progressive disclosure: ~100-token
registry entries, full `SKILL.md` on trigger (sweep 2, "Skills/tools
methodology": the Agent Skills format's mechanism that matters). The public
skill supply chain is rejected (same section: Snyk ToxicSkills, ClawHavoc,
SkillsBench quality). Tools adopt the MCP contract shape — typed schemas,
structured errors — without taking on a new protocol boundary unless
interoperating outward (same section, "MCP 2026"). Instruction files stay
capped and act as a table of contents into `docs/`, the system of record,
with freshness checked in CI (sweep 2, OpenAI harness engineering; ranked
adaptation #3).

**Exists today.** Exactly this posture, predating the sweep: `content/skills/`
first-party `SKILL.md` skills with progressive disclosure, the 60-line cap on
`content/AGENTS.md` enforced by a test, the stdio MCP server with typed tool
arguments, `skill_manage` refusing direct create/update.

**Gap.** No CI freshness check binding `docs/` to code changes; AGENTS.md is a
cap, not yet a maintained TOC; no doc-gardening pass exists.

### 2.6 Eval hygiene

**Target.** Verifiers live outside the agent's writable surface; a tamper
guard blocks any net reduction of tests; trajectories are audited (sweep 2,
"Skills/tools methodology", eval hygiene: Meerkat found harness-level
cheating in top-3 Terminal-Bench submissions; NIST CAISI; "Community loops",
no_human tamper guard; ranked adaptation #1). Regression avoidance is checked
DURING the search for harness changes, not post-hoc (sweep 1, RELAI-VCL
2607.14004). Harness assumptions are stress-tested per model upgrade and
stale scaffolding is deleted (sweep 2, Anthropic 2026-03-24; ranked
adaptation #11).

**Exists today.** `check_guard.py` exists but is inert/off by default; the
guard protects its own hooks from overwrite; `--trend` refuses a release with
any lower score or greater aggregate tokens than the best accepted earlier
release; eval corpora and held-out sets are committed.

**Gap.** Net-test-reduction blocking is not on by default; there is no
systematic trajectory audit (today's audit is per-eval, manual); no scheduled
per-model-upgrade stress-test cadence.

## 3. Component map: exists vs gap (summary)

| Component | Exists today | Gap |
|---|---|---|
| Spine: plan/gate/oracle | workgraph, guard-judged gates, leases, irreversible holds | tamper guard inert; prefix stability unmeasured |
| Memory: consolidation (H1) | dedup on `mem_add`, caps with archive-not-delete | no supersedes/conflict/decay pass; no dry-run/circuit-breaker harness |
| Memory: ranking (H2/H3) | FTS5/BM25, `uses` counters, wikilink graph | no cascade, no learned reranker, no score cache |
| Memory: unlearning (H4) | single-item `mem_forget` | no dependency closure, backflow check or hash-chained log |
| Memory: RL data (H5) | outcome records exist per gate run | no (query, candidates, chosen, outcome) dataset |
| Orchestration | tier routing, bounded subagents, handoff template | no evaluator context separation; no serializable run state; no ephemeral worktrees |
| Decision layer | advisory `routing.next_decision` with HOLD | no typed verdicts, confidence, execute/escalate policy |
| Tools & skills | first-party progressive-disclosure skills, capped rules | no docs-CI freshness; AGENTS.md not a maintained TOC |
| Eval hygiene | guard self-protection, `--trend` keep rule, held-out sets | tamper guard off; no trajectory audit; no stress-test cadence |

## 4. Phased roadmap: v3.0 → v3.x

Phase 1 is `plan/v3-h1-consolidation.md`, already written and **awaiting owner
approval**. Each later phase maps to sweep 2's ranked adaptations and sweep
1's hypotheses, and promotes only through its explicit gate. A phase that
fails its gate changes nothing in the default install.

**Phase 1 — v3.0: consolidation experiment + the eval floor it stands on.**
H1 model-free consolidation pass (sweep 1, H1): frozen hash-bound corpus,
baseline metrics recorded before any change, consolidated copy must pass the
identical query set with no lost fact and higher precision, injected
duplicate/conflict mutants must be caught. Promotion gate: `check_h1.py`
exits 0 (`plan/v3-h1-consolidation.md`, nodes 5–9). Alongside it, the
prerequisite hygiene: tamper guard blocking net test reduction switched from
inert to enforcing, and formalized JSON task status with `passes` flags plus
the start-of-session ritual (sweep 2, ranked adaptations #1, #2). Promotion
gate for the hygiene items: the existing test suite plus a held-out
tamper attempt corpus passes with the guard on; no node completes whose
evidence post-dates its gate.

**Phase 2 — v3.1: learned ranking.** H2 cascade + H3 amortized scoring behind
`kb_search`/`mem_search` (sweep 1, H2/H3). Frozen eval: v2 retrieval cases +
node-4 gate corpus. Promotion gate: precision gain on the 16-case retrieval
gate with no node-4 regression, no accuracy drop on held-out replay beyond
noise, added p50 latency not materially worse (sweep 1, H2/H3
disconfirmations), and the standing token rule (aggregate tokens ≤ baseline).
Cheap companion: prompt-prefix stability measurement and append-only mid-run
discipline (sweep 2, ranked adaptation #7).

**Phase 3 — v3.2: orchestration separation.** Generator/evaluator context
separation with fresh-context grading against pre-written rubrics; subagent
context firewalls with filesystem handoff; serializable run state with
approval gates and idempotency keys (sweep 2, ranked adaptations #4, #8, #6).
Promotion gate: on a frozen set of multi-node plans, separated evaluation
catches injected false-"done" claims that same-context evaluation misses
(control), with no loss of completed-node correctness and crash/replay/
duplicate-event tests passing (v2 contract, "Architecture": new composition
earns its place through exactly these tests).

**Phase 4 — v3.3: decision layer + unlearning.** Typed local decision gates
with confidence; execute above, escalate below (sweep 2, ranked adaptation
#5). H4 blocklist + dependency-closure unlearning with hash-chained log
(sweep 1, H4). Promotion gates: decision-layer thresholds derived from our
logged outcomes with routing quality at least baseline and HOLD rate
reported; unlearning probe eval shows zero retrieval hits for the removed
fact, retained facts untouched, no backflow (sweep 1, H4 disconfirmation).

**Phase 5 — v3.x: deferred learning and fleet hygiene.** H5 preference-data
logging from campaign runs + offline policy evaluation only (sweep 1, H5 — no
local training claim). Per-task ephemeral environments (git worktree +
queryable logs), AGENTS.md-as-TOC with CI docs freshness, per-model-upgrade
harness stress-test cadence with deletable components (sweep 2, ranked
adaptations #10, #3, #11). Promotion gate per item: its own frozen
before/after comparison under the standing quality-and-tokens keep rule.

Rejected from the ranked list and not scheduled: #12's rejections are adopted
as-is (A2A intra-machine, local MCP overhead beyond our existing server,
managed memory pricing, YOLO-default agents, monolithic instruction files,
unisolated verifiers — sweep 2, ranked adaptation #12).

## 5. Explicit non-goals

- **No public skill supply chain.** First-party skills only (sweep 2,
  "Skills/tools methodology": 26.1% of community skills vulnerable, 36%
  prompt-injection, ClawHavoc).
- **No A2A for intra-machine coordination** (sweep 2, "Vendor harness
  mechanisms", Google: reject A2A intra-machine).
- **No managed memory pricing / external memory services** (sweep 2, ranked
  adaptation #12; v2 local-first constraint).
- **No always-on background LLM consolidation.** Consolidation starts
  model-free; any LLM assist is opt-in behind a gate (sweep 1, "Explicitly
  rejected this round").
- **No parameter-level unlearning.** We own no model weights; memory-pathway
  only (sweep 1, preamble and "Explicitly rejected this round").
- **No adopting Mem0/Letta/OpenClaw as the memory core.** That replaces our
  provenance model; we borrow mechanisms only (sweep 1, "Explicitly rejected
  this round").
- **No new runtime, no paid APIs, standard library only for the default
  install** (build contract; sweep 1 preamble).
- **No RL training claims without a budget.** H5 is data collection and
  offline evaluation; we do not fake it (sweep 1, H5).

## 6. What this document is not

Not a commitment to build all of §2: phases past 1 exist only as far as their
gates are written. Not a v2 rewrite: every inherited principle in §1 stays
normative. Not evidence: every mechanism above is a hypothesis with a named
disconfirmation until its phase gate exits 0.

## 7. As-built addendum (2026-11-11)

The draft above is the 2026-11-10 plan. This addendum records what actually
shipped through 2026-11-11, with real verdicts — confirmed, disconfirmed,
split — not a success narrative. The planned text of §1–§6 is unchanged
(additive discipline: this is a dated addendum, not a rewrite; the draft's §6
says the plan was "not evidence", and the record of what was PLANNED stays
intact). Source of truth for track verdicts and key numbers:
`docs/v3/outcome-table-20261111.md` (generated from the frozen registry
`docs/v3/outcome-tracks-20261111.json`; every row's verdict doc and receipts
hash-verified at generation time). The verdict ledger below is
machine-checked against that table by
`.harness-work/v3-docs-sync/check_docs_sync.py` — a doc that drifts from the
evidence fails that gate.

Workstreams landed: `plan/v3-h1-consolidation.md` 9/9, `plan/v3-h2-reranking.md`
9/9, `plan/v3-h3-hybrid.md` 9/9, `plan/v3-h4-dreaming.md` 9/9,
`plan/v3-h5-unlearning.md` 9/9, `plan/v3-h6a-l2-candidacy.md` 10/10,
`plan/v3-h6b-backflow-guard.md` 9/9, `plan/v3-h6c-dreaming-v1.md` 10/10,
`plan/v3-eval-pipeline.md` 18/18, `plan/v3-rea-support.md` 7/7,
`plan/v3-jev-needle.md` 7/7, `plan/v3-settlement-plugin-loop.md` 7/7,
`plan/v3-dev9-deploy-prep.md` 11/11 (staged; install fenced behind the owner
command). Numbering note: the draft used sweep-1's H-numbering; the executed
plans renumbered — draft "H4 unlearning" shipped as track h5, draft "H5 RL
data" stayed deferred, and h4/h6a/h6b/h6c are post-draft tracks.

### 7.1 Verdict ledger (machine-checked)

- h1 — CONFIRMED (as amended) — 26/26 checks; 5/5 mutation controls both directions; recall@5 0.9333 unchanged; value is graph hygiene + a reranker substrate, not lexical rank movement
- h2 — DISCONFIRMED — both arms; recall@5 0.9333 → 0.6000 / 0.6667; topical similarity cannot express absence; lexical ordering carries real fact-level signal
- h3a — DISCONFIRMED — the pure-rerank line closes: semantics can reorder the frozen lexical candidate set only by overriding the lexical evidence that makes the baseline good
- h3b — SPLIT — rule L DISCONFIRMED as specified (false negatives b1/b3/e1); L2 CONFIRMED (f1+f3 suppressed, zero false negatives, zero A–E suppression)
- h4 — DISCONFIRMED (v0 as specified) — safe but not selective: orphan-link precision 0.6071, edge precision 0.3636; DC2/DC4/DC5 hold; infrastructure stays in the tree behind its gates
- h5 — CONFIRMED — within the pre-registered boundary: D1–D6 none triggered; 42/42 checks; 4/4 controls; erasure L1+L2 (L3 not claimed)
- h6a — CONFIRMED — within the documented envelope: 6/6 legs; stage p95 0.040 ms vs the 100 ms budget; ships as HARNESS_KB_HONESTY, opt-in, default OFF
- h6b — CONFIRMED — within the pre-registered boundary: 0 blocking false positives over 133 candidates; 7.7 ms per admission check; relearn re-admits
- h6c — DISCONFIRMED overall — edge arm works (P 0.80 / R 1.0); the model-free orphan ceiling (≈ 0.60 at high recall) holds; the line is dormant until a model-based stance check is authorized
- v2-node4 — OPEN / NOT_QUALIFIED — the 16-case gate remains exit 1; the naive overlap-window arm was rejected at +21.17% tokens (38,970 vs 32,162)

### 7.2 Component map as-built (against §2)

- **Spine (§2.1)** — SHIPPED, beyond what was planned. The workgraph remains
  the only completion authority, now with: the six-tier eval pipeline with
  hash-bound, verifiable receipts (`plan/v3-eval-pipeline.md` 18/18); the
  tamper guard ENFORCING as the first push-tier command (net test reduction
  blocked; every accepted test-surface diff carries a sha256-bound
  attestation, 87 entries at this writing); gate records carrying whole-output
  signatures; and settlement hooks (`plan/v3-settlement-plugin-loop.md`): an
  action is not done until its settlement receipt closes — exit-0 note +
  node record + re-derived gate signature, fail-closed, opt-in via
  `pipeline.py --settle`. Gap that stands: prompt-prefix stability is still
  unmeasured.
- **Memory: consolidation (§2.2.1, H1)** — CONFIRMED as amended. The pass
  shipped as graph hygiene (13 supersedes edges, orphan integration
  candidates, MEMORY.md byte-identical) and as a reranker substrate; the
  lexical rank movement it was designed for did not materialize (recall@5
  unchanged). Verdict: `docs/v3/outcome-table-20261111.md` row h1.
- **Memory: learned ranking (§2.2.2, H2/H3)** — LINE CLOSED as specified.
  H2 disconfirmed on both arms; H3a disconfirmed (the dominance trilemma is
  pre-registered-prediction-exact); H3b split — rule L disconfirmed, rule L2
  confirmed once on the frozen 18. No learned reranker and no score cache
  ship. What ships instead is L2, productionized as track h6a: the
  lexical-evidence honesty rule behind `HARNESS_KB_HONESTY`, opt-in, default
  OFF, flag-off byte-identical. The gap list shrinks by closure, not by
  build.
- **Memory: unlearning (§2.2.3; draft "H4", executed as h5)** — CONFIRMED
  within the pre-registered boundary: certified unlearning with the
  hash-chained tombstone ledger; 8/8 probes zero live occurrences; 17/17
  non-target queries exactly unchanged. Plus h6b, a capability the draft did
  not contain: the write-time backflow guard derived from the ledger,
  CONFIRMED in boundary (0 blocking false positives over 133 candidates).
- **Memory: deferred RL (§2.2.4, draft "H5")** — still deferred. Outcome
  records exist per gate run; the (query, candidates, chosen, outcome)
  dataset was not built. Gap stands; no fake learning shipped.
- **Dreaming (post-draft track)** — h4 DISCONFIRMED v0 (safe but not
  selective; agreement-blindness is the measured boundary) and h6c
  DISCONFIRMED overall (edge-arm fixes work; the model-free orphan ceiling
  holds). The line is dormant until a model-based stance check is
  authorized — that authorization is an owner decision (bridge DQ4).
- **Orchestration (§2.3)** — NOT built as designed: no evaluator context
  separation mechanism, no serializable mid-node run state, no ephemeral
  worktrees. Adjacent mechanisms shipped instead: settlement hooks (work
  settlement auditable after the fact), the plugin admission loop
  (capability intake), and the pipeline as the local CI. The §2.3 gaps
  stand.
- **Decision layer (§2.4)** — SHIPPED as the record substrate, ahead of the
  phase boundary: `harness.jev-decision/v1` (typed choice/score/boolean
  verdicts with confidence; execute-above/escalate-below recorded as policy
  data; fail-closed — missing authority, unbound inputs, out-of-enum
  verdicts all refuse; UNKNOWN is never zero; promotion always NOT_GRANTED)
  and `harness.rea-record/v1` (the five dependency decision types), with the
  admission loop consuming both (domain=adoption). The policy ENGINE on
  `routing.next_decision` is deferred to v1; no model fills decisions until
  calibration is locally measured. Verdict:
  `docs/v3/jev-needle-v0-verdict-20261111.md`.
- **Tools and skills (§2.5)** — the intake valve shipped: no external
  capability is repo-resident without an REA qualification record and a JEV
  adoption decision (`docs/v3/plugin-registry-20261111.json`; first entry
  `lever-experiment-contract-pattern`, admitted with full receipts). The
  docs↔evidence freshness gap closes with THIS slice's consistency gate
  (`.harness-work/v3-docs-sync/check_docs_sync.py`, re-runnable,
  fail-closed). Gap that stands: AGENTS.md is a cap, not a maintained TOC.
- **Eval hygiene (§2.6)** — SHIPPED. Tamper guard enforcing in the push
  tier (the inert `check_guard` posture is superseded by
  `scripts/tamper_guard.py` + the attestation registry); hash-bound pipeline
  receipts with `verify`; secret-scan in push; the settlement scan opt-in;
  mutation controls ran both directions in every hypothesis track. Gaps that
  stand: no systematic trajectory audit; no per-model-upgrade stress-test
  cadence.

### 7.3 Phased roadmap as-built (against §4)

- **Phase 1 (v3.0)** — DONE. H1 confirmed as amended; the tamper guard is
  enforcing (via the eval-pipeline workstream, not the inert check_guard).
  The formalized per-task JSON status and start-of-session ritual items were
  not adopted as separate artifacts; the hash-bound pipeline receipt
  formalizes run status instead.
- **Phase 2 (v3.1)** — CLOSED by disconfirmation. No learned ranking ships;
  the L2 lexical-evidence honesty rule ships opt-in instead (h6a).
- **Phase 3 (v3.2)** — NOT built. Orchestration separation remains
  designed-only; the shipped adjacents are settlement hooks, the admission
  loop, and the pipeline.
- **Phase 4 (v3.3)** — BOTH halves shipped early: unlearning (h5 confirmed)
  and the decision record substrate (JEV/REA). The routing policy engine
  defers to v1.
- **Phase 5 (v3.x)** — partially. dev9 deploy staged 11/11, install fenced
  behind one owner command (the recording-hygiene fix it ships retires the
  gate-record path-leak that the settlement checker's inverse-redaction mode
  works around). The docs-drift consistency gate ships with this slice.
  Ephemeral worktrees, AGENTS.md-as-TOC, and the per-model-upgrade stress
  cadence were not shipped.

### 7.4 What the draft got right and wrong

Right: the inherited principles (§1) held through every workstream —
gate-first, fail-closed, plain records, promotion only through gates,
verifier outside the writable surface. The "v3 is that measurement program"
framing proved itself: H2/H3 closing the learned-ranking line IS the program
working as intended. Wrong or aged: the draft assumed learned reranking was
the ranking future (disconfirmed); it did not foresee the dreaming line's
model-free orphan ceiling; it contained no settlement or capability-admission
mechanism (both arrived via sweep 3); unlearning landed a phase early.
