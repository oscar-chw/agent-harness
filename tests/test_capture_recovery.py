"""Abrupt process loss must not turn one observation into a repeated lesson."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_harness import capture, storage
from tests.test_capture_concurrency import candidate, rows, turn


def interrupt(home, transcript, stage):
    code = '''
import json, os, sys
from pathlib import Path
from agent_harness import capture
home, transcript, stage = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
replace_path, replace_os = Path.replace, os.replace
write_text = Path.write_text
def selected(path):
    path = Path(path)
    return ('data' if path.name == capture.STORE else
            'marker' if path.parent.name == 'state' and path.name.startswith('capture-') else '')
def before(path):
    if stage == selected(path) + '-before': os._exit(91)
def after(path):
    if stage == selected(path) + '-after': os._exit(91)
def path_replace(path, target):
    before(target)
    result = replace_path(path, target)
    after(target)
    return result
def os_replace(source, target, *args, **kwargs):
    before(target)
    result = replace_os(source, target, *args, **kwargs)
    after(target)
    return result
def marker_write(path, text, *args, **kwargs):
    before(path)
    result = write_text(path, text, *args, **kwargs)
    after(path)
    return result
Path.replace, os.replace, Path.write_text = path_replace, os_replace, marker_write
capture.capture_turn(home, str(transcript), 'interrupted')
'''
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))
    result = subprocess.run([sys.executable, '-c', code, str(home), str(transcript), stage],
                            env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 91, result.stdout + result.stderr


@pytest.mark.parametrize('stage', ['data-before', 'data-after', 'marker-before', 'marker-after'])
def test_retry_after_process_exit_counts_once(tmp_path, stage):
    home = tmp_path / 'home'
    transcript = tmp_path / 'events.jsonl'
    transcript.write_text(''.join(json.dumps(event) + '\n' for event in turn()))
    interrupt(home, transcript, stage)
    capture.capture_turn(home, str(transcript), 'interrupted')
    assert [row['count'] for row in rows(home)] == [1]
    capture.capture_turn(home, str(transcript), 'interrupted')
    assert [row['count'] for row in rows(home)] == [1]


@pytest.mark.parametrize('entrypoint', ['record', 'prune', 'other-capture'])
def test_other_writers_recover_an_interrupted_capture_first(tmp_path, entrypoint):
    home = tmp_path / 'home'
    transcript = tmp_path / 'events.jsonl'
    transcript.write_text(''.join(json.dumps(event) + '\n' for event in turn()))
    interrupt(home, transcript, 'data-after')
    if entrypoint == 'record':
        capture.record(home, [candidate('independent')])
    elif entrypoint == 'prune':
        storage.prune(home)
    else:
        events = turn()
        events[0]['uuid'] = 'another-turn'
        capture.capture_turn(home, 'other.jsonl', 'another-session', events=events, started=True)
    capture.capture_turn(home, str(transcript), 'interrupted')
    saved = {row['key']: row for row in rows(home)}
    counts = [row['count'] for key, row in saved.items() if key != 'independent']
    assert counts == [2 if entrypoint == 'other-capture' else 1]
    if entrypoint == 'record':
        assert saved['independent']['count'] == 1


def pending_capture(tmp_path):
    home = tmp_path / 'home'
    transcript = tmp_path / 'events.jsonl'
    transcript.write_text(''.join(json.dumps(event) + '\n' for event in turn()))
    interrupt(home, transcript, 'data-after')
    pending = home / capture.PENDING
    assert pending.is_file()
    return home, transcript, pending


def test_recovery_refuses_unrelated_candidate_changes(tmp_path):
    home, transcript, pending = pending_capture(tmp_path)
    original = (home / capture.STORE).read_bytes()
    (home / capture.STORE).write_bytes(original + b'\n')
    edited = (home / capture.STORE).read_bytes()
    with pytest.raises(ValueError, match='changed during recovery'):
        capture.capture_turn(home, str(transcript), 'interrupted')
    assert (home / capture.STORE).read_bytes() == edited
    assert pending.is_file()


def test_mutated_recovery_record_is_rejected_before_writes(tmp_path):
    home, transcript, pending = pending_capture(tmp_path)
    original = (home / capture.STORE).read_bytes()
    value = json.loads(pending.read_text())
    value['state']['keys'] = []
    pending.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='recovery record changed'):
        capture.capture_turn(home, str(transcript), 'interrupted')
    assert (home / capture.STORE).read_bytes() == original
    assert pending.is_file()


def test_recovery_cannot_redirect_its_marker_outside_state(tmp_path):
    import hashlib
    home, transcript, pending = pending_capture(tmp_path)
    original = (home / capture.STORE).read_bytes()
    victim = tmp_path / 'keep.txt'
    victim.write_text('User data')
    value = json.loads(pending.read_text())
    value['marker'] = '../../keep.txt'
    value.pop('sha256')
    value['sha256'] = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    pending.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='invalid capture recovery'):
        capture.capture_turn(home, str(transcript), 'interrupted')
    assert victim.read_text() == 'User data'
    assert (home / capture.STORE).read_bytes() == original


def test_recovery_clears_its_intent_after_a_real_new_turn(tmp_path):
    home, transcript, pending = pending_capture(tmp_path)
    capture.capture_turn(home, str(transcript), 'interrupted')
    assert not pending.exists()
    events = turn()
    events[0]['uuid'] = 'new-turn'
    capture.capture_turn(home, str(transcript), 'interrupted', events=events, started=True)
    assert [row['count'] for row in rows(home)] == [2]
    assert not pending.exists()
    assert not list(home.glob('*.capture-tmp'))
