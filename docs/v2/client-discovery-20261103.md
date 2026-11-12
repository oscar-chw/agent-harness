# Find the product, then check access

3 November 2026. A missing tool or search result does not mean a product does
not exist. Use current first-party documentation before asking the user to
explain a named provider feature. Then check account availability, the supported
interface, current permissions and actual readback separately.

## Dot and Codex

OpenAI documents Dot as an always-on cloud agent that can coordinate ongoing
work and delegate to Codex. A connected local computer is separate from its
cloud computer. New child tasks receive selected context, not every parent
conversation. Sources: [Meet dots](https://learn.chatgpt.com/docs/dots),
[Tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory),
[October5–9 update](https://learn.chatgpt.com/docs/whats-new/dots-october-9-2026).

Our useful composition is: **optional Dot supervisor → bounded Codex tasks →
shared local harness state, knowledge and evidence**. Today this Codex session
is the actual orchestrator. A bidirectional Dot adapter has not been established.

Current discovery evidence:

- Official product and Codex coordination are documented.
- No direct Dot-message method was found among this session's available tools.
- The recent Codex thread inventory and enabled-surface inventory did not
  identify a Dot conversation. Those inventories are not product/account censuses.
- Computer use explicitly refused `com.openai.codex` for safety reasons.
  Do not retry that effect through an undocumented route or weaken the boundary.
- No installation message has been sent. Keep delivery **NOT_SENT** until a
  supported channel returns actual delivery/readback evidence.

This is a scoped discovery/permission result, not proof Dot is unavailable to the
owner. Do not ask for credentials, invent API routes, create a replacement Dot,
or call a saved handoff a delivered message.

## GitHub Copilot

GitHub's October28 announcement describes a shared Copilot harness for new VS
Code sessions. Our compatibility check uses its native instruction/skill folders
and portable MCP schema; it does not assume every editor harness loads the same
format. [GitHub announcement](https://github.blog/changelog/2026-10-28-github-copilot-in-vs-code-universe-releases/).

The current reference says a set `COPILOT_HOME` replaces the fallback location
for portable MCP discovery. The adapter now selects that destination while
preserving editor-format configuration, instruction/skill locations and
unrelated servers. [Official MCP reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration),
[migration guide](https://code.visualstudio.com/docs/agent-customization/migrate-customizations).

Source/configuration tests and fresh local MCP reads do not prove that an
authenticated VS Code/Copilot session has loaded the integration. Native
verification is still required on each target device. Do not migrate or enable
the owner's disabled hooks as part of this compatibility repair.
