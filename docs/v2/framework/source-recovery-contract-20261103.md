# Optional source packets: minimum compatible contract

3 November 2026. Framework design input only; no implementation, tests, native
calls or activation by this worker. Root owns changes and verification. The
assigned proposal is coherent at its bounded scope; no concrete flaw requiring
a different engine or broader authority was identified. It does not by itself
qualify original paraphrase recovery or all-client support.

## Existing seam and small implementation

`ProjectMemory.read_scoped` currently selects a receipt, filters sensitivity,
item scope and layer, then calls `_visible`. `_visible` enforces sensitivity and
current-versus-history rules, calls `_resolve_sources`, and returns the record.
`_resolve_sources` already resolves each provenance entry through SourceVault
at its stored inclusive lines, in order; it currently discards packet metadata
and returns only text strings. Normal read packets contain the derived item and
provenance pointers, not those original quotes.

Add the proposed exact-bool `include_sources=False` only to the scoped review
surface. One compatible internal route is to let `_resolve_sources` optionally
retain its existing resolver packets instead of their text; let `_visible`
optionally return a copied result with `source_spans`; and have `read_scoped`
use that returned result. Resolve once after full scope selection. Keep default
helper results unchanged for append, normal search, read, latest and recover.
In particular, append's exact-assertion confidence check still compares the same
source strings; exposing quotes must not alter it or change saved confidence.
Do not mutate a loaded journal record to attach transient source packets.

Another equally small refactor is acceptable if it preserves these behaviors;
there is no need for a second resolver, source search or registry. Avoid adding
one call after `_visible` that resolves every source again: validation and returned
bytes should be the same observed packets, not two reads with an intervening
source change. Validate the public bool before resolution; reject integers,
strings and None instead of interpreting truthiness.

`SourceVault.resolve` already validates project/source identity, snapshot hash,
requested lines, current original bytes unless historical, and response size.
Return its packets unchanged, including kind, text, historical and citation
fields. Do not reconstruct a weaker citation from a path or normalize the quote.
Use the original provenance order, even if two entries repeat; implicit merging
or deduplication would change the promised correspondence.

## Required invariants

- Omitted/false `include_sources` preserves the current public read response:
  no added empty source field, changed labels, history semantics or budget.
- True adds only the actual cited `source_spans`. Full sensitivity/scope/layer
  checks precede provenance resolution. The existing same-project journal can
  still be loaded/validated internally; this is not an OS isolation claim.
- Pending notes stay `pending-memory-data` and unusable for current decisions.
  An exact quote is evidence for independent review, not automatic validation
  of the derived claim. A source saying port8081 does not verify port9999.
- Superseded/expired/withdrawn reads retain existing explicit historical rules
  and current-usability flags. Historical access does not reactivate the record,
  authorize its old advice or bypass `recover` refusal/hold behavior.
- Current stale/missing/corrupt evidence refuses as today. No fallback to a
  cached quote, alternative source, widened lines or a convenient live revision.
  Historical mode resolves the retained citation under its existing boundary.
- Budget the entire final UTF-8 JSON, including quotes, citations, item/receipt
  and flags, against `max_bytes`. Keep SourceVault's own bounds as well. Refuse
  an over-budget packet; do not return a shortened quotation as complete.
- Reading performs no capture, journal write, confidence update, graph change
  or candidate promotion. Caller entitlement is still assumed, not authenticated.

## CLI and consumer reach

Add `memory-read --sources` as an explicit opt-in review. In `cmd_memory_read`,
reject `--sources` with `--recover` before invoking recovery; do not put the new
argument into shared kwargs used by `recover`. Preserve existing historical/
verified-receipt combination rules. Ordinary scoped read can pass the bool and
emit the complete bounded JSON through the existing UTF-8 output path. No input
receipt-size increase or new body-bearing command argument is needed.

An authorized shell client can call that CLI with a known project/receipt and
existing explicit scopes, then inspect the original quoted condition omitted
from a derived note. That capability is still an explicit action, not evidence
the client autonomously knows when to use it or interpreted the source correctly.

Existing `launch.prepare` uses ProjectMemory `recover` and accepts only CANDIDATE.
Its context carries item text plus memory/provenance metadata. It does not call
this proposed source-review option or inject original quotes. Pending/withdrawn
holds must remain. Do not make pending records launchable merely because a user
can explicitly review their sources. `context_packet.compile_packet` is an
opt-in exact-text/pointer compiler; it neither resolves provenance nor provides
client tools. Adding this option does not change its schema or default context.

The MCP server's `mem_*` tools use its separate Memory implementation, not this
ProjectMemory API. Inspected desktop adapter wiring can be MCP-only; installing
a CLI flag therefore supplies no new source-packet route to a no-shell client.
Such a client needs an already-authorized host to deliver the explicit packet,
or a separately scoped future tool integration. Do not route around a no-shell
boundary through a generic command runner, enable tools/config, or claim parity.
Existing KB reads may expose configured plain-text sources, but are not a
replacement for exact retained SourceVault history/citations.

## Recoverable lineage versus missing lineage

If the stored provenance spans actually include a ticket-owner approval condition
that a weak derived note omitted, this option can surface that exact condition
for review. If the condition is outside the stored lines, the link was never
saved, or the relevant relationship is absent, this option cannot recover it.
Return the real existing evidence or its error; never guess a lineage link or
silently search/read beyond it. A useful source quote remains data, not a task
instruction or present permission to perform the described action.

Root's scoped-retrieval repair report preserves invalid absent-query fixtures:
`FOREIGN_ONLY` overlapped an allowed `foreign` locator, and another sentinel
overlapped allowed `exact` text. The lesson applies here: use independently
disjoint absence canaries, while an allowed quote mentioning a foreign lead is
not a read of that foreign body. Keep both a genuinely excluded-body control
and a permitted-overlap positive; do not weaken valid exclusion assertions.

Root should verify default compatibility; exact ordered source packets; one
resolution per provenance; scope before body access; pending/history/withdrawal
flags; unchanged append confidence; stale/corrupt and byte-bound refusal; no
writes; and fresh CLI behavior including recovery-combination refusal. These
are proposed obligations, not executed results from this worker.

## Inspected identities and limits

| Repo-relative source | SHA-256 |
|---|---|
| `src/agent_harness/project_memory.py` | `0ffe43618c880e1788173d10a88963c68ec7039a732b972aa72bd15b8c61e8c0` |
| `src/agent_harness/cli.py` | `9219374d32bb5499a0be775ba63b8a5787eb557b1ff0f79f0c7ff02f98ace089` |
| `src/agent_harness/vault_sources.py` | `b2f2be00e99ffe23e144cf3955b1c4013ddead6ef9577a8200d8fdbb70aace98` |
| `src/agent_harness/launch.py` | `1a23f46d762ba3fad113cdf25868b180c05d679d76569c83c6c9134ef17a4422` |
| `src/agent_harness/context_packet.py` | `273782e00aa12876988becb800342036ba013d4df1aa65b4fb334e5f18851b24` |

Read relevant scoped read/visibility/source/CLI/launch/packet functions, MCP
consumer dispatch and Codex/desktop adapter wiring, plus the scoped-repair report.
No installed client/config or root native answer was inspected. Source identity
does not establish installed behavior, semantic retrieval or efficacy; original
requirements, failures and complete-usage unknowns remain.
