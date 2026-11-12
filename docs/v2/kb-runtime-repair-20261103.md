# Know which memory reader answered

3 November 2026. **Diagnostics repaired; the older connected MCP's visibility
difference is still unresolved.** A fresh installed default reader returns the
new capability note. The connected reader still reports no section and supplies
no new runtime metadata. That does not identify its roots or loaded revision.

## What changed

Knowledge tool results now include `_meta["agent-harness/kb"]`:

- The selection captured when the KB was created: default, explicit paths or
  environment-selected paths. Later environment changes do not relabel it.
- Whether the profile is discovered live, plus the stored pinned-root count.
  The count excludes dynamically discovered profile entries; it is not corpus size.
- An opaque home-string identity and a selected loaded-method fingerprint.
  The fingerprint is Python/path-specific, not a full package/configuration
  hash, authenticated build, or proof that disk and connected code match.

These diagnostics do not scan sources, change roots, return document bodies or
expose raw paths/environment values. Missing required read arguments are rejected
before opening the index. Existing text, empty lists, errors and availability
metadata remain intact. No new tool definitions were added.

MCP supports result metadata, but clients may hide it. Protocol source:
[CallToolResult schema](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2025-06-18/schema.json).
An older response lacking these fields proves neither a scope defect nor old code.

## Evidence

- Six new cases failed before the implementation; 59 affected checks passed,
  including the existing context budget and scope tests.
- Isolated control passed all six new cases. Removing metadata failed all six;
  substituting the current environment for captured selection failed four.
- Eight real staged stdio requests used two persistent processes. Default mode
  discovered an added chapter, returned corrected bytes despite preserved mtime,
  and retracted the removed chapter. An explicitly selected file never widened
  to the new chapter. Both owned process groups ended cleanly.
- Fresh installed stdio page listing followed by its actual returned section ID
  read `CLIENT-CAPABILITIES.md#dot-codex-and-capability-discovery` through default
  roots, with metadata. A prior guessed ID was correctly rejected; that was an
  instrument mistake, not a KB repair.

Exact logs, hashes, failures, static review and activation record:
`.harness-work/retrieval/source-reader/kb-runtime/`.
The full post-change regression completed with exit 0: **1,950 passed, 2 skipped,
2 expected failures and 4 marker warnings**, in 503.44 seconds. Command:

```sh
PYTHONDONTWRITEBYTECODE=1 HARNESS_STAGING_PYTHON=/opt/homebrew/bin/python3.11 \
  PYTHONPATH=src python3 -m pytest -q tests eval
```

Terminal receipts are `full-suite.{log,xml}` in that evidence directory.

## Installation and limits

One installed `mcp/server.py` was replaced after exact predecessor checks, affected
tests, static review and staged protocol controls. Backup:
`kb-runtime/installed-server.before.py` in the evidence directory. Its original
SHA is `6ade351ce3c17a40af94d4a0c81c1918b0fc11f7d7634c098ac5e400d7a41309`;
the installed candidate is
`3a37c10808bb4c7952247c23820aedc7b618c1a1d34da37cbb258ba985a2b528`.

No process was forcibly restarted, no native configuration/permissions or hooks
changed, and no source roots expanded. Disk installation does not update imported
code in an existing connection. Do not copy memory into another store to conceal
the discrepancy or call a file read proof that every model used it.

The new wheel is separately retained under
`output/interview-candidate-20261103/revision2/`; the earlier checked wheel and
its manifest remain unchanged as historical evidence. Full-v2 acceptance,
complete matched usage, live client parity, full-vault sync and Dot delivery
are separate unresolved requirements. Four specialists supplied scoped static
inputs; root executed verification. No additional native qualification trial was
run; specialist-session usage remains part of the unallocated whole-task overhead.
