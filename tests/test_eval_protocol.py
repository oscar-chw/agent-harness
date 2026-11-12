"""Frozen RPC sequence: command controls and resolved context precede generation."""
import json

import pytest

from agent_harness.eval_boundary import EvaluationProtocol


def protocol(tmp_path):
    p = EvaluationProtocol(tmp_path / 'actor', tmp_path / 'oracle', 'inside', 'outside',
                           'fixture-model', 'high', 'Read permitted evidence.')
    return p


def pop(p):
    assert p.pending
    return p.pending.pop(0)


def response(identity, result):
    return {'id': identity, 'result': result}


def through_control(p):
    init = pop(p)
    assert init['method'] == 'initialize'
    p.feed(response(init['id'], {}))
    assert pop(p)['method'] == 'initialized'
    account = pop(p)
    assert account['method'] == 'account/read'
    p.feed(response(account['id'], {'account': {'type': 'chatgpt'}}))
    listing = pop(p)
    assert listing['method'] == 'mcpServerStatus/list'
    p.feed(response(listing['id'], {'data': [{'name': 'fixture-server'}], 'nextCursor': None}))
    check = pop(p)
    assert check['method'] == 'command/exec' and 'permissionProfile' in check['params']
    return check


def acknowledged(p):
    check = through_control(p)
    p.feed(response(check['id'], {'exitCode': 0, 'stdout': json.dumps({
        'inside_readable': True, 'oracle_denied': True, 'writes_denied': True}), 'stderr': ''}))
    start = pop(p)
    assert start['method'] == 'thread/start' and 'sandbox' not in start['params']
    assert start['params']['serviceTier'] == 'default'
    assert start['params']['config']['mcp_servers']['fixture-server']['enabled'] is False
    profile = start['params']['permissions']
    return start, {'thread': {'id': 'fresh-thread'}, 'model': 'fixture-model',
                   'modelProvider': 'openai', 'reasoningEffort': 'high',
                   'approvalPolicy': 'never', 'activePermissionProfile': {'id': profile},
                   'sandbox': {'type': 'readOnly', 'networkAccess': False}, 'serviceTier': None}


def test_no_turn_starts_until_control_and_resolved_profile_agree(tmp_path):
    p = protocol(tmp_path)
    start, result = acknowledged(p)
    assert not any(x['method'] == 'turn/start' for x in p.pending)
    events = p.feed(response(start['id'], result))
    check = pop(p)
    assert check['method'] == 'mcpServerStatus/list'
    assert not any(x['method'] == 'turn/start' for x in p.pending)
    p.feed(response(check['id'], {'data': [], 'nextCursor': None}))
    turn = pop(p)
    assert turn['method'] == 'turn/start' and turn['params']['threadId'] == 'fresh-thread'
    assert events[0]['type'] == 'thread.started'
    assert p.receipt['resolved']['model'] == 'fixture-model'
    assert p.receipt['remote_tools'] == 'NOT_VERIFIED'


@pytest.mark.parametrize('field,value', [('model', 'wrong'), ('reasoningEffort', 'low'),
                                        ('approvalPolicy', 'on-request'),
                                        ('activePermissionProfile', {'id': 'wrong'}),
                                        ('sandbox', {'type': 'dangerFullAccess'}),
                                        ('serviceTier', 'fast')])
def test_mismatched_native_context_refuses_before_generation(tmp_path, field, value):
    p = protocol(tmp_path); start, result = acknowledged(p)
    result[field] = value
    with pytest.raises(ValueError, match='boundary'):
        p.feed(response(start['id'], result))
    assert not any(x['method'] == 'turn/start' for x in p.pending)


def test_api_key_account_cannot_start_an_included_quota_trial(tmp_path):
    p = protocol(tmp_path); init = pop(p); p.feed(response(init['id'], {})); pop(p)
    account = pop(p)
    with pytest.raises(ValueError, match='boundary'):
        p.feed(response(account['id'], {'account': {'type': 'apiKey'}}))
    assert not any(x['method'] == 'turn/start' for x in p.pending)


def test_real_probe_failure_prevents_thread_and_turn_creation(tmp_path):
    p = protocol(tmp_path); check = through_control(p)
    with pytest.raises(ValueError, match='boundary'):
        p.feed(response(check['id'], {'exitCode': 0, 'stdout': json.dumps({
            'inside_readable': True, 'oracle_denied': False, 'writes_denied': True})}))
    assert not any(x['method'] in ('turn/start', 'thread/start') for x in p.pending)


def test_usage_is_final_fresh_thread_total_not_sum_of_snapshots(tmp_path):
    p = protocol(tmp_path); start, result = acknowledged(p)
    p.feed(response(start['id'], result)); check = pop(p)
    p.feed(response(check['id'], {'data': [], 'nextCursor': None})); turn = pop(p)
    p.feed(response(turn['id'], {'turn': {'id': 'turn-1'}}))
    for n in (10, 20):
        p.feed({'method': 'thread/tokenUsage/updated', 'params': {'threadId': 'fresh-thread',
                'turnId': 'turn-1', 'tokenUsage': {'total': {'inputTokens': n,
                'cachedInputTokens': 3, 'outputTokens': 4, 'reasoningOutputTokens': 2,
                'totalTokens': n + 4}}}})
    events = p.feed({'method': 'turn/completed', 'params': {'threadId': 'fresh-thread',
                     'turn': {'id': 'turn-1', 'status': 'completed'}}})
    assert not p.finished and not events
    barrier = pop(p)
    assert barrier['method'] == 'thread/read'
    assert barrier['params']['includeTurns'] is False
    events = p.feed(response(barrier['id'], {'thread': {'id': 'fresh-thread', 'status': {'type': 'idle'}, 'turns': []}}))
    assert p.finished and events[-1]['type'] == 'turn.completed'
    assert events[-1]['usage']['input_tokens'] == 20
    assert sum(e['type'] == 'turn.completed' for e in p.events) == 1


def test_foreign_thread_or_turn_cannot_supply_usage(tmp_path):
    p = protocol(tmp_path); start, result = acknowledged(p)
    p.feed(response(start['id'], result)); check = pop(p)
    p.feed(response(check['id'], {'data': [], 'nextCursor': None})); turn = pop(p)
    p.feed(response(turn['id'], {'turn': {'id': 'turn-1'}}))
    with pytest.raises(ValueError, match='boundary'):
        p.feed({'method': 'thread/tokenUsage/updated', 'params': {'threadId': 'other',
                'turnId': 'turn-1', 'tokenUsage': {'total': {}}}})


def test_unscoped_mcp_surface_prevents_generation(tmp_path):
    p = protocol(tmp_path); start, result = acknowledged(p)
    p.feed(response(start['id'], result)); check = pop(p)
    assert check['method'] == 'mcpServerStatus/list'
    with pytest.raises(ValueError, match='boundary'):
        p.feed(response(check['id'], {'data': [{'name': 'unscoped'}], 'nextCursor': None}))
    assert not any(x['method'] == 'turn/start' for x in p.pending)


def test_evaluation_omits_desktop_bridge_without_dropping_native_guard_context():
    parent = {'CODEX_APP_TOOLS_PIPE_PATH': '/fixture-only/bridge', 'HOME': '/fixture/home',
              'PATH': '/fixture/bin', 'CODEX_PERMISSION_PROFILE': 'native-policy'}
    actual = EvaluationProtocol.environment(parent)
    assert 'CODEX_APP_TOOLS_PIPE_PATH' not in actual
    assert actual == {k: v for k, v in parent.items() if k != 'CODEX_APP_TOOLS_PIPE_PATH'}
    assert parent['CODEX_APP_TOOLS_PIPE_PATH'] == '/fixture-only/bridge'


def test_terminal_barrier_uses_late_final_usage_instead_of_an_earlier_snapshot(tmp_path):
    p = protocol(tmp_path); start, result = acknowledged(p)
    p.feed(response(start['id'], result)); check = pop(p)
    p.feed(response(check['id'], {'data': [], 'nextCursor': None})); turn = pop(p)
    p.feed(response(turn['id'], {'turn': {'id': 'turn-1'}}))
    def usage(n):
        return {'method': 'thread/tokenUsage/updated', 'params': {'threadId': 'fresh-thread',
            'turnId': 'turn-1', 'tokenUsage': {'total': {'inputTokens': n,
            'cachedInputTokens': 0, 'outputTokens': 4, 'reasoningOutputTokens': 2,
            'totalTokens': n+4}}}}
    p.feed(usage(10))
    p.feed({'method': 'turn/completed', 'params': {'threadId': 'fresh-thread',
        'turn': {'id': 'turn-1', 'status': 'completed'}}})
    assert not p.finished
    barrier = pop(p)
    p.feed(usage(20))
    events = p.feed(response(barrier['id'], {'thread': {'id': 'fresh-thread', 'status': {'type': 'idle'}, 'turns': []}}))
    assert events[-1]['usage']['input_tokens'] == 20


@pytest.mark.parametrize('status,usage', [({'type': 'active', 'activeFlags': []}, True),
                                        ({'type': 'idle'}, False)])
def test_terminal_barrier_never_passes_an_active_thread_or_missing_usage(tmp_path, status, usage):
    p = protocol(tmp_path); start, result = acknowledged(p)
    p.feed(response(start['id'], result)); check = pop(p)
    p.feed(response(check['id'], {'data': [], 'nextCursor': None})); turn = pop(p)
    p.feed(response(turn['id'], {'turn': {'id': 'turn-1'}}))
    if usage:
        p.feed({'method': 'thread/tokenUsage/updated', 'params': {'threadId': 'fresh-thread',
            'turnId': 'turn-1', 'tokenUsage': {'total': {'inputTokens': 2, 'cachedInputTokens': 0,
            'outputTokens': 1, 'reasoningOutputTokens': 0, 'totalTokens': 3}}}})
    p.feed({'method': 'turn/completed', 'params': {'threadId': 'fresh-thread',
            'turn': {'id': 'turn-1', 'status': 'completed'}}})
    barrier = pop(p)
    with pytest.raises(ValueError, match='terminal|usage'):
        p.feed(response(barrier['id'], {'thread': {'id': 'fresh-thread', 'status': status}}))
    assert not p.finished and not any(e['type'] == 'turn.completed' for e in p.events)
