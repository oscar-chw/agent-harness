# Native turn closure is not provider-cost proof

**Current result:** source controls work, but the actual direct-usage capability
probe is **NOT QUALIFIED**. Learning promotion, whole-workflow token savings and
full V2 remain unqualified. Nothing here was installed or enabled by default.

## What the real source showed

The 1 MiB and 4 MiB tail probes did not include both boundaries of the selected
turn: their scope also included the following active turn. An 8 MiB scoped scan
found the whole 4,104,727-byte turn (itself below 4 MiB), then rejected a counter whose input/output counts
were zero while its last total was 108,556. The original failures are retained.

This stream cannot automatically be equated with provider usage. In the pinned
[official recomputation code](https://github.com/openai/codex/blob/ddd1812a51f4aded35c3ec5446672474d5cb546b/codex-rs/core/src/session/mod.rs#L5728-L5755),
Codex can emit a local context estimate with exactly that kind of zero-component,
positive-total shape. The local event resembles that path; the exact emitter in
the installed app build is **not established** by reading newer upstream code.
We do not delete the event, call it free, or certify complete usage from it.

## What changed

- `native_usage.inspect_turn` requires one matching start/completion and refuses
  nested or aborted boundaries. It checks an explicit source/thread/turn, a
  preceding counter anchor, source identity and exact bytes.
- A turn scan is capped at 32 MiB. Counter pages retain the existing 4 MiB limit
  and share an exact anchor; that anchor is not charged twice. Oversized gaps,
  missing counts, changed files and inconsistent counters still fail. No message
  bodies are returned. Whole-workflow completeness stays false.
- An **opt-in experimental** launch observer can require direct
  `rawResponse/completed` records. It checks thread/turn, unique response IDs,
  counts, native errors/retries and the terminal read barrier. It does not copy
  billing metadata and never falls back to context estimates.

The [upstream event definition](https://github.com/openai/codex/blob/ddd1812a51f4aded35c3ec5446672474d5cb546b/codex-rs/protocol/src/protocol.rs#L2175-L2184)
distinguishes exact response usage from estimated/replayed token-count state.
The [notification is internal-only](https://github.com/openai/codex/blob/ddd1812a51f4aded35c3ec5446672474d5cb546b/codex-rs/app-server-protocol/src/protocol/common.rs#L2082-L2086);
generated type availability is not evidence that stdio clients receive it.

## Actual admission and remaining work

One frozen, consumed, included-quota native invocation reached the terminal
barrier with the existing parent file/command controls intact. The expected direct
response usage was **not observed by this collector**. It did not retain an
inventory of unknown notification methods, so suppression versus an unsupported
delivery path remains unresolved. The partial native UI snapshot reported 23,053
input-plus-output tokens; it is not a complete provider receipt. The failure was
retained, with no controller retry, API-key fallback, promotion or global
configuration change. Native internal retries were not established.
This path is not admitted for current-client promotion or benchmark accounting.

A full regression also exposed a faulty memory canary: searching all response
bytes for `9000` rejects harmless numeric diagnostics. The corrected gate checks
the actual foreign fact and project identity. A harmless-9000 positive control
now passes; injected foreign facts, foreign IDs and wrong retrieval still fail.
The original two-failure reproduction and failed full run remain retained.

Next is a fully owned campaign that records every planning/preparation, worker,
review and retry cost. A source-supported zero-retry provider configuration is
only a candidate until native admission proves its included-login route and
effective settings. Do not spoof internal clients, change native guards, treat
unknown overhead as zero, or activate from these component tests.

Owner-local evidence is in `.harness-work/turn-closure-20261106/`; test/source
qualification and failed native capability admission have separate statuses.
