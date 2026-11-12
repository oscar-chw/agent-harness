# Compact search omissions

Use this opt-in format when a search's omission records crowd out its evidence.
The default format is unchanged. This is a source development feature; the
installed dev7 runtime does not contain it yet.

`harness vault-search --omission-format manifest-index` returns schema
`harness.shared-search/v2`. Supply the usual explicit vault, manifest pin and
allowed IDs. Hit text, citations, scores and source-window counts are unchanged.
The same response byte cap still applies; a requested window is returned whole
or recorded as omitted. This does not solve incomplete evidence windows.

In v2, each omitted entry is `[document_index, reason]`. The index is zero-based
in the **exact pinned manifest's `documents` array**; it is not a result rank or
an index into the caller's allowed-ID list. Reasons remain `limit` or `budget`.
Entries keep their original result order. The manifest hash binds the ID and
source hash without repeating both in every omitted entry.

The compact reader first retains whole windows that fit the default format,
then uses recovered bytes for additional windows. A smaller encoding must not
displace evidence the caller already received. This rule uses source windows
and sizes, never answer labels.

Python callers can expand the references with `read_shared_omissions`, passing
the independently expected vault, manifest hash and allowed IDs. It reads only
the manifest, validates its exact hash, and refuses stale, duplicate, malformed
or out-of-scope references. It does not read document bodies. Expansion can be
larger than the compact response and should not be injected into model context
unless needed.

This is a reference encoding, not evidence that a result is complete, a search
was executed or a source is true. A current pinned manifest is required to
decode it. Source content is still checked when a cited document is read.
Neither format authorizes access beyond the caller's supplied scope.

## Development replay

A [diagnostic replay](benchmarks/compact-omissions-20261106.json) of all 500
already-inspected LongMemEval records completed with zero metadata errors and
no loss of previously recovered answers. It recovered all labelled sessions on
396/470 non-abstention questions within the unchanged 8 KiB cap; the installed
baseline had recovered 331/470 with seven errors. Average evidence-turn coverage
was still only 44.5%, so this does not establish answer correctness.

The first compact candidate lost two previously recovered cases despite a
better aggregate score; it was refused and its failure retained. Synthetic
tests now require preservation across byte limits on both search backends.
These are seen-case repair results. A final frozen candidate still needs fresh
matched evaluation, complete overhead accounting and publication checks.
