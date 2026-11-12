# Assisted source-reader probe: static pre-run review

3 November 2026. **One P2 failure-reporting finding.** No preparation, code/test/
gate execution, model/native call or activation by this reviewer. Root owns
criterion freeze, reproduction, execution and semantic review. This is one
explicitly assisted exposed case, not automatic semantic choice, efficacy or
all-app evidence.

## P2 — Unsuccessful attempts hit a success-only summary field

`native_probe.py:150–151` uses `result[k]` for `answer_chars` unconditionally.
The installed `launch._answer_fields`, lines240–244, returns answer=None,
answer_truncated=None, answer_ref=None and answer_retention=NOT_AVAILABLE for
non-completed results; it does not emit answer_chars. Therefore a normal returned
TIMEOUT, FAILED or OUTPUT_LIMIT result reaches this summary and raises KeyError.

Concrete counterexample for root, **not executed here**: have the installed API
return an otherwise ordinary TIMEOUT receipt with NOT_AVAILABLE retention and
no answer_chars. The final summary comprehension raises instead of reporting
that outcome and its usage status. No unusual filesystem attack is needed.
The native receipt and finally-block readback can already exist, so this is not
a claim their bytes are lost; the driver instead masks its intended terminal
summary with an unrelated exception after consuming its one attempt.

Small repair: treat completion-only answer fields as optional in the summary,
or conditionally include them while preserving the exact failure/usage result.
Do not invent a zero length/full answer for an unavailable result or clear the
consumed marker. Root should exercise success and each returned non-completion
shape before invoking the real probe. No driver edit is made in this review.

## Remaining scope reconciliation

- `HERE.parents[2]` resolves to the canonical repo for this driver's declared
  `.harness-work/retrieval/source-reader/` location. Fixture and receipt/oracle
  paths remain beneath that experiment directory. No alternative root or extra
  source campaign is selected by this calculation.
- Preparation binds the unchanged original contract hash and exact
  paraphrased-source-recovery question. It independently reads original
  supporting files, checks their original pins, and extracts supplied line
  windows into source-policy data. Worker input supplies only its checked
  question to this driver; its hash is recorded rather than treated as proof
  of original-source support. Current original windows use ordinary source
  lines; no claim of a general-purpose extraction validator follows.
- The weakened ticket note is intentionally pending after append's exact-claim
  check. Launch references only the current exact pointer record, not that
  pending note. Preparation therefore does not need to relax CANDIDATE recovery
  or promote the derived claim. Its actual source provenance includes the
  omitted approval condition; the uncited appendix remains outside those lines.
- Task/project instructions direct the reader to ordinary scoped CLI inspection
  and the explicit --sources option as needed. They forbid direct original/
  internal-store reads. A correct answer alone cannot establish this method:
  root must audit actual command events for ordinary read and true --sources
  recovery, exact returned citation/lines, and absence of a direct-body bypass.
- `run:135–142` exclusively creates attempt-consumed.json before calling launch
  once with timeout120 and no resume reference. There is no automatic retry;
  save uses exclusive creation, so a later invocation cannot silently reuse the
  reservation. A consumed marker alone proves neither a native start nor its
  outcome. Preserve it even on setup/execution failure.
- The installed API's default workspace_write=False and the explicit sibling
  oracle deny argument request a fresh read-only invocation. Oracle criteria
  reside outside reader-project, and task/context do not inject those acceptance
  fields. This is a requested permission boundary, not an independently proven
  OS isolation mechanism. Root must record actual tools/source visibility and
  observed compliance; do not infer it from instruction text alone.
- Frozen fixture/source/installed-module/driver/prepared-prompt identities are
  checked before the call. Config content digests and source/fixture drift are
  recorded afterward. These are as-of observations, not continuous monitoring
  or equality enforcement by the probe. Root must inspect nonempty drift or
  unequal config digests and retain the failed qualification. No config content
  was read by this reviewer; only driver source and installed API code were read.
- Native usage/status remain in the actual launch receipt; raw named stdout/
  stderr streams replace temporary streams without changing the call count.
  Cached/reasoning counts remain subsets. Missing/failed/partial usage is not
  zero or complete whole-task cost. Retained answers are resolved with read_answer
  only for completed native runs; root still judges source support and authority.

The original case additionally requires honest lexical/paraphrase limits,
same-scope frozen evaluation before semantic/reranking, preservation of originals
and no blanket private-history reread. The source-policy windows provide that
bounded design context, while the synthetic note makes actual stored-source
recovery observable. No result yet shows the reader states every requirement,
chooses the method unassisted or generalizes beyond this exposed setup.

## Exact inspected identities

| Source | SHA-256 |
|---|---|
| `.harness-work/retrieval/source-reader/native_probe.py` | `768df2853e25cb152e5e773a36726a8f5f9ba5272e92533736dff0165931b4c0` |
| `/Users/me/.agent-harness/lib/agent_harness/launch.py` | `1a23f46d762ba3fad113cdf25868b180c05d679d76569c83c6c9134ef17a4422` |
| `docs/v2/vault/acceptance-cases.json` | `dfc21103e64ae00d4bc9e6404aaa1481c440b18e8f11d020686be2574dac7343` |

Read the driver in full, relevant installed launch invocation/retention/receipt
code, the exact original case, and its two stated local support windows. No new
methodology/vault input or native response was graded. Source hashes/line reads
are not execution evidence. All proposed controls and the native proof remain
NOT_RUN by this worker; root must independently resolve the finding and freeze
the actual inputs/criteria before consuming a call.
