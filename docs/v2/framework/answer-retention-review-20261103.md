# Native answer retention: bounded static review

3 November 2026. **No actionable material finding in the inspected diff.** This
is source review, not a test result, runtime qualification or release approval.
Root owns reproductions and verification. No native answers or root reasoning
were read for this assignment.

## Scope and inspected identities

Exact comparison: `.harness-work/retrieval/answer-pass/launch.py.before` versus
`src/agent_harness/launch.py`; reviewed all of
`tests/test_native_answer_retention.py` and the reused
`qualification.Bindings` path/read/final-currentness boundary. Read the adjacent
event extraction, status/receipt construction and existing source-path helper
only to understand the changed call sites.

| File | SHA-256 |
|---|---|
| `.harness-work/retrieval/answer-pass/launch.py.before` | `5e45f5e68ee489f238d77234a82fa1e1a0de20b167f82d65d1e59b97ce00525e` |
| `src/agent_harness/launch.py` | `1a23f46d762ba3fad113cdf25868b180c05d679d76569c83c6c9134ef17a4422` |
| `tests/test_native_answer_retention.py` | `0d076a0a3a660e8597368379d561de02be147a4a5789622688f2813ba52ed520` |
| `src/agent_harness/qualification.py` | `5c5a776191a80b87199b8b2e665e8c5baa283727c8046a7d0dc329fd42bc6e7e` |

Source hashing/read commands completed; no test, mutant, case or native process
was executed by this reviewer. These hashes identify the inspected bytes only.

## Contract reconciliation

- `launch.py:557–560` retains the last completed agent-message text before
  previewing it; the former unconditional 8192-character slice is removed at
  this extraction point. Selection of the last agent message is existing
  behavior, not proof that every preceding message is a final answer.
- `_answer_fields`, lines240–270, keeps a bounded inline preview and explicit
  truncation/character-count/full-hash metadata. Short answers need no sidecar.
  Long answers within the reused per-file budget get an exclusively created
  0600 sidecar. Existing targets are checked before launch at lines354–359;
  a later creation conflict is caught without overwriting the other artifact.
- A sidecar write/boundary/budget failure returns retention FAILED with no full
  answer reference. `execute`, lines617–622, can still record the completed
  native invocation and its usage separately. COMPLETED_UNGRADED therefore does
  not claim complete retention or answer quality. Consumers must check retention
  or call `read_answer`; continuing to grade the preview alone would bypass this
  new contract and is outside the inspected consumer scope.
- `read_answer`, lines279–311, refuses legacy completeness-unknown receipts and
  invalid retention combinations. Sidecars pass through Bindings, including
  current path/integrity checks, and must match declared bytes, full answer
  hash, character count, exact preview and truncation state. Decoding does not
  imply semantic truth or authenticate who authored the receipt.

## Adversarial cases represented by the test source

Tests44–58 check a long answer's Unicode tail, exact UTF-8 bytes/digest, private
mode, complete reader result and persisted reference. Tests61–69 cover the
inline boundary including exactly8192characters. Tests72–81 require a preexisting
sidecar to block before a subprocess call. Tests84–104 challenge changed body,
missing sidecar, changed preview, traversal and a symlink. Tests107–121 require
late conflict to preserve the existing file and produce a visible unreadable
full-answer result. Tests124–138 retain over-budget failure and reject legacy
metadata absence. These are meaningful source-level assertions, **not reported
passes** from this reviewer.

I found no concrete counterexample in this scope requiring a code/test change.
No claim is made about crash durability, arbitrary hostile concurrent filesystem
mutation, other consumers, native model behavior, all v2 flows or acceptance.
Those properties are not established by this bounded static review. Root should
retain the original failure and run the actual affected tests/controls against
the current subject before qualifying the correction.
