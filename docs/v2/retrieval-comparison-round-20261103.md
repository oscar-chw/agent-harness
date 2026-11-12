# Memory comparison: evidence before a new default

3 November 2026. Development calibration; v2 is not fully qualified.

The first matched reader comparison rejects the naive overlapping-window arm.
It used **38,970** reported native input-plus-output tokens against **32,162**
for section selection, a **21.17% increase** in this pilot. Both readers completed,
but neither supplied every required qualification. The active retrieval default
has not changed. A lossless deduplication candidate is prepared for a later test.

## What was compared

Four exact questions from the original sixteen-case acceptance input: the two
Memory Tax papers, RAW-RAG's transfer limits, the Foundation attribution/gain
claim, and the unread beamnxw lead. The same four complete eligible local reports
(36,267 bytes), original question strings, top-three ceiling, 8,000 source-text
bytes per question and 100 answer words per question were frozen for both arms.
These are historical report bytes, not new primary-paper/publisher/social reads.

Section selection used the installed KB's default scoped lexical/FTS search and
get. The alternative ranked sixteen-line original-text windows with four-line
overlap using the existing BM25 implementation. It is **not** a replication of
dense/reranked RAW-RAG. The input corpus is a selected development corpus, not
the entire vault; known question-specific support pointers did not choose hits.

Each native reader received its retriever's recorded source spans and used no
tools. Thus this tests retrieval selection plus supplied-evidence reading, not
autonomous search, privacy/revision replay or normal producer/cold-reader recovery.
Root kept answer criteria, analysis and native outputs outside the retrieval
corpus. No native hidden-oracle/OS isolation claim follows from that arrangement.

Native calls requested the same configured model, gpt-6.1-sol, at high effort,
read-only, existing login/included quota and disabled web search. They used fresh
ephemeral sessions, fixed order, a120-second/1MiB limit per call, no retries, and
explicit per-server fixture scope. Exact global config hashes matched before and
after each call. Both owned process groups ended. Requested settings and source
scope were controlled; the full provider-expanded input/tool context was not
captured. This single fixed-order pilot is not randomized/repeated causal proof.

## What the answers showed

Root read the actual responses against the original requirements and source
passages. This was meaning adjudication, not keyword/schema scoring.

| Original question | Section arm | Window arm |
|---|---|---|
| Two Memory Tax papers | Correct distinction, abstract/caption limits and local-gain caveat; former paper's selective read depth omitted | Selective/abstract read depths retained; no explicit local-harness-gain caveat |
| RAW-RAG transfer | Correct offline/local limit and matched reader/budget/visibility requirement; selected-method reading depth omitted | Correct offline/local limit; selected-method depth and some comparison qualifications omitted |
| Attribution and30% gain | Correct contributors and unsupported-gain judgment; explicit report date/fresh-read qualification missing | Same substantive correction; explicit report date/fresh-read qualification missing |
| Unread lead | Correct bounded unknown and missing adoption support | Correct bounded unknown and missing adoption support |

No affirmative fabricated method, paper conflation,30% result or local-superiority
claim was found in these eight answers. That does not make an incomplete answer
complete. The original acceptance file and case statuses remain unchanged. Only
the last question met all its original answer requirements in both responses;
this does not qualify its wider retrieval/control or full sixteen-case campaign.

Reported native usage:

| Arm | Input | Output | Input + output | Observed wall time |
|---|---:|---:|---:|---:|
| Section |31,464|698|32,162|31.586s|
| Window |38,272|698|38,970|21.802s|

Cached and reasoning counts are subsets, not added again. The known native-reader
subtotal is71,132tokens. Preparation, worker, root review/orchestration and older
failed-call usage are not fully attributed: **whole-task usage remains UNKNOWN**.
The faster window observation establishes no latency improvement. Duplicate source
text is a directly observed cost opportunity, not proof it caused the entire
token difference. No+15% allowance or relaxed quality gate was introduced.

## The next candidate preserves evidence

The trace shows overlapping windows returning the same source positions more
than once. A separate, opt-in experiment helper now merges only overlapping
intervals from the same pinned document. It verifies input text, whole-file and
window hashes; retains every selected source position and original order of
first retrieval; never bridges an unselected gap or merges different sources.
It does not summarize, retrieve more material, change scope or rewrite originals.

On the exact already-budgeted window evidence, source text falls from28,413 to
26,678bytes, **1,735duplicate bytes removed**, with identical unique source
positions. This is not a model-token saving or quality result. The candidate is
**NATIVE_NOT_RUN**, has not entered the installed runtime and is not promoted.
Both original consumed calls and their freeze are preserved; neither was rerun.

## Checks and retained failures

Root-owned commands:

```
PYTHONPATH=src python3 -m pytest -q \
  .harness-work/retrieval/comparison/test_prepare.py \
  .harness-work/retrieval/comparison/test_raw_windows.py \
  .harness-work/retrieval/comparison/test_reader_driver.py \
  .harness-work/retrieval/comparison/test_merge_windows.py
python3 -m ruff check --config ruff.toml --no-respect-gitignore \
  .harness-work/retrieval/comparison/*.py
python3 .harness-work/retrieval/comparison/run_reader.py section
python3 .harness-work/retrieval/comparison/run_reader.py window
```

The original26instrument checks passed; deduplication first failed8cases, then
its10checks passed after implementation. Final combined result is recorded in
receipts/validation.json. Six isolated mutants were rejected: dropped tail,
wrong window hash, missing-usage acceptance, unexpected-tool acceptance,
bridging a source gap and truncating a union. These are instrument/byte controls,
not native semantic-efficacy tests. Ruff uses explicit ignored-file inclusion;
an earlier directory invocation selected no files and is not claimed as lint.

Preparation initially failed before a native call because a KB get response
contains navigation and normalized line breaks. The corrected adapter binds
selected content to original character spans, restores original source bytes
and omits navigation from reader evidence; original raw get text remains in
the trace. Invented/changed/reordered content still fails binding. This changes
the experiment adapter, not KB runtime, original requirements or acceptance.

The older installed-policy/navigation replay also failed against historical
native config metadata (inode/mtime/ctime). Current adaptive-mode readback passed,
with no writes;75policy/guard/content checks passed,1existing skip. That old
receipt was not repinned and its historical failure remains. No hook, guard,
native permission, credential, shared service, release or device rollout changed.

## Remaining original gate

Node4 remains pending: the other twelve cases, actual correction/withdrawal/scope
controls, completed producer/cold-reader chain and complete matched aggregate
usage are not qualified. Its original missing-script failure is preserved.
The four existing specialists supplied the raw-window adapter, source-backed
rubric, independent counterclaims and full-file corpus manifest. Root ran checks,
the native readers and source/answer adjudication; worker output was not accepted
as verification. No new standing sessions, heartbeat chat or blanket default added.

Evidence: `.harness-work/retrieval/comparison/receipts/` contains the original
freeze, exact prompts, both raw native streams/attempts, root criteria/review,
retrieval traces, preparation failure, mutations and deduplicated candidate.
Role deliverables are named in
`handoffs/v2-completion/retrieval-comparison-assignment-20261103.md`.
