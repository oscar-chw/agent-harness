# Knowledge foundation audit — 31 October 2026

## Answer

The retained reference inventory exists and its saved rows reconcile. A completed,
queryable knowledge graph covering those references has **not been demonstrated**.
The inspected source contains useful local retrieval, provenance, correction and
recovery mechanisms. Neither their presence nor a Markdown architecture proves
whole-corpus coverage, native-client adoption or optimal task/token efficiency.
Do not describe this foundation as finished or globally optimal.

Audit subject: source revision `1573c1e` before these documentation additions,
declared package `0.9.1.dev0`. This is not an installed-version or fleet readback.
No external pages, private transcript stores or blocked configuration paths were
read for this audit. No model calls, dependency installations, migrations,
automatic promotions, releases or hook changes were performed.

## What the retained 100+ references actually establish

Input: the workspace's existing
`agentic-os/plan/harness-v05/dot-link-intake-20261028/{inventory.json,HANDOVER.md}`.
These private inputs remain in place; their provenance records are not copied
into this public-facing report.

| Check performed now | Result | Limit |
|---|---|---|
| Handover bytes match its recorded SHA-256 | PASS | Integrity, not truth or full-text acquisition |
| Every saved inventory row matches a handover row | PASS: 108 items, 110 variants | This handover's denominator, not every link in every session |
| Unique canonical URL identity count | 108 | Canonicalization does not resolve social-share aliases or duplicate methods |
| Drop one item and rerun the row comparison | REJECTED | Negative control for retention only |
| Saved prior-reference pointers | 13 items; 95 without pointers in that inventory | A prior mention is not a verified reading |
| Incoming read-status field | All 108 begin `UNREAD_UNVERIFIED` | Original transfer status; not a fresh judgment that all remain unread |
| Complete source-to-claim-to-implementation-to-evaluation join | NOT ESTABLISHED | No unified current coverage receipt was found in the inspected artifacts |

Inventory SHA-256:
`501dafcc17d404eed09fa999b8518097ee39c8840dcf74de5531ed0c57e4b6bc`.
Handover SHA-256:
`b3aa817acb40fb27105f549f3cf0ab49c17db145b71ce06cad34033e9d68be78`.

[The prior status checkpoint](../v11/STATUS.md) separately records 15 attempted
links, 13 prior-reference matches, three overlapping, and 83 with neither.
Those are historical checkpoint counts, not recomputed current content coverage.
Later references, including RSIHub, MemPalace and the Gulli book, require an
explicit append/reconciliation; the 108-item inventory is not an exhaustive
denominator for this conversation. Unattempted sources must not be labeled
inaccessible, and an access failure must not be labeled a completed reading.

## Architecture: implemented boundaries versus claims

| Layer | Inspected evidence | Verdict |
|---|---|---|
| Task dependency graph | `workgraph/plan.py`, leases and command gates | Execution state; not a graph of research knowledge |
| Source/capability map | [source-evidence-graph.md](../v1/source-evidence-graph.md) explicitly says research evidence, not installed functionality | Useful curated table; not proof of an operational whole-corpus graph |
| Document/KB search | `mcp/kb.py`: scoped document sections, BM25 and FTS5 | Implemented lexical retrieval; not semantic or graph traversal |
| Shared document retrieval | `vault_retrieval.py`: explicit allowed IDs, pinned manifest, lexical/FTS5, bounded excerpts | Opt-in pilot, at most 100 documents/4 MiB per scope; no persistent graph in this module |
| Source and record integrity | `vault_sources.py`, `project_memory.py`; immutable receipts, revisions, pending assertions, withdrawal/history | Valuable correctness foundation; not automatic truth checking of arbitrary prose |
| Conversation inventory | `source_inventory.py` inspects transcript metadata/index progress | Different denominator from shared web links; byte coverage is not semantic extraction |
| Handoffs and cold recovery | Existing source/process tests and bounded native receipts | Partial evidence; not lossless memory or universal client compliance |
| Learning/discovery | `procedures.py`, `improve.py`, `discovery_cycle.py` | Candidate generation and held promotion; daily discovery covers two approved model-document URLs, not the entire ecosystem |

The architecture's separation of authoritative originals, derived indexes,
project/task state and optional learned procedures is a sensible baseline for
the stated requirements. It still needs operational integration and evidence.
Changing Python to Rust, adding a graph database, or increasing agent count does
not by itself close a missing-content or missing-evaluation gap.

## What a usable evidence graph must add

Reuse the current source vault and scope/correction rules. Maintain one versioned
source ledger, with machine-readable relationships and a query interface:

`source revision -> supported claim -> relevant requirement -> decision -> implementation -> evaluation receipt`.

Every support edge needs the cited span and read depth; a model-suggested edge is
a candidate until reviewed. Keep `contradicts`, `supersedes`, `duplicate_of` and
withdrawal visible. A social pointer and the paper/repository it points to are
different source records. Acquisition, reading, claim verification, evaluation
and adoption are separate statuses, not one ambiguous “done” flag.

Acceptance examples, evaluated against independently prepared answers:

- Given a requirement, return the relevant supported sources, competing methods,
  adoption decision and actual test evidence; expose missing links.
- Given an adopted component, recover its rationale and the exact source/eval
  revisions. A missing receipt produces UNKNOWN, not an invented justification.
- A corrected or withdrawn source cannot silently supply current advice; its
  historical record remains inspectable.
- An unrelated/private project cannot influence the query's results.
- Unread sources remain discoverable leads and never appear as verified support.

Start with typed relationships in the existing local persistence approach.
Choose a dedicated graph engine only if measured query/maintenance needs justify
it. A graph visualization is a view of those records, not the evidence itself.

## Efficiency qualification

No matched graph-versus-current retrieval/task comparison was found in the
inspected artifacts. Historical CPU retrieval profiles exist, including both
speedups and regressions; they cannot establish present model quality or savings.

Freeze an authorized, source-pinned question set covering exact lookup, paraphrase,
multi-document reasoning, temporal correction, contradiction, missing evidence,
withdrawal and cross-project exclusion. Keep the same reader, source visibility,
answer checker and output budget for every arm:

1. Current scoped lexical retrieval.
2. Raw source-window retrieval, reusing the existing source receipts.
3. Hybrid retrieval and/or explicit graph traversal, added only where a failure
   justifies it. Separate arms so their marginal benefit is measurable.

Measure evidence recall/precision, supported answer quality, correction/privacy
failures, cold/warm latency, index/storage maintenance and aggregate model tokens
including extraction, reranking, synthesis, retries and workers. A smaller context
packet or CPU speedup alone is not token or task-quality proof. Enforce the existing
quality-at-least-baseline and aggregate-tokens-at-most-baseline acceptance; retain
failed candidates. No new model campaign is authorized or launched by this report.

## Current verification

- `python3 -m pytest -q tests/test_retrieval_canaries.py tests/test_vault_workflow.py tests/test_project_memory_claim_support.py`:
  **18 passed**. Synthetic cold-process retrieval, source correction and stale/
  unsupported evidence controls; not the real link corpus or a model benchmark.
- Earlier in this audit, `python3 -m pytest -q tests/test_handoff_readback.py tests/test_discovery_cycle.py tests/test_v1_learning_loop.py`:
  **64 passed**. Separate handoff/discovery/learning mechanics; not performance.
- Initial use of `python3.11 -m pytest` failed because that interpreter has no
  pytest; no installation or environment alteration was used to hide it.
- Read-only inventory assertions and omitted-row control: **PASS_METADATA_ONLY**,
  as recorded above. The original inputs were not rewritten.
- `python3 eval/kb_retrieval_profile.py --repetitions 7`: **exit 0**, ordered
  responses equal in all three synthetic cases against `5bf8d32`. Broad-query
  warm median: 98.359 -> 42.562 ms; selective: 21.229 -> 20.482 ms; changed-source:
  1.650 -> 1.614 ms. These are observations from one CPU run, not established
  population effects or graph/token advantages. All samples and the candidate
  source digest are in [the summary receipt](../../plan/knowledge-foundation-audit/cpu-profile-summary.json).

## Order before v2 claims

1. Reconcile the retained source denominator and append newer supplied references;
   publish counts by actual read depth, access state and claim/eval coverage.
2. Qualify the small evidence-graph query above using the existing vault, including
   negative controls and correction propagation. Do not infer a live graph from a
   diagram, inventory count or green unit suite.
3. Run the separately scoped matched comparison only after corpus/oracle/budget
   qualification. Keep the simplest arm that meets quality and total-token rules.
4. Build bounded automatic intake/evaluation on that foundation; preserve a
   reversible candidate/promote/rollback boundary. Release names are milestones,
   not evidence that these steps have passed.

This audit completes an evidence assessment, not the outstanding corpus ingestion,
operational knowledge graph, native model comparison or v2 release.
