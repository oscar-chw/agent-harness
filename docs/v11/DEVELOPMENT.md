# v1.1 development: observed models, daily discovery and verified learning

Started 28 October 2026. Source milestone, not a production release or a daily job activation.

## Research and decisions

The [official Work/Codex model guide](https://learn.chatgpt.com/docs/models) documents
Luna for focused repeatable work, Terra for writing/visual work, Sol for sustained
work, and Astra for demanding workflows. These are vendor recommendations, not a
measured ranking on our tasks. The guide says Terra needs CLI 0.159.0 or later.
Exact identifiers and efforts are checked separately against the client's local
model cache; cache visibility is not proof of a successful dispatch or subscription entitlement.

Four requested families are registered in `content/discovery.toml`:

| Family | Exact ID | Proposed effort | Bounded role |
| --- | --- | --- | --- |
| Luna | gpt-6-luna | low | Individual-source extraction/triage |
| Terra | gpt-6.1-terra | medium | Routine grouped notes; check the synthesis |
| Sol | gpt-6.1-sol | high | Implementation and conflicting evidence |
| Astra | gpt-6-astra | high | Explicit difficult/high-impact escalation |

The role/effort mapping is a user-requested candidate policy, not a benchmark
result. No inferred numeric price, latency, reliability or capability score.
The existing route resolver and its context/gate/usage receipts remain in charge.
Unavailable pairs hold; they are not silently replaced with unrelated models.

## Public commands

- `harness model-registry`: read-only local observation, public source pointer,
  supported efforts, unknown performance and missing-model status.
- `harness model-registry --routing-candidate`: emit an override for the existing
  resolver only when every requested pair is visible. It does not write a native
  configuration; automatic progression remains disabled. Normal explicit user
  overrides still take precedence if someone later applies this profile.
- `harness daily-discovery`: at most one cycle per 24 hours. Fetch only the two
  reviewed official model Markdown and documentation-index URLs, each at most 256 KiB with a 12-second total fetch deadline (child killed and reaped),
  plus a 10-second socket timeout; redirects are refused. Record hashes, source text, local registry,
  failure state and the previous successful snapshot in a separate local audit DB.
- `harness daily-discovery --schedule`: describe a 24-hour harness command. This
  is an **inactive schedule specification**, not a registered OS timer. No daily
  update is claimed enabled.

A changed source creates `PROPOSED`, never an install or a promoted skill. An
unchanged snapshot avoids duplicate synthesis; a fetch failure keeps the old
baseline and is visible. Concurrent invocations serialize. At 31 hot audit rows, exact older rows rotate into compressed archives with hash/readback validation before the hot copies are removed. The latest attempt and successful baseline stay hot. A 32 MiB archive cap and 1 MiB encoded-payload cap remain; capacity exhaustion is a visible RETENTION_HOLD before another fetch, never silent deletion or unlimited growth. No model calls occur in the discovery cycle.

### Native schedule controls

macOS only: `harness daily-discovery --enable-schedule` installs a per-user
LaunchAgent with a pinned runner copy, `RunAtLoad` and a 24-hour interval.
`--schedule-status` reads back launchd and the plist identity; `--disable-schedule`
unloads the job and archives its plist while retaining the runner and audit.
No administrator rights, model calls, credentials, code installs from the web,
or native model-setting changes. Other hosts return an explicit unsupported
status. These source controls require separate actual-host qualification before
claiming they are enabled anywhere.

The scheduled command pins the bundle manifest and checks code before invocation.
This catches unintended drift; it is not isolation against a malicious same-OS-user
who can edit launchd jobs and their receipts. A user agent runs while its user is
logged in; this is not an always-on remote service. See [Apple's launchd guidance](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html).
`--history` reads a bounded audit summary without putting downloaded page bodies
into model context. Sources remain data; proposals never execute themselves.

## Learning and rollout

Reuse the existing source-bound procedure prepare/draft/inspect/correct path.
A useful discovery can inform a candidate, but a news article alone is not a
successful task episode. Versioned corrections retain previous evidence.
Promotion remains held until independent frozen evaluation and actual model/
usage provenance support quality >= baseline AND aggregate tokens <= baseline.
Tests do not establish that a model-generated method improves real tasks.

The installed development package is unchanged by this source work. Remaining release work: isolated proposal evaluation and promotion receipts, broader link triage and matched task evals for routing/learning. Native scheduler activation/readback/disable is qualified locally below.

## Budget and first intake

First batch: five explicit-harness links, one Luna-low scout, at most twelve web
operations and five minutes. Five sources could not be accessed; all remain
unread/unverified. No post content or mechanism was inferred. Prior reference
matches and exact provenance are retained in the private intake; this public
note does not publish conversation identifiers or personal source timestamps.

Quota telemetry exposed no reliable remaining-token count. Reserve logic pauses
at <=12,000 observed remaining tokens or before a request would leave <10,000.
Percentages are never converted. Unknown telemetry stays UNKNOWN; callers need
an explicit bounded allowance, not an invented token balance. Current execution
uses one scout plus one bounded review, no paid API or model benchmark campaign.

Live source probe: the changelog Markdown endpoint returned 404 and its HTML exceeded the fixed 256 KiB limit. Those failures remain recorded; the limit was not raised. The cycle instead checks the documented official model page and documentation index at its resolved direct URL. Full changelog ingestion remains deferred.

After repairing that source list, a bounded live canary in an isolated store produced PROPOSED with activation HELD; an immediate second invocation returned NOT_DUE. This verifies fetching and cadence, not an installed OS schedule or semantic performance gain.


Local native qualification: the owner-authorized Studio timer was enabled,
read back as loaded, completed its first discovery run with exit 0, then was
disabled and read back as DISABLED. Re-enabling and readback passed; the audit
DB hash was unchanged across that lifecycle. The job is currently enabled on
that host only, using a frozen candidate runner. The general installed package
was not replaced. This does not prove execution on a future day while logged
out/asleep, or any model/skill promotion.

A stopped job is considered absent only when launchctl returns its observed
absent-service result for this exact label. Other readback failures remain
errors, never successful disable receipts. Code/file mutation controls and
bootstrap failure cases are included in the scheduler tests.


Retention renewal: `--history` includes compressed archive pointers, SHA-256 and
record counts. At archive capacity the timer remains registered but each due
invocation exits nonzero with RETENTION_HOLD before fetching. Keep the archives;
move to separately verified retained storage only under an explicit retention
policy, then renew capacity. No automatic deletion/export destination is assumed.
Normal operation now passes the old 31-run limit; bounded storage can still
require a visible renewal decision. Existing local memory and transcript stores
are never part of this rotation.
