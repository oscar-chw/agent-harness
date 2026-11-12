"""Controller-observed preparation is measured provenance, never automatic promotion."""
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path

import pytest

from agent_harness import procedure_execution as controller, procedures
from . import test_procedure_execution_controller as examples

lab = examples.lab
fake_invoke = examples.fake_invoke


@pytest.fixture
def preparation():
    assert importlib.util.find_spec('agent_harness.procedure_preparation') is not None, 'owned native preparation is required'
    return importlib.import_module('agent_harness.procedure_preparation')


def specification(lab):
    _, project, oracle, proposal, _ = lab
    spec = {'schema': 1, 'episodes': [{k: e[k] for k in ('task_id', 'path', 'task_path')}
                                     for e in proposal['candidate']['episodes']],
            'model': 'fixture-model', 'effort': 'high', 'timeout_seconds': 5}
    path = oracle / 'preparation-spec.json'
    path.write_text(json.dumps(spec))
    return path


def frozen(preparation, lab):
    home, project, oracle, _, _ = lab
    return preparation.prepare(home, str(project), oracle, specification(lab))


def generated(actor, request, oracle, **kwargs):
    receipt = fake_invoke(actor, request, oracle, **kwargs)
    body = {'title': 'Current status extraction', 'trigger': 'status extraction',
            'steps': ['Use only the status explicitly present in the current source.'],
            'exceptions': ['Keep unknown values unknown.'], 'source_ids': ['task-evidence']}
    receipt['answer'] = json.dumps(body)
    receipt['answer_sha256'] = hashlib.sha256(receipt['answer'].encode()).hexdigest()
    return receipt


def test_prepare_binds_sources_but_never_calls_or_promotes(preparation, lab, monkeypatch):
    monkeypatch.setattr(controller, '_invoke', lambda *a, **k: pytest.fail('freeze must not call a model'))
    result = frozen(preparation, lab)
    assert result['status'] == 'PREPARED' and result['calls_max'] == 1
    packet = json.loads(Path(result['freeze_path']).read_text())
    assert len(packet['episodes']) == 2 and packet['runtime'] == controller._runtime()
    assert all(e['sha256'] and e['task_sha256'] for e in packet['episodes'])
    assert not procedures.list_active(lab[0], str(lab[1]))


def test_observed_draft_and_usage_feed_trial_total_but_wider_hold_remains(preparation, lab, monkeypatch):
    monkeypatch.setattr(controller, '_invoke', generated)
    freeze = frozen(preparation, lab)
    result = preparation.execute(lab[0], str(lab[1]), freeze['run_id'])
    assert result['status'] == 'DRAFTED_HELD' and result['observed_tokens'] == 10
    assert result['observed_calls'] == 1 and result['promotion'] == 'NOT_GRANTED'
    proposal = procedures.inspect(lab[0], str(lab[1]), result['procedure_id'])
    assert proposal['status'] == 'proposed' and not procedures.list_active(lab[0], str(lab[1]))
    with procedures._db(lab[0]) as con:
        payload = procedures._proposal(con, str(lab[1]), result['procedure_id'])
    provenance = preparation.observed(lab[0], str(lab[1]), freeze['run_id'], payload)
    assert provenance['tokens'] == 10 and provenance['run_id'] == freeze['run_id']
    trial = controller.prepare(lab[0], str(lab[1]), result['procedure_id'], lab[2], lab[4],
                               preparation_run_id=freeze['run_id'])
    monkeypatch.setattr(controller, '_invoke', fake_invoke)
    outcome = controller.execute(lab[0], str(lab[1]), trial['run_id'])
    assert outcome['known_preparation_tokens'] == 10
    assert outcome['known_candidate_tokens_lower_bound'] == 50
    assert outcome['known_baseline_tokens'] == 20
    assert outcome['usage_complete'] is False and outcome['promotion'] == 'NOT_GRANTED'
    assert 'maintenance' in ' '.join(outcome['holds'])
    with pytest.raises(ValueError, match='consumed|already'):
        preparation.execute(lab[0], str(lab[1]), freeze['run_id'])


@pytest.mark.parametrize('fault', ['wrong-sources', 'extra-authority', 'empty-steps', 'tools-used',
                                   'wrong-model', 'partial-usage', 'crash'])
def test_invalid_preparer_is_consumed_without_draft_or_retry(preparation, lab, monkeypatch, fault):
    calls = []
    def invoke(*args, **kwargs):
        calls.append(1)
        if fault == 'crash':
            raise RuntimeError('preparation failed')
        value = generated(*args, **kwargs)
        answer = json.loads(value['answer'])
        if fault == 'wrong-sources': answer['source_ids'] = ['invented']
        elif fault == 'extra-authority': answer['activate'] = True
        elif fault == 'empty-steps': answer['steps'] = []
        elif fault == 'tools-used': value['runtime_events']['items'] = [{'item_type': 'command_execution'}]
        elif fault == 'wrong-model': value['evaluation_boundary']['resolved']['model'] = 'other'
        else: value['usage_status'] = 'UNKNOWN'
        value['answer'] = json.dumps(answer)
        value['answer_sha256'] = hashlib.sha256(value['answer'].encode()).hexdigest()
        return value
    monkeypatch.setattr(controller, '_invoke', invoke)
    freeze = frozen(preparation, lab)
    result = preparation.execute(lab[0], str(lab[1]), freeze['run_id'])
    assert result['status'] == 'FAILED' and result['promotion'] == 'NOT_GRANTED'
    assert len(calls) == result['observed_calls'] == 1
    assert 'procedure_id' not in result
    with pytest.raises(ValueError, match='consumed|already'):
        preparation.execute(lab[0], str(lab[1]), freeze['run_id'])


def test_receipt_with_foreign_request_identity_yields_no_draft(preparation, lab, monkeypatch):
    def invoke(*args, **kwargs):
        value = generated(*args, **kwargs)
        value['request_sha256'] = 'ff' * 32
        return value
    monkeypatch.setattr(controller, '_invoke', invoke)
    freeze = frozen(preparation, lab)
    result = preparation.execute(lab[0], str(lab[1]), freeze['run_id'])
    assert result['status'] == 'FAILED' and result['promotion'] == 'NOT_GRANTED'
    assert 'request identity' in result['error']
    assert 'procedure_id' not in result
    with pytest.raises(ValueError, match='consumed|already'):
        preparation.execute(lab[0], str(lab[1]), freeze['run_id'])


@pytest.mark.parametrize('fault', ['source', 'task', 'specification', 'runtime', 'freeze'])
def test_stale_preparation_fails_before_native_use(preparation, lab, monkeypatch, fault):
    freeze = frozen(preparation, lab)
    if fault == 'source': (lab[1] / 'episode-0.md').write_text('Changed source')
    elif fault == 'task': (lab[1] / 'task-0.json').write_text('Changed task')
    elif fault == 'specification': specification(lab).write_text('{}')
    elif fault == 'runtime': monkeypatch.setattr(controller, '_runtime', lambda: {'changed': '0'*64})
    else: Path(freeze['freeze_path']).write_text('{}')
    monkeypatch.setattr(controller, '_invoke', lambda *a, **k: pytest.fail('stale input must not invoke'))
    with pytest.raises((ValueError, OSError)):
        preparation.execute(lab[0], str(lab[1]), freeze['run_id'])


@pytest.mark.parametrize('fault', ['foreign-project', 'wrong-candidate', 'forged-run', 'changed-receipt'])
def test_preparation_provenance_cannot_be_transferred(preparation, lab, monkeypatch, fault):
    monkeypatch.setattr(controller, '_invoke', generated)
    freeze = frozen(preparation, lab)
    result = preparation.execute(lab[0], str(lab[1]), freeze['run_id'])
    home, project, oracle, old, suite = lab
    identity, run_id = result['procedure_id'], freeze['run_id']
    if fault == 'foreign-project':
        project = project.parent / 'foreign'; project.mkdir(); (project / '.git').mkdir()
    elif fault == 'wrong-candidate': identity = old['id']
    elif fault == 'forged-run': run_id = 'not-an-observed-preparation'
    else:
        record = Path(freeze['freeze_path']).parent / 'observed.json'
        record.write_text('{}')
    with pytest.raises((ValueError, OSError)):
        controller.prepare(home, str(project), identity, oracle, suite, preparation_run_id=run_id)


def test_preparer_cannot_bless_a_concurrent_source_edit(preparation, lab, monkeypatch):
    def invoke(*args, **kwargs):
        value = generated(*args, **kwargs)
        (lab[1] / 'episode-0.md').write_text('Changed during preparation')
        return value
    monkeypatch.setattr(controller, '_invoke', invoke)
    freeze = frozen(preparation, lab)
    result = preparation.execute(lab[0], str(lab[1]), freeze['run_id'])
    assert result['status'] == 'FAILED' and 'procedure_id' not in result


def test_unknown_run_cannot_become_accounting_authority(preparation, lab):
    with pytest.raises(ValueError):
        controller.prepare(lab[0], str(lab[1]), lab[3]['id'], lab[2], lab[4],
                           preparation_run_id='caller-supplied-pass')


def test_cli_freeze_is_separate_from_explicit_native_execution(preparation, lab, monkeypatch, capsys):
    from agent_harness import cli
    monkeypatch.setenv('HARNESS_HOME', str(lab[0]))
    monkeypatch.setattr(controller, '_invoke', lambda *a, **k: pytest.fail('CLI freeze must not call'))
    spec = specification(lab)
    argv = ['improve', '--project', str(lab[1]), '--prepare-native-draft', str(spec),
            '--oracle-root', str(lab[2])]
    assert cli.main(argv) == 0
    freeze = json.loads(capsys.readouterr().out)
    assert freeze['status'] == 'PREPARED' and freeze['calls_max'] == 1
    monkeypatch.setattr(controller, '_invoke', generated)
    assert cli.main(['improve', '--project', str(lab[1]), '--execute-native-draft', freeze['run_id']]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['status'] == 'DRAFTED_HELD' and result['promotion'] == 'NOT_GRANTED'


def test_cli_does_not_combine_drafting_with_an_apply_or_discovery_action(preparation, lab, monkeypatch, capsys):
    from agent_harness import cli
    monkeypatch.setenv('HARNESS_HOME', str(lab[0]))
    monkeypatch.setattr(controller, '_invoke', lambda *a, **k: pytest.fail('combined actions must not call'))
    argv = ['improve', '--project', str(lab[1]), '--prepare-native-draft', str(specification(lab)),
            '--oracle-root', str(lab[2]), '--propose']
    assert cli.main(argv) == 1
    assert 'one action' in capsys.readouterr().out


@pytest.mark.parametrize('fault', ['measured-failure', 'unknown-failure'])
def test_retry_cannot_erase_previous_preparation_cost(preparation, lab, monkeypatch, fault):
    def failed(*args, **kwargs):
        if fault == 'unknown-failure':
            raise RuntimeError('native startup ended without complete usage')
        receipt = generated(*args, **kwargs)
        answer = json.loads(receipt['answer']); answer['steps'] = []
        receipt['answer'] = json.dumps(answer)
        receipt['answer_sha256'] = hashlib.sha256(receipt['answer'].encode()).hexdigest()
        return receipt
    monkeypatch.setattr(controller, '_invoke', failed)
    first = frozen(preparation, lab)
    assert preparation.execute(lab[0], str(lab[1]), first['run_id'])['status'] == 'FAILED'
    monkeypatch.setattr(controller, '_invoke', generated)
    second = frozen(preparation, lab)
    result = preparation.execute(lab[0], str(lab[1]), second['run_id'])
    with procedures._db(lab[0]) as con:
        payload = procedures._proposal(con, str(lab[1]), result['procedure_id'])
    meter = preparation.observed(lab[0], str(lab[1]), second['run_id'], payload)
    assert meter['tokens'] == (20 if fault == 'measured-failure' else 10)
    assert set(meter['attempt_ids']) == {first['run_id'], second['run_id']}
    assert meter['unknown_attempts'] == ([first['run_id']] if fault == 'unknown-failure' else [])


def test_preparation_cannot_copy_evaluator_files_into_the_actor(preparation, lab):
    spec_path = specification(lab)
    spec = json.loads(spec_path.read_text())
    spec['episodes'][0]['path'] = (lab[2] / 'answer-2.json').relative_to(lab[1]).as_posix()
    spec_path.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match='oracle|evaluator'):
        preparation.prepare(lab[0], str(lab[1]), lab[2], spec_path)


def test_attempt_is_committed_consumed_before_any_native_call(preparation, lab, monkeypatch):
    freeze = frozen(preparation, lab)
    def invoke(*args, **kwargs):
        with procedures._db(lab[0]) as con:
            state = con.execute('SELECT state FROM procedure_preparation_runs WHERE run_id=?',
                                (freeze['run_id'],)).fetchone()[0]
        assert state == 'CONSUMED'
        with pytest.raises(ValueError, match='consumed|already'):
            preparation.execute(lab[0], str(lab[1]), freeze['run_id'])
        return generated(*args, **kwargs)
    monkeypatch.setattr(controller, '_invoke', invoke)
    assert preparation.execute(lab[0], str(lab[1]), freeze['run_id'])['status'] == 'DRAFTED_HELD'
