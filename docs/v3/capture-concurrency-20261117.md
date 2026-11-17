# Reliable lesson capture across sessions

The capture hook records candidate observations when a check fails and later
passes, or a user supplies a correction. Concurrent sessions previously updated
one JSONL file through a shared temporary path without a transaction. Separate
Stop hooks could also read the same deduplication marker before either saved it.

## Repair

- Candidate read, merge and replacement use the existing cross-process store lock.
- A Stop hook checks its turn marker and updates the candidate count within that
  same lock. Concurrent Stops of one turn contribute one occurrence.
- Candidate pruning uses the same lock. It runs after the capture transaction,
  avoiding nested acquisition and stale pruning snapshots.
- Independent turns retain their recurrence count. Existing collection signals,
  redaction, source scope, caps and adoption requirements remain in force.

The original JSONL and marker formats remain readable. The store lock is shared
with existing memory operations and releases when its process exits.

## Checked scope

The first reproduction failed three real concurrent entrypoint tests through
missing temporary files. The repaired source passed those tests plus a pruning
interleaving and six independent capture-hook processes. Removing each of the
marker, record and pruning transaction protections independently made its
corresponding test fail. Restored controls passed.

These checks establish collection reliability for the exercised interleavings.
They provide no new claim about semantic lesson quality, model compliance,
learning transfer or aggregate inference savings. Existing independent procedure
comparison and adoption gates continue to decide whether a learned method helps.
A hard crash between separate candidate and marker persistence operations remains
a distinct recovery boundary. This patch addresses concurrent cooperating writers.
