"""Public learning CLI preserves frozen observation and explicit run identity."""
import json

from agent_harness import cli, procedure_campaign as campaign


def test_freeze_can_request_complete_usage_without_running_models(tmp_path, monkeypatch, capsys):
    calls = []
    def prepare(home, project, oracle, suite, **kwargs):
        calls.append((project, oracle, suite, kwargs))
        return {'status': 'PREPARED', 'campaign_id': 'fixture'}
    monkeypatch.setattr(campaign, 'prepare', prepare)
    rc = cli.main(['--home', str(tmp_path), 'improve', '--project', str(tmp_path),
                   '--prepare-campaign', 'suite.json', '--oracle-root', 'oracle', '--complete-usage'])
    assert rc == 0
    assert calls[0][3] == {'require_complete_usage': True}
    assert json.loads(capsys.readouterr().out)['status'] == 'PREPARED'


def test_adoption_uses_controller_campaign_and_evaluation_run_only(tmp_path, monkeypatch, capsys):
    calls = []
    def adopt(home, project, identity, **kwargs):
        calls.append((project, identity, kwargs))
        return {'status': 'active', 'id': 'pr-fixture'}
    monkeypatch.setattr(campaign, 'adopt', adopt)
    rc = cli.main(['--home', str(tmp_path), 'improve', '--project', str(tmp_path),
                   '--adopt-campaign', 'campaign-fixture', '--evaluation-run', 'run-fixture'])
    assert rc == 0
    assert calls == [(str(tmp_path), 'campaign-fixture', {'run_id': 'run-fixture'})]
    assert json.loads(capsys.readouterr().out)['status'] == 'active'


def test_automatic_adoption_waits_for_a_graded_controller_result(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(campaign, 'run', lambda *a: {'status': 'FAILED', 'trial_run_id': 'bad'})
    monkeypatch.setattr(campaign, 'adopt', lambda *a, **k: (_ for _ in ()).throw(AssertionError('must not adopt')))
    rc = cli.main(['--home', str(tmp_path), 'improve', '--project', str(tmp_path),
                   '--execute-campaign', 'campaign-fixture', '--adopt-if-qualified'])
    assert rc == 1
    assert json.loads(capsys.readouterr().out)['status'] == 'FAILED'


def test_automatic_adoption_runs_the_same_admission_gate(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(campaign, 'run', lambda *a: {'status': 'GRADED_HELD', 'trial_run_id': 'run-fixture'})
    calls = []
    def adopt(home, project, identity, **kwargs):
        calls.append(kwargs)
        raise ValueError('aggregate tokens exceed the baseline')
    monkeypatch.setattr(campaign, 'adopt', adopt)
    rc = cli.main(['--home', str(tmp_path), 'improve', '--project', str(tmp_path),
                   '--execute-campaign', 'campaign-fixture', '--adopt-if-qualified'])
    assert rc == 1 and calls == [{'run_id': 'run-fixture'}]
    assert 'aggregate tokens' in capsys.readouterr().out
