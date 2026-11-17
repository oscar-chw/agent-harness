"""Configured stores survive child-environment filtering and fresh MCP processes."""
import json
import os
import subprocess
import sys

from agent_harness import installer
from agent_harness.mcp.state import State


def rpc(project, home, calls, *, explicit=True):
    env = dict(os.environ, HOME=str(project / 'native-home'))
    env.pop('HARNESS_HOME', None)
    env.pop('HARNESS_PROJECT', None)
    env.pop('PYTHONPATH', None)
    args = installer.mcp_cmd(home)[1:]
    if not explicit:
        args = args[:1]
        env['HARNESS_HOME'] = str(home)
    wire = ''.join(json.dumps({'jsonrpc': '2.0', 'id': i, 'method': 'tools/call',
                    'params': {'name': name, 'arguments': arguments}}) + '\n'
                   for i, (name, arguments) in enumerate(calls, 1))
    result = subprocess.run([sys.executable, *args], input=wire, text=True,
                            capture_output=True, cwd=project, env=env, timeout=15)
    assert result.returncode == 0, result.stderr
    messages = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    assert len(messages) == len(calls), result.stdout
    assert all('result' in m and not m['result'].get('isError') for m in messages), messages
    return messages


def setup(tmp_path):
    home = tmp_path / 'custom-store'
    project = tmp_path / 'project'
    project.mkdir()
    (project / '.git').mkdir()
    installer.copy_harness(home, installer.REPO_ROOT, None)
    return home, project


def test_fresh_configured_mcp_reads_the_selected_store_without_inherited_env(tmp_path):
    home, project = setup(tmp_path)
    State(home=home).state_save('## Goal\nRecover the configured store.\n## Next\nInspect the accepted plan.\n', str(project))
    result = rpc(project, home, [('state_load', {'project': str(project)})])
    assert 'Recover the configured store.' in json.dumps(result)
    assert not (project / 'native-home/.agent-harness/state').exists()


def test_native_stdio_save_and_another_process_pick_up_the_automatic_packet(tmp_path):
    home, project = setup(tmp_path)
    text = '## Goal\nRestore invoice export.\n## Next\nRead the integration test.\n'
    rpc(project, home, [('state_save', {'text': text})])
    assert State(home=home).state_load(str(project)).startswith('## Goal')
    result = rpc(project, home, [('op_state', {'action': 'status'})])
    data = json.dumps(result)
    assert 'Restore invoice export.' in data and 'Read the integration test.' in data
    assert '.harness/checkpoints/' in data
    assert not (project / 'native-home/.agent-harness/state').exists()


def test_legacy_environment_selected_store_still_loads(tmp_path):
    home, project = setup(tmp_path)
    State(home=home).state_save('## Goal\nLegacy selected store.\n## Next\nRead it.\n', str(project))
    result = rpc(project, home, [('state_load', {'project': str(project)})], explicit=False)
    assert 'Legacy selected store.' in json.dumps(result)
