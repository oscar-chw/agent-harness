"""Native Codex prompt observations are candidates with bounded scope and retries."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

from agent_harness import cli
from agent_harness.mcp.memory import Memory


@pytest.fixture
def lab(tmp_path, monkeypatch):
    project = tmp_path / 'project'
    project.mkdir()
    (project / '.git').mkdir()
    home = tmp_path / 'home'
    monkeypatch.setenv('HARNESS_HOME', str(home))
    monkeypatch.delenv('HARNESS_PROJECT', raising=False)
    monkeypatch.chdir(project)
    return home, project


def event(lab, turn='one-turn', prompt='No, keep the decimal contract.'):
    return {'hook_event_name': 'UserPromptSubmit', 'session_id': 'native-session',
            'turn_id': turn, 'cwd': str(lab[1]), 'prompt': prompt}


def deliver(payload):
    output, errors = io.StringIO(), io.StringIO()
    with patch('sys.stdout', output), patch('sys.stderr', errors):
        code = cli.prompt_hook(io.StringIO(json.dumps(payload)))
    assert code == 0
    return output.getvalue(), errors.getvalue()


def saved(lab):
    path = lab[0] / 'candidates.jsonl'
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_native_prompt_entrypoint_captures_one_scoped_correction(lab):
    output, errors = deliver(event(lab))
    values = saved(lab)
    assert len(values) == 1
    assert values[0]['source'] == 'user' and values[0]['count'] == 1
    assert values[0]['summary'] == 'No, keep the decimal contract.'
    assert values[0]['project_sha256']
    assert values[0]['source_sha256'] and values[0]['source_event_sha256']
    assert errors == '' and len(output.encode()) <= 1200
    assert not (lab[0] / 'lessons').exists()


def test_retry_is_idempotent_and_a_new_native_turn_is_a_real_recurrence(lab):
    deliver(event(lab))
    deliver(event(lab))
    assert [row['count'] for row in saved(lab)] == [1]
    deliver(event(lab, turn='second-turn'))
    assert [row['count'] for row in saved(lab)] == [2]


def test_prompt_capture_preserves_existing_recall(lab):
    memory = Memory(home=lab[0], project=str(lab[1]))
    memory.mem_add('Decimal contracts use quantized cents.', scope='project')
    memory.close()
    output, errors = deliver(event(lab))
    assert 'quantized cents' in output
    assert len(saved(lab)) == 1 and errors == ''
    assert len(output.encode()) <= 1200


def test_prompt_secret_is_redacted_before_candidate_persistence(lab):
    fake = 'ghp_' + 'Q' * 36
    deliver(event(lab, prompt='Please remember that fixture token is ' + fake))
    assert len(saved(lab)) == 1
    assert fake not in (lab[0] / 'candidates.jsonl').read_text()
    assert '[REDACTED]' in saved(lab)[0]['summary']


@pytest.mark.parametrize('missing', ['hook_event_name', 'session_id', 'turn_id', 'cwd'])
def test_unqualified_or_legacy_payload_does_not_create_a_native_observation(lab, missing):
    payload = event(lab)
    payload.pop(missing)
    deliver(payload)
    assert saved(lab) == []


def test_plain_requests_do_not_become_lessons(lab):
    deliver(event(lab, prompt='Show the decimal contract.'))
    assert saved(lab) == []


def test_explicit_remember_to_teaching_is_observed(lab):
    deliver(event(lab, prompt='Please remember to keep source evidence.'))
    assert len(saved(lab)) == 1
    assert saved(lab)[0]['count'] == 1
    assert saved(lab)[0]['source'] == 'user'


@pytest.mark.parametrize('first,second', [
    ('No, use port 9000.', 'No, use port 3000.'),
    ('No, use variable ACCOUNT.', 'No, use variable account.'),
    ('No, keep ' + 'x' * 320 + ' alpha.', 'No, keep ' + 'x' * 320 + ' beta.'),
])
def test_distinct_literal_preferences_do_not_collapse_into_recurrence(lab, first, second):
    deliver(event(lab, turn='one', prompt=first))
    deliver(event(lab, turn='two', prompt=second))
    values = saved(lab)
    assert len(values) == 2
    assert len({row['key'] for row in values}) == 2
    assert [row['count'] for row in values] == [1, 1]


def test_invalid_scope_and_nontext_identity_preserve_recall_boundary(lab):
    payload = event(lab)
    payload['cwd'] = 'relative-path'
    deliver(payload)
    assert saved(lab) == []
    payload = event(lab)
    payload['turn_id'] = 1
    deliver(payload)
    assert saved(lab) == []


def test_capture_failure_does_not_suppress_existing_recall(lab, monkeypatch):
    from agent_harness import capture
    memory = Memory(home=lab[0], project=str(lab[1]))
    memory.mem_add('Decimal contracts use quantized cents.', scope='project')
    memory.close()
    def unavailable(*args, **kwargs):
        raise OSError('fixture storage unavailable')
    monkeypatch.setattr(capture, 'capture_prompt', unavailable)
    output, errors = deliver(event(lab))
    assert 'quantized cents' in output
    assert 'prompt capture unavailable: OSError' in errors
    assert 'fixture storage unavailable' not in errors


def test_native_observations_stay_in_their_project_scope(lab):
    other = lab[1].parent / 'other-project'
    other.mkdir()
    (other / '.git').mkdir()
    deliver(event(lab))
    payload = event(lab, turn='another-turn')
    payload['cwd'] = str(other)
    deliver(payload)
    values = saved(lab)
    assert len(values) == 2
    assert len({row['project_sha256'] for row in values}) == 2
    assert [row['count'] for row in values] == [1, 1]


def test_two_native_sessions_can_observe_a_real_recurrence(lab):
    deliver(event(lab))
    payload = event(lab)
    payload['session_id'] = 'another-native-session'
    deliver(payload)
    assert [row['count'] for row in saved(lab)] == [2]


@pytest.mark.parametrize('malformed', ['null', '[]', '"candidate"'])
def test_nonobject_candidates_preserve_store_and_existing_recall(lab, malformed):
    memory = Memory(home=lab[0], project=str(lab[1]))
    memory.mem_add('Decimal contracts use quantized cents.', scope='project')
    memory.close()
    path = lab[0] / 'candidates.jsonl'
    path.write_text(malformed + '\n')
    output, errors = deliver(event(lab))
    assert 'quantized cents' in output
    assert 'prompt capture unavailable: ValueError' in errors
    assert path.read_text() == malformed + '\n'


def test_busy_capture_store_cannot_exceed_native_hook_timeout(lab):
    source = Path(__file__).resolve().parents[1] / 'src'
    env = dict(os.environ, PYTHONPATH=str(source))
    locker = subprocess.Popen([sys.executable, '-c',
        'from pathlib import Path; import sys; from agent_harness.mcp.memory import _store_lock\n'
        'with _store_lock(Path(sys.argv[1])):\n print("locked", flush=True)\n sys.stdin.read()\n',
        str(lab[0])], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env, text=True)
    try:
        assert locker.stdout.readline().strip() == 'locked'
        result = subprocess.run([sys.executable, '-m', 'agent_harness.cli', '_hook-prompt'],
                                input=json.dumps(event(lab)), capture_output=True, text=True,
                                env=env, timeout=4)
        assert result.returncode == 0
        assert 'prompt capture unavailable: TimeoutError' in result.stderr
        assert saved(lab) == []
    finally:
        locker.communicate('', timeout=5)
        assert locker.returncode == 0
    deliver(event(lab))
    assert [row['count'] for row in saved(lab)] == [1]
