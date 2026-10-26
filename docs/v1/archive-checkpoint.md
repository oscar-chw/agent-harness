# V1 archive and retrieval checkpoint — 26 October 2026

Development only. This extends the [previous checkpoint](development-checkpoint.md)
without activating a new reader, changing shared profile roots, migrating a live
index, deploying a package or promoting learned facts.

## Explicit archive boundary

`agent_harness.archive_sources.inspect_source(path, root, max_bytes=131072)`
recognizes bounded JSONL envelopes under an explicit owned source root. It reports
format, inspection extent and hashed metadata, not message text. Missing, denied,
symlinked, outside-root, malformed, mixed and unrecognized input remain distinct.
A prefix match is never evidence that the whole file can be extracted. Parent
traversal is refused before any read. Non-JSONL inputs are refused.

The copy-only adapter recognizes Claude Code and Codex message envelopes using
the existing message selectors and redactor. Workflow journals and normalized
native excerpts are classified as derived records and cannot enter the
conversation adapter: their claims need their own provenance and scope adapter.
A format match alone does not imply that a sidechain or metadata-only file has
any selected conversation messages.

`extract_copy(path, root, expected_project, destination)` requires one exact
project declaration matching the source's cwd evidence. Unknown or mixed scope
fails without publishing output. Its default full-source bound is 8 MiB; a limit,
partial final line, malformed record or changing source prevents staging. It
creates a private, inert JSON packet atomically without replacing an earlier
packet. This Python API is a development component, not automatic MCP discovery
or a command to modify the live store.

Each selected record carries stable source identity, full-source revision hash,
line/byte span, raw-record hash, role and redacted text. Redaction precedes text
limits, including timestamp metadata. Long message truncation is explicit.
Original source files remain untouched. Revision changes create new evidence;
the adapter never silently rewrites an older staged packet.

All output records have `current_fact: false`. Corrections remain in source order;
`correction_resolution: NOT_INFERRED` prevents this stage from claiming that the
latest sentence is true. Semantic reconciliation and promotion are separate
acceptance steps. Tool output, injected wrappers and sidechains are excluded by
the existing selectors, so this is not a lossless transcript format.

## Coverage reconciliation

The private operator census binds every declared source ID to its original
metadata inventory. It separates existing index coverage, evicted index entries,
stale offsets, unindexed files, copy-only candidates and excluded derived records.
Index eviction never means source deletion. A subsequent read-only inventory
rechecked the original source set and recorded newer files separately.

`eval/check_source_reconciliation.py --inventory INVENTORY --report REPORT`
checks the exact source set, metadata binding, admission/evidence consistency and
aggregate counts. Missing or duplicate sources, contradictory admission and a
false semantic-completion claim fail. Unit tests cover those negative controls.
Private manifests and original histories are not published.

Native memory Markdown is a separate corpus. Explicit cwd headers can provide
candidate project mapping; they are not access grants. Unscoped registries and
notes remain private until mapped deliberately. No blanket cross-project
injection, live configuration change or automatic learning was enabled.

## Qualification and limits

Synthetic tests cover both formats, corrections, secrets, revisions, scope,
access denials, symlinks, parent traversal, malformed inputs, resource bounds,
source changes and non-overwriting private output. A bounded exported Codex-copy
canary produced 42 selected records from 282,609 source bytes, with original hash
unchanged. The bounded Claude sample did not qualify: sidechain-only or ambiguous
scope was refused. This is evidence of a hold, not a successful Claude migration.

Independent review found a lexical `..` escape; its regression failed before the
fix. An additional secret-in-timestamp negative control also failed before the
redaction fix. Original failures are retained in private receipts. Scope/header
recognition and unit tests do not establish whole-corpus semantic completeness,
native model memory use, or end-to-end answer accuracy.

Final `bash scripts/check.sh` exited 0: **1,399 passed, 2 skipped, 2 xfailed**,
followed by secret-scan and isolated-install-demo passes. Ruff and diff checks
passed. Three disposable mutants removed the traversal boundary, asserted a
current fact, or bypassed timestamp redaction; each failed its intended tests,
while the unmodified control passed. Receipts are in the work graph. These are
source-checkpoint results, not a release/deployment or semantic-migration verdict.

## Selective-query latency

Discovery now canonicalizes a shared directory once per call rather than once
per regular file. Symlink targets still resolve per file, and every refresh
retains its source stat/access checks. No path, permission or query result is
cached between calls.

Against `5bf8d32`, 21 alternating paired synthetic warm repetitions produced:

| Case | Baseline median | Candidate median | Mean paired delta ± standard error |
| --- | ---: | ---: | ---: |
| Broad, 600 documents | 97.964 ms | 41.688 ms | -56.334 ± 0.530 ms |
| Selective, 600 documents | 20.804 ms | 20.330 ms | -0.488 ± 0.165 ms |
| Changed source, 40 documents | 1.673 ms | 1.626 ms | -0.102 ± 0.059 ms |

All ordered hits/scores matched. Cold measurements and samples are in
`plan/v1-memory-foundation/directory-profile.json`. The changed-source difference
is small relative to its uncertainty. These local measurements remove the earlier
large selective regression on these fixtures; they do not prove universal speed
or token savings. The deployed package and oversized-index doctor failure remain
unchanged. Real migration, cache maintenance and native recovery remain open.

The subsequent [scope/correction checkpoint](scope-correction-checkpoint.md)
qualifies explicit alias decisions, task-level correction replay and maintenance
of disposable index copies. Live activation remains separate.
