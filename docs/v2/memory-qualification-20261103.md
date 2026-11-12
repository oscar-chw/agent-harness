# Memory qualification — 3 November 2026

The local development harness now preserves complete long native answers. Its
memory qualification is still incomplete. No release, all-device parity or token
savings is claimed.

## What changed

`launch.execute` previously cut native answers at 8,192 characters. The new code
keeps that display preview and explicitly marks it. A longer answer is saved in
a private, hash-bound sidecar, subject to the existing 1 MiB file limit.
`launch.read_answer` retrieves and validates the full answer; missing, changed,
unsafe, over-budget or completeness-unknown evidence is refused. A storage
failure is reported separately from native execution completion. Nothing marks
the task correct merely because the native process exited successfully.

The source repair and its reused `qualification.py` dependency were installed as
a reversible local dev3 overlay. Exact predecessor/installed identities, backup
and unchanged native-config hash are in
[activation.json](../../.harness-work/retrieval/answer-pass/activation.json).
Existing open clients are not claimed reloaded.

## Actual evidence

| Check | Result | What it establishes |
|---|---|---|
| Affected launch, binding, recovery and gate-instrument tests | 186 passed | Current source mechanics; not universal agent behavior |
| Retention controls | 13 passed; two copied mutants caught | Full Unicode tail, preview boundary, missing/changed/foreign evidence and retention failures |
| Independent framework review |No material finding in bounded static diff | Source review, not another execution or release approval |
| Fresh native source-answer batch | 11 answers, 57.704 s, exit 0 | Complete 10,274-character answer recovered; 29 source windows byte-checked |
| Root meaning review | 8 complete, 3 partial | Original requirements remain binding; no averaging omissions away |
| Fresh local process/MCP controls | 5 passed in 4.12 s | Correction, scoped ranking, real revocation and original-source recovery at the scopes below |
| Original sixteen-case gate | Exit 1, NOT_QUALIFIED | Current gaps are visible; original missing-script failure retained |

The native trace read only its authorized supplied source packet in two commands.
No MCP, web, message, gate, configuration or service operation occurred. Its
owned process group ended; frozen source/fixture/module pins and native-config
hash stayed unchanged. This is supplied-evidence reading, not autonomous source
discovery or authenticated actor isolation.

Native usage is 109,070 input plus 2,651 output = 111,721 tokens. Cached input and
reasoning output are subsets. Whole earlier-failure, worker, root, ingestion and
maintenance attribution remains UNKNOWN. This is included-quota usage evidence,
not an API bill or a matched token-saving result.

## What the three answers missed

- **Coverage:** omitted the retained incoming `UNREAD_UNVERIFIED` classification.
  The current item 15 read-extent correction was otherwise preserved.
- **Search:** omitted that URL inventory is not ingested searchable content and
  did not retain the missing semantic/reranker comparison clearly enough.
- **Learning:** omitted distinct-input experience and authorized activation/
  rollback requirements. Repeated intake remains a candidate, not an active skill.

The full answers and per-clause root judgments are retained in
[the answer review](../../.harness-work/retrieval/answer-pass/receipts/root-review.json).
The original question/acceptance file and its historical statuses are unchanged.
No automatic retry or global prompt/default promotion follows from these gaps.

## What the local recovery controls actually did

- A fresh CLI consumer used port 8082 after an 8081 decision changed. Dependent graph
  nodes became stale and required reacceptance; the independent branch retained
  its accepted receipt. Old evidence survived. The unchanged gate rejected a
  stale output before accepting the repaired one.
- Fresh lexical and FTS5 readers returned identical own-project results before
  and after 20 matching foreign rows entered the shared cache. Allowed-ID/
  sensitivity paths, a strictly stronger foreign ranking and inventory-lead authority interpretation remain untested
  by this particular KB fixture.
- A fresh MCP reader withheld a genuinely unreadable source after warming its
  cache. It distinguished a clean miss from a partial/read-denied search and an
  unavailable exact read. The original and cached body remained; no purge hid
  the failure. Only temporary fixture permissions changed and were restored.
- A fresh process recovered a missing ticket-owner approval condition from the
  authorized original span after a derived note and lexical query omitted it.
  This used an explicit source receipt; semantic retrieval and unassisted query
  strategy selection remain unproven.

These are source-process controls, not native LLM or matched efficacy results.
Retained fixtures, subject pins, test XML and root adjudication are under
[real-controls](../../.harness-work/retrieval/real-controls/root-review-status-r2.json).
The earlier bounded completed-producer/fresh-native-reader handoff remains
credited separately; it is not silently replaced by these deterministic tests.

## Gate and next requirement

`python3.11 .harness-work/v2-completion/check_retrieval.py` now reads the original
sixteen-case contract and bound root observations. Missing evidence is not a
pass; missing recorded outcomes are not falsely labelled never executed.
Duplicate JSON keys, stale evidence, omitted assertions, described-but-unrun
replays and missing/regressing comparison usage are rejected. 29 instrument
controls passed and four copied mutants failed for their intended defects.
Hashes establish identity; root execution and meaning adjudication remain an
explicit trust boundary, not author authentication or semantic truth.

The original gate remains nonzero for five partial cases and incomplete matched
whole usage. The next qualification needs the missing answer meanings, remaining
ID/sensitivity/inventory and paraphrase-strategy facets, and a prospectively
frozen complete comparison preserving all applicable failed attempts/overhead.
Existing UNKNOWN historical debt must remain visible. Do not promote the rejected
window treatment, close node 4 or infer stable-v2 readiness from test counts.

Commands and logs: `tests/test_native_answer_retention.py`, the affected 186-test
command in the current root packet, `.harness-work/v2-completion/test_check_retrieval.py`,
`retrieval-gate-mutations.json`, `answer-pass/receipts/trace-audit.json`,
`real-controls/results.xml`, and `plan/v2-completion/04-*.md`.

## Dashboard correction found during this qualification

The live MCP dashboard reported old node 16 as “last fail” after a newer node 4
failure. Its loop used file order rather than failure timestamps. The repair
uses event dates, identifies equal-second ties, and keeps invalid-date failures
visible without inventing their order. Four initial regression tests failed;
all six pass after repair. A first implementation used a nonexistent formatter;
the tie test caught it and the implementation was corrected. No test was loosened.

The affected source set passed 55 checks. The staged installed engine passed the
six chronology cases. Only the two matching function bodies were installed,
because unrelated source/installed drift already existed. Exact backups and
identities are in `answer-pass/status-activation.json`. Native configuration was
unchanged. The live MCP status now names node 4. The five local replay tests were
rerun on fresh retained r2 fixtures after this source change: 5 passed in 4.11 s; the
previous freeze/results/review remain intact. This is not whole-package parity
or a new native model experiment.
