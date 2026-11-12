# Bounded semantic/rerank experiment — paraphrased-source-recovery req:1

2026-11-10. DESIGN ONLY — no implementation, no downloads, no native calls yet.
Closes the last case-level gap of plan/v2-completion node 4; also serves as the
first concrete fixture for v3 hypothesis H2 (learned ranking cascade).

## Requirement being closed

paraphrased-source-recovery req:1: "...report a miss honestly and evaluate bounded
semantic/reranking only against frozen same-scope cases." Proof-criteria mapping:
O5 in source-recovery-proof-criteria-20261103.json, whose `must_not` forbids
claiming an unimplemented semantic route. Honored by implementing the arm as
experiment tooling under .harness-work/, NOT as a product retrieval path; any
product integration is a separate gated node.

## Capability probe (2026-11-10, this machine)

- No ollama; no sentence-transformers; no torch on any interpreter.
- numpy available in the managed runtime python3 only.
- HuggingFace cache holds generative models (Qwen3/Qwen2.5/SmolLM2/LFM2/OLMo) —
  unusable without torch; not embedding models anyway.

Decision: **static word-embedding arm (GloVe 6B.100d) + numpy mean-pooling cosine
rerank**, run under the managed python. Rejected: torch/sentence-transformers
install (~GBs, new runtime for the repo — against local-first leanness);
native/provider embeddings (needs authorization, costs tokens, and the point is a
LOCAL bounded arm). Honest limits to record: static non-contextual embeddings,
English-centric, weak on code/CJK — a lower bound on semantic retrieval, which is
the correct conservative shape for this gate.

## Frozen same-scope cases

Reuse `.harness-work/retrieval/real-controls/` (freeze.json, freeze-status-r2.json,
fixtures-status-r2/): the paraphrase probes with known source documents where the
lexical arm honestly missed, plus previously-passing cases and negative controls
(query whose source is absent → both arms MUST still report miss).
Freeze extension: hash-bind the exact query list + expected source IDs + corpus
snapshot into `.harness-work/v2-completion/paraphrase-semantic-freeze-20261110.json`
before any run. No query or corpus edits after freeze.

## Arms

- **A0 (baseline):** current lexical path (vault_retrieval/kb BM25) as-is.
- **A1 (candidate):** A0's top-20 candidates reranked by cosine between mean-pooled
  GloVe vectors of query and candidate text. If the expected source is not in
  A0's candidate set at all, a bounded full-corpus A1 scan is run and RECORDED
  separately (candidate-set recall vs rerank quality must not be conflated).

## Gate criteria (script exits 0 only if ALL hold)

1. Freeze verified (hashes match).
2. Non-regression: every case A0 previously passed still passes under A1.
3. Recovery: the known lexical-miss paraphrase cases recover the correct source
   within top-5 (report per-case; all must recover for PASS).
4. Honest miss: every negative control still reports miss under both arms.
5. Evidence: all outputs hash-bound; usage ledger records zero model tokens,
   wall time, interpreter + numpy versions, GloVe file sha256.

## Validity controls

- Shuffled-vector control: same pipeline with permuted embedding weights must
  FAIL the recovery criterion (proves the metric responds to the embeddings).
- Lexical-strong control: a case where A0 already ranks #1 must stay #1 under A1
  (rerank must not demote exact evidence).
- Duplicate-text control: a near-duplicate of a source must not displace the
  true source's rank.

## Risks / downstream

- Static embeddings may under-recover CJK or code-heavy paraphrases; such a
  failure is a VALID negative result (keep honest miss, report limit) — it does
  not block the gate if it is outside the frozen same-scope case set.
- A PASS feeds: (a) node-4 re-adjudication of paraphrased-source-recovery req:1,
  (b) v3 H2 as the frozen fixture + baseline for the learned-ranking cascade.
- Token economics: zero native calls; the later comparison-level matched campaign
  (node 4 comparison gaps) remains a separately authorized slice.

Next slice: freeze script + GloVe acquisition with sha256 pinning, then arm
implementation, then gate run + re-adjudication.
