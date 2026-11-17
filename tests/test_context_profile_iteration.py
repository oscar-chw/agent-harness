"""Task-scoped native context remains an unpromoted evaluation treatment."""
import importlib.util
import inspect
import json
from pathlib import Path

import pytest

from tests.test_continuation_iteration import observed


@pytest.fixture
def instrument():
    path = Path(__file__).resolve().parents[1] / 'eval/continuation_iteration.py'
    spec = importlib.util.spec_from_file_location('context_profile_instrument', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def freeze(instrument, tmp_path, profile='task_context'):
    out = tmp_path / 'study'
    ref = instrument.prepare(out, mode='simulation', profile=profile)
    return out, ref, json.loads((out / 'oracle/freeze.json').read_text())


def test_profile_prepare_is_publicly_selectable(instrument):
    assert 'profile' in inspect.signature(instrument.prepare).parameters


def test_task_context_has_fresh_cases_and_one_shared_prompt(instrument, tmp_path):
    _, _, frozen = freeze(instrument, tmp_path)
    assert frozen['profile'] == 'task_context'
    assert frozen['candidate'] == ''
    assert frozen['cases'] != instrument.CASES
    assert len(frozen['cases']) == 2
    assert all(case['done'] is False for case in frozen['cases'])
    assert 'UTC+8' in frozen['cases'][0]['next']
    assert 'stale' in frozen['cases'][1]['next']
    assert frozen['memory_policy'] == {'base': True, 'cand': False, 'generate': False}


def test_legacy_default_retains_its_original_treatment(instrument, tmp_path):
    _, _, frozen = freeze(instrument, tmp_path, profile='inherited')
    assert frozen['cases'] == instrument.CASES
    assert frozen['candidate'] == instrument.CANDIDATE
    assert frozen['memory_policy'] is None


@pytest.mark.parametrize('profile', ['unknown', '', None, 0])
def test_unknown_profile_fails_before_creating_output(instrument, tmp_path, profile):
    out = tmp_path / 'study'
    with pytest.raises(ValueError, match='profile'):
        instrument.prepare(out, mode='simulation', profile=profile)
    assert not out.exists()


def test_memory_treatment_preserves_store_tools_and_authority(instrument, tmp_path):
    base = instrument._settings(tmp_path, ['harness', 'other'], native_memory=True)
    cand = instrument._settings(tmp_path, ['harness', 'other'], native_memory=False)
    assert {key for key in base if base[key] != cand[key]} == {'memories.use_memories'}
    assert base['memories.generate_memories'] is cand['memories.generate_memories'] is False
    assert base['features.memories'] is cand['features.memories'] is True
    original = instrument._settings(tmp_path, ['harness', 'other'])
    assert all(base[key] == value and cand[key] == value for key, value in original.items())


@pytest.mark.parametrize('bad', ['false', 0, 1, {}])
def test_non_boolean_memory_control_is_refused(instrument, tmp_path, bad):
    with pytest.raises(ValueError, match='memory'):
        instrument._settings(tmp_path, ['harness'], native_memory=bad)


def admit(instrument, actor, expected, effective):
    return instrument._admit_context(actor, {'account': {'type': 'chatgpt'}},
        {'credits': {'hasCredits': False}, 'primary': {'usedPercent': 20}},
        {'data': [{'name': 'harness'}], 'nextCursor': None}, native_memory=expected,
        effective_config=effective)


@pytest.mark.parametrize('enabled', [True, False])
def test_effective_native_memory_readback_is_required(instrument, tmp_path, enabled):
    good = {'features': {'memories': True}, 'memories': {'use_memories': enabled, 'generate_memories': False}}
    result = admit(instrument, tmp_path, enabled, good)
    assert result['native_memory'] == {'use_memories': enabled, 'generate_memories': False}
    for bad in ({}, {'memories': {}}, {'memories': good['memories'], 'features': {'memories': False}}, {'features': {'memories': True}, 'memories': {'use_memories': not enabled,
                 'generate_memories': False}}, {'features': {'memories': True}, 'memories': {'use_memories': enabled,
                 'generate_memories': True}}):
        with pytest.raises(instrument.PrelaunchRefused, match='memory'):
            admit(instrument, tmp_path, enabled, bad)


def test_simulated_context_gain_cannot_qualify_native_efficacy(instrument, tmp_path):
    out, ref, _ = freeze(instrument, tmp_path)
    prompts = []
    def invoke(actor, prompt, frozen, expected):
        prompts.append(prompt)
        return observed(expected, tokens=8 if actor.name == 'cand' else 10)
    result = instrument.execute(out, authorized_execute=ref['freeze_sha256'], invoke=invoke)
    assert len(prompts) == 4 and len(set(prompts)) == 1
    assert result['paired_quality_equal'] and result['tokens'] == {'base': 20, 'cand': 16}
    assert result['status'] == 'SIMULATION_ONLY' and result['promotion'] == 'NOT_GRANTED'


def test_changed_profile_manifest_invalidates_source_binding(instrument, tmp_path):
    out, ref, _ = freeze(instrument, tmp_path)
    path = out / 'oracle/freeze.json'
    data = json.loads(path.read_text())
    data['memory_policy']['cand'] = True
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='changed'):
        instrument.execute(out, authorized_execute=ref['freeze_sha256'], invoke=lambda *args: None)


@pytest.mark.parametrize('arm,enabled', [('base', True), ('cand', False)])
def test_native_invocation_passes_frozen_memory_mode_before_generation(instrument, tmp_path, monkeypatch, arm, enabled):
    monkeypatch.setattr(instrument, '_preflight', lambda *args: None)
    monkeypatch.setattr(instrument.subprocess, 'check_output', lambda *args, **kwargs: 'fixture')
    seen = []
    def context(*args, **kwargs):
        seen.append(kwargs['native_memory'])
        return {'settings': {}}
    monkeypatch.setattr(instrument, '_native_context', context)
    monkeypatch.setattr(instrument.subprocess, 'run', lambda *args, **kwargs:
                        instrument.subprocess.CompletedProcess([], 1, b'', b''))
    with pytest.raises(instrument.PrelaunchRefused, match='configuration validation'):
        instrument._invoke(tmp_path / arm, 'task', {'profile': 'task_context',
            'memory_policy': {'base': True, 'cand': False, 'generate': False},
            'executable': 'fixture', 'native_version': 'fixture', 'model': 'fixture'}, instrument.CASES[0])
    assert seen == [enabled]


def test_source_manifest_uses_canonical_controller_path(instrument, tmp_path):
    alias = tmp_path / 'controller-alias.py'
    alias.symlink_to(Path(instrument.__file__))
    spec = importlib.util.spec_from_file_location('aliased_context_controller', alias)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module._sources() == instrument._sources()
