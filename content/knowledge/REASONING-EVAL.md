# Reasoning guidance evaluation

## Adding generic guidance

On 17 November 2026, six fresh native Codex pairs covered24 authored closed-world
decisions per arm. Both arms answered24/24 correctly. Adding compact guidance
used150,194 input/output tokens against149,713 without it, an increase of481 tokens
or 0.32%. The candidate was rejected. This supports avoiding extra generic prose
on these already-solved tasks. It leaves broader reasoning competence untested.

## Compressing a guide already selected

A separate 12-call comparison used the existing 4,505-byte reasoning guide as the
baseline. The compact guidance retained24/24 correctness and used 150,194 tokens
against 155,643, saving 5,449 tokens or 3.50%. Each of the six pairs saved tokens.
Mean paired difference was minus 908.17 tokens with a 14.51-token standard error.
These are descriptive results on authored cases, not population confidence or
proof of improved intelligence. Both studies used gpt-6.1-sol at high effort.
All 24 upstream response identities were distinct across the two comparisons.

## What can be learned

Select the amount of reasoning context for the task. The compact recipe is a
candidate replacement where the full guide would otherwise be loaded. This
comparison does not justify adding it to every simple task. Keep the long
reference available for broader judgment, values and teaching that these cases
did not test. Native response behavior on a small suite cannot prove every
future session follows a policy.

The two tranches consumed 605,744 observed tokens, including the rejected candidate
comparison. Their ceilings were 300,000 and 350,000 tokens respectively, 12 calls each.
One earlier local fixture-layout failure made zero provider calls. Preparation
and surrounding chat cost remain UNKNOWN. Net project savings are not established.

## Inspecting the evidence

The public aggregate files are
`eval/results/reasoning-iteration-20261117.json` and
`eval/results/reasoning-compaction-20261117.json`. They retain acceptance results,
usage, uncertainty and receipt hashes without local machine paths or thread IDs.
Exact native requests, immutable event journals and provider receipts remain in
the local experiment archive. The failed first controller source is retained at
local commit 8bad4bd. Later source revisions do not retrospectively change those runs.
