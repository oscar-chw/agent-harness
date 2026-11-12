# Benchmark evidence

**No official end-to-end benchmark score is claimed.** The first public-dataset
retrieval component result is available: [LongMemEval, 6 November](longmemeval-20261106.md).
All 500 records were attempted; 463 were retrieval-graded, 30 abstentions excluded,
and 7 metadata-budget failures retained. This is not QA accuracy, QMD superiority
or whole-task token savings. See [the campaign](PLAN.md) for the remaining tests.

| Evidence | Observed result | What it does not establish |
|---|---|---|
| Frozen dev6 source regression suite | 2,220 passed; 2 skipped; 2 expected failures | Public benchmark performance or universal correctness |
| Dev6 local native handoff readback | Five exact facts + scoped citation; one fresh native invocation; 14 invalid-output controls rejected | Every ordinary app chat follows memory instructions |
| Dev6 evaluation boundary | Local native command/file controls and bookkeeping passed; unprotected controls exposed grading files | Tenant isolation, network-domain containment or model-weight identity |
| LongMemEval_S-cleaned retrieval component, installed dev7 | 500 attempted; 331/470 non-abstention questions recovered every labelled session; 7 errors retained | Adapted both-role corpus; no QA/leaderboard/QMD or whole-task efficiency claim |
| Compact-omission source diagnostic | 500 attempted; 396/470 recovered every labelled session; no errors or loss of previous recoveries | Already-seen cases measured before deployment; not a fresh benchmark or installed QA score |
| Post-dev8 KB read-budget candidate | A requested 400-byte text read returned 18,944–18,947 bytes before the fix and 400 afterward, in both lexical backends | Owned synthetic size comparison; excludes the separate response header; not task quality or token savings |
| Other end-to-end external campaigns | NOT_RUN | No leaderboard position, superiority or token savings |
| Procedure learning | Promotion NOT_GRANTED | A passing test count does not train or activate a skill |

The native readback reported 23,379 input and 95 output tokens. Reasoning tokens
were included in output, not added again. Wider root/orchestration usage was
not fully measured; **this is not an efficiency result**. These are historical
local dev6 component checks. Later development source is a separate candidate.

The compact implementation was subsequently included in the local dev8 runtime;
that deployment does not turn its earlier seen-case diagnostic into a new score.
The later KB read-budget fix is still a source candidate. Its 69-check gate,
fresh-process recovery checks and stdio read/recovery check pass; three copied
defects are rejected. Regression coverage totals 2,324 passing cases across two
runs, with two skips and two existing expected guard failures. The initial full
run had one packaging failure and six setup errors under an older-than-required
builder. The same seven packaging cases pass with the declared compatible local
builder. Both runs are retained; this is not reported as one clean full run.

The byte comparison measures returned text, not model tokens. Wider preparation,
root and review costs remain unmeasured. Original retrieval, learning, complete
usage and release gates remain open.

Before publishing benchmark scores, include the exact release/build, upstream
and dataset/grader pins, task IDs, complete baseline/candidate traces, all failure
categories, per-class outcomes, full usage, uncertainty and deviations from the
official protocol. Keep personal profiles, authentication and private history out
of published traces. Public release/privacy and original completion gates remain
required; this page does not grant publication or submission authority.
