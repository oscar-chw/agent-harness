# v3 research sweep 1 — memory that learns, consolidates and forgets

2026-11-10. Research + analysis stage of the v3 loop. Sources are dated arXiv/vendor
primary hits from this turn's sweep; nothing here is implemented or qualified yet.
Constraints carried from v2: local-first, no paid API, no new runtime, plain
versioned records with hash evidence, gates before promotion. We do not own model
weights, so parameter-level unlearning is out of scope; memory-pathway only.

## What the field converged on (and who)

**Dreaming / asynchronous consolidation is now an industry pattern, not a novelty.**
Anthropic ships a "Dreaming" feature for Claude agents (offline consolidation
between sessions; community-named, not official docs). Letta's sleep-time compute
(2025) runs background agents that reorganize memory during idle time. Google
Vertex AI Memory Bank and Amazon Bedrock AgentCore Memory do async background
extraction. OpenClaw keeps a DREAMS.md with scored promotion from short-term to
long-term memory. arXiv 2604.12034, 2604.14228, 2603.17244.

**The differentiator is consolidation SAFETY, not consolidation itself.**
arXiv 2603.17244 (graph-native cognitive memory): published-item protection,
circuit breakers, dry-run validation, cursor-based resumption, auditable reports —
claimed absent from prior systems. This matches our gate philosophy directly.

**Learned re-ranking beats both pure similarity and naive LLM reranking.**
- AgentMemRec (2610.34673): recommender-style candidate generation + ranking
  cascade, ZERO LLM calls at selection, beats an LLM reranker (80.7 vs 79.8 on
  LongMemEval-S). Retrieval as recommendation, not search.
- EARM (2608.22767): experience-amortized reranking — store past LLM relevance
  scores in an online matrix, complete it causally, only 17.5% of candidates need
  fresh LLM scores, +6.62% over semantic retrieval. Retrieval experience is itself
  a memory.
- PPRO (2607.00017): user profile as explicit ranking prior + GRPO-trained query
  rewriter; retrieval quality AND answer quality as reward.
- MemRL / Memory-R1 / Memento: Q-values or learned policies over memory items.

**Unlearning is now an agent-level problem with a real formulation.**
- SBU (2602.17692): dual-pathway (memory + parameter) unlearning; memory pathway
  = blocklist + dependency closure with reference counting + hash-chained
  tamper-evident log. "Backflow": deleted memory gets regenerated and re-stored.
- AUBench (2610.17659): unlearning benchmark across three channels — parameters,
  persistent memory, tool-call reacquisition.
- DREAM (2610.13267): selective forgetting of POISONED memories via activation
  diagnostics + progressive attenuation with reconsolidation of benign knowledge.

**Self-modification with regression avoidance as a constraint.**
RELAI-VCL (2607.14004): on Terminal-Bench 2.0, checks proposed harness updates
DURING the search, not after; notes mem0/Letta/Karpathy-wiki/Anthropic-Dreaming/
Hermes/MetaClaw all check updates only post-hoc, if at all.

**Also noted:** EngramRAG (2609.32049) — retention half-life scaled by topological
load-bearing weight instead of wall-clock recency (answers "everything just
accumulates"); SUPERSEDES DAG for fact mutation; MemDream (2609.34545) —
Dreamer/Analyst/Consolidator dream cycle with a GRPO policy choosing repair ops;
ChronoMem (2607.27773) — version control + semantic rollback for memory, closest
to our existing hash-bound records.

## Hypotheses for v3 (each with disconfirmation)

- **H1 (consolidation):** a local, model-free-first dreaming pass — dedup,
  SUPERSEDES edges, conflict detection, decay by reference/load-bearing count —
  improves retrieval precision on OUR plan/memory corpus vs current accumulation.
  Disconfirm: no precision gain on frozen replay cases at equal token budget.
- **H2 (learned ranking):** a cascade (cheap lexical/structural candidates ->
  learned reranker using stored outcome signals: gate pass/fail, reuse counts,
  correction events) beats current scoped retrieval on the existing 16-case
  retrieval gate. Disconfirm: node-4 cases do not improve, or added latency >
  current p50 materially.
- **H3 (amortized scoring):** caching query-memory relevance scores (EARM-style)
  cuts repeat-retrieval cost without accuracy loss. Disconfirm: accuracy drop on
  held-out replay beyond noise.
- **H4 (unlearning):** blocklist + dependency-closure deletion over our
  Markdown/SQLite memory (with hash-chained log) can remove a fact AND its
  derived artifacts with zero retrieval hits after deletion, retained facts
  untouched. Disconfirm: any backflow through plans/summaries in probe eval.
- **H5 (RL policy):** GRPO-style learning over repair/ranking decisions is
  feasible locally. Disconfirm (likely near-term): no local training budget ->
  fall back to logged preference data + offline evaluation; do NOT fake it.

## Adaptation map (where each plugs in)

- H1 -> new `memory_consolidate` pass over existing memory store; dry-run +
  circuit breaker per 2603.17244; promotion only through existing gates.
- H2/H3 -> retrieval layer behind kb_search/mem_search; frozen eval =
  docs/v2 retrieval cases + node-4 gate corpus.
- H4 -> memory deletion protocol; audit log reuses our hash-chain conventions.
- H5 -> deferred data collection: log (query, candidates, chosen, outcome) from
  v2-completion campaign runs as training signal.

## Explicitly rejected this round

- Parameter-level unlearning / model fine-tuning: we own no weights.
- Adopting Mem0/Letta/OpenClaw as the memory core: replaces, not improves, our
  provenance model; borrow mechanisms only.
- Any always-on background LLM consolidation: cost unqualified; starts
  model-free, LLM assist opt-in behind a gate.

Next loop stage: plan — pick H1 as first experiment (cheapest, model-free,
directly attacks "everything accumulates"), define frozen eval corpus from
existing memory/plan records.
