"""Owned campaign development precedes drafting; native fixtures are not efficacy proof."""
import importlib
import importlib.util
import json
from pathlib import Path

import pytest

from agent_harness import procedure_execution as C, procedures as P
from . import test_procedure_execution_controller as examples

lab = examples.lab
fake_invoke = examples.fake_invoke


@pytest.fixture
def campaign():
    assert importlib.util.find_spec('agent_harness.procedure_campaign') is not None, 'owned campaign is missing'
    return importlib.import_module('agent_harness.procedure_campaign')


def freeze(campaign, lab):
    home, project, oracle, _, suite = lab
    return campaign.prepare(home, str(project), oracle, suite)


def test_all_inputs_and_answers_are_frozen_before_any_experience_or_draft(campaign, lab, monkeypatch):
    monkeypatch.setattr(C, '_invoke', lambda *a, **k: pytest.fail('prepare must not invoke'))
    r = freeze(campaign, lab)
    f = json.loads(Path(r['freeze_path']).read_text())
    assert len(f['cases']) == 4 and len({c['task_sha256'] for c in f['cases']}) == 4
    assert all(c['answer_sha256'] for c in f['cases'])
    assert f['runtime']['procedure_campaign.py'] and r['model_calls_max'] == 9
    assert r['status'] == 'PREPARED' and r['promotion'] == 'NOT_GRANTED'


def test_development_is_executed_graded_journalled_and_never_uses_caller_episodes(campaign, lab, monkeypatch):
    calls = []
    def invoke(*args, **kwargs):
        calls.append(args[0])
        # The consumed journal must exist before crossing the native boundary.
        with P._db(lab[0]) as con:
            row = con.execute('SELECT state,journal FROM procedure_campaign_runs').fetchone()
        assert row['state'] == 'DEVELOPMENT_CONSUMED'
        journal = json.loads(row['journal'])
        assert journal[-1]['consumed'] is True and len(journal) == len(calls)
        return fake_invoke(*args, **kwargs)
    monkeypatch.setattr(C, '_invoke', invoke)
    f = freeze(campaign, lab)
    r = campaign.collect_development(lab[0], str(lab[1]), f['campaign_id'])
    assert r['status'] == 'DEVELOPMENT_PASSED' and len(calls) == 2
    assert [e['task_id'] for e in r['experiences']] == ['task-0', 'task-1']
    assert all(e['correct'] and e['native_sha256'] and e['artifact_sha256'] for e in r['experiences'])
    assert r['observed_native_tokens'] == 20 and r['usage_complete'] is False
    assert not P.list_active(lab[0], str(lab[1]))
    assert not any(p.exists() for p in calls)  # prior actors retained under denied oracle
    with pytest.raises(ValueError, match='consumed|state'):
        campaign.collect_development(lab[0], str(lab[1]), f['campaign_id'])


@pytest.mark.parametrize('which', ['suite', 'heldout-input', 'heldout-answer', 'development-input'])
def test_any_frozen_input_change_refuses_before_another_native_call(campaign, lab, monkeypatch, which):
    f = freeze(campaign, lab)
    target = {'suite': lab[4], 'heldout-input': lab[1] / 'task-2.json',
              'heldout-answer': lab[2] / 'answer-2.json', 'development-input': lab[1] / 'task-0.json'}[which]
    target.write_text('{}')
    monkeypatch.setattr(C, '_invoke', lambda *a, **k: pytest.fail('stale input must not invoke'))
    with pytest.raises(ValueError, match='changed'):
        campaign.collect_development(lab[0], str(lab[1]), f['campaign_id'])


@pytest.mark.parametrize('fault', ['wrong-answer', 'partial-usage', 'tools', 'crash', 'interrupt'])
def test_failed_development_is_retained_without_drafting_retries_or_activation(campaign, lab, monkeypatch, fault):
    calls = []
    def invoke(*args, **kwargs):
        calls.append(1)
        if fault == 'crash': raise RuntimeError('fixture native crash')
        if fault == 'interrupt': raise KeyboardInterrupt()
        r = fake_invoke(*args, **kwargs)
        if fault == 'wrong-answer':
            r['answer'] = '{"status":"wrong","source_ids":["task-evidence"]}'
            r['answer_sha256'] = C._sha(r['answer'].encode())
        if fault == 'partial-usage': r['usage_status'] = 'UNKNOWN'
        if fault == 'tools': r['runtime_events']['items'] = [{'item_type':'command_execution'}]
        return r
    monkeypatch.setattr(C, '_invoke', invoke)
    f = freeze(campaign, lab)
    if fault == 'interrupt':
        with pytest.raises(KeyboardInterrupt): campaign.collect_development(lab[0], str(lab[1]), f['campaign_id'])
        r = json.loads((Path(f['freeze_path']).parent / 'development.json').read_text())
    else:
        r = campaign.collect_development(lab[0], str(lab[1]), f['campaign_id'])
    assert len(calls) == r['consumed_calls'] == 1 and r['status'] in ('FAILED', 'INTERRUPTED')
    assert r['failures'] and r['usage_complete'] is False and r['promotion'] == 'NOT_GRANTED'
    assert not P.list_active(lab[0], str(lab[1]))
    with pytest.raises(ValueError, match='consumed|state'):
        campaign.collect_development(lab[0], str(lab[1]), f['campaign_id'])


def test_edited_answers_during_generation_do_not_become_trusted_experiences(campaign, lab, monkeypatch):
    def invoke(*args, **kwargs):
        r = fake_invoke(*args, **kwargs)
        (lab[2] / 'answer-2.json').write_text('{}')
        return r
    monkeypatch.setattr(C, '_invoke', invoke)
    f = freeze(campaign, lab)
    r = campaign.collect_development(lab[0], str(lab[1]), f['campaign_id'])
    assert r['status'] == 'FAILED' and r['experiences'] == []
    assert r['attempts'][0]['native_sha256'] and r['observed_native_tokens'] == 10
    with P._db(lab[0]) as con:
        row = con.execute('SELECT journal FROM procedure_campaign_runs WHERE campaign_id=?',
                          (f['campaign_id'],)).fetchone()
    assert json.loads(row['journal'])[0]['native_sha256'] == r['attempts'][0]['native_sha256']


def test_changed_runtime_refuses_before_any_experience(campaign, lab, monkeypatch):
    frozen = freeze(campaign, lab)
    monkeypatch.setattr(campaign, '_runtime', lambda: {'tampered': 'runtime'})
    monkeypatch.setattr(C, '_invoke', lambda *a, **k: pytest.fail('changed runtime must not invoke'))
    with pytest.raises(ValueError, match='runtime changed'):
        campaign.collect_development(lab[0], str(lab[1]), frozen['campaign_id'])


def test_task_copy_must_match_the_freeze_even_after_the_last_source_check(campaign, lab, monkeypatch):
    frozen = freeze(campaign, lab)
    original = campaign._current
    count = 0
    def check(packet):
        nonlocal count
        original(packet)
        count += 1
        if count == 2:
            target = lab[1] / 'task-0.json'
            body = json.loads(target.read_text()); body['evidence'] = 'Status: substituted.'
            target.write_text(json.dumps(body))
    monkeypatch.setattr(campaign, '_current', check)
    monkeypatch.setattr(C, '_invoke', lambda *a, **k: pytest.fail('substituted input must not invoke'))
    result = campaign.collect_development(lab[0], str(lab[1]), frozen['campaign_id'])
    assert result['status'] == 'FAILED' and result['consumed_calls'] == 0
    assert 'task copy' in result['failures'][0]['error']


def test_grader_answer_copy_must_also_match_the_frozen_bytes(campaign, lab, monkeypatch):
    frozen = freeze(campaign, lab)
    original = campaign._current
    calls = 0
    def check(packet):
        nonlocal calls
        original(packet)
        calls += 1
        if calls == 3:
            (lab[2] / 'answer-0.json').write_text('{"status":"substituted"}')
    def invoke(*a, **kw):
        native = fake_invoke(*a, **kw)
        native['answer'] = '{"status":"substituted","source_ids":["task-evidence"]}'
        native['answer_sha256'] = C._sha(native['answer'].encode())
        return native
    monkeypatch.setattr(campaign, '_current', check)
    monkeypatch.setattr(C, '_invoke', invoke)
    result = campaign.collect_development(lab[0], str(lab[1]), frozen['campaign_id'])
    assert result['status'] == 'FAILED' and result['experiences'] == []
    assert result['consumed_calls'] == 1 and 'answer copy' in result['failures'][0]['error']


def test_final_actor_storage_overflow_cannot_finish_development(campaign, lab, monkeypatch):
    monkeypatch.setattr(C, '_invoke', fake_invoke)
    frozen = freeze(campaign, lab)
    original = C._storage
    def storage(path):
        # Earlier retained actors also encounter the next pre-call storage check.
        # Only the final actor distinguishes the terminal check from that guard.
        if any(p.name.endswith('-1') for p in path.glob('campaign-actor-*')):
            raise ValueError('fixture storage cap exceeded')
        original(path)
    monkeypatch.setattr(C, '_storage', storage)
    r = campaign.collect_development(lab[0], str(lab[1]), frozen['campaign_id'])
    assert r['status'] == 'FAILED' and r['consumed_calls'] == 2
    assert 'storage cap' in r['failures'][0]['error']


@pytest.mark.parametrize('fault', ['renamed-input', 'one-development', 'answer-traversal', 'extra-field'])
def test_campaign_freeze_rejects_leakage_overlap_and_unbounded_spec(campaign, lab, fault):
    data = json.loads(lab[4].read_text())
    if fault == 'renamed-input': (lab[1] / 'task-2.json').write_bytes((lab[1] / 'task-0.json').read_bytes())
    elif fault == 'one-development': data['cases'][1]['split'] = 'heldout'
    elif fault == 'answer-traversal': data['cases'][2]['answer_path'] = '../outside.json'
    else: data['caller_scores'] = {'all': 1}
    lab[4].write_text(json.dumps(data))
    with pytest.raises((ValueError, OSError)): freeze(campaign, lab)
    assert not list(lab[2].glob('campaign-*/freeze.json'))


def test_public_cli_freezes_then_collects_owned_development(campaign, lab, monkeypatch, capsys):
    from agent_harness import cli
    monkeypatch.setattr(cli, '_paths', lambda args: (lab[0], lab[0]))
    monkeypatch.setattr(C, '_invoke', fake_invoke)
    base = ['improve', '--project', str(lab[1])]
    assert cli.main(base + ['--prepare-campaign', str(lab[4]), '--oracle-root', str(lab[2])]) == 0
    frozen = json.loads(capsys.readouterr().out)
    assert frozen['status'] == 'PREPARED'
    assert cli.main(base + ['--collect-campaign-development', frozen['campaign_id']]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['status'] == 'DEVELOPMENT_PASSED' and result['promotion'] == 'NOT_GRANTED'


@pytest.mark.parametrize('extra', [['--propose'], ['--execute-native-draft', 'other'],
                                  ['--collect-campaign-development', 'other']])
def test_public_campaign_cli_refuses_combined_actions(campaign, lab, monkeypatch, capsys, extra):
    from agent_harness import cli
    monkeypatch.setattr(cli, '_paths', lambda args: (lab[0], lab[0]))
    assert cli.main(['improve', '--project', str(lab[1]), '--prepare-campaign', str(lab[4]),
                     '--oracle-root', str(lab[2]), *extra]) == 1
    assert 'exactly one' in capsys.readouterr().out
    assert not list(lab[2].glob('campaign-*/freeze.json'))


@pytest.mark.parametrize('option', ['--prepare-campaign', '--collect-campaign-development'])
def test_empty_campaign_option_cannot_fall_through_to_another_action(campaign, lab, monkeypatch, capsys, option):
    from agent_harness import cli, improve
    monkeypatch.setattr(cli, '_paths', lambda args: (lab[0], lab[0]))
    monkeypatch.setattr(improve, 'propose', lambda *a, **kw: pytest.fail('malformed action must not propose'))
    assert cli.main(['improve', '--project', str(lab[1]), option, '', '--propose']) == 1
    assert 'refused' in capsys.readouterr().out
