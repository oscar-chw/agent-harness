# Retrieval availability: smallest signal seam

3 November 2026. Static proposal; verification NOT_RUN. Root owns implementation/checks.
No permission, scope or native setting changes.

## Where availability disappears

In `src/agent_harness/mcp/kb.py`:
- `_ok`, profile-folder discovery and profile-path parsing collapse filesystem
  errors into absent/empty inputs. `discover_files` uses `os.walk` without an
  error callback, so an untraversable subtree can disappear silently.
- `refresh` skips stat/access failures, excludes those files from connection-local
  `kb_live`, and returns only files/changed/removed counts. Do not restore cached bodies after access loss.
- `_index_file` drops old sections and indexes empty text for files above
  2,000,000 bytes or a failed open. It still stores the filesystem fingerprint.
  A transient open failure can therefore leave an empty indexed file that later
  refreshes skip while that fingerprint remains unchanged.
- `search` discards refresh counts and returns only hit dictionaries or `[]`.
  `get` reports a generic missing section; TOC/index also omit unavailable data.
  Thus an ordinary miss, partial discovery and excluded oversize content are
  indistinguishable at the search consumer.

`mcp/server.py` calls the list API and emits one text block/non-error, losing
completeness. Preserve the unreadable-project test's readable descriptor hit.

## Proposed integration

Keep `KB.search(...)`'s hit list. Add a report path sharing one refresh/search;
never rescan or read later global status. Return hits plus call-local availability:
`complete`, `partial` or `unknown`, with bounded aggregate reason codes such
as enumeration failure, inaccessible source and byte exclusion.

Complete means successful scan of selected eligible scope under existing skip
rules, not semantic recall or proof of absence. Enumeration failure has unknown
extent, never zero missing files. Distinguish missing optional default locations
from failed inspection and declared required inputs.

At the MCP boundary preserve the legacy hit-list text block; add bounded
availability metadata and a separate text notice for partial/unknown scans.
Preserve the first block's list shape; a complete call needs no warning. If the
transport cannot carry additive metadata, use an explicit opt-in report surface.
Do not claim legacy clients consumed the new signal.

Gather status only from this call's authorized roots/discovery. Never derive it
from all shared `kb_files` rows or expose denied filenames, old titles/snippets,
bodies, foreign IDs or raw exception paths. Errors do not prove revocation. Keep live filtering before ranking/return;
metadata grants no access. Never broaden roots or elevate access to retry.
Failed indexing must remain retryable rather than marking an empty failed read
as successfully current; preserve cache exclusion during that repair.

## Root-owned countercontrols

- Complete miss: empty hits, complete scoped scan; no nonexistent-fact claim.
  Readable hits and legacy list consumers remain usable.
- Revoke an indexed source: no cached body/title/path leak; partial/unknown signal
  while another readable hit survives, for FTS and fallback.
- Fail directory enumeration: signal unknown extent without enumerating hidden
  names; do not infer no documents from an empty walk.
- Oversize source: byte-exclusion signal; unrelated usable hits survive.
- Transient failed open then recovery without fingerprint change: no stale body
  fallback and no permanently empty “success” cache.
- Shared database with foreign rows: neither hits nor availability metadata
  reveal them. Concurrent calls must not exchange scope/status.
- Explicit missing section: preserve a useful refusal; availability metadata
  must not fabricate that section or justify an all-corpus read.

Proposed checks only. Availability does not establish entailment/current advice
or require blanket stopping/approval.

