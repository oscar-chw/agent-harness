"""Direct completion usage must not be inferred from native context estimates."""
import copy

import pytest

from agent_harness.eval_boundary import EvaluationProtocol
from .test_eval_protocol import acknowledged, pop, response


def ready(tmp_path):
    p = EvaluationProtocol(tmp_path/'actor', tmp_path/'oracle', 'inside', 'outside',
                           'fixture-model', 'high', 'Read evidence.', require_provider_usage=True)
    start, resolved = acknowledged(p)
    p.feed(response(start['id'], resolved)); listing = pop(p)
    p.feed(response(listing['id'], {'data': [], 'nextCursor': None})); turn = pop(p)
    p.feed(response(turn['id'], {'turn': {'id': 'turn-1'}}))
    return p


def usage(inputs=10, outputs=4):
    return {'inputTokens': inputs, 'cachedInputTokens': 2, 'cacheWriteInputTokens': 1,
            'outputTokens': outputs, 'reasoningOutputTokens': 2, 'totalTokens': inputs+outputs}


def upstream(identity='response-1', tokens=None):
    return {'method': 'rawResponse/completed', 'params': {'threadId': 'fresh-thread',
            'turnId': 'turn-1', 'responseId': identity, 'usage': usage() if tokens is None else tokens}}


def snapshot(p, tokens=None):
    p.feed({'method': 'thread/tokenUsage/updated', 'params': {'threadId': 'fresh-thread',
            'turnId': 'turn-1', 'tokenUsage': {'total': usage() if tokens is None else tokens}}})


def finish(p):
    p.feed({'method': 'turn/completed', 'params': {'threadId': 'fresh-thread',
            'turn': {'id': 'turn-1', 'status': 'completed'}}})
    barrier = pop(p)
    return p.feed(response(barrier['id'], {'thread': {'id': 'fresh-thread', 'status': {'type': 'idle'}}}))


def test_requires_direct_upstream_completion_even_with_a_valid_native_snapshot(tmp_path):
    p = ready(tmp_path); snapshot(p)
    with pytest.raises(ValueError, match='provider|upstream|completion'):
        finish(p)
    assert not p.finished


def test_multiple_real_response_ids_sum_once_after_the_terminal_barrier(tmp_path):
    p = ready(tmp_path)
    p.feed(upstream()); p.feed(upstream('response-2', usage(15, 6)))
    snapshot(p, usage(25, 10))
    events = finish(p)
    assert events[-1]['usage']['input_tokens'] == 25
    assert events[-1]['usage']['output_tokens'] == 10
    assert p.receipt['provider_usage']['responses'] == 2
    assert p.receipt['usage_boundary'] == 'native_upstream_completions_after_terminal_read_barrier'
    assert p.receipt['provider_usage']['input_tokens'] == 25
    assert 'usageMetadata' not in p.receipt['provider_usage']


@pytest.mark.parametrize('fault', ['missing', 'partial', 'wrong-thread', 'wrong-turn',
                                    'duplicate', 'cached', 'reasoning', 'bad-total', 'boolean'])
def test_invalid_or_replayed_upstream_reports_never_become_complete(tmp_path, fault):
    p = ready(tmp_path); packet = upstream()
    if fault == 'missing': packet['params']['usage'] = None
    elif fault == 'partial': packet['params']['usage'].pop('outputTokens')
    elif fault == 'wrong-thread': packet['params']['threadId'] = 'other'
    elif fault == 'wrong-turn': packet['params']['turnId'] = 'other'
    elif fault == 'duplicate': p.feed(copy.deepcopy(packet))
    elif fault == 'cached': packet['params']['usage']['cachedInputTokens'] = 10
    elif fault == 'reasoning': packet['params']['usage']['reasoningOutputTokens'] = 5
    elif fault == 'bad-total': packet['params']['usage']['totalTokens'] = 15
    else: packet['params']['usage']['inputTokens'] = True
    with pytest.raises(ValueError, match='provider|upstream|boundary|response'):
        p.feed(packet)


def test_missing_response_cannot_hide_behind_a_larger_cumulative_snapshot(tmp_path):
    p = ready(tmp_path); p.feed(upstream()); snapshot(p, usage(100, 40))
    with pytest.raises(ValueError, match='provider|upstream|usage'):
        finish(p)


def test_native_error_or_retry_prevents_complete_provider_accounting(tmp_path):
    p = ready(tmp_path)
    with pytest.raises(ValueError, match='provider|upstream|retry'):
        p.feed({'method': 'error', 'params': {'threadId': 'fresh-thread', 'turnId': 'turn-1',
                                            'willRetry': True, 'message': 'fixture transport failure'}})


def test_late_response_before_barrier_is_counted_and_after_barrier_is_refused(tmp_path):
    p = ready(tmp_path); p.feed(upstream()); snapshot(p)
    p.feed({'method': 'turn/completed', 'params': {'threadId': 'fresh-thread',
             'turn': {'id': 'turn-1', 'status': 'completed'}}})
    barrier = pop(p)
    p.feed(upstream('late-before-barrier', usage(15, 6)))
    events = p.feed(response(barrier['id'], {'thread': {'id': 'fresh-thread', 'status': {'type': 'idle'}}}))
    assert events[-1]['usage']['input_tokens'] == 25
    with pytest.raises(ValueError, match='provider|upstream|terminal'):
        p.feed(upstream('after-terminal'))


def test_usage_metadata_is_not_copied_into_the_receipt(tmp_path):
    p = ready(tmp_path); packet = upstream()
    packet['params']['usageMetadata'] = {'amount': 'DO_NOT_COPY_BILLING_METADATA', 'metadata': {'private': 'DO_NOT_COPY'}}
    p.feed(packet); snapshot(p); finish(p)
    assert 'DO_NOT_COPY' not in str(p.receipt)


def test_context_counter_scalar_cannot_override_direct_response_counts(tmp_path):
    p = ready(tmp_path); p.feed(upstream())
    context = usage(); context['totalTokens'] = 999
    snapshot(p, context)
    events = finish(p)
    assert events[-1]['usage']['input_tokens'] + events[-1]['usage']['output_tokens'] == 14
    assert p.receipt['provider_usage']['input_tokens'] == 10


def test_provider_response_inventory_has_a_bound(tmp_path):
    p = ready(tmp_path)
    for n in range(64): p.feed(upstream(f'response-{n}'))
    with pytest.raises(ValueError, match='provider|response'):
        p.feed(upstream('one-too-many'))


@pytest.mark.parametrize('flag', [True, 'yes', 1])
def test_direct_provider_mode_cannot_bypass_enforced_native_controls(tmp_path, monkeypatch, flag):
    from agent_harness import launch
    monkeypatch.setattr(launch.subprocess, 'Popen', lambda *a, **k: pytest.fail('invalid control must not spawn'))
    with pytest.raises(ValueError, match='provider|enforced'):
        launch.execute(tmp_path, 'absent-request.json', 'no-native.json', eval_provider_usage=flag)


def test_complete_observer_explicitly_requests_native_raw_response_events(tmp_path):
    p = EvaluationProtocol(tmp_path / 'actor', tmp_path / 'oracle', 'inside', 'outside',
                           'fixture-model', 'high', 'Read evidence.', require_provider_usage=True)
    start, _ = acknowledged(p)
    assert start['params'].get('experimentalRawEvents') is True


def test_ordinary_evaluation_keeps_experimental_raw_events_unrequested(tmp_path):
    p = EvaluationProtocol(tmp_path / 'actor', tmp_path / 'oracle', 'inside', 'outside',
                           'fixture-model', 'high', 'Read evidence.')
    start, _ = acknowledged(p)
    assert 'experimentalRawEvents' not in start['params']
