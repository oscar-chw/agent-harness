"""One entry point composes existing installers without hiding partial failure."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/install-laptop-bundle.py'


@pytest.fixture
def bundle(tmp_path):
    root = tmp_path / "bundle space's"
    home = tmp_path / "home space's"
    root.mkdir(); home.mkdir()
    files = {}
    for directory, filename in [('runtime', 'install.py'), ('knowledge', 'add-knowledge.py')]:
        path = root / directory / filename
        path.parent.mkdir()
        path.write_text('''import json,os,pathlib,sys
if '--check' in sys.argv: raise SystemExit(0)
home=pathlib.Path(sys.argv[sys.argv.index('--home')+1])
with (home/'order.jsonl').open('a') as out:out.write(json.dumps([pathlib.Path(__file__).parent.name,sys.argv[1:]])+'\\n')
raise SystemExit(int(os.environ.get('FAIL_'+pathlib.Path(__file__).parent.name.upper(),'0')))
''')
        files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {'schema': 'harness.laptop-bundle/v1', 'files': files, 'build_id': 'fixture-build'}
    (root / 'BUNDLE.json').write_text(json.dumps(manifest))
    return root, home


def invoke(bundle, *args, fail=None):
    root, home = bundle
    env = {'PATH': os.defpath, 'HOME': str(home), 'PYTHONDONTWRITEBYTECODE': '1'}
    if fail:
        env.update(fail)
    return subprocess.run([sys.executable, str(SCRIPT), '--bundle-dir', str(root), '--home', str(home), *args],
                          env=env, capture_output=True, text=True, timeout=10)


def test_single_entry_installs_runtime_then_knowledge_with_identical_home(bundle):
    result = invoke(bundle, '--tools', 'codex,copilot-vscode')
    assert result.returncode == 0, result.stderr
    rows = [json.loads(line) for line in (bundle[1] / 'order.jsonl').read_text().splitlines()]
    assert [r[0] for r in rows] == ['runtime', 'knowledge']
    assert '--tools' in rows[0][1] and 'codex,copilot-vscode' in rows[0][1]
    assert all(r[1][r[1].index('--home') + 1] == str(bundle[1]) for r in rows)


def test_check_is_read_only_and_does_not_install(bundle):
    result = invoke(bundle, '--check')
    assert result.returncode == 0, result.stderr
    assert not (bundle[1] / 'order.jsonl').exists()


@pytest.mark.parametrize('stage,code,expected_calls', [('RUNTIME', '7', 1), ('KNOWLEDGE', '8', 2)])
def test_failed_phase_stops_and_reports_actual_partial_state(bundle, stage, code, expected_calls):
    result = invoke(bundle, fail={'FAIL_' + stage: code})
    assert result.returncode == int(code)
    assert stage.lower() in result.stderr
    rows = (bundle[1] / 'order.jsonl').read_text().splitlines()
    assert len(rows) == expected_calls
    if stage == 'KNOWLEDGE':
        assert 'runtime completed' in result.stderr.lower()


@pytest.mark.parametrize('fault', ['changed', 'missing', 'symlink', 'traversal', 'duplicate-key'])
def test_invalid_bundle_refuses_before_any_child_install(bundle, fault):
    root, home = bundle
    path = root / 'runtime/install.py'
    if fault == 'changed': path.write_text('changed')
    elif fault == 'missing': path.unlink()
    elif fault == 'symlink':
        target = root / 'other.py'; path.rename(target); path.symlink_to(target)
    elif fault == 'traversal':
        value = json.loads((root / 'BUNDLE.json').read_text())
        value['files']['../outside'] = 'a' * 64
        (root / 'BUNDLE.json').write_text(json.dumps(value))
    else:
        (root / 'BUNDLE.json').write_text('{"schema":"x","schema":"harness.laptop-bundle/v1"}')
    result = invoke(bundle)
    assert result.returncode == 2 and 'refused' in result.stderr.lower()
    assert not (home / 'order.jsonl').exists()


def test_environment_store_is_normalized_once_for_both_phases(bundle):
    root, home = bundle
    manifest = json.loads((root / 'BUNDLE.json').read_text())
    for child in manifest['files']:
        path = root / child
        path.write_text("import json,os,pathlib\nwith (pathlib.Path.home()/'stores.jsonl').open('a') as f:f.write(json.dumps(os.environ['HARNESS_HOME'])+'\\n')\n")
        manifest['files'][child] = hashlib.sha256(path.read_bytes()).hexdigest()
    (root / 'BUNDLE.json').write_text(json.dumps(manifest))
    result = subprocess.run([sys.executable, str(SCRIPT), '--bundle-dir', str(root)],
                            env={'HOME': str(home), 'HARNESS_HOME': '~/custom-store', 'PATH': os.defpath},
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert [json.loads(s) for s in (home / 'stores.jsonl').read_text().splitlines()] == [str(home / 'custom-store')] * 2


def test_knowledge_launch_error_retains_completed_runtime_state(bundle, monkeypatch, capsys):
    root, home = bundle
    entry = runpy.run_path(str(SCRIPT), run_name='test_bundle')
    calls = []

    def launch(command, **kwargs):
        calls.append(command)
        if len(calls) == 2:
            raise OSError('fixture launch failure')
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, 'run', launch)
    monkeypatch.setattr(sys, 'argv', [str(SCRIPT), '--bundle-dir', str(root), '--home', str(home)])
    assert entry['main']() == 2
    message = capsys.readouterr().err.lower()
    assert 'runtime completed' in message and 'knowledge' in message and 'not started' in message
    assert 'rollback' in message and len(calls) == 2
