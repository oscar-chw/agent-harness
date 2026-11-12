# H5 unlearning — verdict

2026-11-10. plan/v3-h5-unlearning node 9. All numbers re-derived from the
hash-bound artifacts by `.harness-work/v3-h5-unlearning/check_h5.py` (exit 0,
42/42 checks) and `mutation_controls_h5.py` (exit 0, 4/4 controls both
directions); artifacts: `inputs-h5-20261110.json` (sha e33ffd8c…),
`eval-h5-20261110.json` (sha bd627530…), `unlearn-apply-h5-20261110.json`
(sha 4ce889aa…), `certification-h5-20261110.json` (sha d16abf6c…),
`relearn-h5-20261110.json` (sha 10f1363f…), `mutation-controls-h5-20261110.json`
(sha 45b8f931…), all bound to freeze e55ccdc2… / corpus af6af281… /
baseline 286a988c… / module 0a189a0d… (src/agent_harness/memory_forget.py,
19 unit tests). Zero model tokens, zero native calls, zero network. The H1
frozen snapshot and the live corpus were never mutated.

## H5 verdict: CONFIRMED — within the pre-registered boundary

The hypothesis — the harness supports CERTIFIED unlearning: a designated page
becomes provably unretrievable (bytes, FTS5 index raw tables, retrieval surface,
consolidation arms) under an auditable hash-chained tombstone ledger, with a
defined relearn path, and no other fact lost or regressed — holds on the frozen
133-page corpus, for a page selected by rules fixed before any run.

Designated by the pre-registered rules (expected page of a frozen query, orphan,
≥1 corpus-unique content string, no outgoing wikilinks — exactly one page
qualifies): `memory/fatqat-gpu-cpu-budget.md` (1220 bytes, sha256 2673f59e…),
the c2 answer page, baseline rank 1.

| pre-registered criterion | result |
|---|---|
| D1 any admissible probe retrievable post-unlearn | NOT triggered — 6 content + 2 identity probes: zero live-page occurrences, zero FTS5 rows, zero retrieval hits quoting them |
| D2 any unrelated query regresses | NOT triggered — 17/17 non-target queries keep their baseline verdicts; in fact every rank and hit count is EXACTLY unchanged |
| D3 tombstone ledger leaks content | NOT triggered — no content-probe string in the ledger; the record carries identity + hashes only |
| D4 consolidation touches the tombstoned page | NOT triggered — 0 actions naming the target post-unlearn, where the same pass proposed 3 inbound links pre-unlearn (same instrument, same run) |
| D5 a mutation control passes when it must fail | NOT triggered — 4/4 controls demonstrate both directions (see matrix below) |
| D6 target inseparable from third-party pages | NOT triggered — the one shared string ("all 4 GPUs" on igsl-tenancy-project) is an unrelated fact (GPU driver state), verified at inputs; the page was separable |

Probe detail, post-unlearn (all certified): page file absent; target sha256
absent from all live page bytes; zero `kb_sections`/`kb_files` rows for the rel;
FTS5 `MATCH` on probe terms returns zero rows; `kb_toc` omits it;
`kb_get('memory/fatqat-gpu-cpu-budget.md')` raises KeyError; the 8 admissible
probes occur on zero live pages; `kb_search('fatqat')` returns zero hits. c2
flips from rank 1 pass to target-absent-at-any-rank (its 10 remaining hits are
related pages that do not carry the fact — certified absence ≠ no results; it
means no result carries the fact). `others_preserved`: every non-target frozen
page byte-identical (the receipted MEMORY.md redaction excepted). Relearn
restore: corpus pages root hash returns af6af281… (byte-identical to the
freeze), all 18 query ranks and scores reproduce baseline-20261110.json
exactly, the ledger gains exactly one relearn record, and the tombstone record
is unchanged (append-only verified).

Mutation controls (both directions each):

| control | green (protection present) | red (must fail) |
|---|---|---|
| stale_index | fresh index certifies ok | pre-erasure index with refresh suppressed FAILS: index_absence + retrieval_absence fire |
| quoted_text_leak | clean corpus certifies ok | planted page quoting `taskset -c 48-95,144-191` + `[[fatqat-gpu-cpu-budget]]` FAILS; the leaker is named and the tombstone records the inbound link |
| incomplete_tombstone | intact ledger certifies ok | field drop / edited field / escrow hash mismatch each FAIL at tombstone_integrity |
| amnesia | erased AND recorded certifies ok | page silently deleted with no record FAILS — "erasure without a record is indistinguishable from loss" |

## The doctrine-tension resolution, as built

The harness doctrine "archive-never-delete" and unlearning's "true forgetting"
were reconciled by making them two layers with different boundaries:

- **Consolidation (H1) is deprecation INSIDE the corpus boundary.** `archive/`
  is skipped by the indexer; bytes stay recoverable in place; fact preservation
  counts every input hash in the output.
- **Unlearning (H5) is certified EXIT from the corpus boundary.** Content leaves
  the corpus entirely — moved to a hash-bound escrow OUTSIDE the corpus root
  (kept here so relearn can be demonstrated; destroying it is a policy choice at
  the call site, and the certificate enumerates it as a declared residual either
  way). What never leaves is the TOMBSTONE RECORD in an append-only hash-chained
  ledger (`tombstones/ledger.jsonl`, a non-indexed suffix): page identity, sha256
  of the erased bytes, redaction receipts, time, reason, authority, chain hash.
- **The chain records THAT we forgot, never WHAT.** Certification asserts the
  ledger contains no content-probe string (D3). Identity is preserved in the
  ledger by design — an audit trail that cannot name what was forgotten is not
  an audit trail.
- **Relearn is a new record superseding the tombstone, never an edit.**
  `restore` returns the escrowed bytes byte-identically under the same authority
  (the tombstone carries the pre-unlearn corpus root hash, so restoration is
  self-verifying); `supersede` writes a brand-new page carrying new evidence
  while the sealed bytes stay escrowed (unit-tested; not exercised end-to-end
  here).

Erasure levels achieved: **L1** (content unretrievable) and **L2** (identity
absent from the retrievable corpus — the MEMORY.md index line that restated the
fact was redacted under the same authority, escrowed, hash-receipted, and
restored on relearn). **L3 (existence uninferable) is NOT claimed**: the ledger
names the page by path; GDPR-grade pseudonymised records are future work.

## What this experiment does NOT claim (honesty bounds)

1. **Boundary scope.** Certification covers the corpus copy under eval. Declared
   residual copies: the H1 frozen snapshot (immutable evidence — erasing it
   would break the H1/H2/H3 gates; this is a SECOND doctrine tension, forensic
   retention vs erasure, resolved here by declaring frozen snapshots outside the
   erasure boundary), the escrow, and the live corpus. A production erasure
   needs copy tracking and a snapshot rotation/purge policy.
2. **Backflow.** SBU's named failure — a forgotten fact gets regenerated and
   re-stored — is DETECTED here (the quoted-text mutant fails certification) but
   not PREVENTED: nothing stops a future session re-adding the fact. Certified
   once ≠ stays forgotten. A write-time admission guard keyed on tombstoned
   hashes/literals is the missing piece (what-follows #1).
3. **Target was easy by design.** The selection rules picked an orphan with no
   outgoing links, so removal perturbed no in-degree and the 17/17 exact-rank
   preservation owes something to that cleanliness. Entangled targets exercise
   redaction depth; the dependency-closure leak case was covered synthetically
   (mutation control 2), not on a real page.
4. **One channel of AUBench's three.** Persistent memory is covered; parameter
   unlearning is out of scope (we own no weights); tool-call reacquisition (the
   budget fact is re-derivable from the environment) is named, not addressed.
5. **F-class unchanged.** The target was not a negative-control false positive;
   f1=7, f2=0, f3=10 hits before and after. Nothing about H5 changes the H2
   retrieval-quality findings.

## What follows — ranked by expected value

1. **Backflow guard at admission time.** Wire the tombstone ledger into the
   memory write path (mem_add admission): a new page whose content hash or
   tombstoned literals match a live tombstone trips review. Closes the
   SBU backflow hole the controls only detect after the fact.
2. **Production integration, owner-gated.** memory_forget is eval-path over
   corpus copies; the live store adds a second channel (the harness JSON memory
   store — untouched here) and needs the irreversible-operation gate
   (`risk: irreversible`, human-held) plus escrow retention policy
   (seal vs destroy).
3. **GDPR-style erasure scope.** Copy enumeration (frozen snapshots, backups,
   git history), pseudonymised tombstones for L3, fact-level closure as a
   sanctioned operation (third-party quote redaction — currently detected and
   fail-closed for human decision).
4. **Relearn-supersede end-to-end eval** (only restore ran the full pipeline;
   supersede is unit-tested) and an entangled-target run to stress redaction
   depth and rank deltas.
5. **KB integration:** kb_search could honour the ledger directly (defence in
   depth under stale indexes); the current proof relies on refresh-on-query,
   which the stale-index control shows is the single point the certification
   exists to police.

Recommendation: H5 stands as the harness's certified-erasure mechanism design;
adopt the tombstone-ledger + fail-closed-certification pattern, hold production
wiring behind the irreversible-operation gate, and do the backflow guard next.
