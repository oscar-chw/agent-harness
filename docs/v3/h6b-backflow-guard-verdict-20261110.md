# H6b verdict — backflow guard at write/admission time (2026-11-10)

**H6b verdict: CONFIRMED** within the pre-registered boundary. A write-time
admission guard derived from H5's hash-chained tombstone ledger PREVENTS the
silent re-admission of a certified-forgotten fact at every repo-owned write
seam — verbatim, near-verbatim under fresh frontmatter, and paraphrase carrying
a unique literal — while unrelated content flows unimpeded (zero false
positives over the full frozen corpus), a relearned fact is admitted again, and
a corrupt ledger fails CLOSED. None of the pre-registered disconfirmation
criteria D1–D7 triggered. Plan: `plan/v3-h6b-backflow-guard.md` (9/9 gated);
eval: `.harness-work/v3-h6b-backflow-guard/check_h6b.py` (11/11);
controls: `mutation_controls_h6b.py` (3/3 both directions).

## What was built (repo-only; dev8 runtime and live stores untouched)

- `src/agent_harness/memory_guard.py` — the guard. The blocklist is DERIVED
  from the tombstone ledger + escrow: an entry exists iff the page is currently
  tombstoned, so a relearn reopens admission by construction (no second
  bookkeeping step to forget). Match legs, pre-registered: L1 exact-bytes,
  L2 normalized-body (frontmatter stripped, whitespace collapsed), L3
  unique-literal (a `mc._literals` span with document frequency exactly 1 over
  the reference corpus + escrow), L4 distinctive-token (>=4 shared tokens in
  the df band [2, cap]) — supplementary, see E4 below. Fail-closed on ledger
  corruption; degraded-loud on missing escrow; `audit_store` scans existing
  content against the blocklist.
- `src/agent_harness/memory_forget.py` — ADDITIVE amendment: a new
  `backflow_refused` record kind in the same chain (`append_refusal`, required
  fields verified, receipts deduped for polling seams). Old ledgers verify
  unchanged; `page_states` semantics untouched (refusals never change a page's
  state); the chain's own integrity rule now protects the refusal history.
- Wiring (opt-in, `guard=None` default = byte-identical old behaviour):
  `Memory._add` (mem_add/lesson_add choke point) and `Memory.sync` (hand-drop
  quarantine: skip indexing, unindex if previously admitted, receipt — the
  user's file is never moved or deleted); `ProjectMemory.append` (refusal as a
  content-free `ValueError`, consistent with that module's contract).
- `tests/test_memory_guard.py` — 24 tests, written first (red), all green;
  they caught one real bug pre-gate (sync's unchanged-file fast path skipped
  the guard, leaving pre-tombstone admissions indexed). Non-regression: 186
  existing tests pass; ruff clean.

## Probe results (eval-h6b-20261110.json, hash-bound)

| probe | result | evidence |
|---|---|---|
| E1 verbatim re-add | REFUSED | legs: exact_bytes, normalized_body, unique_literal |
| E2 near-verbatim (new frontmatter, whitespace churn) | REFUSED | legs: normalized_body, unique_literal |
| E3 paraphrase keeping `taskset -c 48-95,144-191` | REFUSED | leg: unique_literal only — as contracted |
| E4 false-positive sweep, 133 candidates (132 non-target frozen pages + post-redaction MEMORY.md) | **0 blocking false positives** | L1–L3 are FP-free by construction over the reference corpus (a df==1 literal cannot occur on a reference page); measured anyway. L4 alone WOULD have fired on 5 topical neighbours (igsl-gpu-box-hardware-state, igsl-nas-hardware-state, igsl-remote-machine, igsl-tenancy-project, resources-calculated-not-hand-set) — relatedness is not restatement, so the pre-registered demotion rule applied: **L4 ships advisory** (`l4_blocks=False`), reported in every verdict's `signals` |
| E5 post-relearn | ADMITTED | blocklist over the relearned ledger has no entry; the ledger stays at 2 records |
| E6 JSON-store seams | REFUSED + RECEIPTED | mem_add and lesson_add refused (`{'ok': False, 'refused': …}`, nothing written); a hand-dropped .json quarantined at sync (unindexed, absent from mem_search at min_score 0, file intact, receipt deduped across repeated syncs); an unrelated add succeeds in the same run |
| E7 ProjectMemory.append | BLOCKED / CLEAN | content-free ValueError naming the tombstone record_hash; the clean item appends and reads back |
| P6 consolidation arms | UNTOUCHED | 0 actions naming the target on the post-unlearn scratch corpus (132 pages) — covered by construction, asserted |
| D5 content-free receipts | VERIFIED | no content probe string in the scratch ledger bytes; refusal payloads carry identity + hashes + leg names only (7 receipts appended, dedupe held) |
| Z H5 artifacts unchanged | VERIFIED | corpus-base / corpus-h5-unlearned / corpus-h5-relearned / escrow byte-identical after the whole eval; inputs re-check passes |

Guard cost, measured: 7.7 ms per admission check with a 133-document reference
(blocklist rebuilt per admission — freshness chosen over caching; the ledger and
escrow are re-read on every check, reference tokenization cached at
construction).

## Admission-path survey (admission-survey-h6b-20261110.json, written BEFORE any guard code)

| path | seam | status |
|---|---|---|
| P1 `Memory._add` (mem_add/lesson_add) | guard inside `_add`, after sync, before dedup/write | **guarded** |
| P2 `Memory.sync` (hand-dropped files) | quarantine: skip/unindex + receipt; file untouched | **guarded** |
| P3 `capture.record` | staging store; candidates reach memory only via mem_add | covered downstream |
| P4 `weekly_intake.take` | read-only ledger, content-free receipts | n/a (read-only) |
| P5 `ProjectMemory.append` | guard after `_validate`, before any write | **guarded** |
| P6 `memory_consolidate` arms | never synthesize fact content | covered by construction, asserted in eval |
| P7 Markdown corpus writers | NO repo-owned write API exists (external writers) | **named boundary**: eval-level coverage only; production coverage = H5-style certification re-run |
| P8 cli.py | no bulk memory import path exists (negative scan) | n/a |

The survey is hash-bound to the pre-wiring sources; the only post-survey drift
is the node-6 wiring itself (surveyed anchors still present, verified by the
inputs re-check).

## Mutation controls (mutation-controls-h6b-20261110.json — 3/3 both directions)

| control | red (must fail) | green (must pass) |
|---|---|---|
| M1 guard bypassed (unguarded seam) | paraphrase ADMITTED by mem_add **and** flagged by `audit_store` | hooked guard refuses; audit clean; unrelated add flows |
| M2 ledger corrupt — edited record_hash; torn tail write | fail-CLOSED: even unrelated content refused, nothing chained onto a broken ledger | intact ledger admits unrelated, refuses matched |
| M3 escrow destroyed | degraded=True on every verdict; L1 still refuses from the tombstone's page_sha256; paraphrase EVADES — asserted WITH the degraded flag (known-limit detection, not a silent pass) | escrow present: paraphrase refused, not degraded |

## Disconfirmation criteria — all pre-registered, none triggered

D1 (a matched candidate admitted at a guarded seam): not triggered — E1–E3, E6,
E7 refuse. D2 (any false positive in the 133-candidate sweep): not triggered —
0 blocking FPs. D3 (post-relearn still refused): not triggered — E5 admits.
D4 (corrupt ledger admits anything): not triggered — M2 refuses all. D5 (a
receipt or payload leaks content): not triggered — D5 probe clean. D6 (a
control passes when it must fail): not triggered — M1–M3 both directions.
D7 (guard impossible as an additive amendment): not triggered — the
`backflow_refused` kind slots into `verify_ledger`; H5's 19 tests and 186
existing tests pass unchanged.

## Honesty bounds

- **Lexical, not semantic.** A paraphrase that drops every df==1 literal AND
  stays below the (advisory) token threshold evades. Measured, pre-registered,
  flagged: embedding-grade paraphrase detection needs model calls, out of this
  track's scope; L4's signals plus `audit_store` are the current backstop.
- **Clean tail-truncation is invisible.** Removing whole trailing records from
  the ledger defeats any append-only chain without an external anchor; that
  detection is certification-scope (H5 freeze binding), not the guard's.
- **Degraded mode is loud but not paged.** A destroyed escrow leaves L1 only;
  every verdict carries degraded=True, but nothing alerts on it.
- **Identity is not blocked.** The ledger names the page by path; a bare
  mention of the name with no fact content is not refused (H5's L3-existence
  limit, unchanged).
- **Boundary.** Certification covers the repo-owned seams on frozen copies.
  P7 (external Markdown writers) and production wiring into the installed
  runtime are explicitly out of scope; the live corpus and live JSON store were
  strictly read-only throughout.

## Ranked what-follows

1. **Owner-gated production wiring** (irreversible-ish, needs the owner):
   construct `Memory`/`ProjectMemory` with a `Guard` rooted at the store's
   ledger in the MCP server; P7 stays certification-scope.
2. **Ledger head anchoring** for the JSON store (external anchor / freeze
   binding) so clean tail-truncation is detectable outside certification runs.
3. **Escrow durability policy**: replication + a degraded-mode alarm (the flag
   exists; nothing consumes it yet).
4. **Semantic paraphrase leg** (embedding similarity over the escrowed body)
   when model calls are in scope; until then L4-advisory + audit.
5. **Fact-level closure**: the redacted-index-line case (a restatement in
   different words on a third-party page) is handled by H5 redaction +
   certification, not by the admission guard — a combined re-certification arm
   could close the loop.
