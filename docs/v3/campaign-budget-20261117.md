# Bounded learning follow-up

The next-call stop now covers development, native drafting and paired trials in
one campaign. Freeze an observed-token limit before any call with

```sh
harness improve --project /path/to/project --prepare-campaign /path/to/project/oracle/suite.json \
  --oracle-root /path/to/project/oracle --complete-usage --max-native-tokens 250000
```

Execution uses the saved ceiling. Attempts, provider receipts and failed stages
remain recorded. Both evaluation arms count toward consumption. Earlier development
and drafting usage is carried into the trial freeze. An in-flight call can exceed
the limit. The controller then stops before another call. This planning stop
provides no in-flight token guarantee.

An omitted limit preserves existing campaign behavior. Frozen call counts and
timeouts still apply. The limit cannot be raised at execution. Learning adoption
continues to require independently replayed outcomes and complete aggregate cost.
The previous generated-method loss and failed semantic orphan arm remain held.

A separate reuse correction distinguishes absent registration from absent
knowledge. Missing exact capability IDs now direct inspection of broader records,
skills and the local vault before external research. Source coverage still needs
inspection. The change establishes an actionable protocol, with model adherence
and token effects requiring their own measurements.

Regression tests use the production controllers and a fake native transport.
They establish call stopping, retained usage and unchanged adoption rules. They
provide no new native efficacy result. Stable v3.0.0 and its frozen release assets
retain their original evidence. This follow-up is qualified separately.

## MCP store correction

Configured server commands now carry an explicit harness store. This preserves
the selected store when a client filters inherited environment variables. Cold
stdio tests exercise a saved state, a fresh process and an automatic board packet
under a filtered environment. The original native probe returned correct answers
after filesystem fallback. Both recorded MCP state reads missed the fixture, so
its automatic-MCP claim is now unqualified. The original responses, usage and
budget failure remain in the corrected public receipt.

One subsequent fresh native session read the fixture through two MCP responses
and used zero shell commands. It answered correctly in 13.69 seconds and reported
102,522 input/output tokens. Its 90,000-token planning threshold was exceeded
in-flight, so the aggregate qualification remains NOT_QUALIFIED. The one-call
bound was honored. No second call followed. [Readback receipt](../../eval/results/v3-native-store-binding-20261117.json).

## Stop after a failed mandatory quality check

A campaign prepared with `--complete-usage` must pass every held-out
candidate answer and citation check before adoption. The controller now
stops after the first verified failure of that requirement and reports
`QUALITY_REJECTED`. It retains the failing grade, consumed requests and
usage. The result distinguishes planned trial calls left unrun from attempted
calls with missing usage. A later campaign still pays for all consumed
calls from the earlier rejected campaign, including its baseline calls.

The fixture ran the existing controller through a nine-call schedule.
A rejected candidate stopped after seven calls when the baseline came first,
and after five when the candidate came first. A baseline failure alone did
not stop the trial. Diagnostic-only campaigns kept full evaluation, and
the original adoption gate still requires complete replay. These controlled
transport results measure controller behavior. No native learning trial
or provider-token measurement was added.
[Regression cases](../../tests/test_v3_learning_cycle.py)
