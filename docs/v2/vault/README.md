# Source coverage and local recall contract

2 November 2026. Bounded reconciliation and acceptance specification. No source
intake, retrieval engine, native learning promotion or installation is activated.
The orchestrator owns integration and the original `v2-completion` gates.

## Coverage that can be claimed

[`coverage-ledger.json`](coverage-ledger.json) retains all 108 transferred source
identities and their 110 original exact variants. The original inventory's SHA-256
is `501dafcc17d404eed09fa999b8518097ee39c8840dcf74de5531ed0c57e4b6bc`;
the handover's is
`b3aa817acb40fb27105f549f3cf0ab49c17db145b71ce06cad34033e9d68be78`.
The ledger appends 30 distinct URLs from the bounded documented reviews, giving
138 URL identities. Eleven additions are the 31 October reference-review URLs;
the other additions come from the source-evidence map and second-brain contract.
This denominator excludes other historical research and concurrent worker output.
It is a defined local evidence snapshot, not a census of every supplied source.

The transferred rows' reconciled **reported** depths are: 98 uninspected, seven
snippet only, one title snippet, one metadata only, and one complete post text.
The last is the Alex Lavaee post; attached video remains untranscribed. The
metadata-only YouTube record retains a reported fetch failure and root-reported
title/chapters, not a transcript read. A prior pointer alone does not count as
reading. All 108 original `incoming_read_status=UNREAD_UNVERIFIED` fields remain
unchanged as historical transfer fields. See the input-pinned observations for
each reconciliation. This worker acquired/read **zero primary web sources**.

Across the 138 identities, reported depths are 98 uninspected, eight snippets,
one title snippet, one metadata-only, one caption/frame, four abstracts, 20
selected-section reads, three complete post texts, one complete article text and
one complete idea file. “Complete” refers to that text artifact, not its media,
comments, linked projects, reproducibility or truth. Current access and freshness
remain `NOT_ATTEMPTED` / `NOT_REVALIDATED` even when an earlier report read it.

The 28 October checkpoint reports 15 failed fetches, 13 prior matches, three
overlapping, and 83 with neither. It lacks a per-item attempt map. Keep this
aggregate intact; do not label 15 arbitrarily chosen rows inaccessible or the
other 83 read. Named leads RSIHub, MemPalace and the Gulli book lack resolved
identity/read-depth evidence in these selected inputs and stay outside URL totals.
Cross-project items 19, 20 and 104 remain retained leads with no harness adoption.

Three claim checks on the Linux Foundation announcement are retained as
**historical reported** supports/contradicts/does-not-support relations from
[`source-check-workflow.md`](../../v1/source-check-workflow.md). They are not new
primary-source verification. The map's implementation counterparts are existing
capabilities, not proof that a source caused their adoption. No complete
source → claim → adoption → implementation → evaluation join is established.

## Ledger semantics and correction

Each `source_id` hashes its canonical URL. Transfer item numbers, original exact
variants, classification, triage, row hash and JSON pointer remain recoverable.
Private conversation IDs/text are not copied: the immutable original inventory
pointer/hash retains provenance under its existing access boundary. New exact
spellings are appended separately from `transfer.exact_variants`. No redirects,
social-share aliases, arXiv versions, related papers or same-method sources are
silently merged. A social lead and its paper/repository are different records.

`access`, `reading`, `support`, `adoption`, `evaluation`, `source_revision` and
`freshness` are independent fields. `UNKNOWN`, `NOT_ESTABLISHED` and `NOT_RUN`
mean different things. A successful fetch does not prove a read; a read does not
prove support; support does not establish adoption or measured benefit. A document
report of a read is explicitly `HISTORICAL_LOCAL_REVIEW_REPORT`. Input paths,
hashes and line ranges bind that report; they do not become primary-source pins.
Only versioned paper locators carry `URL_VERSION_ONLY`; absent original content
hashes remain null. Local input digests must never fill those nulls.

Append a new observation/relationship when evidence changes. Preserve its older
scope, revision, date and result, with explicit `supersedes`, `contradicts`,
`duplicate_of` or `withdrawn` relations where justified. Never promote an old read
because a URL still exists. A corrected identity needs a reviewed relation and
retained original row; a guessed alias must remain unresolved. Schema changes
need a version bump and explicit migration proposal; this packet performs none.

## Local-first retrieval and authority

1. Resolve the authorized project, allowed document IDs/sensitivities and current
   task first. Read its graph/handoff for live state. A similar old passage cannot
   override a current requirement, a withdrawal, an access boundary or a gate.
2. For documentation use section IDs/TOC and exact receipt/ID lookup, then scoped
   lexical/FTS5 search. Expand only the needed neighboring source lines and report
   budget omissions. `KB` refreshes configured roots; its installed-session and
   cross-device behavior need their own receipt. `search_shared_documents` is an
   opt-in, explicit-ID pilot, capped at 100 documents/4 MiB per scope. It is not
   a search engine over all 138 external source URLs.
3. Resolve supporting originals and revisions before relying on the answer.
   `SourceVault.resolve` refuses changed current originals; explicit historical
   reads remain labeled history. A receipt proves bytes and provenance, not the
   truth of arbitrary paraphrases. `ProjectMemory` leaves non-exact purportedly
   verified assertions pending; normal recall withholds them.
4. Return the bounded supporting span, source/revision and qualifications. When
   support is absent, say unknown and identify the missing source or relation.
   A no-match is a retrieval result, not proof no knowledge exists. An error,
   unread lead, inaccessible source and missing source each retain their status.
5. Consult new public evidence only when missing/stale facts could change the
   answer and acquisition is authorized. Record the minimal new read. Never bulk
   ingest raw private history, bypass failed tools or call a remote embedding
   endpoint to maintain an offline claim.

This contract reuses `src/agent_harness/{vault_sources,vault_retrieval,project_memory}.py`,
`src/agent_harness/mcp/kb.py` and
[`memory-placement.md`](../../v1/memory-placement.md). These implementation
references describe mechanics, not qualification of the whole live corpus.

## Freshness, correction and privacy

- Distinguish source-byte freshness from factual validity. A matching digest of
  an old document does not make a price, vendor API, security rule or policy
  current. Recheck the consequential span when its time/version can matter.
- A new current source/record revision invalidates only dependent advice/results;
  retain unaffected branch evidence. Require renewed resolution and the original
  outcome gate before reaccepting dependent work. Preserve older immutable
  receipts and explicit historical access; withdrawal stays terminal for that
  identity. Do not delete sources or caches as a correction mechanism.
- Filter project, sensitivity and permitted IDs **before** reading/scoring or
  expanding evidence. Caller-declared scope is an interface contract, not an
  authentication service. A source path in this ledger grants no permission to
  open another project. Cross-project leads are metadata only.
- A cache/index is derived and rebuildable; it cannot grant access after a source
  is removed or permission revoked. Preserve originals and report a broken index.
  Never purge history, raise caps or widen configured roots to hide missing hits.
- Local storage is not local inference. Source excerpts returned to a native
  hosted reader may leave the machine within that client's authorized context.
  New remote rerankers/models need explicit service/data authority. Keep capture
  redaction and bounded excerpts; do not include credentials, full transcripts or
  private conversation provenance in a public derived ledger.

## Concrete gaps and next evidence

**Semantic/reranking:** current KB/shared-vault routes are lexical/BM25 with FTS5
candidate selection. Dense embeddings, cross-encoder ranking, query routing,
multi-hop source graph traversal and whole-corpus entity resolution are not
implemented or qualified by this packet. Before adding one: freeze authorized
source revisions, prepare independent paraphrase/multi-source/correction/privacy
oracles, demonstrate a lexical failure, then compare current lexical, raw-window,
semantic/reranked and combined views as separate arms using the same reader,
scope and budget. Specify embedding version/isolation, incremental update,
withdrawal/rebuild and offline fallback. Count ingestion, maintenance, ranking,
all reader/worker/retry tokens, latency and storage. Accept an improvement only
with quality at least baseline and aggregate tokens at most baseline, preserving
per-case safety/correction checks and all failed attempts. No service or campaign
is launched here.

**Automatic learning:** existing discovery is bounded to two approved official
model-document URLs and produces proposals; weekly intake reads changed local
candidate observations, not verified independent experiences. Repeated counts or
source hashes do not authenticate an actor or establish successful transfer.
`procedures.change` deliberately refuses promotion; local binder receipts remain
`HOLD_UNVERIFIED_BOUNDARY`. Gate-observation work owned by the orchestrator may
add fail/pass observations; it does not fill the promotion/effectiveness gap.
Missing: selected lawful experience corpus, task/source and distinct-input
bindings, trusted actor/oracle separation, effective-model/usage-to-artifact
provenance, independently frozen grader, held-out comparison, authorized
reversible activation and observed rollback/selective recall. See
[`weekly-learning-intake.md`](../../v1/weekly-learning-intake.md) and
`src/agent_harness/procedures.py`. No fabricated scores can close these gaps.

**Cold acceptance:** [`acceptance-cases.json`](acceptance-cases.json) supplies
concrete questions, expected supported answers, refusal controls and source
pointers. All remain `NOT_RUN` as cold/native answer trials. Existing synthetic
test pointers are preparation evidence, not results for these real-source cases.
Root must freeze an independent oracle, run fresh consumers against the same
visible sources, retain actual responses/citations/usage and judge unsupported
claims, scope leaks, stale advice and whole-task outcomes. MacBook Air dev2
parity, continuous synchronization and general efficacy remain unverified.

Metadata QA is available through `python3 docs/v2/vault/validate_coverage.py
--check-inputs --negative-controls`. It validates retention, references, report
depth and artifact integrity; it cannot verify the external source statements or
grade retrieval/model answers. This is subordinate to root's original gates.
