# Source file types: bounded static review

3 November 2026. No concrete must-fix compatibility/correctness defect found in
the exact diff against .harness-work/retrieval/source-file-types/
vault_sources.before.py or the inspected test source. No tests/models/native
calls or source/test/gate edits performed here.

_read now opens nonblocking where supported, validates the opened descriptor as
a regular file, then performs the existing bounded binary read. This addresses
FIFO replacement before open, rather than relying on a stale path-type check.
O_BINARY preserves binary semantics on Windows; missing optional flags fall
back without changing the regular-file requirement. fdopen(closefd=False) and
the outer finally give descriptor ownership to os.close on success, type/size
refusal and read/wrapper errors. Regular bytes, hash validation and scope/span
logic are unchanged by this diff.

Tests inspect public source/catalogue reads, original capture, saved snapshots,
project manifest, replacement-at-open, exact CRLF/Unicode bytes, bad pins and
closure paths. These are authored checks, not results executed by this reviewer;
root's two public-FIFO reproductions remain root-owned evidence.

This is not a deadline guarantee for regular files on stalled storage, new
filesystem isolation, semantic source verification or original16 acceptance.
POSIX-only FIFO tests do not establish native Windows execution. Shipped ZIP
and live runtime remain frozen and are not qualified by this source review.
