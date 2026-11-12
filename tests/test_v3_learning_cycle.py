"""Transport fixtures exercise adoption logic, never native efficacy or real usage.

Only the native transport is replaced. Requests, source stores, campaign stages,
grades, history accounting, activation and withdrawal use production code.
"""
import hashlib
import json
from pathlib import Path

import pytest

from agent_harness import launch, procedure_campaign as M, procedure_execution as C, procedures as P
from . import test_procedure_execution_controller as examples
from .test_procedure_native_preparation import generated

lab = examples.lab


@pytest.fixture
def transport(monkeypatch):
    def execute(actor, request_path, receipt_path, **kwargs):
        request = C._json(actor / request_path)
        options = {k: kwargs['native_' + k] for k in ('model', 'effort')}
        options['timeout'] = kwargs['timeout']
        factory = generated if 'Draft a short reusable procedure' in request['task'] else examples.fake_invoke
        receipt = factory(actor, request, kwargs['eval_deny_root'], **options)
        receipt.update({k: v for k, v in launch.prepare(actor, request_path).items()
                        if k in ('request_sha256', 'context_sha256', 'prompt_sha256', 'memory_receipts')})
        receipt['thread_id'] = 'fixture-' + actor.name
        receipt['eval_deny_root_sha256'] = hashlib.sha256(str(kwargs['eval_deny_root']).encode()).hexdigest()
        baseline = actor.name.endswith('-base')
        tokens = 1000 if baseline else 10
        receipt['usage'] = {'input_tokens': tokens - 1, 'cached_input_tokens': 0, 'output_tokens': 1}
        if kwargs.get('eval_provider_usage'):
            boundary = receipt['evaluation_boundary']
            boundary['usage_boundary'] = 'native_upstream_completions_after_terminal_read_barrier'
            boundary['provider_usage'] = {
                'status': 'OBSERVED_UPSTREAM_COMPLETIONS', 'responses': 1,
                'response_id_sha256': [hashlib.sha256(actor.name.encode()).hexdigest()],
                **receipt['usage'], 'cache_write_input_tokens': 0, 'reasoning_output_tokens': 0,
                'scope': 'fresh native thread upstream completions; not whole-workflow cost'}
        return receipt
    monkeypatch.setattr(launch, 'execute', execute)
    monkeypatch.setattr(launch, 'read_answer', lambda actor, receipt: receipt['answer'])
    return execute


def freeze(lab, *, complete=True):
    assert callable(getattr(M, 'adopt', None)), 'controller-owned accepting adoption is missing'
    return M.prepare(lab[0], str(lab[1]), lab[2], lab[4], require_complete_usage=complete)


def finish(lab):
    frozen = freeze(lab)
    result = M.run(lab[0], str(lab[1]), frozen['campaign_id'])
    assert result['status'] == 'GRADED_HELD', result
    return frozen, result


def adopt(lab, frozen, result):
    return M.adopt(lab[0], str(lab[1]), frozen['campaign_id'], run_id=result['trial_run_id'])


def test_controller_owned_qualified_transport_reaches_activation_and_rollback(lab, transport):
    frozen, result = finish(lab)
    accepted = adopt(lab, frozen, result)
    assert accepted['status'] == 'active' and accepted['usage_complete'] is True
    assert accepted['candidate_tokens'] == 70 and accepted['base_tokens'] == 2000
    identity = result['procedure_id']
    assert P.matches(lab[0], str(lab[1]), 'status extraction')
    assert P.inspect(lab[0], str(lab[1]), identity)['status'] == 'active'
    with P._db(lab[0]) as con:
        events = con.execute("SELECT action FROM procedure_events WHERE id=?", (identity,)).fetchall()
    assert [r[0] for r in events].count('native_verified_active') == 1
    with pytest.raises(ValueError):
        adopt(lab, frozen, result)
    P.change(lab[0], str(lab[1]), identity, rollback=True)
    assert not P.matches(lab[0], str(lab[1]), 'status extraction')
    assert P.withdrawn(lab[0], str(lab[1]), {identity}) == [identity]
    with pytest.raises(ValueError):
        adopt(lab, frozen, result)


def test_native_aggregate_counters_cannot_certify_campaign_usage(lab, transport):
    frozen = freeze(lab, complete=False)
    result = M.run(lab[0], str(lab[1]), frozen['campaign_id'])
    with pytest.raises(ValueError, match='usage|observer|complete'):
        adopt(lab, frozen, result)
    assert P.list_active(lab[0], str(lab[1])) == []


@pytest.mark.parametrize('fault', ['missing-provider', 'foreign-request', 'missing-request', 'foreign-prompt',
                                  'regression', 'token-excess', 'reused-response', 'malformed-provider',
                                  'malformed-response-id', 'wrong-provider-counts'])
def test_untrusted_transport_claims_fail_closed(lab, transport, monkeypatch, fault):
    def execute(*args, **kwargs):
        receipt = transport(*args, **kwargs)
        actor = args[0]
        if fault == 'missing-provider':
            receipt['evaluation_boundary'].pop('provider_usage', None)
        elif fault == 'foreign-request':
            receipt['request_sha256'] = 'f' * 64
        elif fault == 'missing-request':
            receipt.pop('request_sha256')
        elif fault == 'foreign-prompt':
            receipt['prompt_sha256'] = 'f' * 64
        elif fault == 'regression' and actor.name.endswith('-candidate') and '-2-' in actor.name:
            receipt['answer'] = '{"status":"wrong","source_ids":["task-evidence"]}'
            receipt['answer_sha256'] = C._sha(receipt['answer'].encode())
        elif fault == 'token-excess' and actor.name.endswith('-candidate'):
            receipt['usage']['input_tokens'] = 3000
            receipt['evaluation_boundary']['provider_usage']['input_tokens'] = 3000
        elif fault == 'reused-response':
            receipt['evaluation_boundary']['provider_usage']['response_id_sha256'] = ['f' * 64]
        elif fault == 'malformed-provider':
            receipt['evaluation_boundary']['provider_usage'] = []
        elif fault == 'malformed-response-id':
            receipt['evaluation_boundary']['provider_usage']['response_id_sha256'] = [{}]
        elif fault == 'wrong-provider-counts':
            receipt['evaluation_boundary']['provider_usage']['input_tokens'] += 1
        receipt.update(correct=True, score=1, usage_complete=True, promotion='GRANTED')
        return receipt
    monkeypatch.setattr(launch, 'execute', execute)
    frozen = freeze(lab)
    result = M.run(lab[0], str(lab[1]), frozen['campaign_id'])
    with pytest.raises(ValueError):
        M.adopt(lab[0], str(lab[1]), frozen['campaign_id'], run_id=result.get('trial_run_id', 'missing'))
    assert P.list_active(lab[0], str(lab[1])) == []


@pytest.mark.parametrize('fault', ['native', 'request', 'answer', 'task', 'runtime', 'omitted-observation',
                                  'foreign-run', 'foreign-project', 'correction'])
def test_adoption_replays_saved_evidence_and_current_candidate(lab, transport, monkeypatch, fault):
    frozen, result = finish(lab)
    folder = Path(frozen['freeze_path']).parent
    trial = folder.parent / ('run-' + result['trial_run_id'])
    if fault == 'native':
        (trial / 'native-3.json').write_text('{}')
    elif fault == 'request':
        next(trial.glob('trial-*/request.json')).write_text('{}')
    elif fault == 'answer':
        (lab[2] / 'answer-2.json').write_text('{"status":"changed"}')
    elif fault == 'task':
        (lab[1] / 'task-2.json').write_text('{}')
    elif fault == 'runtime':
        monkeypatch.setattr(M, '_runtime', lambda: {})
    elif fault == 'omitted-observation':
        data = C._json(trial / 'result.json')
        data['observations'].pop()
        (trial / 'result.json').write_bytes(P.encoded(data))
    elif fault == 'foreign-run':
        result['trial_run_id'] = 'foreign'
    elif fault == 'foreign-project':
        other = lab[1].parent / 'other'
        other.mkdir()
        with pytest.raises(ValueError):
            M.adopt(lab[0], str(other), frozen['campaign_id'], run_id=result['trial_run_id'])
        return
    else:
        candidate = P.inspect(lab[0], str(lab[1]), result['procedure_id'])['candidate']
        candidate['steps'] = ['A corrected method needs fresh evaluation.']
        P.correct(lab[0], str(lab[1]), result['procedure_id'], candidate)
    with pytest.raises((ValueError, OSError)):
        adopt(lab, frozen, result)
    assert P.list_active(lab[0], str(lab[1])) == []


@pytest.mark.parametrize('phase', ['development', 'preparation', 'trial'])
def test_unknown_failed_history_blocks_a_fresh_campaign(lab, transport, monkeypatch, phase):
    def crash(*args, **kwargs):
        name = args[0].name
        if (phase == 'development' and name.startswith('campaign-actor-')
                or phase == 'preparation' and name.startswith('prepare-actor-')
                or phase == 'trial' and name.startswith('trial-')):
            raise RuntimeError('fixture transport interrupted without terminal usage')
        return transport(*args, **kwargs)
    monkeypatch.setattr(launch, 'execute', crash)
    first = freeze(lab)
    assert M.run(lab[0], str(lab[1]), first['campaign_id'])['status'] == 'FAILED'
    monkeypatch.setattr(launch, 'execute', transport)
    frozen, result = finish(lab)
    with pytest.raises(ValueError, match='usage|history|unknown'):
        adopt(lab, frozen, result)


def test_complete_observed_failed_development_is_retained_as_selection_cost(lab, transport, monkeypatch):
    def wrong_answer(*args, **kwargs):
        receipt = transport(*args, **kwargs)
        receipt['answer'] = '{"status":"wrong","source_ids":["task-evidence"]}'
        receipt['answer_sha256'] = C._sha(receipt['answer'].encode())
        return receipt
    monkeypatch.setattr(launch, 'execute', wrong_answer)
    first = freeze(lab)
    assert M.run(lab[0], str(lab[1]), first['campaign_id'])['status'] == 'FAILED'
    monkeypatch.setattr(launch, 'execute', transport)
    frozen, result = finish(lab)
    assert adopt(lab, frozen, result)['candidate_tokens'] == 80


def test_known_prior_campaign_cost_is_charged_to_candidate(lab, transport):
    finish(lab)
    frozen, result = finish(lab)
    with pytest.raises(ValueError, match='tokens|baseline'):
        adopt(lab, frozen, result)


def test_source_change_after_activation_withholds_recall(lab, transport):
    frozen, result = finish(lab)
    adopt(lab, frozen, result)
    (lab[1] / 'task-0.json').write_text('changed source')
    identity = result['procedure_id']
    assert P.inspect(lab[0], str(lab[1]), identity)['status'] == 'stale'
    assert not P.matches(lab[0], str(lab[1]), 'status extraction')
    assert P.stale(lab[0], str(lab[1]), {identity}) == [identity]


@pytest.mark.parametrize('source, at_check, calls', [('task', 2, 0), ('answer', 3, 1)])
def test_trial_consumes_only_hash_bound_bytes_after_last_currentness_check(
        lab, transport, monkeypatch, source, at_check, calls):
    frozen = C.prepare(lab[0], str(lab[1]), lab[3]['id'], lab[2], lab[4])
    current = C._current
    checks = []
    def change_after_check(*args, **kwargs):
        current(*args, **kwargs)
        checks.append(1)
        if len(checks) == at_check:
            target = lab[1] / 'task-0.json' if source == 'task' else lab[2] / 'answer-0.json'
            target.write_text('{"status":"changed after check"}')
    monkeypatch.setattr(C, '_current', change_after_check)
    result = C.execute(lab[0], str(lab[1]), frozen['run_id'])
    assert result['status'] == 'FAILED' and result['observed_calls'] == calls
    assert result['observations'] == [] and result['failures']


def test_collection_rejects_foreign_request_before_declaring_development_passed(lab, transport, monkeypatch):
    def foreign(*args, **kwargs):
        receipt = transport(*args, **kwargs)
        receipt['request_sha256'] = 'f' * 64
        return receipt
    monkeypatch.setattr(launch, 'execute', foreign)
    frozen = freeze(lab)
    result = M.collect_development(lab[0], str(lab[1]), frozen['campaign_id'])
    assert result['status'] == 'FAILED' and result['experiences'] == []
    assert result['consumed_calls'] == 1 and result['attempts'][0]['native_sha256']


def test_concurrent_adoption_commits_one_activation_event(lab, transport):
    from concurrent.futures import ThreadPoolExecutor
    frozen, result = finish(lab)
    def accept(_):
        try:
            return adopt(lab, frozen, result)['status']
        except ValueError:
            return 'refused'
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(accept, range(2)))
    assert sorted(outcomes) == ['active', 'refused']
    with P._db(lab[0]) as con:
        count = con.execute("SELECT count(*) FROM procedure_events WHERE id=? AND action='native_verified_active'",
                            (result['procedure_id'],)).fetchone()[0]
    assert count == 1


def test_suite_metadata_edit_between_parsing_and_freezing_prevents_development(lab, monkeypatch):
    inputs = M._inputs
    def edited_suite(*args, **kwargs):
        result = inputs(*args, **kwargs)
        data = json.loads(lab[4].read_text())
        data['effort'] = 'low'
        lab[4].write_text(json.dumps(data))
        return result
    monkeypatch.setattr(M, '_inputs', edited_suite)
    frozen = freeze(lab, complete=False)
    monkeypatch.setattr(C, '_invoke', examples.fake_invoke)
    with pytest.raises(ValueError, match='changed|copy'):
        M.collect_development(lab[0], str(lab[1]), frozen['campaign_id'])


@pytest.mark.parametrize('bad_ids', [[{}], [[]], [True], ['invalid']])
def test_complete_observer_validates_response_ids_before_hashing(lab, transport, bad_ids):
    actor = lab[1] / 'fixture-observer-actor'
    actor.mkdir()
    request = C._actor(actor, {'instruction': 'Read the status.', 'evidence': 'Status: case-0.'}, None)
    receipt = C._invoke(actor, request, lab[2], model='fixture-model', effort='high', timeout=5,
                        require_complete_usage=True)
    context = {'model': 'fixture-model', 'effort': 'high', 'require_complete_usage': True}
    assert C._complete_tokens(receipt, context) == 10
    receipt['evaluation_boundary']['provider_usage']['response_id_sha256'] = bad_ids
    with pytest.raises(ValueError, match='upstream|usage|observation'):
        C._complete_tokens(receipt, context)


def test_json_formatting_does_not_make_a_development_task_unseen(lab, transport):
    import json
    task = lab[1] / 'task-0.json'
    (lab[1] / 'task-2.json').write_text(json.dumps(json.loads(task.read_text()), indent=4))
    with pytest.raises(ValueError, match='overlap|duplicate|unseen'):
        freeze(lab)


def test_nonterminal_sibling_history_cannot_certify_complete_usage(lab, transport, monkeypatch):
    cheap = [True]
    def execute(*args, **kwargs):
        receipt = transport(*args, **kwargs)
        if cheap[0]:
            receipt['usage']['input_tokens'] = 9
            provider = receipt['evaluation_boundary'].get('provider_usage')
            if provider:
                provider['input_tokens'] = 9
        return receipt
    monkeypatch.setattr(launch, 'execute', execute)
    _, first = finish(lab)
    cheap[0] = False
    frozen, current = finish(lab)
    with P._db(lab[0]) as con:
        con.execute("UPDATE procedure_execution_runs SET state='CONSUMED' WHERE run_id=?",
                    (first['trial_run_id'],))
    with pytest.raises(ValueError, match='progress|terminal|consumed|unknown'):
        adopt(lab, frozen, current)
    assert P.list_active(lab[0], str(lab[1])) == []
