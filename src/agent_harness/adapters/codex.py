"""Codex CLI: AGENTS.md, [mcp_servers.*] in config.toml, shared skills in ~/.agents/skills.

Per the provider specs (Codex 0.159): custom prompts (~/.codex/prompts) are deprecated in favour of
skills, so none are written; `[profiles]` tables are no longer read, so none are written; Codex's own
memories stay as they are (off by default).

A profile may add Codex settings of its own, merged key by key into the user's tables (their other
keys stay; uninstall takes out only these):

    [codex.config.features]
    use_legacy_landlock = true
"""
from __future__ import annotations

import os
import re
from typing import Dict, List

from .. import routing
from .base import Adapter, Ctx, FileChange, base_dir, mcp_servers, shared_skills, which
from .claude_code import hpath


class CodexAdapter(Adapter):
    name = "codex"
    title = "Codex"

    def detect(self, ctx: Ctx) -> bool:
        return which("codex") or (ctx.home / ".codex").is_dir()

    def plan(self, ctx: Ctx) -> List[FileChange]:
        root = base_dir(ctx)
        project = ctx.scope == "project"
        codex = root / ".codex"
        tables = {f"mcp_servers.{n}": {"command": c[0], "args": c[1:]} for n, c in mcp_servers(ctx).items()}
        # Pre-approve this server's tools only. "approve" is valid in Codex 0.145 (prompt|writes|approve) and
        # in the current MCP docs (auto|prompt|writes|approve); 0.145 rejects "auto", and then every harness
        # call came back "user cancelled MCP tool call" (eval 2026-09-30).
        tables["mcp_servers.harness"]["default_tools_approval_mode"] = "approve"
        for name, body in profile_tables(ctx.profile).items():
            if name[1:] in tables:                 # e.g. [codex.config.mcp_servers.harness]: extra keys for ours
                tables[name[1:]].update(body)
            else:
                tables[name] = body
        note = "agent rules (replaces the file)"
        if not project and (codex / "AGENTS.override.md").is_file():
            note += "; NOTE: your AGENTS.override.md takes precedence and hides it"
        changes = [
            FileChange(root / "AGENTS.md" if project else codex / "AGENTS.md", "replace", ctx.rules, note),
            FileChange(codex / "config.toml", "merge-toml", tables,
                       "registers the harness MCP server; other settings untouched"),
        ]
        if os.name != "nt":
            # Additive JSON merge preserves user hooks and leaves inline TOML
            # hooks untouched. Native Codex must still trust each definition.
            prefix = "PYTHONPATH=" + hpath(ctx, "lib") + " python3 -m agent_harness.cli "
            hooks = {
                "UserPromptSubmit": [{"hooks": [{"type": "command", "command": prefix + "_hook-prompt",
                                                  "timeout": 5, "additionalContextLimit": 1200}]}],
                "SessionStart": [{"matcher": "startup|resume|compact",
                                  "hooks": [{"type": "command", "command": prefix + "_hook-context",
                                             "timeout": 5, "additionalContextLimit": 6000}]}],
            }
            from .. import installer
            config = codex / "config.toml"
            before = config.read_text(encoding="utf-8") if config.is_file() else ""
            inline = installer.load_toml(installer.toml_merge(before, tables)).get("hooks", {})
            for event in list(hooks):
                groups = inline.get(event, []) if isinstance(inline, dict) else []
                command = hooks[event][0]['hooks'][0]['command']
                equivalent = [g for g in groups if isinstance(g, dict) and
                              any(isinstance(h, dict) and h.get('command') == command
                                  and h.get('enabled', True) is not False for h in g.get('hooks', []))]
                if event == 'SessionStart':
                    missing = []
                    for source in ('startup', 'resume', 'compact'):
                        covered = False
                        for group in equivalent:
                            try:
                                covered |= not group.get('matcher') or bool(re.search(group['matcher'], source))
                            except (re.error, TypeError):
                                pass  # Invalid existing matcher does not supply coverage.
                        if not covered:
                            missing.append(source)
                    if missing:
                        hooks[event][0]['matcher'] = '|'.join(missing)
                    else:
                        del hooks[event]
                elif any(not group.get('matcher') for group in equivalent):
                    del hooks[event]
            if hooks:
                changes.append(FileChange(codex / "hooks.json", "merge-json", {"hooks": hooks},
                                      "scoped recall/context; review exact definitions in Codex /hooks; "
                                      "existing inline hooks stay and may produce a multiple-source warning"))
        if routing.available(ctx.content):          # one subagent per tier: model + effort from routing.toml
            for name, tier in routing.resolve(ctx.content, ctx.home, ctx.profile).items():
                changes.append(FileChange(codex / "agents" / f"{routing.PREFIX}{name}.toml", "replace",
                                          routing.codex_agent(name, tier),
                                          f"subagent {routing.PREFIX}{name}: {tier['codex']['model'] or 'default model'}, "
                                          f"effort {tier['codex']['effort']}"))
        return changes + shared_skills(ctx)


def profile_tables(profile: dict) -> Dict[str, dict]:
    """The profile's [codex.config.*] tables as shared ("+name") TOML tables."""
    conf = ((profile or {}).get("codex") or {}).get("config") or {}
    out: Dict[str, dict] = {}

    def walk(prefix: str, d: dict) -> None:
        scalars = {k: v for k, v in d.items() if not isinstance(v, dict)}
        if scalars and prefix:
            out["+" + prefix] = scalars
        for k, v in d.items():
            if isinstance(v, dict):
                walk(f"{prefix}.{k}" if prefix else k, v)
    if isinstance(conf, dict):
        walk("", conf)
    return out
