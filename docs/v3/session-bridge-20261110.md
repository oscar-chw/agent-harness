# Cross-session bridge — Kimi Work harness session, 2026-11-10

Purpose: the system is centralized. This record lets Codex/Claude sessions see what the
Kimi Work session did on 2026-11-10, where the evidence lives, and what decisions are open.
Everything listed is in this repo (docs/, plan/, .harness-work/) or in the harness memory
store (tags: agent-harness, v3). Conventions unchanged: /usr/bin/python3 for pytest gates,
no commits without owner request, additive receipts only, live memory corpus read-only.

## v2-completion: 51/56 — node 4 TERMINAL, owner decision needed for 5–8

- Node 42 done (request-identity guards fail-closed at both boundaries; tests/test_procedure_execution.py, 13 tests; gate 71/71).
- Node 56 verified green (stale last-fail cleared, 69/69).
- Node 4 campaign — three acts, all evidence under `.harness-work/v2-completion/matched-usage-20261110/`:
  1. v1 measurement (9 attempts / 8 model-reaching): candidate 124,536 vs base 113,681 → +9.55%;
     nonregression holds; gate gap: `comparison: aggregate tokens exceed baseline`.
  2. Token decomposition (zero calls): excess is ~105% AMBIENT CONFOUND — the CLI skills snapshot
     flip-flopped 14,717↔38,794 chars mid-campaign (sequence A A B A A B B B). Controlled component:
     candidate −306 tokens (−0.27%) — no real regression. See token-decomposition-20261110.md.
  3. v2 ambient-pinned re-run (freeze v4): ABORTED fail-closed at call 3 — the ambient variant is
     not stable even across 72 s back-to-back identical invocations and no CLI flag pins it.
     11/16 model-reaching calls used; remaining 5 slots frozen unspent (amendment-2 forbids
     replacement calls after an ambient abort).
- Standing state: `retrieval-results.json` carries measurement_v1 labeled CONFOUNDED + v2 abort
  annotation; v1 fields untouched; refs rebound to freeze v4.
- OWNER DECISION (nodes 5–8 chain behind 4):
  (a) accept the annotated confounded measurement and re-derive node 4's gate semantics around it;
  (b) leave 4 red / 5–8 blocked, treat the measurement as the v3-justifying evidence it was
      designed to be, and move on;
  (c) re-measure in future if the ambient becomes pinnable.

## v3 hypotheses (the loop: hypothesis → research → analysis → plan → experiment → eval)

- H1 memory consolidation v0 — COMPLETE, 9/9 gated (plan/v3-h1-consolidation.md).
  Freeze 133 pages (sha af6af281…), baseline recall@5 0.933 / MRR 0.819; consolidation:
  13 supersedes edges, 83 orphan-link proposals, MEMORY.md untouched; eval delta ≈ 0 —
  lexical-improvement DISCONFIRMED, value = graph hygiene + reranker substrate;
  5/5 mutation controls both directions. Artifacts: `.harness-work/v3-h1-consolidation/`.
- H2 pure semantic rerank — COMPLETE, 9/9 gated, DISCONFIRMED (plan/v3-h2-reranking.md).
  b1 recovered 9→5 but A/D collapse (lexical signal discarded); F traps invisible to similarity;
  recommendation: do NOT integrate. Verdict doc: docs/v3/h2-reranking-verdict-20261110.md.
- H3 hybrid (lexical-primary + bounded semantic boost + F lexical-evidence rule) —
  PAUSED BY OWNER mid-node-7 (nodes 1–6 gated). Preserved analysis: dominance trilemma
  (any band δ ≥ 0.11 recovering b1 chains a1/d1 into collapse; any additive w > 6.3 is
  semantic-dominant = H2's failure mode); rule L (evidence rule) observed over-firing on
  answerable queries in the partial eval. Resume only on owner request.
- Eval pipeline workstream — STARTED 2026-11-10 (plan/v3-eval-pipeline.md): owner directive
  that evaluation was never unified (unit → integration → e2e → perf → ship/CI-CD + coding
  standards). Survey + design + local-first runner skeleton; no hosted CI wiring.

## Knowledge graph

Session findings were persisted to the harness memory store (mem_add, scope user,
tags agent-harness/v3/…): sweeps 1–3, corpus recon, node-4 measurement + root cause,
tamper-guard qualification, H1 outcome, H2 verdict (by the H2 agent), campaign terminal.
