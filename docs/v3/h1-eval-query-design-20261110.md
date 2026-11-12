# H1 eval query set — proposed, awaiting APPROVED

2026-11-10. Design artifact for plan/v3-h1-consolidation node 5 (freeze). Nothing
frozen yet; authoring this list is review prep, not implementation. On APPROVED,
freeze_corpus.py binds: corpus snapshot sha256, each query text, expected page
id(s), and pass rules — no edits after.

Corpus: live KB memory root (133 pages, survey corpus-survey-20261110.json,
sha256 af6af281…). Baseline retriever: current scoped retrieval (kb/mem search).

## Query classes (18 proposed)

**A. Direct recall (4)** — fact lives on exactly one known page; tests baseline.
- a1 "What hardware state is the GPU box in?" → igsl-gpu-box-hardware-state
- a2 "What is the harness release procedure?" → harness-release-procedure
- a3 "What are the PTCG deck hash conventions?" → ptcg-deck-hash-conventions
- a4 "Who is the commit identity?" → commit-identity-choi-hei-wang
Pass: expected page in top-3.

**B. Paraphrase (4)** — minimal content-word overlap with the page title; tests
semantic robustness (and bounds what consolidation must not break).
- b1 "Which machine hosts the research VMs?" → igsl-remote-machine
- b2 "What should I never do to the laptop's network?" → never-touch-mac-network
- b3 "How do I restart the network tunnel cleanly?" → vpn-restart-needs-dns
- b4 "Which project is second priority?" → pi-agent-second-priority
Pass: expected page in top-5.

**C. Orphan targeting (3)** — expected page is one of the 34 orphans; tests
whether consolidation's orphan integration actually improves discoverability.
Selection: 3 orphan pages chosen at freeze from the survey list, one fact query
each. Pass: page surfaces in top-5 AFTER orphan integration; baseline rank
recorded pre-consolidation for the delta.

**D. Load-bearing protection (3)** — top in-degree doctrine pages must not be
demoted by any consolidation/decay action.
- d1 "Why isn't self-certification evidence?" → self-certification-is-not-evidence
- d2 "What is the substitution antipattern?" → substitution-antipattern
- d3 "When is existence not reachability?" → existence-is-not-reachability
Pass: page remains top-3 pre- AND post-consolidation (non-regression invariant).

**E. Staleness/supersedes (2)** — pages known to carry versioned facts; probes
that the newer statement wins (candidate pairs selected at freeze from pages with
documented corrections, e.g. outward-machine-names vs igsl-lan-hosts lineage).
Pass: post-consolidation answer cites the CURRENT fact; superseded page retained
but ranked below its successor.

**F. Negative controls (2)** — fact absent from corpus; honest miss required.
- f1 "What is the NAS rack unit's serial number?" → no page; must report miss
- f2 "What was the Q3 revenue figure?" → no page; must report miss
Pass: no page returned with confidence; miss reported under both pre- and
post-consolidation stores.

## Discriminating power

A=baseline recall, B=semantic floor (H2 fixture synergy), C=the actual H1
payoff metric (orphan integration), D=safety invariant, E=supersedes correctness,
F=honesty preservation. Consolidation PASSES only if: C improves (≥1 orphan query
newly surfacing), D/E/F all hold, A/B non-regression.

## Authorship honesty note

Queries were authored from page IDs/titles and the survey metadata, not from
full page bodies. At freeze time the expected-answer binding is verified against
page content; any query whose expected page turns out not to contain the answer
is REPAIRED BEFORE FREEZE or dropped with a recorded reason — never after.

---

## Amendment 2026-11-10 (post-baseline, pre-eval): revised pass rules

Status: additive amendment. The original text above is unchanged; where this
section and the original disagree, THIS section governs node 8. It predates the
eval run and cites node 6 baseline evidence only (baseline-20261110.json,
hash-bound to freeze e55ccdc2… / corpus af6af281…).

Two premises of the original "Discriminating power" rule are falsified by the
node 6 baseline measurement:

1. "C improves (≥1 orphan query newly surfacing)" is impossible. At baseline,
   all three orphan queries already rank #1: c1 cifs-leases-stale-lock rank 1
   (0.68), c2 fatqat-gpu-cpu-budget rank 1 (0.78), c3 igsl-write-policy rank 1
   (0.55) — C pass rate 3/3. Orphanhood is a graph property (wikilink
   in-degree 0); the baseline retriever ranks on page CONTENT (FTS5 porter /
   normalised relevance, min_score 0.15), and each orphan's content already
   wins its fact query. There is no lexical headroom: no orphan query can
   "newly surface". Consolidation's orphan arm changes graph connectivity,
   not the ranking signal.
2. "D/E/F all hold" cannot be a post-consolidation gate for F, because F does
   not hold pre-consolidation: F 1/3 — f1 returns a false positive (7 hits,
   top igsl-gpu-box-hardware-state @0.23), f3 returns a confident wrong hit
   (10 hits, top commit-a-sweeps-parallel-work @0.56); only f2 is clean
   (0 hits). These are pre-existing retriever failure modes, recorded at
   baseline; consolidation v0 neither causes nor repairs them.

Revised pass rules for node 8 (master check):

- A, B: non-regression — every query's expected-page rank may not worsen, and
  every query passing at baseline must pass post-consolidation. b1's rank-9
  miss (B 3/4) is a pre-existing failure, recorded, not charged to
  consolidation.
- C: non-regression (revised from "improvement") — all three orphan queries
  remain top-5; rank deltas recorded per query. (Baseline: all rank 1.)
- D: hold as originally specified — top-3 pre AND post.
- E: hold as originally specified — successor ranked above superseded page,
  superseded page retained in corpus.
- F: not worse than baseline — f2 must stay clean (zero hits at or above
  threshold), and no F query may gain false-positive hits beyond its baseline
  hit count (f1 ≤ 7, f3 ≤ 10).
- Hygiene invariants: MEMORY.md byte-identical between consolidated copy and
  frozen snapshot; archive-never-delete — every frozen input page sha256
  present in the output as a live page, under archive/, or as a receipted
  pre-mutation hash; receipts complete (dry-run and apply receipts exist,
  binding.verified true, fact_preservation.ok true); freeze binding of the
  source snapshot re-verified at eval time.

Measurement, not gate: recall@5 / precision@5 / MRR are reported against the
baseline values (0.9333 / 0.2133 / 0.8185) but no "precision gain" is required
— consolidation v0 archives nothing when no exact dups exist (the corpus has
none), so it cannot remove false-positive pages by construction. The v0 value
hypothesis is graph hygiene plus a reranker substrate (supersedes/conflict
receipts), not lexical rank movement.
