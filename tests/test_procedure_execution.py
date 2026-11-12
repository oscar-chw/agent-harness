"""Node-42 accepting-execution boundary: executed project-local learning stays held.

These tests run the real controller lifecycle (prepare -> execute) behind the
shared fake native seam and assert the boundary the node demands: a graded
trial is never an accepting learning event, caller-supplied scores are not
accepted anywhere in the execution result path, and consumed evidence persists.

GAP (intended, current safe behavior): trusted accepting execution/activation
is still unimplemented. procedures.change() refuses every non-rollback status
transition, so activation assertions below assert refusal, not a finished
promotion path. These tests add no verified flags, perform no direct database
writes (read-only SELECT inspections only) and promote nothing from results.
"""
import hashlib
import inspect
import json
from pathlib import Path

import pytest

from agent_harness import procedure_execution as C, procedures as P
from . import test_procedure_execution_controller as examples
from . import test_procedure_native_preparation as native_preparation

lab = examples.lab
fake_invoke = examples.fake_invoke


def freeze(lab):
    home, project, oracle, proposal, suite = lab
    return C.prepare(home, str(project), proposal['id'], oracle, suite)


def campaign_invoke(actor, request, oracle, **kwargs):
    # Same dispatch the owned-campaign suite uses: the native drafting call gets
    # the draft fixture, trial calls get the exact-answer fixture.
    if 'Draft a short reusable procedure' in request['task']:
        return native_preparation.generated(actor, request, oracle, **kwargs)
    return fake_invoke(actor, request, oracle, **kwargs)


def journal_row(home, run_id):
    # Read-only inspection of the attempt journal; tests never write to it.
    with P._db(home) as con:
        row = con.execute('SELECT state,result FROM procedure_execution_runs WHERE run_id=?',
                          (run_id,)).fetchone()
    return None if row is None else (row['state'], row['result'])


def test_freeze_alone_grants_no_authority_and_activates_nothing(lab, monkeypatch):
    home, project, oracle, proposal, suite = lab
    monkeypatch.setattr(C, '_invoke', lambda *a, **k: pytest.fail('freeze must not invoke a model'))
    frozen = freeze(lab)
    assert frozen['status'] == 'PREPARED' and frozen['promotion'] == 'NOT_GRANTED'
    assert not (Path(frozen['freeze_path']).parent / 'result.json').exists()
    assert P.inspect(home, str(project), proposal['id'])['status'] == 'proposed'
    assert P.list_active(home, str(project)) == []
    assert P.matches(home, str(project), 'status extraction') == []
    with pytest.raises(ValueError, match='independent grader'):
        P.change(home, str(project), proposal['id'])


def test_full_lifecycle_ends_graded_held_with_promotion_not_granted(lab, monkeypatch):
    home, project, oracle, proposal, suite = lab
    calls = []

    def invoke(*args, **kwargs):
        calls.append(1)
        return fake_invoke(*args, **kwargs)

    monkeypatch.setattr(C, '_invoke', invoke)
    frozen = freeze(lab)
    result = C.execute(home, str(project), frozen['run_id'])
    assert result['status'] == 'GRADED_HELD' and result['promotion'] == 'NOT_GRANTED'
    assert result['usage_complete'] is False and result['holds']
    assert result['known_preparation_tokens'] == 'UNKNOWN'
    assert len(calls) == result['observed_calls'] == 6
    assert result['known_candidate_tokens_lower_bound'] == 40
    assert result['known_baseline_tokens'] == 20
    assert len(result['observations']) == 6
    # Grades are controller-computed against frozen oracle answers; every
    # observation is exactly the controller schema, with no caller field.
    for o in result['observations']:
        assert set(o) == {'correct', 'tokens', 'answer_sha256', 'native_receipt_sha256',
                          'task_id', 'class', 'split', 'arm'}
        assert type(o['correct']) is bool and o['correct'] is True
    # The accepting-execution boundary is not crossed by a graded lifecycle.
    assert P.inspect(home, str(project), proposal['id'])['status'] == 'proposed'
    assert P.list_active(home, str(project)) == []
    assert P.matches(home, str(project), 'status extraction') == []
    with pytest.raises(ValueError, match='consumed|already'):
        C.execute(home, str(project), frozen['run_id'])


def test_held_result_cannot_activate_through_any_public_path(lab, monkeypatch, capsys):
    from agent_harness import cli
    home, project, oracle, proposal, suite = lab
    monkeypatch.setattr(C, '_invoke', fake_invoke)
    frozen = freeze(lab)
    result = C.execute(home, str(project), frozen['run_id'])
    assert result['status'] == 'GRADED_HELD'
    identity = proposal['id']
    # Direct status change with the controller result, with no evidence, or as
    # a rollback are all refused; GAP: accepting activation does not exist yet.
    with pytest.raises(ValueError, match='independent grader'):
        P.change(home, str(project), identity, result)
    with pytest.raises(ValueError, match='independent grader'):
        P.change(home, str(project), identity)
    with pytest.raises(ValueError, match='only an active'):
        P.change(home, str(project), identity, rollback=True)
    # An execution result is not a promotion comparison for evaluate() either.
    with pytest.raises(ValueError):
        P.evaluate(proposal, result)
    # The CLI apply path carries the same refusal, with and without --eval.
    monkeypatch.setenv('HARNESS_HOME', str(home))
    claim = Path(project) / 'claimed-execution-result.json'
    claim.write_text(json.dumps(result))
    assert cli.main(['improve', '--project', str(project), '--apply', identity,
                     '--eval', str(claim)]) == 1
    assert 'independent grader' in capsys.readouterr().out
    assert cli.main(['improve', '--project', str(project), '--apply', identity]) == 1
    assert 'independent grader' in capsys.readouterr().out
    # None of the attempts changed any lifecycle state.
    view = P.inspect(home, str(project), identity)
    assert view['status'] == 'proposed' and view['evidence_sha256'] is None
    assert P.list_active(home, str(project)) == []
    assert P.matches(home, str(project), 'status extraction') == []


@pytest.mark.parametrize('name', ['prepare', 'execute', '_invoke'])
def test_execution_api_accepts_no_caller_score_or_grader(name):
    # Structural guard: no score/grade/grader/runner parameter and no **kwargs
    # through which caller-controlled grading could enter the execution path.
    parameters = list(inspect.signature(getattr(C, name)).parameters.values())
    forbidden = {'score', 'scores', 'grade', 'grades', 'grader', 'runner',
                 'quality', 'verdict', 'passed', 'correct', 'result', 'evidence'}
    assert not forbidden & {p.name for p in parameters}
    assert all(p.kind is not inspect.Parameter.VAR_KEYWORD for p in parameters)


@pytest.mark.parametrize('claim', ['false-success', 'false-failure'])
def test_caller_scores_stuffed_into_native_receipt_never_grade(lab, monkeypatch, claim):
    home, project, oracle, proposal, suite = lab

    def invoke(*args, **kwargs):
        receipt = fake_invoke(*args, **kwargs)
        # Caller-controlled grading claims ride along on the receipt; the
        # controller must grade from the frozen oracle answer, not these.
        receipt.update({'score': 1.0 if claim == 'false-success' else 0.0,
                        'grade': 'PASS' if claim == 'false-success' else 'FAIL',
                        'correct': claim == 'false-success',
                        'quality': {'correctness': 1}, 'promotion': 'GRANTED',
                        'usage_complete': True})
        if claim == 'false-success':
            receipt['answer'] = '{"status":"caller-claims-success","source_ids":["task-evidence"]}'
            receipt['answer_sha256'] = hashlib.sha256(receipt['answer'].encode()).hexdigest()
        return receipt

    monkeypatch.setattr(C, '_invoke', invoke)
    frozen = freeze(lab)
    result = C.execute(home, str(project), frozen['run_id'])
    if claim == 'false-success':
        # The first (development) case fails the frozen grader despite claims.
        assert result['status'] == 'FAILED'
        assert 'frozen grader' in result['failures'][0]['error']
        assert all(o['correct'] is False for o in result['observations'])
    else:
        # Correct answers with caller-claimed failure still grade correct.
        assert result['status'] == 'GRADED_HELD'
        assert all(o['correct'] is True for o in result['observations'])
    # Caller claims never reach the result: no score fields, promotion and
    # usage completeness stay controller-owned.
    assert 'score' not in result and 'grade' not in result and 'quality' not in result
    assert result['promotion'] == 'NOT_GRANTED' and result['usage_complete'] is False
    for o in result['observations']:
        assert set(o) == {'correct', 'tokens', 'answer_sha256', 'native_receipt_sha256',
                          'task_id', 'class', 'split', 'arm'}
    assert P.inspect(home, str(project), proposal['id'])['status'] == 'proposed'
    with pytest.raises(ValueError, match='consumed|already'):
        C.execute(home, str(project), frozen['run_id'])


def test_failed_trial_retains_consumed_attempt_pinned_receipt_and_failure(lab, monkeypatch):
    home, project, oracle, proposal, suite = lab

    def invoke(*args, **kwargs):
        receipt = fake_invoke(*args, **kwargs)
        receipt['answer'] = '{"status":"wrong","source_ids":["task-evidence"]}'
        receipt['answer_sha256'] = hashlib.sha256(receipt['answer'].encode()).hexdigest()
        return receipt

    monkeypatch.setattr(C, '_invoke', invoke)
    frozen = freeze(lab)
    result = C.execute(home, str(project), frozen['run_id'])
    assert result['status'] == 'FAILED' and result['promotion'] == 'NOT_GRANTED'
    assert 'frozen grader' in result['failures'][0]['error']
    assert result['failures'][0]['usage'] == 'UNKNOWN_UNLESS_OBSERVED'
    folder = Path(frozen['freeze_path']).parent
    # The attempt file is committed consumed before invocation; the receipt
    # hash is pinned into the journaled attempt only after the reply lands.
    attempt = json.loads((folder / 'attempt-1.json').read_text())
    assert attempt['consumed'] is True and attempt['request_sha256']
    receipt_path = folder / 'native-1.json'
    journaled = result['execution_attempts'][0]
    assert journaled['native_sha256'] == hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    assert journal_row(home, frozen['run_id'])[0] == 'FAILED'
    recorded = journal_row(home, frozen['run_id'])[1]
    # A refused re-execution changes nothing in the journal or on disk.
    with pytest.raises(ValueError, match='consumed|already'):
        C.execute(home, str(project), frozen['run_id'])
    assert journal_row(home, frozen['run_id']) == ('FAILED', recorded)
    assert (folder / 'result.json').is_file()
    assert P.inspect(home, str(project), proposal['id'])['status'] == 'proposed'
    assert P.list_active(home, str(project)) == []


def test_graded_trial_pins_its_evidence_and_refuses_reexecution(lab, monkeypatch):
    home, project, oracle, proposal, suite = lab
    monkeypatch.setattr(C, '_invoke', fake_invoke)
    frozen = freeze(lab)
    result = C.execute(home, str(project), frozen['run_id'])
    assert result['status'] == 'GRADED_HELD'
    folder = Path(frozen['freeze_path']).parent
    assert len(list(folder.glob('attempt-*.json'))) == 6
    assert len(list(folder.glob('native-*.json'))) == 6
    assert len(list(folder.glob('observed-*.json'))) == 6
    for attempt in result['execution_attempts']:
        assert attempt['consumed'] is True and attempt['request_sha256'] and attempt['native_sha256']
    result_bytes = (folder / 'result.json').read_bytes()
    state, recorded = journal_row(home, frozen['run_id'])
    assert state == 'GRADED_HELD' and recorded == result_bytes.decode()
    with pytest.raises(ValueError, match='consumed|already'):
        C.execute(home, str(project), frozen['run_id'])
    assert (folder / 'result.json').read_bytes() == result_bytes
    assert journal_row(home, frozen['run_id']) == (state, recorded)
    # Finished actors stay retained under the denied oracle; none linger.
    assert len(list(folder.glob('trial-' + frozen['run_id'] + '-*'))) == 6
    assert not list(Path(project).glob('trial-*'))
    assert P.list_active(home, str(project)) == []


def test_foreign_request_identity_fails_closed_and_stays_held(lab, monkeypatch):
    home, project, oracle, proposal, suite = lab

    def invoke(*args, **kwargs):
        receipt = fake_invoke(*args, **kwargs)
        receipt['request_sha256'] = 'ff' * 32
        return receipt

    monkeypatch.setattr(C, '_invoke', invoke)
    frozen = freeze(lab)
    result = C.execute(home, str(project), frozen['run_id'])
    assert result['status'] == 'FAILED' and result['promotion'] == 'NOT_GRANTED'
    assert result['observations'] == []
    assert 'request identity' in result['failures'][0]['error']
    attempt = result['execution_attempts'][0]
    assert attempt['consumed'] is True and attempt['native_sha256']
    # The foreign receipt is retained as evidence but trusted as nothing.
    assert (Path(frozen['freeze_path']).parent / 'native-1.json').is_file()
    assert P.inspect(home, str(project), proposal['id'])['status'] == 'proposed'
    assert P.list_active(home, str(project)) == []
    with pytest.raises(ValueError, match='consumed|already'):
        C.execute(home, str(project), frozen['run_id'])


def test_correction_after_held_trial_withdraws_and_replacement_cannot_activate(lab, monkeypatch):
    home, project, oracle, proposal, suite = lab
    monkeypatch.setattr(C, '_invoke', fake_invoke)
    frozen = freeze(lab)
    result = C.execute(home, str(project), frozen['run_id'])
    assert result['status'] == 'GRADED_HELD'
    # Rollback of stored advice is the correction path: withdraw and redraft.
    corrected = P.correct(home, str(project), proposal['id'],
                          {**proposal['candidate'], 'title': 'Corrected status reading'})
    assert corrected['status'] == 'proposed' and corrected['supersedes'] == proposal['id']
    retired = P.inspect(home, str(project), proposal['id'])
    assert retired['status'] == 'rolled_back' and retired['superseded_by'] == corrected['id']
    # The held trial result belongs to the withdrawn candidate; it activates
    # neither the old row nor the replacement. GAP: accepting activation does
    # not exist, so the safe behavior is unconditional refusal here.
    with pytest.raises(ValueError, match='already'):
        P.change(home, str(project), proposal['id'], result)
    with pytest.raises(ValueError, match='independent grader'):
        P.change(home, str(project), corrected['id'], result)
    with pytest.raises(ValueError, match='only an active'):
        P.change(home, str(project), corrected['id'], rollback=True)
    assert P.inspect(home, str(project), corrected['id'])['status'] == 'proposed'
    assert P.list_active(home, str(project)) == []
    assert P.withdrawn(home, str(project), {proposal['id'], corrected['id']}) == [proposal['id']]


def test_owned_campaign_finishes_held_and_cannot_be_accepted(lab, monkeypatch):
    from agent_harness import procedure_campaign
    home, project, oracle, proposal, suite = lab
    monkeypatch.setattr(C, '_invoke', campaign_invoke)
    frozen = procedure_campaign.prepare(home, str(project), oracle, suite)
    result = procedure_campaign.run(home, str(project), frozen['campaign_id'])
    assert result['status'] == 'GRADED_HELD' and result['promotion'] == 'NOT_GRANTED'
    assert result['usage_complete'] is False and result['holds']
    # Independently executed roles keep their own observed usage; nothing is
    # caller-scored and the drafted method stays a proposed, inactive candidate.
    assert result['observed_role_tokens'] == {'development': 20, 'preparation': 10,
                                              'trial_base': 20, 'trial_candidate': 40}
    assert len(result['observations']) == 6 and all(o['correct'] for o in result['observations'])
    generated = P.inspect(home, str(project), result['procedure_id'])
    assert generated['status'] == 'proposed' and generated['evidence_sha256'] is None
    assert P.list_active(home, str(project)) == []
    with pytest.raises(ValueError, match='independent grader'):
        P.change(home, str(project), result['procedure_id'], result)
    with pytest.raises(ValueError, match='only an active'):
        P.change(home, str(project), result['procedure_id'], rollback=True)
    assert P.inspect(home, str(project), result['procedure_id'])['status'] == 'proposed'
    with pytest.raises(ValueError, match='consumed|terminal'):
        procedure_campaign.run(home, str(project), frozen['campaign_id'])
