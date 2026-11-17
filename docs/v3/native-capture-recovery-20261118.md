# Reliable correction capture and recovery

Version 3.0.5 adds two collection mechanisms to the existing learning lifecycle.

## Codex prompt observations

The registered prompt hook reads Codex's documented session, turn, project and
prompt fields. An explicit correction or teaching request can produce a scoped,
redacted candidate. The native turn identifies retries. An independent turn
can contribute another occurrence. Literal numbers, letter case and full wording
remain part of a new Codex candidate's identity.

The existing recall output remains available when capture storage fails.
Prompt capture uses a short lock-acquisition budget so a busy store returns a
diagnostic within the hook's deadline. That busy delivery remains unrecorded
until retried. Malformed candidate objects retain their original bytes while
ordinary recall continues.
Ordinary requests produce no lesson candidate. Existing hook definitions and
native configuration remain in place. Actual native delivery depends on the
client's enabled and trusted hooks. Codex test-result capture remains unavailable.

## Process termination recovery

One bounded write-ahead intent records the candidate store's prior hash, desired
bytes and corresponding turn marker. Cooperating writers hold the existing
cross-process store lock. If a process exits between data and marker replacement,
the next capture, direct record or prune completes that pending operation first.

Unexpected candidate edits, changed intent contents and redirected marker paths
are rejected. The pending record is retained for diagnosis. Successful completion
clears it. Existing candidate and marker formats remain readable, and the existing
candidate cap still applies. This covers process termination. Power-loss durability
and hostile processes with the same filesystem access need additional controls.

## Evidence and limits

The frozen 3.0.4 reproduction produced nine failures and seven passing controls.
The first candidate passed 33 focused checks. Review then reproduced two further
defects in contention and malformed candidate handling. Their regression cases
are included in the final source gate. Eight independently broken source variants
were rejected, and restored controls passed. Paired local hook invocations kept
identical context output while recording corrections in the candidate arm.

These results qualify the exercised collection and recovery mechanisms.
Native model adherence, reasoning improvement, transfer, aggregate token savings
and other-device uptake need their own evidence. Candidate observations remain
outside active methods until the existing independent evaluation and adoption
requirements are satisfied.

The machine-readable qualification is in
[the result record](../../eval/results/v3-native-capture-recovery-20261118.json).

## Protocol references

Codex documents the stable prompt-event fields and separate native hook trust.
The transcript format is explicitly unstable, so this integration reuses the
registered prompt event. [Prompt event](https://learn.chatgpt.com/docs/hooks#userpromptsubmit),
[common fields](https://learn.chatgpt.com/docs/hooks#common-input-fields),
[hook trust](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks).
