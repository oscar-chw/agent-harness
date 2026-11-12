# Native procedure promotion remains held

Source diagnosis, 2 November 2026. Authority for native qualification and any
release belongs to the orchestrator and the owner. This packet performs neither.

## The actual boundary

`procedures.evaluate()` can validate declared comparison arithmetic and input
bindings. `freeze_case()` pins task/answer hashes before binding artifacts.
`bind_hold()` hashes the task, answer, artifacts, grader implementation and
single-run native-format usage, then stores `HOLD_UNVERIFIED_BOUNDARY`.
`procedures.change()` **unconditionally refuses the promotion branch**, including
apparently good comparisons and binder receipts. It is not a feature flag that
can be cleared by replacing a status field. Existing active rows without the
`native_verified_active` evidence marker are withheld from recall; writing that
marker directly would bypass the missing qualification, not supply it.

The underlying missing links are causal, not clerical:

- A frozen answer hash does not prove the actor could not read the answer through
  an accessible path, tool, retrieval result or previous context. Hiding a path
  from the prompt or separating two processes under one OS user is insufficient.
- `launch.execute()` currently reports `effective_model_evidence: UNKNOWN` and,
  for an evaluation profile, `permission_boundary:
  requested_eval_profile_unverified`. Requested settings do not prove the actual
  model/effort or effective native deny behavior. Tests of generated profile
  configuration do not establish the native runtime boundary.
- `bind_hold()` accepts caller-supplied usage JSON. It validates shape and hashes
  it, but does not authenticate a provider invocation or bind that invocation's
  complete usage and final artifact. A structurally complete receipt may still
  be copied or fabricated. Resumed/failed/ambiguous usage is not complete usage.
- An exact-byte grader is a limited mechanical oracle. Its code hash proves
  identity only. It does not prove a separate trusted invocation graded the
  actor's exact artifact, or that the oracle is adequate for open-ended work.
- No existing positive consumer converts independently qualified native evidence
  into an active procedure. CPU fixtures manually seed active-state rows to test
  recall/withdrawal. They are explicitly not a promotion implementation.

These findings agree with the retained v1 acceptance matrix and the dev2 handoff.
They do not imply that all local workflow/KB behavior is broken. Source mechanics,
installed readback, native behavior and broad efficacy are separate claims.

## Smallest credible qualification path

This is a proposal for the integration owner after separate campaign authority;
it authorizes no model run, native configuration change, install or release.

1. **Freeze one narrow candidate and the unchanged control.** Use genuinely
   independent source episodes and fresh tasks for the claimed procedure. Pin
   trees/overlays, development/held-out split, budgets, retry rules, oracle,
   dimensions and all-token collector as in `evaluation.md`. Start with exact
   structured outputs whose oracle can be independently executed. This qualifies
   only that narrow procedure, not general research or design judgment.
2. **Qualify native isolation before spending a task campaign.** Under an
   authorized supported native boundary, test allowed task projection access
   and denied oracle/evaluator access using harmless sentinels. Attempt the
   actual relevant read routes, including retrieval; retain effective runtime
   denial evidence. Include an intentionally exposed-oracle negative so the
   isolation verifier itself fails. If the native product cannot provide a
   verifiable boundary, retain HOLD and name the unsupported capability. Do not
   alter guards or substitute an unqualified executor.
3. **Qualify invocation-to-result provenance.** Bind request/run identity,
   effective model/effort evidence, environment/tool revision, start/end status,
   immutable artifact hash and provider usage events. Prove mismatched run IDs,
   altered artifact/usage, unknown identity and missing attempts are rejected.
   A requested model string or caller-signed assertion is not independent proof.
4. **Qualify the external grader.** Run a frozen independently controlled grader
   on the exact bound artifacts. Keep the answer/evaluator outside actor writes
   and reads. Test a correct control, incorrect artifact, changed grader,
   changed oracle, missing receipt and replayed receipt for another candidate.
   The sound control must pass; each named defect must fail for its own reason.
5. **Run the smallest authorized paired pilot, then independent final tasks.**
   Include trigger, irrelevant-task and changed-constraint cases. Preserve all
   attempts and charge every role, adaptation and failure. Enforce per-case/
   dimension quality non-regression AND complete aggregate tokens at most the
   unchanged baseline, plus a measurable gain. An inconclusive pilot remains
   inconclusive; a tuned pilot is development evidence. No campaign is run here.
6. **Add a narrowly scoped accepting verifier/consumer under review.** This is
   future runtime work outside the worker's scope. Consume only the independently
   authenticated evidence and exact frozen candidate. Revalidate project, source,
   split, artifacts, grader, complete usage, expiry/replay and authority before
   an atomic event/state change. Retain all current forged-score and binder HOLD
   negatives. There must be no caller-set `verified` shortcut, direct database
   update or unconditional removal of `change()`'s refusal. If these prerequisites
   cannot be verified, a manual assertion cannot turn the outcome into PASS.
7. **Test the promoted consumer and rollback at the claimed boundary.** Check
   fresh-client relevant recall, irrelevant-task silence, source change,
   correction/withdrawal, concurrent/retried consumption, wrong-project refusal
   and rollback. Recheck the exact integrated candidate and installed client;
   each additional device needs its own authorized readback. Retain historical
   versions and invalidate dependent claims when sources/runtime/model change.

The root's original `check_learning.py`, `check_native.py`, `check_release.py`
and device gate must bind this evidence rather than accept narrative status.
Their absence or missing evidence is a real hold. A local case replay is useful
preparation, and cannot replace steps 2–7. Existing quota, privacy, permissions
and no-paid-usage constraints remain in force throughout.

## Evidence to preserve on an unsuccessful attempt

Record exactly which boundary was unverified or refused, candidate/control and
oracle hashes, available native receipts, failed negative-control result,
partial/unknown usage, the independently valid completed work, next permitted
action and the prerequisite for resumption. Do not wake peers, poll models,
change native permissions or repeat an unchanged campaign to fill an evidence
field. A small honest HOLD is preferable to an accepting gate without proof.
