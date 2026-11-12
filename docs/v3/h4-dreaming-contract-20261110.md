# H4 dreaming — contract (pre-registered)

2026-11-10. plan/v3-h4-dreaming node 5. Written BEFORE any H4 gated run; every
threshold and criterion below is frozen here. Amendments, if any, are additive
and must cite pre-eval evidence only (H1 amendment precedent). Zero model calls,
zero network; live memory corpus strictly read-only.

H4 is the dreaming CONTROL LOOP over H1's consolidation MECHANISM
(src/agent_harness/memory_consolidate.py). H1 answers "what can be proposed";
H4 answers "when does the pass run, how are proposals scored, and what gets
promoted" — modeled on OpenClaw's dreaming gates (docs/v3/oss-mechanics
-20261110.md), adapted model-free per local-first constraints.

## 1. Phases and phase-scoped write surfaces (OpenClaw Light/REM/Deep)

| phase | does | may write |
|---|---|---|
| Light | runs the H1 mechanism on a corpus COPY; stages the raw candidate set | `staged-candidates` receipt under the dreaming work dir only |
| REM | scores and ranks every candidate; records promote-explain evidence | `scored-candidates` receipt only |
| Deep | gates and promotes | (a) orphan-link appends into the CORPUS COPY (source pages only, never MEMORY.md, never archive/), (b) review-ledger files under the work dir |

A PhaseGuard mediates every write and refuses out-of-scope writes fail-closed.
Refusals are receipted. Dry-run is the default: no bytes move, all decisions
receipted. Apply requires an explicit dst ≠ src.

## 2. Trigger model (when a dream runs)

State: `{sessions_since_last_dream, pages_changed_since_last_dream,
last_dream_session}`. Deterministic rule, receipted either way:

- BOOTSTRAP: no prior dream recorded → triggered (first dream over the corpus).
- SESSIONS: sessions_since_last_dream ≥ 5 → triggered.
- CHURN: pages_changed_since_last_dream ≥ 10 → triggered.
- Otherwise NOT triggered: Deep refuses (fail-closed); Light/REM may run as a
  survey (receipt-only).
- Cooldown: a second Deep run with the same session stamp is a no-op.

## 3. Candidate scoring (model-free analogues of OpenClaw's Deep score)

OpenClaw: score = 0.30 relevance / 0.24 frequency / 0.15 query diversity /
0.15 recency / 0.10 consolidation / 0.06 concept richness; promote iff ALL of
minScore 0.8, minRecallCount 3, minUniqueQueries 3. Their features need
retrieval telemetry + LLM judgments; this corpus has neither (uses counters are
index-side, survey 2026-11-10). Substitutes, all computed from frozen bytes +
the wikilink graph (idf(t) = ln(N / df(t)), N = 133 pages, H1 tokenization):

### 3.1 orphan_inbound_link (source S → orphan O, shared distinctive tokens T)

- s_lex   = min(1, Σ_{t∈T} idf(t) / 14.0)        — lexical support mass (≈ relevance)
- s_clust = 1 if any t∈T is itself a page stem (link-cluster membership,
          ≈ query diversity: independent pages referencing the same
          neighbourhood), else 0
- s_auth  = min(1, indegree(S) / 10)             — integrating page's authority
- s_sub   = min(1, bytes(O) / 2000)              — orphan substance
- score   = 0.45·s_lex + 0.25·s_clust + 0.20·s_auth + 0.10·s_sub

Gates, ALL required (OpenClaw all-three-gates posture):
- G-Support: |T| ≥ 4          (≈ minRecallCount 3, one notch stricter than H1's 3)
- G-Lex:     s_lex ≥ 0.35     (real idf mass — generic-vocabulary matches die here)
- G-Score:   score ≥ 0.55

Promotion writes the [[O]] append on S in the corpus copy (H1's apply shape).

### 3.2 supersedes_edge (successor A → superseded B, H1 fact_scope)

- strong literals Ls = matched literals that are not bare dotted suffixes
  (H1's _WEAK_LITERAL rule)
- s_scope = min(1, (|Ls| + |shared_tokens| / 4) / 3)
- s_ctx   = min(1, best_ctx / 4), where best_ctx = max over l∈Ls of |Wa ∩ Wb|,
  Wa = content tokens of A's marker paragraph, Wb = content tokens of B's
  literal-bearing paragraph(s) carrying l (context agreement ≈ relevance of the
  correction to B's actual claim)
- s_date  = min(1, (a_date − b_date).days / 14)  — minor term; H1 showed
  recency alone is the failure mode
- s_auth  = min(1, indegree(A) / 10)
- score   = 0.35·s_scope + 0.30·s_ctx + 0.20·s_date + 0.15·s_auth

Gates, ALL required:
- G-StrongLit: |Ls| ≥ 1
- G-Ctx:       s_ctx ≥ 0.5 (≥2 shared content tokens between the paragraphs)
- G-Score:     score ≥ 0.55

Promotion writes the edge to the review ledger only (receipt-level; the corpus
keeps both pages — H1's fact-scoped retention). conflict_flags and
undirected version_candidates are carried to the ledger as review-only records,
never promoted.

## 4. Hygiene metrics (before = frozen corpus; after = promoted-apply copy)

- orphan rate: orphans / 133 (baseline 34/133; 31 orphans received proposals,
  3 never did: quant-reference-books, user-is-the-admin,
  vscode-watcher-exclude-plain-paths)
- in-degree distribution histogram (0 / 1–2 / 3–4 / ≥5) before vs after
- supersedes coverage: promoted edges vs the frozen adjudicated true set
- ledger sizes (promoted vs review-only records)

## 5. Ground truth (frozen in the node-5 inputs artifact, hash-bound)

Every one of the 13 supersedes edges and 83 orphan proposals in the H1 apply
receipt carries a true/false label adjudicated from actual page bytes (marker
paragraphs, literal contexts, page subjects) BEFORE any score was computed.
Label semantics: TRUE = the link/edge is warranted — same system, incident,
project or a direct doctrine↔instance relation (this corpus's own linking
habit); FALSE = coincidental/generic token overlap across unrelated subjects.
The labels define the apply-all baseline precision (what H1 did: promote
everything) and the dreaming gate's precision/recall.

## 6. Pre-registered predictions (design analysis over candidate evidence)

Recorded before the gated run, honestly, so the eval can confirm OR refute:

- P1: orphan gates promote roughly 35–50 of 83 proposals; promoted precision
  lands 0.75–0.90 vs apply-all ≈ 0.49 — the 0.80 bar is reachable but not
  trivially; orphans integrated ≈ 15–23 of 34 (8 proposed orphans carry only
  FALSE proposals; 3 were never proposed — 23 is the perfect-gate ceiling).
- P2: edge gates kill the two `.08` dotted-suffix edges at G-StrongLit and the
  coincidental-numeric edges at G-Ctx; the known hard cases are
  baidu→igsl-18-storage (install provenance vs speed correction — scope
  mismatch) and igsl-tenancy→config-declares-kernel-disagrees (the two pages
  AGREE; the correction does not refute the target). If those pass, edge
  precision degrades toward 0.67 and DC3 fires — agreement-vs-supersession is
  the predicted model-free boundary (stance detection needs a model).
- P3: retrieval ranks do not move (H1's amendment finding: the retriever ranks
  content, not graph); the dreaming value is hygiene + precision, not rank.

## 7. Disconfirmation criteria (the verdict keys)

- DC1: orphan-link promoted precision < 0.80, or beats apply-all precision by
  < 0.20 (same labels).
- DC2: promoted links integrate < 15 orphans.
- DC3: edge promoted precision < 0.75 or recall < 0.75 on the true set.
- DC4: any invariant violation — fact loss, MEMORY.md drift, freeze binding
  failure, dry-run writes bytes, promotion without a trigger, any
  archive/delete by H4.
- DC5: retrieval regression under the amended H1 rules (A/B/C/D non-regression,
  E holds, F not worse than baseline hit counts).

CONFIRMED iff no DC fires; otherwise DISCONFIRMED per criterion. Fail-closed:
an invariant violation also blocks the apply artifact from counting as output.
