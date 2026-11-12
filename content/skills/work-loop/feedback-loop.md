# Assess a bounded feedback experiment

Use optional `harness loop-check` when an actual optimization or iterative
experiment has matched baseline/candidate observations to assess. It reads
reported results; it does not run experiments, authenticate measurements or
schedule another attempt.

## Choose a proportional path
- Direct questions and tiny fixes use the existing work-loop and relevant check.
- Ordinary delivery without a useful scalar metric uses its acceptance checks;
  do not invent a score or require a Loop Card, extra agents or experiments.
- A real comparison can use required checks with `metric: null`; otherwise name
  the scalar metric and its units. Load this guide only when that comparison helps.

## Freeze before observing results
- Keep the objective, cases, required checks, evidence scope and attempt ceiling
  in the contract. Bind results to the exact contract bytes; retain old attempts.
- For a metric, freeze min/max direction, minimum useful effect and noise floor
  before seeing candidate results. A positive median gain must meet the minimum
  effect and exceed the noise floor; small fluctuations are not improvement.
- Use the same model, effort, tools and source visibility in both arms. Context
  hashes record the reported match; they do not attest effective model or access.
- Independent acceptance belongs outside the candidate's control. A model must
  not rewrite the oracle, checks, thresholds or scope to accept its own work.
  Correct a demonstrably invalid check through the existing review path, retaining
  its failure and valid controls; never silently redefine success after a result.

## Record the whole observation
- Each case needs distinct baseline/candidate run IDs, artifact hashes, evidence
  scope, every required check, metric samples and input/output token counts.
- All checks must PASS together on the SAME run and artifact. Never combine
  separate successful attempts or estimate joint success from marginal totals.
- Keep per-case quality/scope/correction failures visible; another case's gain
  cannot offset them. Median metric regression also rejects the candidate.
- Include adaptation, retrieval, review, failed attempts and maintenance overhead
  in complete candidate usage. Cached/reasoning counts are subsets, not extra
  tokens to add again. Missing usage stays UNKNOWN, never zero.

## Assess, then decide within authority
Run `harness loop-check --project-root ROOT --contract FILE --results FILE`
with bounded project-relative JSON evidence. Exit0 means ACCEPT_CANDIDATE;
exit1 means valid REJECT_CANDIDATE/INCONCLUSIVE; exit2 means invalid/unavailable
input. Unknown/unrun checks or incomplete usage prevent acceptance. Required
candidate checks must all pass; total candidate tokens must not exceed baseline,
and an observed check, token or above-noise metric gain is still required.

The assessment describes declared evidence, not proof the checks ran, source
truth or general efficacy. ACCEPT_CANDIDATE grants no skill/method activation,
native permission, installation, deployment or promotion; use their existing
independent evidence and authorization paths.

The attempt index is declared evidence, not a runner-enforced call ledger.
Stop at the frozen attempt ceiling (`stop: true`, `STOP_EXPERIMENT`), or sooner
when authority/resources end. Remaining attempts are not permission for calls.
Use the returned bounded next action as advice; do not bypass a refusal or repeat
the same failed approach. Report missing evidence and preserve consumed attempts.
