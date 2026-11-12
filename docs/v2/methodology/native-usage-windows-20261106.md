# Native usage windows — source candidate

Learning acceptance needs actual input/output measurements for every relevant
role. A goal-progress counter cannot supply that evidence. The current
[Codex app-server documentation](https://learn.chatgpt.com/docs/app-server)
describes active-thread usage notifications separately from thread metadata.
Our locally generated client schemas likewise expose the goal counter separately.

`native_usage.inspect_window` reads an explicitly selected, authorized native
JSONL source. It validates the thread header and exact byte interval, retains
counter pointers and hashes, and copies no message bodies. It follows no child
symlinks; an explicitly selected root alias is supported. Unsupported platforms
fail visibly. The interval is capped at 4 MiB; the separately bounded thread
header is at most 1 MiB. Both are reread to detect changes while observing.

The first usage record is an anchor. Later cumulative increments must match each
record's last-request counters. Duplicates count once; missing/null usage,
resets, invalid numbers, inconsistent totals and partial records fail. Cached
input and reasoning output remain subsets: neither subtract nor add them again.
A constant historical total offset stays explicit. A consistent local interval
does not repair historical discrepancies or establish whole-workflow coverage.

The source tests and copied-defect controls cover these behaviors. An owner-local
native interval also passed the transition checks, including its explicit
historical offset. This is bookkeeping evidence, not a model-quality benchmark.
The helper is not installed, a background collector or an activation mechanism.

Remaining work: bind authorized roles and campaign boundaries before inference,
include preparation, failed attempts, review and maintenance, avoid overlapping
counts, and seal only after the relevant native turns terminate. A fresh
app-server's local `notLoaded` status does not prove another app process stopped.
The current learning controller still refuses promotion. No caller-written
receipt or successful counter read clears the quality and complete-usage gates.
