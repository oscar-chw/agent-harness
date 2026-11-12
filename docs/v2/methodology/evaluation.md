# Frozen comparison contract

Proposed qualification protocol. No native comparison, held-out result or model
campaign was run for this packet. Visible `cases.json` is development material;
using its answers to tune a candidate makes it unsuitable as held-out evidence.

## Freeze before changing or running either arm

The integration owner records a manifest with baseline and candidate tree hashes,
all overlays, procedure/instruction bytes, corpus/source revisions, task input
hashes, split membership, grader/version hash, quality dimensions and thresholds,
model/effort, tools/permissions, budgets, stopping rules, attempt policy and run
order. Record the actual dirty-tree files; a shared HEAD alone does not freeze
this checkout. Retain a recoverable unchanged control, not a renamed candidate.

The baseline is the current authorized workflow **without the candidate method**,
including its existing native instructions and mandatory safety controls. The
candidate differs only by the proposed procedure or guidance. Use the same task,
available evidence, model/effort, tool access, budget and environment for a pair.
Reset task state between arms; do not let the control inherit the candidate's
answers or repair. Evaluate the untouched control in the same campaign, rather
than importing a convenient old token total. An obviously broken harness or
measurement pipeline invalidates the instrument; a genuinely weak task answer
is a baseline outcome to preserve, not a reason to discard that pair.

Keep development episodes, final held-out tasks and evaluator/oracle material
separate. An independent custodian prepares new held-out inputs and an outcome
oracle after the candidate is fixed; the actor gets only its authorized task
projection. Hashes detect byte reuse, not semantic contamination. Check near
duplicates, copied observations and reused answers as well as IDs. A case exposed
for diagnosis is development evidence for the next revision. A new final test is
needed after tuning on that exposure. Do not silently regenerate the baseline,
discard a hard case or shrink the denominator after seeing results.

For a narrow procedure, select only its claimed task class plus relevant
non-trigger controls. For a general methodology claim, cover all five classes
below. At least two disjoint held-out inputs per claimed class are a **minimum
coverage design**, not adequate statistical power or a current validator rule.
Predeclare more pairs/repetitions if needed to resolve the claimed effect. A
single successful canary can establish feasibility only. With a small sample,
report raw paired outcomes and uncertainty; do not call a noisy difference an
efficiency improvement. For replicated numerical effects, report paired effect
and standard error, along with the individual cases and known dependencies.

## Grade useful outcomes, not ritual compliance

Each case pins task-specific dimensions before running. The desired action is
evidence for judging the process; an equivalent simpler method that satisfies
the same observable contract is valid. A plan or diagnosis vocabulary earns no
credit by itself. Examples for **new** held-out cases:

| Class | Outcome oracle and required negatives |
|---|---|
| Coding | Execute the original reproduction, malformed/boundary inputs and affected regressions against the resulting artifact. A correct patch with a loosened valid check, unrelated damage or false completion fails integrity. |
| Research | Check whether the actual question was answered, each material claim is supported by its cited current source, missing evidence is disclosed and scope is complete. A citation that exists but does not entail the claim fails. Missing evidence must not become a guessed fact. |
| Debugging | Give an incident with competing causes and a probe that distinguishes them. Verify causal repair, recovery and original acceptance; retain valid independent branches. Include environment failure, faulty check, missing artifact, stale receipt and changed premise cases. |
| Daily work | Known arithmetic/text task completes directly and correctly without an unnecessary process burden. Add an ambiguous consequential external action that must remain held. Shortness alone does not pass correctness or authority. |
| Learning | A repeated observation may draft a source-bound dormant candidate; a copied observation, unrelated task, stale source or forged evaluation cannot activate it. Test correction, withdrawal, fresh-client selective recall and rollback separately from promotion. |

Coding's executable checks do not grade research support. Exact-byte equality
is suitable for a small exact-output task, not open-ended prose or design quality.
A model judge, if separately authorized later, needs calibration against sound
and deliberately wrong artifacts; it cannot be its own actor or see treatment
labels unnecessarily. No judge calls are authorized by this document.

## Count every attempt and every role

Use provider-reported **input plus output** tokens for each invocation. Cached
input is included in input, not subtracted and not added twice. Retain raw usage
events and the adapter's accounting semantics. Record unknown, partial, resumed
or ambiguous usage explicitly; do not replace it with zero or a byte estimate.

Let `B` be the sum of all baseline actor attempts plus all baseline-associated
preparation, retrieval, coordinator, review, grading, retry and maintenance model
usage. Let `C` be the same total for the candidate, **plus all candidate creation,
adaptation and failed candidate revisions in the registered campaign**. Common
evaluation/coordination usage is charged by a preregistered rule (equal sharing
when genuinely common), exactly once, never omitted from both sides. Machine-only
checks consume zero model tokens, but wall time and human corrections still need
separate reporting. Do not retrospectively enlarge `B` to pay for candidate R&D.

Acceptance requires, jointly:

1. All registered cases/attempts accounted for; usable native isolation/provenance
   and current artifact/evaluator bindings; no authority/integrity violation.
2. Candidate quality at least baseline **on every case and every dimension**.
3. `C <= B`, with at least one measured quality improvement or strictly fewer
   total tokens. Equality in both quality and tokens is no improvement.

For the current `procedures.evaluate()` arithmetic schema, per-pair `base.tokens`
must contain complete baseline charges and `cand.tokens` complete candidate run
charges. Remaining candidate-wide charges belong in `overhead_tokens`; do not
duplicate charges across those fields. A campaign collector must compute them
from invocation receipts. The function checks finite values and arithmetic; it
does not prove that a caller's `usage_complete: true` is true. Failed runs often
have partial usage; until completeness is established, the comparison stays
unqualified. A diagnostic actor-only table is useful but cannot pass acceptance.

The dev2 handoff retains a concrete caution: its second development round passed
the round comparison, while cumulative candidate attempts exceeded cumulative
controls. Those cases were reused for tuning and were not a fresh final held-out
comparison. This packet does not reinterpret that pilot as net R&D savings.

## Existing enforcement versus missing evidence

Paths below are source checks, not claims about a live campaign. Run from the
repository root. Parametrized test names represent their collected fault cases.

| Condition | Existing enforcing surface/check | What remains outside it |
|---|---|---|
| Same request/context; current artifact receipt | `method_control.decide`; `tests/test_method_control.py::test_failure_and_stale_dependency_never_become_authority`, `::test_independent_gate_feedback_revises_method_without_redefining_gate`, `::test_gate_receipt_cannot_pass_an_absent_artifact` | Hash binding does not authenticate the grader or assess gate adequacy. |
| No compulsory workflow for single ready work; failure-specific advice | `tests/test_method_control.py::test_direct_simple_work_and_plan_only_for_real_dependencies`, `::test_diagnosis_matches_failure_and_a_current_pass_supersedes_it`, `::test_bad_artifact_triggers_intent_gap_and_cause_analysis_without_user_diagnosis` | Native semantic selection and domain-quality adequacy remain unmeasured. |
| Correct a demonstrably faulty check while retaining valid coverage | Owner working rules and `standards` prescribe original failure, independent requirement, invalid control and re-verification; `coding-faulty-check` makes that contract concrete | No existing general runtime gate proves the requirement was independently settled or that the correction preserved valid coverage. This case is `contract_only`; root outcome review remains required. |
| Candidate/source/project binding and distinct evidence | `procedures._episodes`, `_bound_file`, `evaluate`; `tests/test_procedure_preparation.py::test_invalid_sources_are_refused_without_a_store`; `tests/test_v1_learning_loop.py::test_two_task_inputs_one_observation_do_not_establish_recurrence`, `::test_source_edit_after_draft_refuses_promotion` | Different source hashes do not prove independent or relevant events. |
| Held-out unique IDs and byte-disjoint unchanged inputs | `procedures.evaluate`, `freeze_case`; `tests/test_v1_learning_loop.py::test_renaming_a_development_task_does_not_make_it_unseen`, `::test_changed_heldout_input_and_duplicate_input_under_two_names_are_refused` | Semantic leakage, minimum class coverage, unseen custodian and actor oracle denial are not established. |
| Matched declared model/effort/tools/budget/benchmark; pinned grader | `procedures.evaluate`; `tests/test_v1_learning_loop.py::test_promotion_refuses_invalid_or_unmatched_evidence` (`context`, stale/project/schema faults) | This checks caller metadata, not effective model identity, unchanged control execution or grader independence. No complete native manifest enforcer is supplied here. |
| Per-case/dimension non-regression, complete declared usage, non-increasing aggregate tokens, measured gain | Same parametrized test (`regression`, `cost`, `unknown-usage`, `missing-dimension`, `no-gain`, nonfinite/overflow faults); `::test_equal_quality_and_lower_total_tokens_is_a_valid_gain`; legacy `tests/test_v1_legacy_promotion.py` | No verified collector yet proves all attempts/roles/R&D/common charges were included. `evaluate` is an arithmetic validator, not promotion authority. |
| Frozen answer/task and immutable artifact/usage/grader binder receipt | `procedures.freeze_case`, `bind_hold`; `tests/test_procedure_independence.py::test_local_binder_hashes_frozen_task_artifacts_grader_and_provider_usage`, `::test_local_binder_refuses_changed_or_missing_evidence`, `::test_concurrent_same_task_retry_is_idempotent_but_conflict_is_refused` | A single-run local receipt is not authenticated provider provenance or answer isolation; retries cannot be silently collapsed. |
| Unverified evidence cannot promote; legacy unverified rows do not recall | `procedures.change`, `_active`; `tests/test_procedure_independence.py::test_caller_written_scores_and_grader_hash_cannot_activate_a_method`, `::test_old_caller_scored_active_row_is_quarantined_from_recall`; preparation test `::test_prepared_candidate_drafts_inspects_corrects_and_still_cannot_promote` | Current path deliberately has no positive native promotion consumer. |
| Correction, withdrawal, scope and fresh-session recall mechanics | `tests/test_v1_learning_loop.py::test_skill_manage_correct_withdraws_bad_advice_in_fresh_session`, `::test_a_promoted_skill_stops_recall_when_its_bound_source_changes`, `::test_other_project_cannot_activate_or_rollback` | Active-state fixtures are synthetic. They prove consumer mechanics, not native promotion, transfer or universal compliance. |
| Outcome-level coding grading/missing-run checks | `eval/quality_grade.py`, `eval/quality_report.py`; `tests/test_quality_eval.py` | Historical coding gain rule uses median tokens up to **1.15×** and aggregate dimension totals. It is NOT the stricter v2 per-case/total-token gate and must not qualify v2 alone. Preserve it as its own historical instrument. |
| Complete general methodology/native/release qualification | Root `plan/v2-completion.md` nodes 2, 5, 6 and 7 name dedicated gates | At worker start their `.harness-work/v2-completion/check_*.py` scripts were absent. Required missing evidence blocks these claims; this documentation/replay cannot close those nodes. |

`tests/test_learning_arms.py` covers optional snapshot/nudge mechanics, not learned
method benefit. Neither an injected reminder nor a test count is an efficacy
measurement. Learning-observation code is owned by the orchestrator; this packet
does not duplicate its checks or certify its evolving implementation.
