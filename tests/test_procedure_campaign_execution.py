"""Owned campaign stages; fixture receipts do not prove native learning efficacy."""
import json
from pathlib import Path

import pytest

from agent_harness import procedure_campaign as M, procedure_execution as C, procedures as P
from . import test_procedure_execution_controller as examples
from .test_procedure_native_preparation import generated

lab = examples.lab


@pytest.fixture
def pipeline():
    assert callable(getattr(M, 'run', None)), 'campaign must own drafting and paired execution'
    return M


def freeze(lab):
    return M.prepare(lab[0], str(lab[1]), lab[2], lab[4])


def fake(actor, request, oracle, **kwargs):
    r = (generated(actor, request, oracle, **kwargs) if 'Draft a short reusable procedure' in request['task']
         else examples.fake_invoke(actor, request, oracle, **kwargs))
    r['request_sha256'] = P.digest(request)
    return r


def collect(lab, monkeypatch):
    monkeypatch.setattr(C, '_invoke', fake)
    frozen = freeze(lab)
    M.collect_development(lab[0], str(lab[1]), frozen['campaign_id'])
    return frozen


def test_one_controller_run_owns_development_drafting_and_paired_execution(pipeline, lab, monkeypatch):
    calls = []
    def invoke(actor, request, oracle, **kwargs):
        calls.append(request['task'])
        if 'Draft a short reusable procedure' in request['task']:
            evidence = (actor / 'evidence.md').read_text()
            assert 'case-0' in evidence and 'case-1' in evidence
            assert 'case-2' not in evidence and 'case-3' not in evidence
            with P._db(lab[0]) as con:
                row = con.execute('SELECT state FROM procedure_campaign_runs').fetchone()
                stage = con.execute("SELECT payload FROM procedure_campaign_stages WHERE stage='preparation'").fetchone()
            assert row['state'] == 'PREPARATION_CONSUMED'
            assert json.loads(stage['payload'])['child_run_id']
        return fake(actor, request, oracle, **kwargs)
    monkeypatch.setattr(C, '_invoke', invoke)
    frozen = freeze(lab)
    result = pipeline.run(lab[0], str(lab[1]), frozen['campaign_id'])
    assert len(calls) == frozen['model_calls_max'] == 9
    assert sum('Draft a short reusable procedure' in x for x in calls) == 1
    assert result['status'] == 'GRADED_HELD' and result['usage_complete'] is False
    assert result['promotion'] == 'NOT_GRANTED' and result['trial_run_id'] and result['preparation_run_id']
    assert result['observed_role_tokens'] == {'development': 20, 'preparation': 10,
                                              'trial_base': 20, 'trial_candidate': 40}
    assert len(result['observations']) == 6 and all(o['correct'] for o in result['observations'])
    assert not P.list_active(lab[0], str(lab[1]))
    assert P.inspect(lab[0], str(lab[1]), result['procedure_id'])['status'] == 'proposed'
    with pytest.raises(ValueError, match='state|consumed'):
        pipeline.run(lab[0], str(lab[1]), frozen['campaign_id'])


def test_draft_can_only_use_replayed_controller_owned_development(pipeline, lab, monkeypatch):
    frozen = collect(lab, monkeypatch)
    result = M.draft(lab[0], str(lab[1]), frozen['campaign_id'])
    assert result['status'] == 'DRAFTED_HELD'
    candidate = P.inspect(lab[0], str(lab[1]), result['procedure_id'])
    assert candidate['status'] == 'proposed'
    with P._db(lab[0]) as con:
        proposal = P._proposal(con, str(lab[1]), result['procedure_id'])
    episodes = proposal['candidate']['episodes']
    assert {e['task_id'] for e in episodes} == {'task-0', 'task-1'}
    assert all('campaign-sources-' in e['path'] for e in episodes)
    assert not P.list_active(lab[0], str(lab[1]))
    with pytest.raises(ValueError, match='state|consumed'):
        M.draft(lab[0], str(lab[1]), frozen['campaign_id'])


@pytest.mark.parametrize('fault', ['result', 'native', 'experience', 'request'])
def test_changed_development_evidence_cannot_reach_preparation(pipeline, lab, monkeypatch, fault):
    frozen = collect(lab, monkeypatch)
    folder = Path(frozen['freeze_path']).parent
    if fault == 'request':
        target = next(folder.glob('campaign-actor-*/request.json'))
    else:
        target = folder / {'result':'development.json', 'native':'development-native-0.json',
                           'experience':'development-experience-0.json'}[fault]
    target.write_text('{}')
    monkeypatch.setattr(C, '_invoke', lambda *a, **k: pytest.fail('changed evidence must not invoke'))
    with pytest.raises(ValueError, match='changed|bound|evidence|request|experience'):
        M.draft(lab[0], str(lab[1]), frozen['campaign_id'])


@pytest.mark.parametrize('phase', ['development', 'preparation', 'trial'])
def test_failures_are_consumed_without_automatic_retry_or_activation(pipeline, lab, monkeypatch, phase):
    calls = []
    def invoke(actor, request, oracle, **kw):
        calls.append(1)
        should_fail = ((phase == 'development' and len(calls) == 1)
                       or (phase == 'preparation' and 'Draft a short reusable procedure' in request['task'])
                       or (phase == 'trial' and len(calls) == 4))
        if should_fail:
            raise RuntimeError('bounded fixture failure')
        return fake(actor, request, oracle, **kw)
    monkeypatch.setattr(C, '_invoke', invoke)
    frozen = freeze(lab)
    result = M.run(lab[0], str(lab[1]), frozen['campaign_id'])
    assert result['status'] == 'FAILED' and result['usage_complete'] is False
    assert len(calls) == {'development':1, 'preparation':3, 'trial':4}[phase]
    assert not P.list_active(lab[0], str(lab[1]))
    with pytest.raises(ValueError, match='state|consumed'):
        M.run(lab[0], str(lab[1]), frozen['campaign_id'])


def test_an_incorrect_heldout_candidate_stays_visible_and_cannot_activate(pipeline, lab, monkeypatch):
    def invoke(actor, request, oracle, **kw):
        r = fake(actor, request, oracle, **kw)
        if 'Procedure candidate' in request['task'] and 'case-2' in (actor / 'evidence.md').read_text():
            r['answer'] = '{"status":"wrong","source_ids":["task-evidence"]}'
            r['answer_sha256'] = C._sha(r['answer'].encode())
        return r
    monkeypatch.setattr(C, '_invoke', invoke)
    frozen = freeze(lab)
    result = M.run(lab[0], str(lab[1]), frozen['campaign_id'])
    wrong = [o for o in result['observations'] if o['split'] == 'heldout' and o['arm'] == 'candidate' and not o['correct']]
    assert len(wrong) == 1 and result['status'] == 'GRADED_HELD'
    assert result['promotion'] == 'NOT_GRANTED' and not P.list_active(lab[0], str(lab[1]))


def test_changed_sources_between_stages_refuse_before_more_calls(pipeline, lab, monkeypatch):
    frozen = collect(lab, monkeypatch)
    (lab[2] / 'answer-2.json').write_text('{}')
    monkeypatch.setattr(C, '_invoke', lambda *a, **k: pytest.fail('changed oracle must not invoke'))
    with pytest.raises(ValueError, match='changed'):
        M.run(lab[0], str(lab[1]), frozen['campaign_id'])


def test_correction_withdraws_a_generated_method_before_it_can_be_trialled(pipeline, lab, monkeypatch):
    frozen = collect(lab, monkeypatch)
    result = M.draft(lab[0], str(lab[1]), frozen['campaign_id'])
    with P._db(lab[0]) as con:
        old = P._proposal(con, str(lab[1]), result['procedure_id'])
    P.correct(lab[0], str(lab[1]), old['id'], {**old['candidate'], 'steps':['A corrected source-bound approach.']})
    monkeypatch.setattr(C, '_invoke', lambda *a, **k: pytest.fail('withdrawn method must not invoke'))
    with pytest.raises(ValueError, match='proposed|procedure|preparation'):
        M.evaluate(lab[0], str(lab[1]), frozen['campaign_id'])


@pytest.mark.parametrize('phase', ['preparation', 'trial'])
def test_interrupt_preserves_child_identity_and_consumes_parent_stage(pipeline, lab, monkeypatch, phase):
    calls = []
    def invoke(actor, request, oracle, **kw):
        calls.append(1)
        if len(calls) == (3 if phase == 'preparation' else 4):
            raise KeyboardInterrupt()
        return fake(actor, request, oracle, **kw)
    monkeypatch.setattr(C, '_invoke', invoke)
    frozen = freeze(lab)
    with pytest.raises(KeyboardInterrupt): M.run(lab[0], str(lab[1]), frozen['campaign_id'])
    with P._db(lab[0]) as con:
        row = con.execute('SELECT state FROM procedure_campaign_runs').fetchone()
        stage = con.execute('SELECT payload FROM procedure_campaign_stages WHERE stage=?',(phase,)).fetchone()
    assert row['state'] == 'INTERRUPTED' and json.loads(stage['payload'])['child_run_id']
    with pytest.raises(ValueError, match='state|consumed'):
        M.run(lab[0], str(lab[1]), frozen['campaign_id'])


def test_public_cli_can_execute_a_frozen_campaign_without_an_extra_action(pipeline, lab, monkeypatch, capsys):
    from agent_harness import cli
    monkeypatch.setattr(cli, '_paths', lambda args:(lab[0],lab[0]))
    monkeypatch.setattr(C, '_invoke', fake)
    frozen = freeze(lab)
    assert cli.main(['improve','--project',str(lab[1]),'--execute-campaign',frozen['campaign_id']]) == 0
    r = json.loads(capsys.readouterr().out)
    assert r['status'] == 'GRADED_HELD' and r['promotion'] == 'NOT_GRANTED'


def test_preparation_size_is_admitted_before_burning_development_quota(pipeline, lab, monkeypatch):
    for index in (0,1):
        p = lab[1] / f'task-{index}.json'
        task = json.loads(p.read_text()); task['evidence'] += 'x' * 4500
        p.write_text(json.dumps(task))
    monkeypatch.setattr(C, '_invoke', lambda *a, **k: pytest.fail('oversized preparation must not invoke'))
    with pytest.raises(ValueError, match='preparation.*budget|8192'):
        freeze(lab)


@pytest.mark.parametrize('phase', ['preparation', 'trial'])
def test_child_context_must_match_the_parent_freeze_before_child_execution(pipeline, lab, monkeypatch, phase):
    from agent_harness import procedure_preparation as S
    frozen = collect(lab, monkeypatch)
    if phase == 'trial': M.draft(lab[0], str(lab[1]), frozen['campaign_id'])
    engine = S if phase == 'preparation' else C
    original = engine.prepare
    def changed(*args, **kwargs):
        # Simulate a source swap during child freeze, then restore the parent.
        spec = Path(args[3] if phase == 'preparation' else args[4])
        raw = spec.read_bytes(); body = json.loads(raw); body['model'] = 'different-model'
        spec.write_text(json.dumps(body))
        try: return original(*args, **kwargs)
        finally: spec.write_bytes(raw)
    monkeypatch.setattr(engine, 'prepare', changed)
    monkeypatch.setattr(engine, 'execute', lambda *a, **k: pytest.fail('different child must not execute'))
    operation = M.draft if phase == 'preparation' else M.evaluate
    result = operation(lab[0], str(lab[1]), frozen['campaign_id'])
    assert result['status'] == 'FAILED' and 'child context' in result['error']


@pytest.mark.parametrize('option', ['--execute-campaign', '--prepare-campaign', '--collect-campaign-development'])
def test_pipeline_cli_rejects_empty_or_combined_actions(pipeline, lab, monkeypatch, capsys, option):
    from agent_harness import cli, improve
    monkeypatch.setattr(cli, '_paths', lambda args:(lab[0],lab[0]))
    monkeypatch.setattr(improve, 'propose', lambda *a, **k: pytest.fail('malformed action must not propose'))
    assert cli.main(['improve','--project',str(lab[1]),option,'','--propose']) == 1
    assert 'refused' in capsys.readouterr().out
