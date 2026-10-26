# V1 development checkpoint — 26 October 2026

This development branch is separate from the deployed 0.9.1.dev0 patch. The
package version is still inherited from that patch; this is not a v1 release,
automatic update, or completed memory migration.

## What changed

- Scoped retrieval cannot use other projects' cache statistics to rank its hits.
  Peer updates invalidate the fallback ranker; see the first memory checkpoint.
- `harness source-inventory` reconciles declared transcript file metadata with
  read-only index progress. It does not read message bodies, import archives,
  delete sources, or change the index. Optional `--archive-root PATH` declares an
  additional metadata-only archive; `--details` includes hashed identifiers.
- Cold stdio client tests exercise scoped Claude/Codex history, redaction,
  source corrections and permission revocation using synthetic copied sources.
  Cached text is excluded when its source is no longer readable.
- Pure short-word stemming uses a bounded 1,024-entry cache. Document bodies and
  query responses are not memoized; words over 64 characters bypass it.

## Evidence and limits

`bash scripts/check.sh` passed: **1,376 passed, 2 skipped, 2 xfailed**, followed by
the secret scan and isolated install demo. The full gate exited 0. Independent
bounded review found no actionable must-fix; its targeted tests do not replace
the main-loop full gate. Original failures and passing receipts remain in the
work graph. Source code was unchanged after this full run; subsequent edits add
documentation and redact local identifiers from public evidence copies.

Seven paired synthetic repetitions against the correct pre-optimization
checkpoint `5bf8d32` produced identical ordered hits and scores:

| Case | Baseline warm median | Candidate warm median |
| --- | ---: | ---: |
| Broad, 600 documents | 101.352 ms | 54.814 ms |
| Selective, 600 documents | 23.362 ms | 32.953 ms |
| Changed source, 40 documents | 1.866 ms | 2.290 ms |

The broad case improved, while selective and changed-source cases regressed.
These are local synthetic observations, not a general speedup or a model-token
or task-quality claim. Samples and cold timings are in
`plan/v1-memory-foundation/retrieval-profile.json`; reproduce with
`python3 eval/kb_retrieval_profile.py --baseline 5bf8d32 --repetitions 7`.

## Outstanding acceptance

`COMPLETE` inventory means only that the declared roots and discovery patterns
were scanned. `BYTE_OFFSET_COVERED` means matching indexed metadata and offset,
not valid message extraction, semantic completeness or lossless migration.
Unsupported readers, evicted files, stale offsets and unknown counts remain
explicit. Hashed paths are metadata identifiers, not content identities or an
anonymization guarantee. Symlinks are excluded and scans have entry/time limits.

Live read-only reconciliation confirmed missing archive reader coverage and
native Codex memory outside the shared profile roots. Project-local vaults and
other client histories still need an explicit registry. Private source manifests
are deliberately not published. No live index purge, migration or cap increase
was performed; the installed oversized-index doctor failure remains unresolved.

Still required before v1 release: migration reconciliation with semantic
canaries, safe cache maintenance, actual native-client recovery, mixed-backend
coherence, and held-out quality/aggregate-token evidence. Fresh synthetic MCP
processes do not establish that a running model remembers or uses retrieved data.
