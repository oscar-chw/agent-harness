# Weekly learning intake (on demand, candidate only)

`harness improve --weekly-intake` is a small, local reader of changed capture
evidence. It is **not** a timer, model runner, skill generator or permission to
change rules. Run it by hand when reviewing a week of work:

```sh
harness improve --weekly-intake --since 0 --max-items 10 --max-output-bytes 2048 --json
```

A user message beginning with an explicit correction or teaching cue such as
“Please remember that…” becomes a *candidate observation*. The Stop hook binds
it to its actual current directory (the git root when present) by a local path
hash. It keeps the redacted excerpt plus hashes of the source message and
transcript event. A replayed event does not increment the count, and at most 20 event hashes are
retained per candidate. Intake returns the project hash for routing. These
hashes can match retained events but do not authenticate the speaker, establish
that two tasks were independent or relevant, or make a procedure active. A
later draft still needs project-local source files and distinct task inputs.

The `--since` value is the last returned cursor. The capture store is
atomically rewritten and capped, so a byte offset would silently miss edits.
The intake instead compares each retained candidate's count and digest with
the last delivered row in a private SQLite ledger under
`<HARNESS_HOME>/weekly-intake/`. It advances the cursor only for candidates
actually returned, caps one response by item count and UTF-8 bytes, and keeps
the last 52 content-free audit receipts. The returned `receipt_sha256` binds
the source digest, prior/next cursor and selected IDs. It is an audit pointer,
not a quality verdict. The byte cap is a conservative context-size control;
it is not measured model token usage.
The capture store is local to one harness home, not a project-indexed evidence
graph. Its rows do not prove which project or independent task produced a
repeat; that binding must be supplied by the later source-episode draft.

`NO_CHANGE` is terminal for that invocation: no candidate is proposed and no
model is called. A malformed, redirected, missing or rewound source, an evicted
previously delivered row, stale cursor, or output that cannot fit the budget
returns `HOLD` without advancing the cursor. Captured text is screened for
credential-shaped strings before it is shown; receipts store IDs and hashes,
not the captured summary or evidence. This reader neither authenticates a
claim's truth nor distinguishes two independent tasks merely from a repeat
count.

An item with `count >= 2` is still only a **candidate signal**. To draft a
repeatable method, use the existing source-bound
`skill_manage draft` / `harness improve --draft-procedure` path with distinct
task-input episodes. `harness improve --apply` currently rejects caller-attested
scores; local freeze/bind receipts stay `HOLD_UNVERIFIED_BOUNDARY` and do not
activate advice. Future promotion requires verified native actor isolation,
effective model and usage-to-artifact provenance, independent frozen grading,
and a matched held-out comparison with no per-case quality regression, a
measurable gain and aggregate tokens including overhead no greater than the
baseline. Legacy active rows without native verification are withheld from
recall; rollback and source-staleness checks remain. Weekly intake performs no
promotion, and no gain has been measured for the intake itself.

A recurring schedule would need a separately authorized scheduler and a
bounded run policy. This candidate command does not install one, wake chats,
buy usage, or start Claude/Codex. Review whether the captured source and
matched comparison are sound before any durable promotion.
