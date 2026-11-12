"""Failed/repeated controller trials retain costs; fixtures are not native proof."""
import hashlib
from pathlib import Path

import pytest

from agent_harness import procedure_execution as C, procedures as P
from . import test_procedure_execution_controller as examples

lab = examples.lab


def run(lab):
    home, project, oracle, proposal, suite = lab
    frozen = C.prepare(home, str(project), proposal['id'], oracle, suite)
    return frozen, C.execute(home, str(project), frozen['run_id'])


@pytest.mark.parametrize('fault', ['wrong-model', 'invalid-answer', 'changed-suite'])
def test_received_usage_survives_rejection_before_grading(lab, monkeypatch, fault):
    def invoke(*args, **kwargs):
        receipt = examples.fake_invoke(*args, **kwargs)
        if fault == 'wrong-model':
            receipt['evaluation_boundary']['resolved']['model'] = 'other-model'
        elif fault == 'invalid-answer':
            receipt['answer'] = 'not JSON'
            receipt['answer_sha256'] = hashlib.sha256(receipt['answer'].encode()).hexdigest()
        else:
            lab[4].write_text('{}')
        return receipt
    monkeypatch.setattr(C, '_invoke', invoke)
    frozen, result = run(lab)
    assert result['status'] == 'FAILED' and not result['observations']
    assert result['known_candidate_tokens_lower_bound'] == 10
    assert result['execution_usage']['unknown_attempts'] == []
    assert result['usage_complete'] is False and result['promotion'] == 'NOT_GRANTED'
    assert (Path(frozen['freeze_path']).parent / 'native-1.json').is_file()


@pytest.mark.parametrize('unknown', [False, True])
def test_new_run_cannot_erase_failed_execution_cost_or_unknowns(lab, monkeypatch, unknown):
    def fail(*args, **kwargs):
        if unknown:
            raise RuntimeError('native call ended before its usage was received')
        receipt = examples.fake_invoke(*args, **kwargs)
        receipt['answer'] = '{}'
        receipt['answer_sha256'] = hashlib.sha256(b'{}').hexdigest()
        return receipt
    monkeypatch.setattr(C, '_invoke', fail)
    first, failed = run(lab)
    assert failed['status'] == 'FAILED'
    monkeypatch.setattr(C, '_invoke', examples.fake_invoke)
    second, result = run(lab)
    assert result['known_candidate_tokens_lower_bound'] == (40 if unknown else 50)
    meter = result['execution_usage']
    assert meter['attempt_ids'] == [first['run_id'], second['run_id']]
    assert meter['known_prior_tokens'] == (0 if unknown else 10)
    assert meter['unknown_attempts'] == ([{'run_id': first['run_id'], 'call': 1}] if unknown else [])
    assert result['known_baseline_tokens'] == 20
    assert result['promotion'] == 'NOT_GRANTED' and result['usage_complete'] is False


def test_all_prior_trial_arms_are_selection_overhead_not_a_new_baseline(lab, monkeypatch):
    monkeypatch.setattr(C, '_invoke', examples.fake_invoke)
    first, _ = run(lab)
    _, result = run(lab)
    # The preceding four candidate and two baseline calls all cost real usage.
    assert result['execution_usage']['known_prior_tokens'] == 60
    assert result['known_candidate_tokens_lower_bound'] == 100
    assert result['known_baseline_tokens'] == 20
    assert first['run_id'] in result['execution_usage']['attempt_ids']


def test_consumed_journal_survives_missing_final_result(lab, monkeypatch):
    monkeypatch.setattr(C, '_invoke', examples.fake_invoke)
    save = C._save
    def fail_final(path, data):
        if path.name == 'result.json':
            raise OSError('simulated final result write failure')
        return save(path, data)
    monkeypatch.setattr(C, '_save', fail_final)
    with pytest.raises(OSError, match='simulated'):
        run(lab)
    monkeypatch.setattr(C, '_save', save)
    _, result = run(lab)
    assert result['execution_usage']['known_prior_tokens'] == 60
    assert result['known_candidate_tokens_lower_bound'] == 100
    assert result['execution_usage']['unknown_attempts'] == []


def test_crash_between_receipt_file_and_journal_stays_unknown_not_zero(lab, monkeypatch):
    class SimulatedProcessLoss(BaseException):
        pass
    checkpoint = C._checkpoint
    def crash_on_receipt(home, project, run_id, attempts):
        if 'native_sha256' in attempts[-1]:
            raise SimulatedProcessLoss()
        return checkpoint(home, project, run_id, attempts)
    monkeypatch.setattr(C, '_checkpoint', crash_on_receipt)
    monkeypatch.setattr(C, '_invoke', examples.fake_invoke)
    with pytest.raises(SimulatedProcessLoss):
        run(lab)
    with P._db(lab[0]) as con:
        prior = con.execute('SELECT run_id,freeze_path FROM procedure_execution_runs').fetchone()
    receipt = Path(prior['freeze_path']).parent / 'native-1.json'
    assert receipt.is_file()  # Present bytes alone do not authenticate a received response.
    monkeypatch.setattr(C, '_checkpoint', checkpoint)
    _, result = run(lab)
    assert result['execution_usage']['unknown_attempts'] == [{'run_id': prior['run_id'], 'call': 1}]
    assert result['known_candidate_tokens_lower_bound'] == 40
    assert result['usage_complete'] is False and result['promotion'] == 'NOT_GRANTED'


def test_changed_prior_receipt_refuses_before_another_native_call(lab, monkeypatch):
    monkeypatch.setattr(C, '_invoke', examples.fake_invoke)
    frozen, _ = run(lab)
    native = Path(frozen['freeze_path']).parent / 'native-1.json'
    native.write_text('{}')
    monkeypatch.setattr(C, '_invoke', lambda *a, **k: pytest.fail('changed accounting cannot launch'))
    with pytest.raises(ValueError, match='receipt|usage|changed'):
        run(lab)


def test_legacy_runs_keep_verified_costs_and_unobserved_calls_unknown(lab, monkeypatch):
    monkeypatch.setattr(C, '_invoke', examples.fake_invoke)
    frozen, result = run(lab)
    result.pop('execution_attempts', None)
    path = Path(frozen['freeze_path']).parent / 'result.json'
    path.write_bytes(P.encoded(result))
    with P._db(lab[0]) as con:
        con.execute('UPDATE procedure_execution_runs SET result=? WHERE run_id=?',
                    (P.encoded(result).decode(), frozen['run_id']))
    _, current = run(lab)
    assert current['execution_usage']['known_prior_tokens'] == 60
    assert not current['execution_usage']['unknown_attempts']


def test_candidate_rename_cannot_reset_canonical_development_debt(lab, monkeypatch):
    monkeypatch.setattr(C, '_invoke', examples.fake_invoke)
    run(lab)
    home, project, oracle, proposal, suite = lab
    changed = P.correct(home, str(project), proposal['id'],
                        {**proposal['candidate'], 'title': 'Renamed candidate'})
    _, result = run((home, project, oracle, changed, suite))
    assert result['execution_usage']['known_prior_tokens'] == 60
    assert result['known_candidate_tokens_lower_bound'] == 100


def test_prepared_but_unconsumed_run_does_not_invent_usage(lab, monkeypatch):
    home, project, oracle, proposal, suite = lab
    unused = C.prepare(home, str(project), proposal['id'], oracle, suite)
    monkeypatch.setattr(C, '_invoke', examples.fake_invoke)
    frozen, result = run(lab)
    assert unused['run_id'] not in result['execution_usage']['attempt_ids']
    assert result['execution_usage']['attempt_ids'] == [frozen['run_id']]
    assert result['known_candidate_tokens_lower_bound'] == 40


def test_native_invocation_sees_its_consumed_attempt_already_committed(lab, monkeypatch):
    import json
    def invoke(*args, **kwargs):
        with P._db(lab[0]) as con:
            row = con.execute('SELECT state,result FROM procedure_execution_runs').fetchone()
        assert row['state'] == 'CONSUMED'
        attempts = json.loads(row['result'])['execution_attempts']
        assert attempts[-1]['consumed'] is True
        assert 'native_sha256' not in attempts[-1]
        return examples.fake_invoke(*args, **kwargs)
    monkeypatch.setattr(C, '_invoke', invoke)
    _, result = run(lab)
    assert result['status'] == 'GRADED_HELD'


def test_distinct_canonical_inputs_are_not_the_same_execution_series(lab, monkeypatch):
    monkeypatch.setattr(C, '_invoke', examples.fake_invoke)
    first, _ = run(lab)
    home, project, oracle, proposal, suite = lab
    for n in range(2):
        task = project / f'task-{n}.json'
        task.write_text(task.read_text().replace(f'case-{n}', f'new-{n}'))
        answer = oracle / f'answer-{n}.json'
        answer.write_text(answer.read_text().replace(f'case-{n}', f'new-{n}'))
    candidate = P.prepare(str(project), {**proposal['candidate'], 'episodes': [
        {k: e[k] for k in ('task_id', 'path', 'task_path')}
        for e in proposal['candidate']['episodes']]})
    changed = P.correct(home, str(project), proposal['id'], candidate)
    _, result = run((home, project, oracle, changed, suite))
    assert first['run_id'] not in result['execution_usage']['attempt_ids']
    assert result['execution_usage']['known_prior_tokens'] == 0
    assert result['known_candidate_tokens_lower_bound'] == 40


def test_legacy_unobserved_attempt_stays_unknown(lab, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError('old native failure had no complete receipt')
    monkeypatch.setattr(C, '_invoke', fail)
    frozen, failed = run(lab)
    failed.pop('execution_attempts')
    (Path(frozen['freeze_path']).parent / 'result.json').write_bytes(P.encoded(failed))
    with P._db(lab[0]) as con:
        con.execute('UPDATE procedure_execution_runs SET result=? WHERE run_id=?',
                    (P.encoded(failed).decode(), frozen['run_id']))
    monkeypatch.setattr(C, '_invoke', examples.fake_invoke)
    _, result = run(lab)
    assert result['execution_usage']['unknown_attempts'] == [{'run_id': frozen['run_id'], 'call': 1}]
    assert result['known_candidate_tokens_lower_bound'] == 40
