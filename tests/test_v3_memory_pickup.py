"""Instrument controls for the authored native pickup experiment, without inference."""
import json

import pytest

from eval import v3_memory_pickup as experiment


def test_freeze_uses_actual_current_and_archived_store_records(tmp_path):
    out = tmp_path / 'study'
    result = experiment.prepare(out)
    assert result['status'] == 'FROZEN_NOT_RUN'
    oracle = out / 'project/qualification-oracle'
    frozen = experiment.C._json(oracle / 'freeze.json')
    assert frozen['preparation_model_calls'] == 0
    assert frozen['max_calls'] == 8 and frozen['retries'] == 0
    assert not (out / 'freeze.json').exists()
    for case in frozen['cases']:
        baseline = experiment.C._json(out / case['tasks']['history']['path'])
        candidate = experiment.C._json(out / case['tasks']['current']['path'])
        old, current = json.loads(baseline['evidence']), json.loads(candidate['evidence'])
        assert old['current'] == current['current']
        assert len(old['historical_revisions']) == 6
        assert old['historical_revisions'][-1] == current['current']
        assert case['tasks']['history']['evidence_bytes'] > case['tasks']['current']['evidence_bytes']
        assert len(baseline['evidence'].encode()) < 8192


@pytest.mark.parametrize('fault', ['runtime', 'evaluator', 'task', 'consumed'])
def test_bad_freeze_or_consumption_stops_before_a_model_call(tmp_path, monkeypatch, fault):
    out = tmp_path / 'study'
    experiment.prepare(out)
    path = out / 'project/qualification-oracle/freeze.json'
    frozen = experiment.C._json(path)
    if fault == 'runtime':
        frozen['runtime'] = {}
    elif fault == 'evaluator':
        frozen['evaluator_sha256'] = '0' * 64
    elif fault == 'task':
        (out / frozen['cases'][0]['tasks']['history']['path']).write_text('{}')
    else:
        experiment.save(out / 'journal.json', [])
    experiment.save(path, frozen)
    monkeypatch.setattr(experiment.C, '_call', lambda *a: pytest.fail('must not invoke native model'))
    with pytest.raises((ValueError, AssertionError)):
        experiment.run(out)


def test_missing_trials_cannot_become_a_successful_report(tmp_path):
    out = tmp_path / 'study'
    experiment.prepare(out)
    experiment.save(out / 'journal.json', [])
    with pytest.raises(AssertionError):
        experiment.verify(out)
