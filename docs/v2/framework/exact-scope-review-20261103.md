# Exact-ID scope correction: bounded static review

3 November 2026. **No actionable scope/lookup regression or invalid test
expectation found in the named correction.** Source review only; no tests,
reproductions, native calls, gates or activation by this worker. Root owns those
steps and original acceptance. Root's reported4FAIL/2PASS then6PASS is attributed
assignment context, not this reviewer's execution evidence.

## Inspected identities

| Source | SHA-256 |
|---|---|
| `.harness-work/retrieval/scope-round/vault_retrieval.before-exact-scope.py` | `478bf8a4c1ac3a4db727de9b5610f9851b310d7687563377756961656b2792c5` |
| `src/agent_harness/vault_retrieval.py` | `58a2a6ddcd67ec9bf4c14bc75e0c68026b86a268f73eb817be63d665d9f75160` |
| `tests/test_shared_retrieval_exact_scope.py` | `94eb4d81b8bc828ff336f73358de9f75cab98825413df0dd12047cbb9f89295e` |
| `tests/test_shared_retrieval_selection_boundaries.py` | `2daef33b7da8a1e8ab8f2ef04a415e0a7be7c31e2cc1bd9e97042debab1c36c0` |

Reviewed the exact before/current diff and both test files in full. Source
reads/hashes identify reviewed bytes; they are not passing test receipts.

## Why the change fits the scoped contract

The only behavior change is the implicit exact-ID membership test at
`vault_retrieval.py:76–78`: it consults `documents`, populated solely from
`allowed_ids` at lines67–75, instead of every catalogue identity. Catalogue
schema/identity validity and allowed-ID membership checks remain intact. No
excluded body is added to reads, candidates, corpus statistics or output.

If an approved note contains `quartzterm` and an excluded catalogue entry gains
that ID, a scoped text query continues through lexical/FTS ranking over approved
documents. Before the correction that metadata alone diverted the query to an
empty out-of-scope exact lookup. Resolving the query word as allowed text does
not retrieve the excluded note; the approved document's citation remains its own.

An approved exact ID still has precedence over lexical interpretation, including
opaque IDs whose terms are removed by query filtering. Leading/trailing query
whitespace retains the existing stripped-ID behavior. Explicit document-reader
authorization is not altered. A query mentioning an excluded ID can return an
approved document that genuinely contains matching words; it cannot grant access
to the excluded document. Treating every such allowed-text hit as a leak would
reintroduce the excluded-metadata interference.

## Test expectation review

- `test_shared_retrieval_exact_scope.py:30–44` keeps approved bytes and allowed
  IDs fixed while adding a stale, nonpublic excluded entry. It first requires a
  positive allowed hit, then exact hit equality (including score/citation/text),
  matches status, no omissions and no excluded body/document result. It covers
  lexical/FTS and padded/unpadded queries. The permitted manifest pin changes;
  comparing hits rather than the whole envelope is appropriate.
- Lines47–55 retain approved opaque-ID lookup with score1.0 and a genuinely
  unrelated no-match control. They do not require a lexical engine to recover a
  term intentionally filtered from ordinary queries.
- The shared-selection suite separately instruments body opens, compares scoped
  scores/order with excluded stale/nonpublic/better matches, checks selected
  invalid-source refusals and runs a fresh CLI with explicit IDs. Its excluded
  exact-ID no-match fixture has no overlapping allowed query words; that
  expectation remains consistent with this correction. It does not establish
  that all references to an excluded ID must yield no allowed text hit.

No concrete counterexample requiring another edit was identified within this
scope. Static coherence does not establish executed FTS availability, privacy
enforcement, actual CLI/native behavior or all sixteen-case qualification.
Caller scope remains explicit selection, not authentication. Root should run its
affected positive/negative controls against the pinned subjects and retain the
original failing reproduction before any activation or qualification claim.
