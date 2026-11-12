"""Protocol-level cross-session pickup, with bounded delivery and no live model calls."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_harness.mcp.server import Server, tool_list
from agent_harness.operational_state import OperationalState


def message(method, **params):
    return {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}


def initialize(server, name='fixture-client'):
    return server.handle(message('initialize', protocolVersion='2025-06-18',
                                 clientInfo={'name': name}, capabilities={}))['result']


def read(server):
    return server.handle(message('tools/call', name='session_recent', arguments={}))['result']


def board_text(response):
    return '\n'.join(item['text'] for item in response.get('content', [])
                     if item.get('type') == 'text' and item['text'].startswith('Shared board'))


@pytest.fixture
def lab(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / '.git').mkdir()
    home = tmp_path / 'hh'
    monkeypatch.setenv('HARNESS_HOME', str(home))
    monkeypatch.delenv('HARNESS_ENABLE', raising=False)
    monkeypatch.delenv('HARNESS_DISABLE', raising=False)
    store = OperationalState(home, tmp_path)
    store.put('build', {'goal': 'Build the parser', 'stage': 'test',
                        'summary': 'Parser implemented; integration gate pending',
                        'next': 'Run the integration gate'}, expected=0, request_id='seed')
    return tmp_path, home, store


def test_board_is_default_and_explicit_disable_wins(lab, monkeypatch):
    assert 'op_state' in {t['name'] for t in tool_list()}
    monkeypatch.setenv('HARNESS_DISABLE', 'op_state')
    assert 'op_state' not in {t['name'] for t in tool_list()}
    assert 'Build the parser' not in initialize(Server(home=lab[1]))['instructions']


@pytest.mark.parametrize('client', ['codex', 'claude-code', 'kimi', 'cursor', 'copilot-vscode',
                                   'gemini-cli', 'claude-desktop', 'jupyter-ai', 'unknown-mcp-client'])
def test_any_cold_mcp_session_gets_current_board_automatically(lab, client):
    response = initialize(Server(home=lab[1]), client)
    assert 'Build the parser' in response['instructions']
    assert 'Run the integration gate' in response['instructions']
    assert 'cursor' in response['instructions']


def test_running_session_receives_changes_once_without_polling_messages(lab):
    server = Server(home=lab[1])
    initialize(server)
    assert not board_text(read(server))
    lab[2].put('build', {'stage': 'review', 'next': 'Inspect the diff'}, expected=1, request_id='changed')
    delta = board_text(read(server))
    assert 'review' in delta and 'Inspect the diff' in delta
    assert not board_text(read(server))


def test_existing_checkpoint_entrypoints_publish_for_a_cold_session(lab):
    writer = Server(home=lab[1])
    initialize(writer, 'kimi')
    response = writer.handle(message('tools/call', name='session_note',
                                    arguments={'summary': 'Review found a race; next fix the lease renewal.'}))
    assert not response['result']['isError']
    reader = initialize(Server(home=lab[1]), 'codex')
    assert 'Review found a race' in reader['instructions']
    assert 'next fix the lease renewal' in reader['instructions']


def test_snapshot_budget_preserves_omission_metadata(lab):
    for i in range(20):
        lab[2].put('task-%02d' % i, {'summary': 'x' * 200}, expected=0, request_id='seed-%d' % i)
    packet = initialize(Server(home=lab[1]))['instructions'].split('Shared board', 1)[1]
    assert len(packet.encode()) <= 1200
    assert 'omitted' in packet


def test_unchanged_board_cost_is_zero_after_startup(lab):
    server = Server(home=lab[1])
    initial = initialize(server)['instructions']
    full = json.dumps(lab[2].snapshot())
    delivered = initial.encode()
    for _ in range(20):
        delivered += board_text(read(server)).encode()
    assert len(delivered) < len(full.encode()) * 20
    assert all(not board_text(read(server)) for _ in range(5))


def test_real_separate_stdio_process_picks_up_written_checkpoint(lab):
    root = Path(__file__).resolve().parents[1]
    env = {k: v for k, v in os.environ.items() if not k.startswith('HARNESS_')}
    env.update(HARNESS_HOME=str(lab[1]), PYTHONPATH=str(root / 'src'))
    commands = [message('initialize', protocolVersion='2025-06-18',
                        clientInfo={'name': 'cold-process'}, capabilities={})]
    proc = subprocess.run([sys.executable, str(root / 'src/agent_harness/mcp/server.py')],
                          input=''.join(json.dumps(c) + '\n' for c in commands), text=True,
                          cwd=lab[0], env=env, capture_output=True, timeout=10)
    assert proc.returncode == 0, proc.stderr
    reply = json.loads(proc.stdout)['result']
    assert 'Build the parser' in reply['instructions']
    assert 'Run the integration gate' in reply['instructions']


def test_duplicate_checkpoint_does_not_create_board_churn(lab):
    server = Server(home=lab[1])
    initialize(server)
    event = message('tools/call', name='session_note', arguments={'summary': 'Parser done; run integration.'})
    assert not server.handle(event)['result']['isError']
    cursor = lab[2].snapshot()['cursor']
    assert not server.handle(event)['result']['isError']
    assert lab[2].snapshot()['cursor'] == cursor


def test_auto_checkpoint_redacts_before_truncation(lab):
    server = Server(home=lab[1])
    initialize(server)
    secret = 'ghp_' + 'Q' * 36
    summary = 'x' * 280 + secret
    server.handle(message('tools/call', name='state_save', arguments={'text': summary}))
    state = lab[2].snapshot()
    serialized = json.dumps(state)
    assert 'ghp_' not in serialized
    assert '[REDACTED]' in serialized


def test_new_task_outside_startup_budget_remains_discoverable(lab):
    for i in range(20):
        lab[2].put('a-%02d' % i, {'summary': 'Existing work ' * 20}, expected=0, request_id='other-%d' % i)
    server = Server(home=lab[1])
    initialize(server)
    lab[2].put('z-critical', {'summary': 'New blocking finding'}, expected=0, request_id='critical')
    delta = board_text(read(server))
    assert 'z-critical' in delta
    assert len(delta.encode()) <= 1200


def test_automatic_publication_uses_canonical_saved_project(lab, monkeypatch):
    other = lab[0] / 'other'
    (other / '.git').mkdir(parents=True)
    monkeypatch.setenv('HARNESS_PROJECT', str(other))
    server = Server(home=lab[1])
    initialize(server)
    server.handle(message('tools/call', name='state_save', arguments={'text': 'Private project B checkpoint'}))
    assert 'Private project B' not in json.dumps(lab[2].snapshot())


def test_explicit_root_from_subdirectory_still_publishes(lab, monkeypatch):
    nested = lab[0] / 'nested'
    nested.mkdir()
    monkeypatch.chdir(nested)
    server = Server(home=lab[1])
    initialize(server)
    server.handle(message('tools/call', name='state_save',
                          arguments={'text': 'Canonical root checkpoint', 'project': str(lab[0])}))
    assert 'Canonical root checkpoint' in initialize(Server(home=lab[1]))['instructions']


def test_existing_board_secrets_are_redacted_on_delivery(lab):
    secret = 'ghp_' + 'R' * 36
    lab[2].put('legacy', {'summary': secret}, expected=0, request_id='legacy')
    result = initialize(Server(home=lab[1]))['instructions']
    assert 'ghp_' not in result
    assert '[REDACTED]' in result


def test_omitted_changes_are_delivered_on_later_boundary(lab):
    for i in range(8):
        lab[2].put('long-%d' % i, {'summary': 'Changed detail ' * 20}, expected=0, request_id='long-%d' % i)
    server = Server(home=lab[1])
    replies = initialize(server)['instructions']
    for _ in range(8):
        replies += board_text(read(server))
    assert all('long-%d' % i in replies for i in range(8))
    assert not board_text(read(server))


def test_multibyte_summary_cannot_starve_board(lab):
    lab[2].put('a-large', {'summary': '界' * 300}, expected=0, request_id='large')
    server = Server(home=lab[1])
    text = initialize(server)['instructions'] + board_text(read(server))
    assert 'a-large' in text and 'build' in text


def test_status_response_does_not_repeat_identical_board_context(lab):
    server = Server(home=lab[1])
    initialize(server)
    lab[2].put('build', {'summary': 'Fresh exact summary'}, expected=1, request_id='fresh')
    response = server.handle(message('tools/call', name='op_state', arguments={'action': 'status'}))['result']
    assert json.dumps(response).count('Fresh exact summary') == 1


def test_reconnection_deduplicates_the_same_advisory_checkpoint(lab):
    for _ in range(3):
        server = Server(home=lab[1])
        initialize(server)
        server.handle(message('tools/call', name='session_note', arguments={'summary': 'Stable checkpoint'}))
    matching = [r for r in lab[2].snapshot()['tasks'] if r['value'].get('summary') == 'Stable checkpoint']
    assert len(matching) == 1


def test_failed_tool_still_delivers_a_new_blocker(lab):
    server = Server(home=lab[1])
    initialize(server)
    lab[2].put('build', {'blocked_on': 'Independent evaluator unavailable'}, expected=1, request_id='blocked')
    response = server.handle(message('tools/call', name='kb_get', arguments={}))['result']
    assert response['isError'] is True
    assert 'Independent evaluator unavailable' in board_text(response)


def test_explicit_status_also_redacts_secret_fields(lab):
    server = Server(home=lab[1])
    lab[2].put('secret', {'summary': 'ghp_' + 'S' * 36}, expected=0, request_id='secret')
    response = server.handle(message('tools/call', name='op_state', arguments={'action': 'status'}))['result']
    assert 'ghp_' not in json.dumps(response)
    assert '[REDACTED]' in json.dumps(response)


def test_long_checkpoint_suffix_changes_are_visible(lab):
    server = Server(home=lab[1])
    initialize(server)
    server.handle(message('tools/call', name='state_save', arguments={'text': 'A' * 350 + ' gate pending'}))
    response = server.handle(message('tools/call', name='state_save',
                                    arguments={'text': 'A' * 350 + ' STOP: newly discovered data loss'}))['result']
    assert 'STOP: newly discovered data loss' in board_text(response)
    assert 'full_text_sha256' in board_text(response)


def test_successive_notes_update_one_current_connection_checkpoint(lab):
    server = Server(home=lab[1])
    initialize(server)
    for i in range(20):
        server.handle(message('tools/call', name='session_note', arguments={'summary': 'Checkpoint %d' % i}))
    rows = [row for row in lab[2].snapshot()['tasks'] if row['value'].get('stage') == 'checkpoint_saved']
    assert len(rows) == 1
    assert rows[0]['value']['summary'] == 'Checkpoint 19'


def test_credential_shaped_task_identity_is_refused(lab):
    with pytest.raises(ValueError, match='identifier'):
        lab[2].put('ghp_' + 'Q' * 36, {'summary': 'ordinary'}, expected=0, request_id='bad-id')
