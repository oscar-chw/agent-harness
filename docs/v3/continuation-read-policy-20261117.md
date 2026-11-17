# Continuation policy result

The board-first sentence stays outside the default guidance. Both arms recovered
the exact task goal and next action in both cases, and preserved the absence of
verified completion. Candidate inference use increased by **9.64%**.

| Measure | Current guidance | Board-first candidate |
|---|---|---|
| Correct task recoveries | 2/2 | 2/2 |
| Reported input plus output tokens | 176,028 | 192,993 |
| MCP reads by case | 1, 2 | 1, 1 |
| Cached share of input | 70.14% | 74.24% |

## What the trace establishes

Fewer MCP reads did not produce lower measured token use. One candidate run had
a 59,336-byte native memory-instruction block. Its matched baseline had 33,776
bytes. The initial input counts differed by 6,166 tokens. These observations
identify inherited context size as a variable to control and measure. They do
not establish which component caused the expansion.

Included-quota economics remain unmeasured. Cached input is already part of
total input, so the aggregate counts include it once.

The two paired token differences were −679 and +17,644, with descriptive standard
error 9,161.5. Two authored cases establish no population or transfer claim.
The requested native profile disabled remote apps for the study and selected
the shared memory read tools. Native host policy remained in force.

## Accounting and adoption

Four fresh native calls used 369,021 reported tokens across both arms. The final
in-flight call exceeded the 350,000 planning ceiling by 19,021. No further call
started. An earlier CLI startup failure is retained as one consumed attempt
with unknown usage. Preparation, review and whole-project costs remain unmeasured.
The candidate is rejected for the tested profile, with promotion NOT_GRANTED.

Before generation, the controller checks native ChatGPT account mode, an open
included window, the selected command/store and configuration validity. Credit
availability alone does not mean credits were used. Exhausted included windows
and API-key accounts are refused. The credit-admission correction follows the
[official pricing guidance](https://learn.chatgpt.com/docs/pricing).

The study instrument has failing-first controls for invalid actions, source
errors, frozen-data changes, unknown usage, consumed attempts and configuration
rejection before model launch. [Instrument](../../eval/continuation_iteration.py),
[checks](../../tests/test_continuation_iteration.py),
[aggregate receipt](../../eval/results/v3-continuation-read-policy-20261117.json).

The next comparison should measure task-scoped native context while retaining
shared project memory. The existing release keeps its qualified memory and
adoption mechanisms. Learning efficacy retains its independent outcome gate.
