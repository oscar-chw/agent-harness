# Connected KB visibility: static diagnosis

3 November 2026. Static only; no tests/native calls, config/environment/process reads or changes.

Root reports CLIENT-CAPABILITIES.md is readable by a fresh explicit KB but absent
from live MCP. This establishes a visibility difference, not its cause.

Current server.py:198-212 lazily creates and retains one KB. KB:475-487 pins
explicit paths; HARNESS_KB_PATHS also disables live profile discovery. Default
mode instead rediscovers the selected home's profile on every _walk (537-539),
while original project/configured roots stay pinned. get:727-747 refreshes before
lookup and separates unavailable/partial discovery from ordinary missing IDs.
Replacing disk modules does not replace already-imported Python code/objects.

Hypotheses:
- Old loaded implementation: compatible with the observation; current source or
  installed file hashes do not establish the connected process's loaded revision.
- Explicit/pinned roots excluding the new file: also compatible, including a
  default list resolved by a caller then passed as explicit paths. It is a valid
  scope policy, not inherently a cache defect.
- Different harness home/profile or source alias/section ID: not distinguished
  by a fresh explicit-path success. That success need not use live's home or ID.
- Current default live-profile implementation, same home/readability/ID: should
  discover a newly published profile page without reconnecting. Its ordinary
  no-section result would warrant investigation, but those premises are unproven.
  Permission/discovery failures require their actual live result, not inference.

Minimal root readback: retain exact live get/page-list response and fresh response
for the same known ID. Current initialize serverInfo reports package version only;
it cannot separate overlays sharing dev3. Do not widen roots or force restart.

If missing observability blocks diagnosis, add one bounded read-only health seam:
loaded implementation/build identity captured at import, KB initialized flag,
captured selection mode (explicit/environment/default), live-profile flag and
opaque home/root identities plus availability counts. Use instantiated state,
not a new scan/environment dump. Disk hash alone is not loaded-code identity.
Expose no bodies, foreign cached paths or credentials; change no scope. Proposal
only; older servers lacking it still cannot be diagnosed from disk alone.

Root owns verification; cause remains NOT_ESTABLISHED.

