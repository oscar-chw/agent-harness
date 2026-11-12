# Selection scope: current seams and one narrow gap

3 November 2026. Static Framework input for original cross-project-exclusion.
No tests, source controls, native calls or gates run here. Root owns reproduction,
implementation and qualification. Original sixteen-case acceptance stays intact.

## Selection and read order

| Existing seam | Selection before source reads/ranking | Remaining boundary |
|---|---|---|
| KB `default_kb_paths`, `KB.__init__`, discovery/refresh | Explicit paths or environment override, otherwise selected profile/configured roots plus current project docs/README/AGENTS; refresh discovers/checks only those selected roots for current readable files | Defaults are a scope policy, not proof a native child received the intended roots; KB has no per-record sensitivity/layer/approved-ID interface |
| KB FTS and BM25 search | Connection-local `kb_live` joins constrain candidates and corpus statistics before ranking/truncation; fallback ranker is rebuilt against the live set/current database stamp | Shared SQLite can retain other projects' cached bodies; their mere existence is not selection and must not influence results |
| ProjectMemory `read_scoped`/`recover` | Validate declared sensitivity, item-scope and layer lists; select receipt from this project's journal; check these three dimensions before resolving source provenance, including historical reads | Journal loading/validation precedes selection; labels are advisory caller declarations, not authentication |
| ProjectMemory `_search_matches` | Load current same-project records, filter sensitivity/scope/layer into `visible`, then compute text budget/exact identity/tokens/corpus; expired/withdrawn and pending records do not enter normal ranked results | Source snapshots/current original bytes are resolved for matching pending candidates or ranked results, before output, not for every record before scoring |
| Shared `search_shared_documents` | Read/hash-check the permitted catalogue; validate its identities and approved-ID membership; read only `allowed_ids` documents; build lexical/FTS candidates and BM25 statistics from those documents | Exact-query classification currently consults all catalogue IDs; see gap below |
| Shared `read_shared_document` | Select one ID from the pinned catalogue; check type, public-rights declarations and provenance metadata before reading that document body; check body hash/header identity and requested lines | Direct read has one explicit document ID, not a search allowlist; caller must authorize that read beforehand |

`SourceVault.resolve` binds project/source receipts, stored snapshot integrity,
line bounds and current original bytes unless explicitly historical. Shared
`_shared_text` checks the supplied file hash. A pin proves the selected byte
revision, not current external permission, factual truth or semantic entailment.
ProjectMemory currentness labels and current source-byte checks are separate.

## What selection does not mean

ProjectMemory `_load` reads and integrity-checks the entire authorized project's
record journal, including stored assertion text and receipt metadata. It does
not call `_resolve_sources` for each entry. Thus excluded same-project record
bytes are loaded internally, but excluded original source bodies need not be
opened, ranked or emitted. Do not describe this as an OS read barrier or as
loading metadata only. Corrupt journal structure can fail the whole load; that
differs from an excluded record pointing to stale original source bytes.

Likewise, a pinned shared catalogue includes metadata for unselected IDs; that
is distinct from opening their body paths. Validating catalogue identity/schema
integrity is legitimate. Public metadata/rights are publisher declarations, not
a license to access private editions or permission to widen the corpus. Missing
or stale selected sources must not become silent no-match; excluded sources
should not need freshness/body validation merely to answer from allowed ones.

KB deliberately supports profile file links to canonical knowledge. A selected
root is not an assertion that every resolved file is lexically beneath it, nor
an authenticated project membership label. Freeze the intended resolved sources
and explicit consumer environment; do not infer another project's access from
a same-project ledger lead. Items19/20/104 can remain named leads without body
resolution/adoption. Do not blanket-ban intended links or delete foreign cache.

Current `vault-search` CLI passes explicit `--allow-id` values to the same shared
search function. Memory CLI supplies declared sensitivity/scope/layer lists to
the public scoped APIs. No new selector or alternate engine is needed. Root's
earlier availability report preserves a native wrong-environment setup failure
and a later explicit-server-environment success: source tests cannot establish
that every already-open consumer is configured identically.

## Concrete scope-invariance gap: excluded exact ID suppresses allowed text

`vault_retrieval.py:76–81` recognizes an exact ID against the complete catalogue's
`identities`, then returns no ranked result if that ID is not in approved
`documents`. Consequently excluded metadata can change allowed retrieval even
though no excluded body is opened.

Root counterexample, NOT_RUN here: hold `allowed_ids=['allowed-note']` and that
note's bytes fixed, with the word `quartzterm` in its body. Query `quartzterm`.
With no such catalogue ID, lexical/FTS retrieval can return the allowed note.
Add a valid, unselected catalogue entry whose ID is `quartzterm`, updating only
the catalogue pin. The same query now becomes an out-of-scope exact-ID lookup
and returns an empty ranked list. This is selected-result interference, not a
demonstrated private-body leak or foreign-cache read.

Smallest proposed integration: classify implicit exact-ID search using approved
documents/IDs, as ProjectMemory already does with `visible`; retain strict scope
on explicit document reads. Do not acquire the excluded body or broaden IDs to
make the query work. Root should reproduce both backends and freeze intended
exact-ID semantics before fixing; an explicit ID-read refusal must remain valid.
No runtime edit is performed by this worker.

## Root-owned controls

- In-scope positive returns its exact evidence. Independently vary sensitivity,
  scope and layer so each excluded, better-matching record never reaches source
  resolution/ranking or response text/receipts. Repeat for exact reads/recovery.
- An excluded record's original becomes stale/missing after its legitimate
  recording; allowed recall still works. A selected stale matching source
  refuses honestly. Do not corrupt the shared journal as a substitute control.
- Public shared catalogue includes excluded stale/nonpublic/better matches;
  approved results and scores remain unchanged, and excluded body reads do not
  occur. Selected nonpublic or mismatched-body evidence refuses before emission.
- Add/remove the excluded exact-ID metadata above; require the chosen scoped
  semantics. Keep genuine exact approved IDs and unrelated no-match controls.
- Warm foreign KB rows in another connection; keep selected rankings/statistics
  and availability metadata independent in FTS and fallback. Revoked cached text
  stays excluded while valid independent hits remain usable.
- Fresh CLI uses the same frozen explicit IDs/roots, rather than merely testing
  the Python function or relying on parent environment inheritance. No real
  private source or expanded native scope is needed for these controls.

No control here is an executed PASS. All scopes require prior caller authority;
none of these APIs authenticates that authority or replaces native/OS controls.

## Inspected source identities

| Repo-relative source | SHA-256 |
|---|---|
| `src/agent_harness/mcp/kb.py` | `af063d2cca1178e41d1716490dbd854a0d26a3dd051b9b4bb7c9997128084df9` |
| `src/agent_harness/project_memory.py` | `0ffe43618c880e1788173d10a88963c68ec7039a732b972aa72bd15b8c61e8c0` |
| `src/agent_harness/vault_retrieval.py` | `478bf8a4c1ac3a4db727de9b5610f9851b310d7687563377756961656b2792c5` |
| `src/agent_harness/vault_sources.py` | `b2f2be00e99ffe23e144cf3955b1c4013ddead6ef9577a8200d8fdbb70aace98` |
| `src/agent_harness/cli.py` | `9219374d32bb5499a0be775ba63b8a5787eb557b1ff0f79f0c7ff02f98ace089` |

Read scopes: relevant selection/discovery/search/read/recovery functions, their
source-resolution boundary, existing KB scope tests and earlier availability
report. Hashes identify inspected source bytes, not installed behavior or tests.
