"""Adapter destination controls only; root owns execution and native qualification."""
import json
import sys

import pytest

from agent_harness.adapters.base import Ctx
from agent_harness.adapters.copilot_vscode import CopilotVSCodeAdapter


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    monkeypatch.delenv('COPILOT_HOME', raising=False)
    home = tmp_path / 'home'
    home.mkdir()
    harness = home / '.agent-harness'
    content = harness / 'content'
    skill = content / 'skills' / 'fixture-method'
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text('---\nname: fixture-method\n---\nInspect evidence.\n')
    return Ctx(home=home, harness_home=harness, content=content, profile={},
               rules='Preserve source scope.\n',
               mcp_cmd=[sys.executable, str(harness / 'server.py')])


def by_path(ctx):
    changes = CopilotVSCodeAdapter().plan(ctx)
    assert len({change.path for change in changes}) == len(changes)
    return {change.path: change for change in changes}


def value(change):
    return json.loads(change.content) if change.kind == 'replace' else change.content


def test_unset_copilot_home_keeps_default_portable_schema(ctx):
    change = by_path(ctx)[ctx.home / '.copilot' / 'mcp-config.json']
    assert change.kind == 'merge-json'
    entry = value(change)['mcpServers']['harness']
    assert entry == {'type': 'stdio', 'command': ctx.mcp_cmd[0], 'args': ctx.mcp_cmd[1:]}


def test_override_moves_only_portable_mcp_not_instructions_skills_or_editor_config(
        ctx, tmp_path, monkeypatch):
    before = by_path(ctx)
    default = ctx.home / '.copilot' / 'mcp-config.json'
    selected = tmp_path / 'separate copilot home' / 'mcp-config.json'
    monkeypatch.setenv('COPILOT_HOME', str(selected.parent))
    after = by_path(ctx)

    assert set(after) == (set(before) - {default}) | {selected}
    assert value(after[selected]) == value(before[default])
    for path in set(before) - {default}:
        assert after[path].kind == before[path].kind
        assert after[path].content == before[path].content
    assert ctx.home / '.copilot/instructions/harness.instructions.md' in after
    assert ctx.home / '.agents/skills/fixture-method' in after
    assert not selected.exists(), 'planning must not install configuration'


def test_override_merges_jsonc_preserving_other_servers_and_top_level_keys(
        ctx, tmp_path, monkeypatch):
    selected = tmp_path / 'copilot-selected' / 'mcp-config.json'
    selected.parent.mkdir()
    original = ('// owned fixture\n{\n'
                ' "mcpServers": {"other": {"command": "other-tool", "args": ["--keep"],},},\n'
                ' "fixtureSetting": {"keep": true},\n}\n')
    selected.write_text(original)
    monkeypatch.setenv('COPILOT_HOME', str(selected.parent))
    change = by_path(ctx)[selected]
    assert change.kind == 'replace'
    merged = value(change)
    assert merged['mcpServers']['other'] == {'command': 'other-tool', 'args': ['--keep']}
    assert merged['mcpServers']['harness']['command'] == ctx.mcp_cmd[0]
    assert merged['fixtureSetting'] == {'keep': True}
    assert selected.read_text() == original


def test_invalid_override_config_refuses_without_falling_back_to_default(
        ctx, tmp_path, monkeypatch):
    selected = tmp_path / 'copilot-selected' / 'mcp-config.json'
    selected.parent.mkdir()
    selected.write_text('{"mcpServers": broken fixture}')
    monkeypatch.setenv('COPILOT_HOME', str(selected.parent))
    adapter = CopilotVSCodeAdapter()
    paths = {change.path for change in adapter.plan(ctx)}
    assert selected not in paths
    assert ctx.home / '.copilot/mcp-config.json' not in paths
    assert any('refused' in note and str(selected) in note for note in adapter.notes(ctx))
    assert selected.read_text() == '{"mcpServers": broken fixture}'
