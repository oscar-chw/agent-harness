# KB runtime metadata: bounded static review

3 November 2026. No concrete must-fix found in the named diff/test source.
No tests/gates/native calls, activation or source edits by reviewer.
Original connected-KB visibility cause remains NOT_ESTABLISHED, not fixed.

The tool-result _meta object is an additive MCP result field. Existing text,
isError and first JSON-list block remain intact; setdefault also preserves
retrieval_availability metadata. Custom diagnostics do not replace tool output.
Whether a particular connector exposes _meta requires actual transport readback.

Server construction hashes selected in-memory method code objects, not current
disk bytes. Its docstring correctly limits this to selected Python methods.
This is not a whole-package/global-helper identity, authenticated build, portable
digest across Python/install paths, or proof the connected server matches disk.
Equal digests cannot establish equal helper/configuration behavior; absence from
an older response establishes no cause. No stronger identity claim is justified.

Selection is captured when the lazy KB is created; diagnostics reuse instantiated
state without scanning. Missing required read arguments are checked before that
creation. Metadata includes flags/counts and a home-string digest, not source
bodies, raw paths or environment/config values. The digest is an opaque comparison
label, not canonical filesystem identity or confidentiality authentication.

Tests inspect default versus pinned selection, unchanged post-creation selection,
new default-profile discovery, preserved empty lists and missing-argument behavior.
They do not verify live connector delivery or distinguish the original failure.
Root owns execution and qualification.

