# v1 acceptance matrix — public candidate

25 October 2026. `PASS` applies only to the named check and source revision;
`PARTIAL` is narrower evidence, `NOT_RUN` means no qualifying run, and
`BLOCKED` names an unmet boundary, and `NOT_QUALIFIED` means a required runtime
boundary is still unverified. This matrix does not authorize model calls,
installation, or rollout. See the [source/evidence graph](source-evidence-graph.md)
for research coverage rather than treating a linked URL as an adopted feature.

| Claim | Existing mechanism and receipt | Status | Required next evidence |
| --- | --- | --- | --- |
| CPU source and integration behavior | On `adc33c4`, `HARNESS_STAGING_PYTHON=/opt/homebrew/bin/python3.11 PYTHONPATH=src python3 -m pytest -q tests ./eval` exited 0: **1322 passed, 2 skipped, 2 xfailed**. The later POSIX editor-home guard at `5c25973` passed **171 affected tests**, lint, diff check, and a fresh-clone history secret scan; the full suite was not repeated on that revision. | PARTIAL | Run the configured full suite on the eventual exact release source and read its exit result; then verify the installed package and native runtime separately. |
| Raw-evidence retrieval baseline | Source receipts plus current FTS/BM25 retrieval exist. [Raw-RAG v1](https://arxiv.org/html/2610.30755v1) is a selected primary research baseline, not an installed component. | NOT_RUN | Frozen authorized export, same questions/reader/evidence budget, revision and withdrawal negatives, answer-support and whole-campaign cost comparison. |
| Optional reversible document view | Source spans and bounded context packets exist; [TextFold upstream format](https://github.com/chenxiachan/textfold/blob/main/docs/format.md) is a presentation reference, not an installed plugin. | NOT_RUN | Fixed documents with hidden conditions and changed-source negatives; require exact original-span recovery and measured total tokens/latency. |
| **Independent procedure promotion** | `procedures.change()` now refuses caller-written scores, even when `grader_sha256` looks valid. `freeze_case()` hashes task and answer before artifacts exist; `bind_hold()` rechecks those hashes, hashes actor artifacts and complete native-format usage receipts, computes a narrow exact-byte grade and stores one immutable local receipt per task. The receipt explicitly says `HOLD_UNVERIFIED_BOUNDARY`; it cannot activate a method. Existing active rows without native verification are quarantined from recall as `held_unverified`, not deleted. Synthetic active-row fixtures still test recall and rollback, not model transfer. | **BLOCKED** | Prove the actor could not read the frozen answer in the actual native run; bind the effective model/effort and provider usage to the actor artifact, add an independently run grader with a frozen version, then qualify a paired held-out comparison. Do not promote from local hashes alone. |
| Teach → versioned method → fresh selective recall | Explicit teaching/correction becomes a redacted local candidate with a project-path hash and up to 20 distinct source-event hashes. A repeated event stays dormant; existing procedure tests exercise scoped recall and rollback with synthetic, caller-supplied comparison scores. Distinct events do **not** prove distinct relevant task inputs. | PARTIAL | Require two independently sourced relevant task episodes, source-bound method draft, the independent promotion receipt above, irrelevant-task and changed-source negatives, rollback, then a fresh-client held-out model check. No current CPU receipt proves model transfer. |
| Native answer-pack isolation and effective model identity | `launch.execute()` can request a bounded model/effort and an eval deny root, but reports `permission_boundary: requested_eval_profile_unverified` and `effective_model_evidence: UNKNOWN`. | NOT_QUALIFIED | Observe effective sandbox denial of the frozen oracle for the actual actor, pin effective model/effort and complete usage, then run a separately authorized bounded paired trial. |

The immediate CPU step is the **independent promotion binder test** in the
fourth row. It must fail before implementation; adding a hash field to the
caller JSON is insufficient. Only after that boundary is demonstrated should
an authorized native A/B test evaluate whether a taught method improves work.
