"""Long native answers must remain recoverable beyond their display preview."""
import hashlib
import json
import sys

import pytest

from agent_harness import launch
from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize


@pytest.fixture
def project(tmp_path, monkeypatch):
    identity = initialize(tmp_path)
    (tmp_path / 'policy.md').write_text('Use only the supplied fixture evidence.\n')
    source = SourceVault(tmp_path, identity).capture('policy.md')
    item = {'id': 'policy', 'project_id': identity, 'layer': 'project_facts', 'kind': 'fact',
            'scope': 'task', 'text': 'Use only the supplied fixture evidence.',
            'provenance': [{'source': source, 'start_line': 1, 'end_line': 1}],
            'confidence': 'verified', 'sensitivity': 'internal', 'access_boundary': 'local_user',
            'owner': 'fixture', 'freshness': 'current'}
    receipt = ProjectMemory(tmp_path, identity).append(item, expected=None)
    (tmp_path / 'request.json').write_text(json.dumps({
        'schema': launch.SCHEMA, 'project_id': identity, 'task': 'Answer every supplied case.',
        'references': [receipt], 'scope': {'allowed_sensitivities': ['internal'],
        'allowed_scopes': ['task'], 'layers': ['project_facts']}, 'max_context_bytes': 4096}))
    monkeypatch.setenv('PATH', str(tmp_path))
    return tmp_path


def native(project, answer):
    events = [
        {'type': 'thread.started', 'thread_id': '01a16828-6ebc-7e82-9fd6-99f867c645fc'},
        {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': answer}},
        {'type': 'turn.completed', 'usage': {'input_tokens': 100, 'cached_input_tokens': 0, 'output_tokens': 50}},
    ]
    path = project / 'codex'
    path.write_text('#!' + sys.executable + '\nimport json,sys\nsys.stdin.read()\n'
                    + 'for event in ' + repr(events) + ': print(json.dumps(event),flush=True)\n')
    path.chmod(0o700)


def test_long_unicode_answer_retains_last_case_and_byte_bound_reference(project):
    answer = 'source evidence\n' * 600 + '最後一題: missing-condition-preserved\n'
    native(project, answer)
    result = launch.execute(project, 'request.json', 'native.json', timeout=5)
    assert result['native_completion'] == 'COMPLETED_UNGRADED'
    assert result['answer_truncated'] is True
    assert result['answer'] == answer[:8192]
    reference = result['answer_ref']
    full = (project / reference['path']).read_bytes()
    assert full == answer.encode('utf-8')
    assert reference['sha256'] == hashlib.sha256(full).hexdigest()
    assert reference['bytes'] == len(full)
    assert (project / reference['path']).stat().st_mode & 0o777 == 0o600
    assert launch.read_answer(project, result) == answer
    assert json.loads((project / 'native.json').read_text())['answer_ref'] == reference


@pytest.mark.parametrize('size', [1, 8191, 8192])
def test_short_answer_stays_inline_without_an_unneeded_file(project, size):
    answer = 'x' * size
    native(project, answer)
    result = launch.execute(project, 'request.json', 'native.json', timeout=5)
    assert result['answer'] == answer
    assert result['answer_truncated'] is False and result['answer_ref'] is None
    assert not (project / 'native.json.answer.txt').exists()
    assert launch.read_answer(project, result) == answer


def test_preexisting_answer_target_is_rejected_before_spending_a_call(project, monkeypatch):
    target = project / 'native.json.answer.txt'
    target.write_text('existing owner output')
    def forbidden(*args, **kwargs):
        raise AssertionError('must not launch with an existing output target')
    monkeypatch.setattr(launch.subprocess, 'Popen', forbidden)
    with pytest.raises(ValueError, match='answer.*exists'):
        launch.execute(project, 'request.json', 'native.json', timeout=5)
    assert target.read_text() == 'existing owner output'
    assert not (project / 'native.json').exists()


@pytest.mark.parametrize('fault', ['changed-body', 'missing', 'changed-preview', 'foreign-ref', 'symlink'])
def test_full_answer_reader_rejects_unbound_or_unavailable_data(project, fault):
    answer = 'source evidence\n' * 600 + 'tail-criterion\n'
    native(project, answer)
    result = launch.execute(project, 'request.json', 'native.json', timeout=5)
    path = project / result['answer_ref']['path']
    if fault == 'changed-body':
        path.write_text(answer.replace('tail-criterion', 'fake-criterion'))
    elif fault == 'missing':
        path.unlink()
    elif fault == 'changed-preview':
        result['answer'] = 'forged prefix'
    elif fault == 'foreign-ref':
        result['answer_ref']['path'] = '../foreign-answer.txt'
    else:
        copy = project / 'copied-answer.txt'
        copy.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(copy)
    with pytest.raises(ValueError):
        launch.read_answer(project, result)


def test_late_storage_conflict_is_visible_and_does_not_overwrite(project, monkeypatch):
    answer = 'source evidence\n' * 600
    native(project, answer)
    original = launch.subprocess.Popen
    def late_conflict(*args, **kwargs):
        (project / 'native.json.answer.txt').write_text('concurrent output')
        return original(*args, **kwargs)
    monkeypatch.setattr(launch.subprocess, 'Popen', late_conflict)
    result = launch.execute(project, 'request.json', 'native.json', timeout=5)
    assert result['answer_truncated'] and result['answer_ref'] is None
    assert result['answer_retention'] == 'FAILED'
    assert (project / 'native.json.answer.txt').read_text() == 'concurrent output'
    assert (project / 'native.json').exists()
    with pytest.raises(ValueError, match='retained'):
        launch.read_answer(project, result)


def test_over_budget_answer_is_explicit_not_claimed_fully_retained(project):
    from agent_harness.qualification import FILE_LIMIT
    native(project, 'x' * (FILE_LIMIT + 1))
    result = launch.execute(project, 'request.json', 'native.json', timeout=5)
    assert result['native_completion'] == 'COMPLETED_UNGRADED'
    assert result['answer_truncated'] and result['answer_retention'] == 'FAILED'
    assert result['answer_ref'] is None
    assert not (project / 'native.json.answer.txt').exists()
    with pytest.raises(ValueError, match='retained'):
        launch.read_answer(project, result)


def test_legacy_preview_without_completeness_metadata_is_not_assumed_full(project):
    with pytest.raises(ValueError, match='completeness'):
        launch.read_answer(project, {'native_completion': 'COMPLETED_UNGRADED', 'answer': 'old preview'})
