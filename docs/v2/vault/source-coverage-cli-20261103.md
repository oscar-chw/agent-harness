# What has the harness actually read?

Use `source-coverage` to inspect one authorized local metadata ledger. It reports
recorded evidence, not whether the model learned or understood the sources.

From this source checkout:

```sh
python3 bin/harness source-coverage --ledger docs/v2/vault/coverage-ledger.json
```

That is the historical 138-identity snapshot, including 108 transferred identities
and 110 transferred URL spellings. Its incoming `UNREAD_UNVERIFIED` labels are
historical intake state, not a current claim that every source remains unread.

To include the separately recorded additions and read-extent correction:

```sh
python3 bin/harness source-coverage --ledger docs/v2/vault/coverage-ledger.json --reconciliation docs/v2/vault/r5-reconciliation-20261103.json
```

This selects the 237-URL union. It corrects the old `COMPLETE_POST_TEXT` claim to
`POST_TEXT_EXTENT_UNSPECIFIED`; the historical ledger remains unchanged. A changed
base hash, incomplete membership or misbound correction is an error, not a pass.
Dates describe selected records; there is no implicit latest-file discovery.

Add `--source-id 'EXACT_CANONICAL_URL_OR_SOURCE_ID'` for one record's states and
JSON pointer, bound to the containing file hash. Near matches fail explicitly.
Reading, access, adoption and evaluation stay separate; missing evidence is not
evidence of universal non-use. Numeric `declared_summary` counts are the base
author's declarations; `denominator` and `reported` are recomputed from records.

The command reads only the explicit ledger/reconciliation, at most 2 MiB each;
it opens no linked evidence, private chats or websites and changes no stores.
Report output is capped at 32 KiB. Duplicate identities/JSON keys, oversized or
malformed input and unknown IDs fail with exit 2. Exit 0 means the report could
be built, never verified source support, semantic retrieval, learning or release.

This source candidate is not in the already delivered laptop ZIP. No default
hook or model prompt changed. The original 16-case qualification remains open.
