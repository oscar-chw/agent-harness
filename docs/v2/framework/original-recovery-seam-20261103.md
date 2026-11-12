# Original-note recovery: existing seams

3 November 2026. Static only; root checks. Original case remains
PARAPHRASE_CHALLENGE. No acceptance/gate changes.

vault-search searches explicit allowed IDs using lexical/FTS5 BM25 or exact
identity. Hits carry pinned citations, line bounds and source_window omission
counts. It can miss paraphrases; a miss is not source absence. No semantic or
reranking route is implemented by these APIs.

With a known authorized original, vault-read resolves root/source/SHA plus chosen
line bounds; vault-document resolves a pinned catalogue/document ID and bounds.
They reject stale pins and oversized responses rather than substitute a summary.
An omitted condition can therefore be read through the existing reader without
increasing search defaults or trusting the derived view. source_refs declare
provenance; they do not fetch upstream originals.

SourceVault.capture retains full project UTF-8 text with source/content identity.
resolve accepts independent span bounds and explicit historical mode when the
current original changed. ProjectMemory.read_scoped checks scope before resolving
provenance; memory-read --sources returns exactly the recorded spans, preserving
confidence/history. It neither expands spans nor grants recovery approval.

No demonstrated defect prevents reading a known retained original. CLI limit:
--sources cannot request neighboring historical snapshot lines; the existing
SourceVault.resolve API can. This does not establish a need for another abstraction
or changed acceptance. Unknown source identity, an unretained original or lexical
miss remains a disclosed recovery gap, never invented evidence or authority for
broad private-history rereads.
No tests/models/code edits. Unified ZIP/live settings remain frozen.
