"""Kimi Code CLI: AGENTS.md, mcp.json and the shared .agents/skills directory.

Conventions verified 2026-11-09 against:
- https://www.kimi.com/code/docs/en/kimi-code-cli/customization/mcp.html
- https://www.kimi.com/code/docs/en/kimi-code-cli/customization/agents.html
- https://www.kimi.com/code/docs/en/kimi-code-cli/customization/skills.html
- https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/data-locations.html

Kimi owns its permission and model defaults. This adapter adds shared harness
interfaces, additive user hooks and tier agents without changing another client's
execution policy or model routing.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Tuple

from .. import routing
from .base import Adapter, Ctx, FileChange, mcp_servers, shared_skills, which
from .claude_code import check_guard_command, guard_command, hpath
from .copilot_vscode import json_change, merged_map, stdio_entry


def kimi_home(ctx: Ctx) -> Path:
    override = os.environ.get("KIMI_CODE_HOME")
    return Path(override).expanduser().absolute() if override else ctx.home / ".kimi-code"


class KimiAdapter(Adapter):
    name = "kimi"
    title = "Kimi Code"

    def detect(self, ctx: Ctx) -> bool:
        return which("kimi") or kimi_home(ctx).is_dir()

    def _config_dir(self, ctx: Ctx) -> Path:
        if ctx.scope == "project" and ctx.project is not None:
            return ctx.project / ".kimi-code"
        return kimi_home(ctx)

    def _changes(self, ctx: Ctx) -> Tuple[List[FileChange], List[str]]:
        refused: List[str] = []
        config = self._config_dir(ctx)
        ours = {name: stdio_entry(command, with_type=False) for name, command in mcp_servers(ctx).items()}

        def build(existing: dict) -> dict:
            servers = merged_map(existing, "mcpServers", ours)
            current = existing.get("mcpServers", {})
            current = current.get("harness") if isinstance(current, dict) else None
            if isinstance(current, dict):
                # Keep the owner's client-specific cwd/env/enablement when refreshing the owned launch command.
                harness = dict(current)
                harness.update(ours["harness"])
                servers["harness"] = harness
            return {"mcpServers": servers}

        mcp: Optional[FileChange] = json_change(
            config / "mcp.json", build, "Kimi MCP: mcpServers.harness (stdio)", refused)
        changes = [FileChange(config / "AGENTS.md", "replace", ctx.rules,
                              "Kimi agent rules (replaces the file; backup kept)")]
        if mcp is not None:
            changes.append(mcp)
        return changes, refused

    def _hooks(self, ctx: Ctx) -> List[dict]:
        prefix = "PYTHONPATH=" + hpath(ctx, "lib") + " python3 -m agent_harness.cli "
        return [
            {"event": "PreToolUse", "matcher": "Bash", "command": guard_command(ctx), "timeout": 5},
            {"event": "PreToolUse", "matcher": "Edit|Write", "command": check_guard_command(ctx), "timeout": 5},
            {"event": "Stop", "command": prefix + "_hook-kimi-stop", "timeout": 30},
            {"event": "SessionStart", "matcher": "startup|resume",
             "command": prefix + "_hook-context", "timeout": 5},
            {"event": "UserPromptSubmit", "command": prefix + "_hook-prompt", "timeout": 5},
            {"event": "PreCompact", "command": prefix + "_hook-kimi-precompact", "timeout": 5},
        ]

    def plan(self, ctx: Ctx) -> List[FileChange]:
        changes = self._changes(ctx)[0]
        config = self._config_dir(ctx)
        if ctx.scope != "project":
            changes.append(FileChange(config / "config.toml", "merge-toml", {"+": {"hooks": self._hooks(ctx)}},
                                      "Kimi guard, recall, context and compaction hooks; existing hooks stay"))
        if routing.available(ctx.content):
            for name, tier in routing.resolve(ctx.content, ctx.home, ctx.profile).items():
                changes.append(FileChange(config / "agents" / f"{routing.PREFIX}{name}.md", "replace",
                                          routing.kimi_agent(name, tier),
                                          f"subagent {routing.PREFIX}{name}: "
                                          f"{tier['kimi']['model'] or 'default model'}, effort {tier['kimi']['effort']}"))
        if ctx.scope != "project":
            changes.append(FileChange(config / "agents/harness-orchestrator.md", "replace",
                                      routing.kimi_orchestrator(),
                                      "main agent with bounded built-in delegation"))
        return changes + shared_skills(ctx)

    def notes(self, ctx: Ctx) -> List[str]:
        return self._changes(ctx)[1] + [
            "Start a new Kimi session to load newly added MCP servers, hooks and agents; /mcp shows connections.",
            "Kimi permissions and model defaults stay unchanged; workers pin their tier with CLI/environment options.",
        ]
