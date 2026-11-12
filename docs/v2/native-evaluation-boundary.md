# Native evaluation boundary

This optional development path checks a native Codex thread before generation.
It is not a full V2 release or permission to promote a learned procedure.

Use `harness launch --help` for the complete options. An enforced evaluation
needs a fresh request, pinned model and effort, read-only work and a sibling
oracle directory. Add `--eval-deny-root` and `--eval-enforce-boundary` explicitly.
Ordinary launches do not acquire this evaluation transport.

The handshake:

1. Confirm native ChatGPT login, without retrieving credentials.
2. Probe the named native command profile: task evidence readable, oracle denied,
   writes denied. Keep native managed restrictions.
3. Create a temporary thread and check its resolved model, effort, provider,
   profile, read-only policy and standard service tier.
4. Disable evaluation-thread MCP servers and plugin/app tools; check the full
   runtime MCP surface before sending the task. Global configuration is not edited.
5. Bind response and usage to that fresh thread and turn. After completion, use
   metadata-only terminal readback: temporary threads reject full-history reads.
6. Record the latest native total once. Cached input is already included in input;
   reasoning is already included in output. Never add either twice.

An unsupported profile, unexpected approval request, malformed protocol or
incomplete usage does not pass. Protocol failures leave a `.failure.json` record;
that path cannot silently start another invocation. Output collection is bounded.
A failure's observed usage remains partial/unknown, not zero.

Observed locally, 6 November 2026: command controls and an empty MCP surface;
one real-project cold handoff reader recovered current facts, next work and holds.
Its original fixture failure is retained: exact whole-object equality incorrectly
rejected the source-ID citation required by the prompt. The corrected factual and
citation check rejected eleven invalid variants, without another model call.

Limits: this does not qualify every native read route, backend model weights,
whole-task token benefit, universal session compliance or learning promotion.
The original sixteen-case comparison and actual device checks remain separate.
Current development evidence is under `.harness-work/full-v2-20261105/`.

Native protocol and permission controls follow [Codex App Server](https://developers.openai.com/codex/app-server)
and [Codex permissions](https://developers.openai.com/codex/permissions); installed-client
capabilities must still be checked rather than inferred from those documents.
