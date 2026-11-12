# H6c dreaming v1 — contract

2026-11-10. Frozen BEFORE any v1 scoring run, per plan/v3-h6c-dreaming-v1 node 6.
Bindings (sha256): H1 freeze e55ccdc2… / corpus af6af281… / baseline 286a988c… /
H1 apply receipt d2726339… / H4 labels 4ac7032f… / H4 apply receipt b9711f6d… /
H4 scored-candidates receipt + dominance analysis
(.harness-work/v3-h6c-dreaming-v1/dominance-analysis-20261110.json, node 5).
MODEL-FREE ONLY: zero model/native calls, zero network; live corpus read-only;
all runs on frozen-corpus copies. v0 module bytes untouched — v1 is a new module
(src/agent_harness/memory_dreaming_v1.py) importing v0 machinery.

## 1. What changes vs v0 (the H4 verdict's follow-ups #1, #2, #4)

Edge arm (supersedes_edge):
- s_ctx is replaced by literal-local, idf-weighted windows (v0's paragraph-level
  s_ctx was agreement-blind — 20 shared tokens on the worst FP).
- A two-sided stance/negation signal is added: the successor must carry
  correction language near the correction marker; the superseded page must NOT
  carry correction language near the literal (already-corrected = agreement).
- s_auth becomes log-scaled.

Orphan arm (orphan_inbound_link):
- s_lex is recalibrated to BM25-style idf (v0's raw log(N/df) saturated at
  N=133: 4–9 moderately generic tokens maxed it).
- s_auth becomes log-scaled (v0 gave hub sources a flat +0.20).
- s_clust, s_sub, and all four weights are UNCHANGED.

Trigger model, phase scoping (Light/REM/Deep), PhaseGuard write surfaces
(deep-only orphan-link appends on memory/*.md, never MEMORY.md, never
archive/), supersedes-edges-to-ledger-only, dry-run default, and fail-closed
posture are UNCHANGED from v0 (they all held; the failure was scoring).

## 2. v1 formulas (exact)

Tokenization note: mc._tokens drops stopwords ('not', 'no', 'never', 'only',
'was' are stopwords) — so stance is matched on RAW lowercase words, context
overlap on content tokens.

- raw_words(text) = [m.group(0).lower() for m in re.finditer(r'\w+', text)]
- literal_windows(text, L, k=8): every position where raw_words(L) occurs as a
  contiguous span; the window is the ≤k raw words immediately before plus the
  ≤k immediately after the span (the literal span itself is excluded).
- content(window) = {w in window : w not in mc._STOP and len(w) > 2}
- BM25 idf: idf1(t) = log(1 + (N − df(t) + 0.5) / (df(t) + 0.5)), N = page count
  (133 for the frozen corpus; computed, not hard-coded).
- s_auth_log(page) = log(1 + indegree(stem)) / log(1 + max_indegree);
  max_indegree = 20 on the frozen corpus (computed from the wikilink graph by
  the node-5 analysis, not hard-coded).

Edge arm:
- s_scope: unchanged from v0 — min(1, (|strong| + |shared|/4) / 3).
- s_ctx_local = min(1, max over strong literals L and over all window pairs
  (wA in A-windows(L), wB in B-windows(L)) of Σ_{t in content(wA) ∩ content(wB)}
  idf1(t) / CTX_SAT_V1), CTX_SAT_V1 = 6.0. (Reasoning: two rare tokens df≤4
  contribute ≈ 3.9 each; three df≈10 tokens ≈ 7.8; generic pairs like
  {live, data} or {sudo} contribute ≈ 2–3.8 and must NOT pass alone.)
- s_stance_net = 1 iff stanceA AND NOT stanceB, else 0, where
  stanceA: ≥1 STANCE_LEXICON word occurs in the successor's marker paragraph
  (the paragraph located via fact_scope.marker_excerpt, same locator as v0;
  paragraph scope, because verified correction language can sit >8 words from
  the literal while remaining the same correction statement);
  stanceB: ≥1 STANCE_LEXICON word occurs in ANY superseded-side ±8 window of
  any strong literal.
- STANCE_LEXICON (frozen): wrong, corrects, corrected, superseded, supersedes,
  stale, retracted, retracts, suspect, unverified, broken, misleading,
  outdated, garbage, invalid, mistake, beware, fixed. Exact raw-word match,
  lowercase.
- s_date: unchanged from v0.
- composite: score_v1 = 0.30·s_scope + 0.30·s_ctx_local + 0.10·s_date
  + 0.10·s_auth_log + 0.20·s_stance_net.

Orphan arm:
- s_lex_v1 = min(1, Σ_{t in shared} idf1(t) / LEX_SAT_V1), LEX_SAT_V1 = 8.0.
  (Reasoning: 4 df=2 tokens ≈ 15.9 saturate; 4 df≈10 tokens ≈ 10.4 pass;
  4 df≈40 tokens ≈ 4.8 → 0.60; 4 df≈80 tokens ≈ 2.0 → 0.26 — the bar requires
  genuinely distinctive shared vocabulary.)
- s_auth_v1 = s_auth_log(source). s_clust, s_sub unchanged.
- composite: score_v1 = 0.45·s_lex_v1 + 0.25·s_clust + 0.20·s_auth_v1
  + 0.10·s_sub (v0 weights unchanged).

## 3. v1 gates (ALL required; OpenClaw posture, unchanged structure)

Edges: G-StrongLit ≥ 1 strong (non-dotted-suffix) matched literal;
G-CtxLocal s_ctx_local ≥ 0.5 (i.e. best window-pair idf mass ≥ 3.0);
G-StanceA = 1; G-StanceB = 0; G-Score ≥ 0.55.
Orphans: G-Support |shared| ≥ 4; G-Lex s_lex_v1 ≥ 0.35; G-Score ≥ 0.55.
Promotion surfaces and trigger: unchanged from v0. gate_overrides (test/mutation
hook) may lower any threshold and are receipted loudly, as in v0.

## 4. Dominance pre-analysis findings (node 5 artifact; v0 scores × frozen labels)

- Orphan arm: 19 distinct v0 thresholds reach P ≥ 0.80, but the MAXIMUM recall
  among them is 0.4878 (best point P=0.941 at R=0.390). Re-thresholding v0
  cannot reach P ≥ 0.80 at R ≥ 0.50 — v1 must improve the ranking itself.
- Edge arm: the v0 envelope ceiling at full recall is 0.3636; every threshold
  above 0.88 promotes only false edges. v0's edge ranking is anti-correlated at
  the top — new signals are required, not new cut-points.

## 5. Pre-registered expectations (predictions, not gates)

- P1 edge arm: v1 P ∈ [0.67, 1.00], R ∈ [0.50, 1.00]. Mechanistic expectation
  from the verified window mechanics: the four v0 FPs with zero window overlap
  die on G-CtxLocal; the generic-overlap FPs (sudo / live-data) die on idf
  mass; the predicted residual FP is tenancy→config (agreement restatement:
  high-idf overlap {network, passed, vacuously, while} plus stanceA present —
  the agreement case the H4 verdict flagged as the model-free boundary); the
  predicted recall risk is 10g→remote-machine (single moderate token {linked},
  mass near the G-CtxLocal bar).
- P2 orphan arm: v1 P ∈ [0.65, 0.85] at the fixed 0.55 gate, R ∈ [0.50, 0.83].
  The envelope (§4) says P ≥ 0.80 at R ≥ 0.50 requires a strictly better
  ranking than v0's; BM25-idf demotes generic-vocabulary FPs and log-auth
  demotes hub-source FPs, but neither adds information — sharpening, not
  re-ordering, is the realistic hope.
- P3 invariants + retrieval: hold unchanged (v1 writes through the same
  PhaseGuard surface; retrieval queries do not touch promoted links' targets).
- P4 ceiling clause: if edge-arm v1 P lands in [0.36, 0.60], the model-free
  ceiling predicted by H4 is confirmed.

## 6. Disconfirmation criteria (measured against the frozen labels; derived and
REPORTED by check_h6c.py, never asserted)

- DC1: orphan-link v1 precision < 0.80, OR improvement over v0's 0.6071 < 0.10.
- DC2: orphan-link v1 recall < 0.50.
- DC3: supersedes-edge v1 precision < 0.75 OR recall < 0.75.
- DC4: any invariant violation (fact loss — every input page hash live in the
  output or in a receipted mutation chain terminating live on disk; MEMORY.md
  byte-identical; freeze binding; dry-run purity; promotion only on a fired
  trigger; archive-never-delete).
- DC5: retrieval regression on the 18-query harness under the amended H1 rules.
- DC6 (dormancy clause, recorded either way): edge-arm v1 precision in
  [0.36, 0.60] ⇒ the model-free ceiling holds; the dreaming line goes dormant
  until a model-based stance check is explicitly authorized.

H6c is CONFIRMED iff DC1–DC5 all hold; DISCONFIRMED per criterion otherwise.
DC6 is diagnostic and is recorded in the verdict either way.

## 7. Epistemic status (recorded honestly, pre-run)

The edge-arm signal DESIGN was informed by the frozen H4 FP evidence and the
frozen label rationales (adjudicated blind to scores in H4); with n=13 edges
(4 true) the edge arm is a mechanism test on the corpus that motivated the
fixes, not a generalization proof. The orphan arm is cleaner: no orphan page
bytes were inspected for v1 design — the changes are re-scalings of existing
signals, and the dominance analysis used only frozen v0 scores × frozen labels.
No v1 score was computed on any labelled candidate before this contract froze;
the eval runs once per arm and reports whatever it shows, including dormancy.

## 8. Amendment 1 (2026-11-10, additive, post-implementation pre-eval)

Recorded after the node-7 implementation, BEFORE any v1 scoring run on the
labelled candidate set (the eval has not run):

1. _content is implemented as exact mc._tokens parity (delegation, not a
   re-implementation), because the corpus token regex
   [A-Za-z0-9][A-Za-z0-9_.-]{1,} keeps hyphenated compounds whole. Window
   POSITIONS remain in the raw \w+ stream; overlap membership re-tokenizes.
2. G-StanceA is structurally near-vacuous on H1-generated candidates: H1 only
   proposes supersedes edges from paragraphs matching MARKER_CORRECTION
   (supersed*/corrects/corrected/correction/retract*/was wrong/were wrong/
   replaced by/replaces the/no longer true), and that vocabulary overlaps the
   frozen STANCE_LEXICON. The gate is kept as defense-in-depth (a wider future
   candidate generator would need it) and its bite is proven by the node-9
   mutation control on synthetic candidates whose marker matches
   MARKER_CORRECTION via 'correction' alone (not a stance-lexicon word).
   The discriminative work on this corpus is done by G-CtxLocal and G-StanceB.
3. Refined expectation (within the already-registered P1 range): with
   G-StanceA near-vacuous and G-StanceB measured absent on all 13 frozen
   candidates' superseded-side windows, the edge arm's outcome hinges on the
   G-CtxLocal idf masses — the predicted FP survivor remains tenancy→config
   (agreement restatement) and the predicted recall risk remains
   10g→remote-machine ({linked} alone, mass near the bar); polymarket's
   generic {live, data} overlap sits closest to the G-CtxLocal bar among the
   FPs. All thresholds and formulas remain exactly as frozen in §2–§3.
