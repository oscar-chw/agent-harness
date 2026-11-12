# Copilot compatibility: bounded current-doc review

3 November 2026. **Concrete MCP destination gap; runtime unchanged by worker.**
Official current bodies were read, plus Copilot adapter, shared-skills helper,
Copilot memory tests and relevant existing adapter controls. No test, install,
login/native session, model call or client/config/guard change performed.

## Current documentation and source fit

VS Code distinguishes profile/workspace `mcp.json` with `servers` from portable
Copilot configuration with `mcpServers`. Its current reference explicitly uses
`$COPILOT_HOME/mcp-config.json`, falling back to `~/.copilot/mcp-config.json`;
with the override set it does not inspect both directories. Remote resolution
uses the remote environment. [Official MCP configuration reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration#automatic-mcp-server-discovery).

The migration guidance distinguishes Copilot from Local sessions: Copilot uses
skills rather than `.prompt.md` workflows. It lists `.agents/skills` at workspace
and user scope as supported skill destinations. User instructions migrate to
`~/.copilot/instructions`. Configured instruction/skill locations remain supported
for editor forwarding; calling those settings deprecated/Local-only is stale.
[Official migration guidance](https://code.visualstudio.com/docs/agent-customization/migrate-customizations).

The instruction reference lists `~/.copilot/instructions` for targeted user
instructions, `.github/copilot-instructions.md` for repository-wide guidance,
and `applyTo: '**'` for file-wide applicability. It also distinguishes inline
suggestions from instruction-consuming agent sessions. No COPILOT_HOME relocation
rule for instructions was present in the inspected article. Therefore this MCP
finding does not justify moving instructions or skills. [Official instruction reference](https://code.visualstudio.com/docs/agent-customization/custom-instructions).

The owner's October28 change is context for urgency; this review does not
independently establish the rollout date or the user's installed session target.

## Concrete defect and minimum change

`CopilotVSCodeAdapter._changes` always plans the portable file under
`ctx.home/.copilot/mcp-config.json`. With a nondefault COPILOT_HOME, that output
misses the documented portable destination. VS Code-format forwarding can still
work for eligible servers, so this is not proof every Copilot session loses MCP;
it breaks the adapter's promised portable configuration path.

Root can choose the portable MCP directory from the override, otherwise use
`ctx.home/.copilot`, and feed that file into the existing JSON/JSONC merge/refusal
helper. Preserve other servers/top-level data and invalid-file refusal. Keep
VS Code user/remote MCP, instruction paths, shared skills and hooks untouched.
Empty/relative/tilde override conventions were not specified by these pages;
do not invent broad relocation semantics to solve the evidenced absolute-path
case. No default permission or hook migration is required.

`base.shared_skills` already plans `.agents/skills` at its selected user/project
scope. `tests/test_copilot_memory.py` exercises generated default portable and
editor entries through fresh harness MCP processes and the shared memory store;
it does not set COPILOT_HOME or operate a logged-in VS Code Copilot session.
Thus it cannot catch this destination mismatch or certify native loading.

## Authored root-owned controls

New `tests/test_copilot_universe_compat.py` covers unset fallback, an absolute
override moving only the portable target, preservation of JSONC/unrelated server
data, and refusal of malformed override config without silently falling back.
It only plans changes in disposable paths. **NOT_RUN here**; root must preserve
the failing-first result, apply the smallest repair, and run these plus existing
adapter/context/shared-memory/merge controls. No previous test was weakened.

Document/schema compatibility, local process memory continuity and actual VS Code
Copilot login/loading/use are separate evidence. No native or interview demo
success, synchronization, efficacy, release or all-device claim follows here.

Inspected source SHA-256:

- `adapters/copilot_vscode.py`: `2ac741be0c73525fdb9131add64832787fe177e600dea8e94eadf3baefe5cb21`
- `adapters/base.py`: `b47fe66782eac174df8ac184d6b6f144076513d008994f5e15f977f94d3140a2`
- `tests/test_copilot_memory.py`: `bb14ea1c5b1eb875e2fe28808d16d1f575f3a3b5c6821cd0297a44c4ed7a8c2c`

Adapter paths above are under `src/agent_harness/`. Web read scope was the
current migration/MCP/instruction bodies and relevant tables, not linked provider
pages. Markdown endpoints failed through the web tool; rendered primary bodies
were read instead. Hashes and authored tests are not passing verification.
