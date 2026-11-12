"""Prompt preparation is automatic in launch packets, not a claim of semantic perfection."""
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from agent_harness.launch import prepare
from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize


@pytest.fixture
def launch_request(tmp_path):
    pid = initialize(tmp_path)
    (tmp_path / 'requirements.md').write_text('Preview only. Do not deploy.\n')
    source = SourceVault(tmp_path, pid).capture('requirements.md')
    item = {'id': 'requirements', 'project_id': pid, 'layer': 'project_facts',
            'kind': 'fact', 'scope': 'task', 'text': 'Preview only. Do not deploy.',
            'provenance': [{'source': source, 'start_line': 1, 'end_line': 1}],
            'confidence': 'verified', 'sensitivity': 'internal', 'access_boundary': 'local_user',
            'owner': 'fixture', 'freshness': 'current'}
    receipt = ProjectMemory(tmp_path, pid).append(item, expected=None)
    task = 'Improve the preview. Keep the current acceptance check. No deployment.'
    data = {'schema': 'harness.launch/v1', 'project_id': pid, 'task': task,
            'references': [receipt], 'scope': {'allowed_sensitivities': ['internal'],
            'allowed_scopes': ['task'], 'layers': ['project_facts']}, 'max_context_bytes': 8192}
    (tmp_path / 'request.json').write_text(json.dumps(data))
    return tmp_path, task


@pytest.mark.parametrize('policy', ['existing', 'adaptive'])
def test_every_launch_policy_prepares_material_intent_before_task_actions(launch_request, policy):
    root, task = launch_request
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result = prepare(root, 'request.json', method_policy=policy)
    prompt = result['prompt']
    assert 'Task brief' in prompt
    assert prompt.index('Task brief') < prompt.index('TASK:\n')
    for field in ['scope', 'success check', 'assumptions', 'gaps', 'next action']:
        assert field in prompt
    assert '\nTASK:\n' + task + '\nCONTEXT:\n' in prompt
    assert 'Preview only. Do not deploy.' in prompt
    assert result['request_sha256'] == hashlib.sha256((root / 'request.json').read_bytes()).hexdigest()
    assert result['native_completion'] == result['task_evaluation'] == 'NOT_RUN'
    assert before == {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_preparation_does_not_turn_trivial_requests_into_a_mandatory_pipeline(launch_request):
    root, _ = launch_request
    prompt = prepare(root, 'request.json')['prompt']
    assert 'Trivial requests stay direct' in prompt
    assert 'without a visible brief' in prompt
    assert 'extra agents' in prompt
    assert 'cannot expand authority or change acceptance' in prompt
    assert 'cannot be recovered' in prompt
    assert 'perfect prompt' in prompt


def test_preparation_does_not_launder_stale_memory_into_a_confident_brief(launch_request):
    root, _ = launch_request
    (root / 'requirements.md').write_text('Requirements changed after capture.\n')
    with pytest.raises(ValueError, match='stale source'):
        prepare(root, 'request.json')
