# Context sufficiency: narrowed static assessment

3 November 2026. Static only; root verifies. Both actor traces show
cat source-packet.json, exit 0 and 32,898 output characters without a truncation
notice. The packet contains selected windows, not whole underlying sources;
reading it fully does not establish semantic coverage.

The title-only StopIteration hypothesis is refuted: read_shared_document requires
the catalogue title as content header line 2, giving the selector a valid anchor.
No crash fix or ranking change is warranted on that hypothesis. The earlier
match-origin/body-anchor proposal is broader than this narrowed task.

Concrete seam: vault_retrieval.search_shared_documents returns hit start/end but
not total lines or surrounding omission extent. Add only
total_lines=len(lines), omitted_before=start-1, omitted_after=len(lines)-end,
using the same _lines result and validated pinned document already in scope.
Keep fields inside the UTF-8 output-budget calculation and retain whole-hit
admission/limit/budget omission behavior. Metadata consumes budget; it must not
justify silent clipping or a larger allowance.

These counts expose boundaries without extra reads, context-default changes,
automatic follow-up or wider access. A missing approval condition in an excerpt
cannot establish its absence from the source. Nonzero counts support a permitted
bounded follow-up or an insufficient-context statement; zero counts still prove
neither support, applicability nor action authority. Root's proposed follow-up
demonstration remains unverified here. Original16 and activation stay unchanged;
no tests/models/production edits performed.

## Count fields: static re-review

3 November 2026. No concrete must-fix found in the new source_window fields or
inspected test source. document_lines and before/after counts use the same
already validated lines and inclusive citation bounds. They enter the existing
whole-hit UTF-8 budget admission; ranking, excerpt radius and read scope are
unchanged. The older exact-scope diff is separate from this count-field change.

Tests cover bounded follow-up to an omitted approval condition, neighboring/full
windows, title/exact discovery, CRLF/Unicode, budget exclusion and fresh CLI.
Root reports two failures before and 13 passes after; this reviewer did not
execute them. The synthetic follow-up demonstrates an available read route,
not autonomous semantic recovery. Zero omitted lines does not certify complete
answers or authority. Installed runtime/laptop artifacts remain unchanged;
original16 acceptance and model-effectiveness claims are not established here.
