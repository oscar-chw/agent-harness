"""Public CLI preparation must retain source bindings and the promotion hold."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def lab(tmp_path):
    root = tmp_path / 'project'
    root.mkdir()
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    spec = {'schema': 1, 'title': 'Check empty inputs', 'trigger': 'parser repair',
            'steps': ['Reproduce the empty input before editing.'],
            'exceptions': ['Do not apply to unrelated tasks.'], 'episodes': []}
    for n in (1, 2):
        (root / f'task{n}.txt').write_text(f'Input contract {n}')
        (root / f'check{n}.txt').write_text(f'Observed failure then passing check {n}')
        spec['episodes'].append({'task_id': str(n), 'path': f'check{n}.txt', 'task_path': f'task{n}.txt'})
    return root, tmp_path / 'home', spec


def cli(lab, *args):
    root, home, _ = lab
    env = dict(os.environ, HOME=str(home), HARNESS_HOME=str(home / 'harness'),
               PYTHONPATH=str(ROOT / 'src'))
    return subprocess.run([sys.executable, str(ROOT / 'bin/harness'), 'improve',
                           '--project', str(root), *args], env=env, cwd=root,
                          capture_output=True, text=True, timeout=20)


def prepare(lab, spec=None):
    root, _, default = lab
    p = root / 'spec.json'
    p.write_text(json.dumps(default if spec is None else spec))
    return cli(lab, '--prepare-procedure', str(p))


def test_cli_prepares_real_hashes_without_a_store(lab):
    root, home, spec = lab
    before = copy.deepcopy(spec)
    result = prepare(lab)
    assert result.returncode == 0, result.stdout + result.stderr
    candidate = json.loads(result.stdout)
    assert spec == before
    for episode in candidate['episodes']:
        assert episode['sha256'] == hashlib.sha256((root / episode['path']).read_bytes()).hexdigest()
        assert episode['task_sha256'] == hashlib.sha256((root / episode['task_path']).read_bytes()).hexdigest()
    assert not (home / 'harness/procedures.sqlite').exists()


def test_prepared_candidate_drafts_inspects_corrects_and_still_cannot_promote(lab):
    root, home, _ = lab
    result = prepare(lab)
    assert result.returncode == 0, result.stdout + result.stderr
    p = root / 'candidate.json'
    p.write_text(result.stdout)
    draft = cli(lab, '--draft-procedure', str(p))
    assert draft.returncode == 0, draft.stdout
    old = json.loads(draft.stdout)
    view = cli(lab, '--inspect-procedure', old['id'])
    assert view.returncode == 0 and json.loads(view.stdout)['status'] == 'proposed'
    held = cli(lab, '--apply', old['id'])
    assert held.returncode != 0 and 'independent grader' in held.stdout
    candidate = json.loads(result.stdout)
    candidate['steps'].append('Record the actual output.')
    p.write_text(json.dumps(candidate))
    corrected = cli(lab, '--correct-procedure', old['id'], '--draft-procedure', str(p))
    assert corrected.returncode == 0, corrected.stdout
    new = json.loads(corrected.stdout)
    assert new['status'] == 'proposed' and new['supersedes'] == old['id']
    old_view = json.loads(cli(lab, '--inspect-procedure', old['id']).stdout)
    assert old_view['status'] == 'rolled_back' and old_view['superseded_by'] == new['id']
    assert not (home / '.agents/skills/learned').exists()


@pytest.mark.parametrize('fault', ['missing', 'escape', 'absolute', 'symlink_escape', 'duplicate_source', 'duplicate_task', 'oversize', 'extra_field'])
def test_invalid_sources_are_refused_without_a_store(lab, fault):
    root, home, spec = lab
    if fault == 'missing': spec['episodes'][0]['path'] = 'absent.txt'
    elif fault in ('escape', 'absolute', 'symlink_escape'):
        outside = root.parent / 'outside.txt'
        outside.write_text('Not authorized for this project')
        if fault == 'escape': spec['episodes'][0]['path'] = '../outside.txt'
        elif fault == 'absolute': spec['episodes'][0]['path'] = str(outside)
        else:
            (root / 'linked.txt').symlink_to(outside)
            spec['episodes'][0]['path'] = 'linked.txt'
    elif fault == 'duplicate_source': (root / 'check2.txt').write_bytes((root / 'check1.txt').read_bytes())
    elif fault == 'duplicate_task': (root / 'task2.txt').write_bytes((root / 'task1.txt').read_bytes())
    elif fault == 'oversize': (root / 'check1.txt').write_bytes(b'x' * 65537)
    else: spec['activate'] = True
    result = prepare(lab)
    assert result.returncode == 1 and 'refused' in result.stdout, result.stderr
    assert not (home / 'harness/procedures.sqlite').exists()


def test_source_change_after_preparation_is_rejected_by_draft(lab):
    root, _, _ = lab
    result = prepare(lab)
    assert result.returncode == 0
    p = root / 'candidate.json'
    p.write_text(result.stdout)
    (root / 'check1.txt').write_text('Changed observation')
    result = cli(lab, '--draft-procedure', str(p))
    assert result.returncode == 1 and 'source changed' in result.stdout


def test_prepare_and_inspect_cannot_silently_combine_actions(lab):
    root, _, spec = lab
    p = root / 'spec.json'
    p.write_text(json.dumps(spec))
    for args in [('--prepare-procedure', str(p), '--propose'),
                 ('--inspect-procedure', 'pr-unknown', '--weekly-intake')]:
        result = cli(lab, *args)
        assert result.returncode == 1 and ('refused' in result.stdout or 'HOLD' in result.stdout)


def test_draft_refuses_evidence_replaced_by_a_pipe_without_waiting(lab):
    root, home, _ = lab
    result = prepare(lab)
    assert result.returncode == 0
    p = root / 'candidate.json'
    p.write_text(result.stdout)
    source = root / 'check1.txt'
    source.unlink()
    os.mkfifo(source)
    env = dict(os.environ, HOME=str(home), HARNESS_HOME=str(home / 'harness'),
               PYTHONPATH=str(ROOT / 'src'))
    result = subprocess.run([sys.executable, str(ROOT / 'bin/harness'), 'improve',
                             '--project', str(root), '--draft-procedure', str(p)],
                            cwd=root, env=env, capture_output=True, text=True, timeout=2)
    assert result.returncode == 1 and 'regular file' in result.stdout
    assert not (home / 'harness/procedures.sqlite').exists()


def test_existing_json_input_symlinks_still_work(lab):
    root, _, spec = lab
    path = root / 'spec.json'
    path.write_text(json.dumps(spec))
    alias = root / 'alias.json'
    alias.symlink_to(path)
    result = cli(lab, '--prepare-procedure', str(alias))
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)['title'] == spec['title']
