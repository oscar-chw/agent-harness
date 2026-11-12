# Scope, corrections and copy maintenance — development checkpoint

This checkpoint adds deterministic handling of source/project ambiguity and tests
existing correction machinery through task outcomes. It does not activate a live
migration, make free-form semantic judgments, or qualify every native client.

## Source/project decisions

`source_scope.resolve_scope` requires a source ID/revision, observed declarations,
an explicit registry and the caller's allowed projects. A registry binds an exact
source revision and the complete set of declared aliases to one private/internal/
public project label. Missing declarations, an unmapped or changed source,
conflicting mappings, unexpected aliases, privacy changes and disallowed projects
produce distinct quarantine reasons. Filenames, lexical similarity and recency
cannot silently decide a project.

The decision is advisory: `activation_allowed` and `current_fact_authority` remain
false. It is not an authentication or authorization service. Registry ownership
and caller permissions remain external prerequisites. `assert_current` rejects
old readiness after relevant observations, policy, allowed-project set or source
revision change.

The archive copy adapter accepts this explicit registry as an optional path for
known aliases. Without it, the earlier strict single-declared-project rule remains.
A resolved copy records the registry decision and explicit caller-provided project
ID. The original path-hash identity remains explicitly labeled for the old path.
No actual unscoped native memory was guessed into a project. The previous private
census remains evidence of declared headers, not approval to share those records.

## Correction resolution and task evidence

Reuse `ProjectMemory` and `SourceVault`: immutable revisions, source receipts,
compare-and-swap writes, current-source checks and explicit historical reads.
An explicit correction of the same record ID supersedes the old receipt while
preserving it. A direct cited assertion can retain the source-match `verified`
label; an unsupported paraphrase becomes pending. This does not establish the
truth of arbitrary prose or automatically link conflicting records with different
identities. That unresolved semantic step remains quarantined.

Run `PYTHONPATH=src python3 eval/memory_task_canary.py` for an application replay:

| Case | Required outcome |
| --- | --- |
| Initial approved port | Fresh CLI result produces a config matching the separate task contract |
| Explicit corrected port | Another fresh client produces the corrected config, not the old one |
| Stale writer/readiness | Refused; no silent overwrite or reuse |
| Unsupported semantic claim | Held as pending, not used as a verified fact |
| Changed source | Current recall refuses stale evidence |
| Withdrawal | No usable current hit |
| Cross-project or ambiguous mapping | Quarantined |
| Old source/record evidence | Remains byte-identical and historically readable |

The replay passed all ten outcomes across five fresh harness CLI processes. A
negative control substitutes an incorrect retrieved port and the independent
application assertion fails. This is source-process task evidence, not an LLM
benchmark, native Codex/Claude loading, compaction test, or model-token result.
The subsequent three-call native Codex smoke test was separately authorized and
completed against source `aa8a201` on 26 October. Initial recall returned the
approved value, correction recall returned its replacement, and an unsupported
claim returned HOLD. Each trace contains the declared successful retrieval;
all three finished within 90 seconds, with zero retries and unchanged fixtures.
The private acceptance receipt retains a duplicate-hook diagnostic and unknown
effective model identity. This is not a compaction or comparative quality test.

## Disposable SQLite maintenance

`index_copy.compact_copy(..., offline=True)` requires an explicitly disposable
input. It refuses missing, corrupt, linked, oversized, changing sources and an
existing destination. It opens the source read-only, backs it up to a private
new file, compacts only that copy, closes SQLite connections, and publishes without
replacement only after integrity and logical row/rowid fingerprints match.
WAL data is included; the result must be self-contained in DELETE journal mode.
Source and WAL hashes are checked before and after. There is no pruning command,
source deletion, live pointer swap or cap increase.
SQLite may maintain ordinary WAL reader-coordination metadata; the byte-preservation
claim covers the main database and WAL, not every filesystem timestamp or SHM byte.

The input-plus-WAL cap is 32 MiB and the maximum work deadline is ten seconds.
These do not constitute a general bound on every SQLite in-memory allocation.
The `offline=True` declaration is a caller contract, not proof that another
process cannot write; detected change fails before publication. A live-copy,
large-index or shared-user operation needs separate qualification and authority.

`PYTHONPATH=src python3 eval/index_maintenance_canary.py` verified actual harness
KB and session-search results before and after compaction of a disposable fixture.
Artificial padding created free pages: 2,183,168 bytes became 86,016 bytes, with
identical queries and unchanged source documents. A separate uncheckpointed-WAL
fixture preserves FTS results and publishes no required WAL sidecar. Neither
ratio predicts live disk savings; the installed doctor's oversized-index failure
remains open.

## Acceptance boundary

Source tests, task replay, copy-query equivalence and independent bounded review
qualify this development slice. Native recall beyond the bounded synthetic smoke,
whole-corpus correction completeness, unresolved real mappings, model-quality/aggregate-token comparison
and live activation are **NOT QUALIFIED** by those results. Original histories,
profiles, deployed Studio package, cache cap and native trust are unchanged.

The full source gate exited 0: **1,421 passed, 2 skipped, 2 xfailed**, followed by
secret-scan and isolated-demo passes. The index application canary was also run
directly after it was added; it does not invoke a model. Ruff and diff checks pass.
