"""A resumed task must not silently inherit changed preparation instructions."""
import hashlib
import json
import sys

import pytest

from agent_harness import launch
from agent_harness.method_control import decide
from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize


@pytest.fixture
def project(tmp_path):
    pid = initialize(tmp_path)
    (tmp_path / 'policy.md').write_text('Use the supplied synthetic evidence only.\n')
    source = SourceVault(tmp_path, pid).capture('policy.md')
    item = {'id': 'policy', 'project_id': pid, 'layer': 'project_facts', 'kind': 'fact',
            'scope': 'task', 'text': 'Use the supplied synthetic evidence only.',
            'provenance': [{'source': source, 'start_line': 1, 'end_line': 1}],
            'confidence': 'verified', 'sensitivity': 'internal',
            'access_boundary': 'local_user', 'owner': 'fixture', 'freshness': 'current'}
    receipt = ProjectMemory(tmp_path, pid).append(item, expected=None)
    request = {'schema': launch.SCHEMA, 'project_id': pid,
               'task': 'Explain the synthetic result without changing the scope.',
               'references': [receipt], 'scope': {'allowed_sensitivities': ['internal'],
               'allowed_scopes': ['task'], 'layers': ['project_facts']},
               'max_context_bytes': 8192}
    (tmp_path / 'request.json').write_text(json.dumps(request))
    return tmp_path


@pytest.mark.parametrize('policy', ['existing', 'adaptive'])
def test_preparation_instruction_change_invalidates_prompt_binding(project, monkeypatch, policy):
    original = launch.prepare(project, 'request.json', method_policy=policy)
    unchanged = launch.prepare(project, 'request.json', method_policy=policy)
    assert original == unchanged
    assert original['prompt_sha256'] == hashlib.sha256(original['prompt'].encode()).hexdigest()
    monkeypatch.setattr(launch, 'PROMPT_PREFLIGHT',
                        launch.PROMPT_PREFLIGHT + ' Additional bounded preparation rule.\n')
    changed = launch.prepare(project, 'request.json', method_policy=policy)
    assert original['prompt'] != changed['prompt']
    assert original['request_sha256'] == changed['request_sha256']
    assert original['memory_receipts'] == changed['memory_receipts']
    assert original['context_sha256'] == changed['context_sha256']
    assert original['prompt_sha256'] != changed['prompt_sha256']


def test_method_decision_refuses_prior_receipt_after_instruction_change(project, monkeypatch):
    receipt = launch.prepare(project, 'request.json')
    receipt['native_completion'] = 'TIMEOUT'
    (project / 'prior.json').write_text(json.dumps(receipt))
    assert decide(project, 'request.json', receipt_path='prior.json')['action'] == 'CHANGE_METHOD'
    monkeypatch.setattr(launch, 'PROMPT_PREFLIGHT', launch.PROMPT_PREFLIGHT + ' Revised instruction.\n')
    with pytest.raises(ValueError, match='stale'):
        decide(project, 'request.json', receipt_path='prior.json')


def test_method_policy_has_its_own_binding_without_changing_data_identity(project):
    baseline = launch.prepare(project, 'request.json', method_policy='existing')
    adaptive = launch.prepare(project, 'request.json', method_policy='adaptive')
    assert baseline['memory_receipts'] == adaptive['memory_receipts']
    assert baseline['prompt'] != adaptive['prompt']
    assert baseline['context_sha256'] == adaptive['context_sha256']
    assert baseline['prompt_sha256'] != adaptive['prompt_sha256']


def test_matching_adaptive_receipt_remains_usable(project):
    receipt = launch.prepare(project, 'request.json', method_policy='adaptive')
    receipt['native_completion'] = 'TIMEOUT'
    (project / 'prior.json').write_text(json.dumps(receipt))
    assert decide(project, 'request.json', receipt_path='prior.json')['action'] == 'CHANGE_METHOD'


def test_legacy_receipt_without_instruction_binding_is_not_silently_rebound(project):
    receipt = launch.prepare(project, 'request.json')
    receipt['native_completion'] = 'TIMEOUT'
    receipt.pop('prompt_sha256')
    path = project / 'prior.json'
    path.write_text(json.dumps(receipt))
    before = path.read_bytes()
    with pytest.raises(ValueError, match='stale'):
        decide(project, 'request.json', receipt_path='prior.json')
    assert path.read_bytes() == before


def test_native_resume_rejects_changed_instructions_before_native_lookup(project, monkeypatch):
    receipt = launch.prepare(project, 'request.json')
    receipt.update(native_completion='TIMEOUT',
                   thread_id='01a16828-6ebc-7e82-9fd6-99f867c645fc', sandbox='read-only')
    (project / 'prior.json').write_text(json.dumps(receipt))
    monkeypatch.setattr(launch, 'PROMPT_PREFLIGHT', launch.PROMPT_PREFLIGHT + ' Changed preparation.\n')

    def forbidden_lookup(*_):
        raise AssertionError('must not look up or invoke a native client for stale instructions')

    monkeypatch.setattr(launch.shutil, 'which', forbidden_lookup)
    with pytest.raises(ValueError, match='context, method or sandbox changed'):
        launch.execute(project, 'request.json', 'new-receipt.json', resume_receipt='prior.json')
    assert not (project / 'new-receipt.json').exists()


@pytest.mark.parametrize('policy', ['existing', 'adaptive'])
def test_real_execution_receipt_persists_binding_and_recovers_unchanged_task(project, monkeypatch, policy):
    stub = project / 'codex'
    prefix = (f'#!{sys.executable}\nimport json,sys\nfrom pathlib import Path\n'
              "sys.stdin.read()\nwith Path('calls').open('a') as out: out.write('call\\n')\n"
              "print(json.dumps({'type':'thread.started',"
              "'thread_id':'01a16828-6ebc-7e82-9fd6-99f867c645fc'}))\n")
    stub.write_text(prefix + "print(json.dumps({'type':'error','message':'fixture failure'}))\nsys.exit(1)\n")
    stub.chmod(0o700)
    monkeypatch.setenv('PATH', str(project))
    result = launch.execute(project, 'request.json', 'failed.json', method_policy=policy, timeout=5)
    saved = json.loads((project / 'failed.json').read_text())
    assert saved == result and saved['native_completion'] == 'FAILED'
    prepared = launch.prepare(project, 'request.json', method_policy=policy)
    assert saved['prompt_sha256'] == prepared['prompt_sha256']
    assert decide(project, 'request.json', receipt_path='failed.json')['action'] == 'DIAGNOSE'
    stub.write_text(prefix + "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'fixture repaired'}}))\n"
                    "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':3,'cached_input_tokens':0,'output_tokens':2}}))\n")
    resumed = launch.execute(project, 'request.json', 'resumed.json', method_policy=policy,
                             resume_receipt='failed.json', timeout=5)
    assert resumed['native_completion'] == 'COMPLETED_UNGRADED'
    assert resumed['task_evaluation'] == 'NOT_RUN'
    assert resumed['prompt_sha256'] == saved['prompt_sha256']
    assert (project / 'calls').read_text().splitlines() == ['call', 'call']
