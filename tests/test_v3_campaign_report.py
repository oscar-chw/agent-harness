"""Inspection replays evidence without inference or promotion."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from agent_harness import cli, procedure_campaign as campaign, procedures
from . import test_v3_learning_cycle as examples

finish = examples.finish
lab = examples.lab
transport = examples.transport


def test_assessment_reports_full_cost_without_activating(lab, transport, monkeypatch):
    frozen, result = finish(lab)
    monkeypatch.setattr(campaign.C, '_call', lambda *a: pytest.fail('inspection cannot call a model'))
    report = campaign.assess(lab[0], str(lab[1]), frozen['campaign_id'], run_id=result['trial_run_id'])
    assert report['status'] == 'QUALIFIED_UNADOPTED'
    assert report['base_tokens'] == 2000
    assert report['candidate_tokens'] == 70
    assert report['overhead_tokens'] == 50
    assert report['usage_complete'] is True and report['promotion'] == 'NOT_GRANTED'
    assert procedures.list_active(lab[0], str(lab[1])) == []
    assert campaign.assess(lab[0], str(lab[1]), frozen['campaign_id'],
                           run_id=result['trial_run_id']) == report


def test_cost_regression_remains_held_and_reports_the_gap(lab, transport, monkeypatch):
    from agent_harness import launch

    def expensive(*args, **kwargs):
        receipt = transport(*args, **kwargs)
        if args[0].name.endswith('-candidate'):
            receipt['usage']['input_tokens'] = 3000
            receipt['evaluation_boundary']['provider_usage']['input_tokens'] = 3000
        return receipt

    monkeypatch.setattr(launch, 'execute', expensive)
    frozen, result = finish(lab)
    report = campaign.assess(lab[0], str(lab[1]), frozen['campaign_id'], run_id=result['trial_run_id'])
    assert report['status'] == 'HELD'
    assert report['candidate_tokens'] > report['base_tokens']
    assert report['token_deficit'] == report['candidate_tokens'] - report['base_tokens']
    assert 'aggregate tokens' in report['reason']
    assert procedures.list_active(lab[0], str(lab[1])) == []


def test_inspection_refuses_missing_or_changed_evidence(lab, transport):
    frozen, result = finish(lab)
    with pytest.raises(ValueError):
        campaign.assess(lab[0], str(lab[1]), frozen['campaign_id'], run_id='foreign')
    (lab[1] / 'task-2.json').write_text('{}')
    with pytest.raises(ValueError):
        campaign.assess(lab[0], str(lab[1]), frozen['campaign_id'], run_id=result['trial_run_id'])


def test_public_inspection_is_read_only_and_nonqualifying_reports_exit_one(tmp_path, monkeypatch, capsys):
    calls = []

    def assess(home, project, identity, **kwargs):
        calls.append((project, identity, kwargs))
        return {'status': 'HELD', 'promotion': 'NOT_GRANTED', 'reason': 'aggregate tokens'}

    monkeypatch.setattr(campaign, 'assess', assess, raising=False)
    rc = cli.main(['--home', str(tmp_path), 'improve', '--project', str(tmp_path),
                   '--assess-campaign', 'campaign', '--evaluation-run', 'run'])
    assert rc == 1
    assert calls == [(str(tmp_path), 'campaign', {'run_id': 'run'})]
    assert json.loads(capsys.readouterr().out)['promotion'] == 'NOT_GRANTED'


def test_inspection_cannot_create_a_missing_store(tmp_path):
    home = tmp_path / 'absent'
    with pytest.raises(ValueError):
        campaign.assess(home, str(tmp_path), 'missing', run_id='missing')
    assert not home.exists()


def test_correction_during_replay_invalidates_assessment(lab, transport, monkeypatch):
    frozen, result = finish(lab)
    original = campaign._history

    def corrected(*args):
        history = original(*args)
        old = procedures.inspect(lab[0], str(lab[1]), result['procedure_id'])['candidate']
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(procedures.correct, lab[0], str(lab[1]), result['procedure_id'],
                        {**old, 'steps': ['Use the independently corrected method.']}).result(timeout=5)
        return history

    monkeypatch.setattr(campaign, '_history', corrected)
    with pytest.raises(ValueError, match='changed|current|state'):
        campaign.assess(lab[0], str(lab[1]), frozen['campaign_id'], run_id=result['trial_run_id'])


def test_bad_answer_json_still_has_known_usage_and_still_fails_output_grading(lab, transport):
    actor = lab[1] / 'actor'
    actor.mkdir()
    task = campaign.C._json(lab[1] / 'task-0.json')
    campaign.C._actor(actor, task, None)
    receipt = transport(actor, 'request.json', 'native.json', native_model='fixture-model',
                        native_effort='high', timeout=5, eval_deny_root=lab[2], eval_provider_usage=True)
    receipt['answer'] = r'{"status":"\q"}'
    receipt['answer_sha256'] = campaign.C._sha(receipt['answer'].encode())
    frozen = {'model': 'fixture-model', 'effort': 'high', 'require_complete_usage': True}
    assert campaign.C._complete_tokens(receipt, frozen) == 10
    with pytest.raises(ValueError):
        campaign.C._native_output(receipt, frozen)


def test_assessment_uses_read_only_store_connections_and_preserves_bytes(lab, transport, monkeypatch):
    frozen, result = finish(lab)
    db = lab[0] / 'procedures.sqlite'
    before = db.read_bytes()
    connect, observed = sqlite3.connect, []
    writes = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
              sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_ALTER_TABLE,
              sqlite3.SQLITE_DROP_TABLE}

    def checked(path, *args, **kwargs):
        connection = connect(path, *args, **kwargs)
        if 'procedures.sqlite' in str(path):
            observed.append((path, kwargs))
            connection.set_authorizer(lambda action, *rest: sqlite3.SQLITE_DENY
                                      if action in writes else sqlite3.SQLITE_OK)
        return connection

    monkeypatch.setattr(sqlite3, 'connect', checked)
    report = campaign.assess(lab[0], str(lab[1]), frozen['campaign_id'], run_id=result['trial_run_id'])
    assert report['status'] == 'QUALIFIED_UNADOPTED'
    assert observed and all('mode=ro' in str(path) and options.get('uri') for path, options in observed)
    assert db.read_bytes() == before
