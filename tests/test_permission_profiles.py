"""Permission choice is explicit, persists, and never removes another owner's hooks."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def call(home, *args):
    return subprocess.run([sys.executable, str(ROOT/'bin/harness'), '--home', str(home),
                           'install', '--yes', '--tools', 'claude-code,codex', *args],
                          capture_output=True, text=True, timeout=30)


def test_explicit_and_autonomous_profiles_change_only_owned_policy(tmp_path):
    settings = tmp_path/'.claude/settings.json'
    settings.parent.mkdir()
    settings.write_text(json.dumps({'hooks': {'PreToolUse': [{'matcher': 'Other', 'hooks': [
        {'type': 'command', 'command': 'owner-existing-hook'}]}]},
        'permissions': {'deny': ['Read(private.txt)']}}))
    explicit = call(tmp_path, '--permission-profile', 'explicit')
    assert explicit.returncode == 0, explicit.stdout + explicit.stderr
    body = json.loads(settings.read_text())
    assert body['permissions']['defaultMode'] == 'default'
    assert 'guard.py' in json.dumps(body['hooks']['PreToolUse'])
    auto = call(tmp_path, '--permission-profile', 'autonomous')
    assert auto.returncode == 0, auto.stdout + auto.stderr
    body = json.loads(settings.read_text())
    assert body['permissions']['defaultMode'] == 'auto'
    hooks = json.dumps(body['hooks'])
    assert 'owner-existing-hook' in hooks
    assert 'guard.py' not in hooks and '_hook-stop' not in hooks
    assert '_hook-capture' in hooks
    assert body['permissions']['deny'] == ['Read(private.txt)']
    from agent_harness.installer import load_toml
    conf = load_toml((tmp_path/'.codex/config.toml').read_text())
    assert conf['sandbox_mode'] == 'workspace-write'
    assert conf['approval_policy'] == 'on-request'
    assert conf['approvals_reviewer'] == 'auto_review'
    state = json.loads((tmp_path/'.agent-harness/installed.json').read_text())
    assert state['permission_profile'] == 'autonomous'
    repeated = call(tmp_path)
    assert repeated.returncode == 0, repeated.stdout + repeated.stderr
    assert json.loads(settings.read_text())['permissions']['defaultMode'] == 'auto'


def test_unspecified_noninteractive_install_preserves_native_policy(tmp_path):
    settings = tmp_path/'.claude/settings.json'
    settings.parent.mkdir()
    settings.write_text(json.dumps({'permissions': {'defaultMode': 'acceptEdits'}}))
    result = call(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(settings.read_text())['permissions']['defaultMode'] == 'acceptEdits'


def test_preserve_after_an_owned_profile_keeps_current_native_values(tmp_path):
    assert call(tmp_path, '--permission-profile', 'autonomous').returncode == 0
    settings = tmp_path/'.claude/settings.json'
    body = json.loads(settings.read_text())
    body['permissions']['defaultMode'] = 'acceptEdits'
    settings.write_text(json.dumps(body))
    result = call(tmp_path, '--permission-profile', 'preserve')
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(settings.read_text())['permissions']['defaultMode'] == 'acceptEdits'
    from agent_harness.installer import load_toml
    native = load_toml((tmp_path/'.codex/config.toml').read_text())
    assert native['sandbox_mode'] == 'workspace-write'
    assert native['approvals_reviewer'] == 'auto_review'


def test_invalid_saved_posture_is_reported_without_partial_install(tmp_path):
    state = tmp_path/'.agent-harness/installed.json'
    state.parent.mkdir()
    state.write_text(json.dumps({'permission_profile': 'invalid'}))
    result = call(tmp_path)
    assert result.returncode != 0
    assert 'unknown permission profile' in result.stdout + result.stderr
    assert 'Traceback' not in result.stdout + result.stderr
    assert not (tmp_path/'.claude').exists()


def test_autonomy_not_silently_written_to_unsupported_claude_project_scope(tmp_path):
    home = tmp_path/'home'
    project = tmp_path/'project'
    home.mkdir()
    project.mkdir()
    result = call(home, '--project', str(project), '--permission-profile', 'autonomous')
    assert result.returncode != 0
    assert 'user scope' in result.stdout + result.stderr
    assert not (home/'.agent-harness').exists()
    assert not (project/'.claude/settings.json').exists()


def test_interactive_choice_once_and_invalid_choices_do_not_loop(monkeypatch):
    from agent_harness.permission_profiles import choose
    values = iter(['2'])
    monkeypatch.setattr('builtins.input', lambda _: next(values))
    assert choose(None, None, True) == 'autonomous'
    assert choose(None, 'autonomous', True) == 'autonomous'
    monkeypatch.setattr('builtins.input', lambda _: 'invalid')
    with pytest.raises(ValueError):
        choose(None, None, True)


def test_invalid_selection_does_not_write(tmp_path):
    assert call(tmp_path, '--permission-profile', 'anything').returncode == 2
    assert list(tmp_path.iterdir()) == []


def test_explicit_native_posture_and_uninstall_restore_original_settings(tmp_path):
    settings = tmp_path/'.claude/settings.json'
    config = tmp_path/'.codex/config.toml'
    settings.parent.mkdir()
    config.parent.mkdir()
    original = {'permissions': {'defaultMode': 'acceptEdits'}, 'owner': True}
    settings.write_text(json.dumps(original))
    config.write_text('sandbox_mode = "workspace-write"\nowner = true\n')
    result = call(tmp_path, '--permission-profile', 'explicit')
    assert result.returncode == 0, result.stdout + result.stderr
    from agent_harness.installer import load_toml, uninstall
    native = load_toml(config.read_text())
    assert native['sandbox_mode'] == 'read-only'
    assert native['approvals_reviewer'] == 'user'
    assert json.loads(settings.read_text())['permissions']['defaultMode'] == 'default'
    uninstall(tmp_path/'.agent-harness')
    assert json.loads(settings.read_text()) == original
    assert load_toml(config.read_text()) == {'sandbox_mode': 'workspace-write', 'owner': True}


def test_root_policy_merge_and_uninstall_restore_original_native_values():
    from agent_harness.installer import load_toml, toml_merge, toml_unmerge
    original = 'sandbox_mode = "read-only"\n# owner comment\n[features]\nowner = true\n'
    patch = {'+': {'sandbox_mode': 'workspace-write', 'approval_policy': 'on-request'}}
    merged = toml_merge(original, patch)
    parsed = load_toml(merged)
    assert parsed['sandbox_mode'] == 'workspace-write'
    assert parsed['approval_policy'] == 'on-request'
    assert parsed['features']['owner'] is True
    assert '# owner comment' in merged
    restored = load_toml(toml_unmerge(merged, patch, original))
    assert restored == load_toml(original)
    assert load_toml(toml_merge('', patch))['sandbox_mode'] == 'workspace-write'
