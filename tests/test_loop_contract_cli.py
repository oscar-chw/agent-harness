"""Real read-only CLI assessment and meaningful invalid-input controls."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]


def fixture(root):
    contract = {'schema': 'harness.loop-contract/v1', 'objective': 'Useful outcome with less usage',
                'cases': ['case-1'], 'required_checks': ['functionality', 'security'],
                'required_scope': 'local', 'max_attempts': 2, 'metric': None}
    path = root / 'contract.json'
    path.write_text(json.dumps(contract))
    context = {'model': 'fixture-model', 'effort': 'standard', 'tools_sha256': 'a' * 64,
               'source_scope_sha256': 'b' * 64}

    def run(identity, artifact, tokens):
        return {'run_id': identity, 'artifact_sha256': artifact, 'scope': 'local',
                'checks': {key: {'run_id': identity, 'artifact_sha256': artifact, 'status': 'PASS'}
                           for key in contract['required_checks']},
                'input_tokens': tokens, 'output_tokens': 10, 'metric_samples': []}

    results = {'schema': 'harness.loop-results/v1',
               'contract_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
               'attempt': 1, 'usage_complete': True, 'overhead_tokens': 10,
               'base_context': context, 'candidate_context': dict(context),
               'pairs': [{'case_id': 'case-1', 'base': run('baseline-1', 'c' * 64, 100),
                          'candidate': run('candidate-1', 'd' * 64, 50)}]}
    (root / 'results.json').write_text(json.dumps(results))
    return results


def call(root, *extra):
    env = {**os.environ, 'HOME': str(root / 'home'),
           'HARNESS_HOME': str(root / 'home/.agent-harness')}
    # Isolate application writes from Apple's interpreter bytecode cache.
    return subprocess.run([sys.executable, '-B', str(REPO / 'bin/harness'), 'loop-check',
                           '--project-root', str(root), '--contract', 'contract.json',
                           '--results', 'results.json', *extra], env=env, capture_output=True,
                          text=True, timeout=15)


def snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob('*') if path.is_file()}


def test_real_cli_accepts_the_complete_pair_and_writes_nothing(tmp_path):
    fixture(tmp_path)
    before = snapshot(tmp_path)
    result = call(tmp_path)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report['decision'] == 'ACCEPT_CANDIDATE'
    assert report['promotion'] == 'NOT_GRANTED'
    assert report['base_tokens'] == 110 and report['candidate_tokens'] == 70
    assert snapshot(tmp_path) == before
    assert not (tmp_path / 'home').exists()


@pytest.mark.parametrize('status', ['FAIL', 'UNKNOWN', 'NOT_RUN'])
def test_valid_unqualified_result_is_nonzero_and_preserves_reason(tmp_path, status):
    results = fixture(tmp_path)
    results['pairs'][0]['candidate']['checks']['security']['status'] = status
    (tmp_path / 'results.json').write_text(json.dumps(results))
    result = call(tmp_path)
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert report['decision'] == ('REJECT_CANDIDATE' if status == 'FAIL' else 'INCONCLUSIVE')
    assert report['reasons'] and report['promotion'] == 'NOT_GRANTED'


def test_contract_edit_after_measurement_is_refused(tmp_path):
    fixture(tmp_path)
    path = tmp_path / 'contract.json'
    path.write_text(path.read_text() + '\n')
    result = call(tmp_path)
    assert result.returncode == 2
    assert 'harness loop-check:' in result.stderr and 'contract' in result.stderr.lower()


def test_duplicate_json_keys_are_refused_before_using_either_value(tmp_path):
    fixture(tmp_path)
    path = tmp_path / 'results.json'
    path.write_text(path.read_text().replace('"usage_complete": true',
                                           '"usage_complete": false, "usage_complete": true'))
    result = call(tmp_path)
    assert result.returncode == 2
    assert 'duplicate' in result.stderr.lower()


def test_symlink_and_credential_named_inputs_are_refused(tmp_path):
    fixture(tmp_path)
    (tmp_path / 'alias.json').symlink_to(tmp_path / 'contract.json')
    result = call(tmp_path, '--contract', 'alias.json')
    assert result.returncode == 2 and 'symlink' in result.stderr.lower()
    result = call(tmp_path, '--contract', '.env')
    assert result.returncode == 2 and 'credential' in result.stderr.lower()


@pytest.mark.parametrize('name', ['contract.json', 'results.json'])
def test_open_time_symlink_replacement_never_reads_the_outside_file(tmp_path, monkeypatch,
                                                                  capsys, name):
    from argparse import Namespace
    from agent_harness.cli import cmd_loop_check
    fixture(tmp_path)
    outside = tmp_path.parent / (tmp_path.name + '-outside.json')
    target = tmp_path / name
    outside.write_bytes(target.read_bytes())  # valid input: rejection cannot be a schema accident
    outside_identity = (outside.stat().st_dev, outside.stat().st_ino)
    original_open, original_fdopen = os.open, os.fdopen
    replaced, outside_reads = [], []

    def replace_before_open(path, *args, **kwargs):
        if Path(path).name == name and not replaced:
            target.unlink()
            target.symlink_to(outside)
            replaced.append(True)
        return original_open(path, *args, **kwargs)

    def observe_read(fd, *args, **kwargs):
        info = os.fstat(fd)
        if (info.st_dev, info.st_ino) == outside_identity:
            outside_reads.append(True)
        return original_fdopen(fd, *args, **kwargs)

    monkeypatch.setattr(os, 'open', replace_before_open)
    monkeypatch.setattr(os, 'fdopen', observe_read)
    code = cmd_loop_check(Namespace(project_root=str(tmp_path), contract='contract.json',
                                   results='results.json'))
    assert replaced and code == 2
    assert not outside_reads, 'source boundary must hold before bytes are read'
    assert 'harness loop-check:' in capsys.readouterr().err


def test_parent_directory_replacement_never_reads_outside(tmp_path, monkeypatch, capsys):
    from argparse import Namespace
    from agent_harness.cli import cmd_loop_check
    fixture(tmp_path)
    folder = tmp_path / 'inputs'
    folder.mkdir()
    (tmp_path / 'contract.json').rename(folder / 'contract.json')
    outside = tmp_path.parent / (tmp_path.name + '-outside')
    outside.mkdir()
    (outside / 'contract.json').write_bytes((folder / 'contract.json').read_bytes())
    identity = (outside.joinpath('contract.json').stat().st_dev,
                outside.joinpath('contract.json').stat().st_ino)
    original_open, original_fdopen = os.open, os.fdopen
    replaced, outside_reads = [], []

    def swap_parent(path, *args, **kwargs):
        if Path(path).name == 'inputs' and not replaced:
            folder.rename(tmp_path / 'original-inputs')
            folder.symlink_to(outside, target_is_directory=True)
            replaced.append(True)
        return original_open(path, *args, **kwargs)

    def observe_read(fd, *args, **kwargs):
        info = os.fstat(fd)
        if (info.st_dev, info.st_ino) == identity:
            outside_reads.append(True)
        return original_fdopen(fd, *args, **kwargs)

    monkeypatch.setattr(os, 'open', swap_parent)
    monkeypatch.setattr(os, 'fdopen', observe_read)
    code = cmd_loop_check(Namespace(project_root=str(tmp_path), contract='inputs/contract.json',
                                   results='results.json'))
    assert replaced and code == 2
    assert not outside_reads
    assert 'harness loop-check:' in capsys.readouterr().err
