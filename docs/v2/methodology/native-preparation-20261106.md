# Native preparation of procedure drafts

The controller can now draft a procedure from explicit development observations
and retain the native usage that created it. **Drafting does not activate it.**
This development increment uses native Codex; it does not establish execution
support for every provider or application.

1. Freeze two or more distinct task/observation sources, the model, effort and
   timeout. Evaluator files cannot become preparation evidence.
2. Record the attempt as consumed, then make one bounded native drafting call.
3. Check observed model, file boundary, empty tool surface, usage and output
   schema. Save a source-bound proposed procedure; retain failed attempts.
4. When preparing a trial, resolve that preparation by its controller run ID.
   Include known earlier attempts on the same source fingerprints; unknown
   usage remains visible. Renaming files cannot erase the debt.

The controller runs these checks; caller-written scores or a JSON receipt cannot
stand in for execution. Procedure benefit still needs independent held-out
evaluation. Complete surrounding orchestration, review and maintenance accounting
is not yet qualified, so promotion remains held.

## Use the explicit native action

Store a preparation specification beneath an existing project-local directory
named `oracle` or ending in `-oracle`. It names 2–20 development episodes, each
with `task_id`, `path` and `task_path`, plus `schema: 1`, an available native
`model`, `effort` and `timeout_seconds` (at most 120). Episode files stay outside
the oracle; their combined projected evidence must fit 8 KiB. They are data,
not instructions or proof that an experience succeeded.

```sh
harness improve --project "$PROJECT" \
  --prepare-native-draft "$ORACLE/spec.json" --oracle-root "$ORACLE"

# Only this separate action consumes the frozen native invocation:
harness improve --project "$PROJECT" --execute-native-draft "$RUN_ID"
```

The native client uses its normal login. No credential export, paid-extra-usage
purchase or global permission change is part of this flow. Repeating a consumed
run is refused. Trials may consume a successful preparation through the Python
controller's `preparation_run_id`; that is provenance, not promotion authority.

## Observed proof and limits

One real preparation call used two retained, completed synthetic status-extraction
observations. It produced a proposed procedure, reported 23,881 input plus 219
output tokens (**24,100 total**), and its worker exited. Reasoning tokens are a
subset of output. No method became active. A cold reader recovered that usage
inside the trial store's write transaction. Six altered native observations
were rejected; five copied implementation defects were caught.

These are lifecycle/provenance checks, not evidence that the generated procedure
improves general work. The full functional source suite passed 2,316 tests, with
2 skips and 2 expected failures. The subsequent dev8 label change was checked as
a version-literal-only delta, with 22 version/package checks. Wider model costs
remain unknown and cannot be counted as zero. Full V2 is not yet qualified.
