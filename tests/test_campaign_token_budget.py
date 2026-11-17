"""Observed-token stops use the production controller and a fake native transport."""
import json
from pathlib import Path

import pytest

from agent_harness import cli, launch, procedure_campaign as M, procedures as P
from . import test_v3_learning_cycle as examples

lab = examples.lab
transport = examples.transport


def freeze(lab, limit):
    return M.prepare(lab[0], str(lab[1]), lab[2], lab[4],
                     require_complete_usage=True, native_token_limit=limit)


@pytest.mark.parametrize('limit,calls', [(1, 1), (20, 2), (30, 3), (40, 4), (50, 5),
                                        (1040, 6), (1060, 7), (1070, 8)])
def test_ceiling_stops_the_next_call_across_every_campaign_stage(lab, transport, monkeypatch, limit, calls):
    invoked = []

    def counted(*args, **kwargs):
        invoked.append(args[0].name)
        return transport(*args, **kwargs)

    monkeypatch.setattr(launch, 'execute', counted)
    frozen = freeze(lab, limit)
    bound = json.loads(Path(frozen['freeze_path']).read_text())
    assert bound['native_token_limit'] == limit
    result = M.run(lab[0], str(lab[1]), frozen['campaign_id'])
    assert result['status'] == 'FAILED'
    assert len(invoked) == calls
    assert 'token ceiling' in json.dumps(result)
    assert P.list_active(lab[0], str(lab[1])) == []
    first = json.loads((Path(frozen['freeze_path']).parent / 'development-native-0.json').read_text())
    assert P._native_tokens(first) == 10
    if calls > 3:
        child = json.loads(next(lab[2].glob('run-*/freeze.json')).read_text())
        assert child['native_token_limit'] == limit and child['native_tokens_before'] == 30
        assert len(list(lab[2].glob('run-*/native-*.json'))) == calls - 3
    with pytest.raises(ValueError, match='consumed|terminal'):
        M.run(lab[0], str(lab[1]), frozen['campaign_id'])
    assert len(invoked) == calls


def test_under_budget_completes_and_includes_baseline_as_consumption(lab, transport, monkeypatch):
    invoked = []

    def counted(*args, **kwargs):
        invoked.append(args[0].name)
        return transport(*args, **kwargs)

    monkeypatch.setattr(launch, 'execute', counted)
    frozen = freeze(lab, 3000)
    result = M.run(lab[0], str(lab[1]), frozen['campaign_id'])
    assert result['status'] == 'GRADED_HELD' and len(invoked) == 9
    assert sum(result['observed_role_tokens'].values()) == 2070
    report = M.assess(lab[0], str(lab[1]), frozen['campaign_id'], run_id=result['trial_run_id'])
    assert report['status'] == 'QUALIFIED_UNADOPTED'
    assert report['candidate_tokens'] == 70 and report['base_tokens'] == 2000
    assert P.list_active(lab[0], str(lab[1])) == []


def test_unknown_usage_stops_without_another_call_or_erasing_the_receipt(lab, transport, monkeypatch):
    invoked = []

    def unknown(*args, **kwargs):
        invoked.append(args[0].name)
        result = transport(*args, **kwargs)
        result.pop('usage')
        return result

    monkeypatch.setattr(launch, 'execute', unknown)
    frozen = freeze(lab, 3000)
    result = M.run(lab[0], str(lab[1]), frozen['campaign_id'])
    assert result['status'] == 'FAILED' and len(invoked) == 1
    assert result['unknown_usage_attempts'] == ['task-0']
    retained = Path(frozen['freeze_path']).parent / 'development-native-0.json'
    assert retained.exists() and 'usage' not in json.loads(retained.read_text())
    assert P.list_active(lab[0], str(lab[1])) == []


@pytest.mark.parametrize('limit', [True, 0, -1, 1.5, '3000'])
def test_invalid_limits_refuse_before_freezing_or_invoking(lab, transport, monkeypatch, limit):
    monkeypatch.setattr(launch, 'execute', lambda *a, **k: pytest.fail('invalid budget cannot invoke'))
    with pytest.raises(ValueError, match='token.*limit'):
        freeze(lab, limit)


def test_cli_freezes_the_limit_and_rejects_changing_it_at_execution(lab, transport, capsys):
    args = ['--home', str(lab[0]), 'improve', '--project', str(lab[1])]
    rc = cli.main(args + ['--prepare-campaign', str(lab[4]), '--oracle-root', str(lab[2]),
                          '--max-native-tokens', '20', '--complete-usage'])
    assert rc == 0
    frozen = json.loads(capsys.readouterr().out)
    assert json.loads(Path(frozen['freeze_path']).read_text())['native_token_limit'] == 20
    rc = cli.main(args + ['--execute-campaign', frozen['campaign_id'], '--max-native-tokens', '3000'])
    assert rc == 1
    assert 'prepare-campaign' in capsys.readouterr().out
