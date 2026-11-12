# Minimal source-answer completeness mechanism

3 November 2026. Static proposal; root verifies. Checked: work-loop/reasoning.md,
philosophy/source-answer-completeness-design-20261103.md, vault_retrieval.py,
project_memory.py and CLI vault/memory readers.

Smallest seam: extend content/skills/work-loop/reasoning.md's task-fit/source-
support review with one conditional draft pass. For a nontrivial source-backed
answer, map each distinct user ask/binding task requirement to an answer sentence
plus source span, or a scoped gap. Keep source qualifications that change meaning,
applicability or next action. Repair supported omissions; preserve conflicts and
unresolved requirements. Declaring a gap does not satisfy it. Stop after one
pass; simple answers stay direct. Reuse the existing philosophy candidate.

No new CLI needed. vault-search returns bounded windows/omission metadata;
context-lines caps at eight. vault-read/vault-document reads permitted pinned
evidence; memory-read --sources exposes retained scoped spans. A hit/snippet is
not the complete source. Never widen scope automatically. Bindings/hashes prove
byte identity, not support/completeness; launch.read_answer checks retained-body
integrity, not whether every ask is met.

Keep this mapping temporary and derived only from task/permitted evidence:
no oracle clauses, case IDs, expected numbers, extra agent/model or verified-
memory claim. Preserve original16 questions, requirements, forbidden claims and
failures. Root evaluates separately; no regrade, consumed-call retry, default
activation or efficacy claim follows from this note.

## Coverage CLI: bounded static review

3 November 2026. No concrete must-fix found in source_coverage.py, its CLI
registration and test source. The command reads only the explicitly selected
ledger, bounds regular-file bytes, rejects duplicate JSON keys/source identities,
checks URL-derived identities and recomputes record counts. It labels declaration
summaries separately; evidence verification stays NOT_RUN, source-claim joins
NOT_EVALUATED and corrections NOT_APPLIED. No linked inputs or URLs are read.

The historical projection is not an answer-completeness check or r5 union.
The tests explicitly retain that boundary; they were inspected, not executed.
Any reconciliation extension must require explicit pinned inputs, identify the
base/correction revisions and their applicable scope, preserve conflicts/unknowns
and avoid promoting declared read/adoption states into verified evidence.
A ledger hash identifies selected bytes; it does not certify their assertions.
No native/model/default activation or original16 acceptance change was reviewed.

## Reconciliation follow-up: two P2 findings

3 November 2026. Static only; no tests/models, ZIP changes or effectiveness proof.

P2 source_coverage.py:115-129: original reading.status is not validated before
replacement. A hash-bound base with reading={} and a correction omitting
old_status passes None==None, then raises uncaught KeyError at reading["status"]
(CLI catches ValueError only). A matching non-string/empty old status can instead
survive in a successful report, bypassing the base-only schema check. Validate
original status with _text before matching/mutation; root should cover missing,
empty and non-string old labels with reconciliation.

P2 coverage_report retains base denominator_boundary/claim_class unlabelled
while reporting union counts and reconciliation as_of. The real base boundary
excludes concurrent documents, yet r5 adds identities from additional inputs.
Expose base metadata as base_* and give the union an explicit selected-input
boundary; consumers otherwise receive incompatible count/scope metadata.

Base SHA, index/pointer and correction-flag checks bind declarations, not primary
reads. Original16 and laptop delivery remain separate.

## Reconciliation fixes: static re-review

3 November 2026. Both recorded P2s are addressed in the inspected source.
_reconcile validates original_status with _text before comparison or mutation,
then preserves that validated value. The regression source covers missing,
empty, integer and object labels, including CLI exit 2 without traceback.
Reconciled output now preserves base_as_of/base_claim_class/
base_denominator_boundary and supplies a union-specific boundary and
SELECTED_LOCAL_METADATA_PROJECTION class. Tests assert base/projection separation.
No remaining concrete defect found in these exact fixes.

Root reports five retained before-failing cases, the failed-then-repaired node24
gate and 119 passes. This reviewer did not execute those checks. Declaration
projection remains separate from semantic support, answer completeness,
effectiveness, default activation, original16 acceptance and laptop delivery.
