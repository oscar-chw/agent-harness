# Optional source packets: bounded implementation review

3 November 2026. **No actionable concrete correctness or contract defect found
in the inspected new hunks.** Static review only; tests/gates/native/model calls,
installation and activation NOT_RUN by this worker. Root's reported45FAIL before
and45PASS plus Ruff afterward are attributed context, not reviewer verification.

## Exact scope and identities

Reviewed only the ProjectMemory source-packet and CLI `--sources` changes against
the supplied before-files, plus both new test sources. Unrelated preexisting CLI
work is outside this review. No native answers, credentials, installed config or
new security/authorization service was examined or proposed.

| Source | SHA-256 |
|---|---|
| `.harness-work/retrieval/source-review/source-project_memory.py.before` | `0ffe43618c880e1788173d10a88963c68ec7039a732b972aa72bd15b8c61e8c0` |
| `src/agent_harness/project_memory.py` | `2acc995e6f1fd02329aaa11b2d31a8e00e8d6e101adde180985d22f7c549a24b` |
| `.harness-work/retrieval/source-review/source-cli.py.before` | `9219374d32bb5499a0be775ba63b8a5787eb557b1ff0f79f0c7ff02f98ace089` |
| `src/agent_harness/cli.py` | `e97e458bc13a2d14c20d8f5b54854eda13cbb2b430d1abd5325805b31d3c6e8c` |
| `tests/test_project_memory_source_packets.py` | `20df4ea6c353942a91454f180ade2c7a886577816bcc6b6559684ea26f4937da` |
| `tests/test_memory_source_packets_cli.py` | `e23e51d03f83470ec417ff6a91cc3fbb88631b0fba63f0164024f270784a9a8d` |

Source reads/hashing completed. These identify inspected bytes, not test passes.

## Contract reconciliation

- `project_memory.py:137–144` resolves each actual provenance entry once at
  its stored line span and preserves the resolver packet when requested. Order
  and repeated provenance entries remain intact. Default calls still receive
  source strings, preserving append's exact-assertion check at lines152–159.
- `read_scoped`, lines242–256, validates an exact bool, then retains existing
  receipt/history selection and sensitivity/scope/layer checks before `_visible`
  can touch source bodies. Same-project journal validation is not confused with
  resolving excluded originals. No broader source search or guessed link is added.
- `_visible`, lines198–212, keeps freshness restrictions before resolution,
  uses the same resolved packets for validation/output, and returns a copied
  result only when opted in. It does not attach fields to the journal item or
  mutate confidence. Default `_visible` callers keep their previous return shape.
- Existing supersession/history/current-usability data from `_selected_receipt`
  remain in the returned result. Lines257–262 retain pending-memory-data and
  false current usability. The option does not change recover's HOLD or terminal
  withdrawal behavior. Historical access is still evidence review, not revival.
- Lines263–265 budget the entire final UTF-8 JSON after adding source packets,
  citations and flags; oversize results refuse rather than return clipped quotes.
  Existing SourceVault resolution/integrity/size boundaries remain applicable.
- `cli.py:1036–1049` rejects sources with recovery before invoking recover;
  existing historical/verified-receipt combination checks remain. Only ordinary
  scoped read receives `include_sources`. The parser adds an opt-in store_true
  flag; default invocation supplies false. The existing UTF-8 output path emits
  the same serialization whose bytes the API budgets.

## Test-source assessment

The API tests compare omitted/false defaults and the complete opted-in packet;
exercise actual ordered SourceVault quotes/citations with CRLF, Unicode line
separators, repeated entries and uncited text; count delegated real resolver
calls; retain pending/recovery holds; exercise superseded/withdrawn/history rules;
and distinguish scope refusal from admitted corrupt-source failure. They include
stale/corrupt source, invalid bool, exact UTF-8 budget and no-write controls.

The fresh-CLI tests retrieve the actual stored ticket-owner approval omitted
from a pending note while retaining its pending classification. They assert
unchanged default stdout, real receipt/citation identity, selected line limits,
current-versus-history/supersession/withdrawal behavior, explicit scope refusal
before unavailable sources, whole-packet budget, recovery-combination refusal
and no new files. These are meaningful assertions by inspection; this reviewer
did not execute them, mutants or fixtures and reports no passing result for them.

No concrete counterexample requiring a new edit was identified in this scope.
This does not certify all consumers, no-shell reach, semantic support, native
model compliance or original sixteen-case/efficacy acceptance. SourceVault is
authorized-path evidence retrieval, not authentication/DLP. Showing stored
lineage cannot recover an omitted condition outside those lines or lineage that
was never saved; it grants no action authority or confidence promotion.

Root should retain the failing-first evidence and independently run applicable
checks against current exact subjects before installation/qualification. No
runtime, tests, gates, default MCP tools or other packets were changed by this
reviewer.
