"""Task artifacts stay navigable without deleting evidence or injecting content."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def call(project, *args):
    return subprocess.run([sys.executable, str(ROOT / 'bin/harness'), 'workspace', *args],
                          cwd=project, capture_output=True, text=True, timeout=10)


def test_inspection_is_read_only_and_absence_is_not_completion(tmp_path):
    result = call(tmp_path, '--task', 'example')
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert body['status'] == 'NOT_CREATED' and body['files'] == []
    assert body['completion'] == 'NOT_EVALUATED'
    assert list(tmp_path.iterdir()) == []


def test_init_creates_one_index_and_reuses_it(tmp_path):
    first = call(tmp_path, '--task', 'example', '--init')
    assert first.returncode == 0, first.stderr
    base = tmp_path / '.harness-work/example'
    assert {p.name for p in base.iterdir()} == {'README.md', 'scratch', 'outputs'}
    index = base / 'README.md'
    assert 'scratch/' in index.read_text() and 'outputs/' in index.read_text()
    index.write_text(index.read_text() + '\nOwner note: retain this.\n')
    before = {str(p.relative_to(base)): p.stat().st_mtime_ns for p in base.rglob('*')}
    for _ in range(3):
        repeated = call(tmp_path, '--task', 'example', '--init')
        assert repeated.returncode == 0, repeated.stderr
    after = {str(p.relative_to(base)): p.stat().st_mtime_ns for p in base.rglob('*')}
    assert before == after
    assert 'Owner note: retain this.' in index.read_text()


def test_inventory_returns_metadata_not_file_content_or_other_tasks(tmp_path):
    assert call(tmp_path, '--task', 'one', '--init').returncode == 0
    base = tmp_path / '.harness-work/one'
    (base / 'outputs/result.txt').write_text('DO_NOT_INJECT_CONTENT')
    (base / 'scratch/log.txt').write_bytes(b'x' * 100)
    other = tmp_path / '.harness-work/two'
    other.mkdir()
    (other / 'private.txt').write_text('not relevant')
    result = call(tmp_path, '--task', 'one')
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    rows = {p['path']: p for p in body['files']}
    assert rows['outputs/result.txt']['bytes'] == len('DO_NOT_INJECT_CONTENT')
    assert rows['outputs/result.txt']['kind'] == 'output'
    assert rows['scratch/log.txt']['kind'] == 'scratch'
    assert body['scratch_bytes'] == 100
    assert body['total_bytes'] == sum(p['bytes'] for p in rows.values())
    assert 'DO_NOT_INJECT_CONTENT' not in result.stdout
    assert 'private.txt' not in result.stdout


@pytest.mark.parametrize('task', ['../outside', '/absolute', '.', '..', 'a/b', 'a\\b', 'x'*129])
def test_invalid_task_cannot_write(tmp_path, task):
    assert call(tmp_path, '--task', task, '--init').returncode == 2
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('part', ['root', 'task', 'index', 'ignore', 'output', 'nested'])
def test_symlinks_are_refused_without_following_them(tmp_path, part):
    project = tmp_path / 'project'
    project.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    secret = outside / 'private.txt'
    secret.write_text('never read or modify')
    if part == 'root':
        (project / '.harness-work').symlink_to(outside, target_is_directory=True)
    elif part == 'task':
        (project / '.harness-work').mkdir()
        (project / '.harness-work/one').symlink_to(outside, target_is_directory=True)
    else:
        assert call(project, '--task', 'one', '--init').returncode == 0
        base = project / '.harness-work/one'
        if part == 'index':
            (base / 'README.md').unlink()
            (base / 'README.md').symlink_to(secret)
        elif part == 'ignore':
            (base.parent / '.gitignore').unlink(missing_ok=True)
            (base.parent / '.gitignore').symlink_to(secret)
        elif part == 'output':
            (base / 'outputs/link').symlink_to(secret)
        else:
            (base / 'scratch/link').symlink_to(outside, target_is_directory=True)
    blocked = call(project, '--task', 'one', '--init')
    assert blocked.returncode == 2 and 'symlink' in blocked.stderr
    assert 'never read or modify' not in blocked.stdout
    assert secret.read_text() == 'never read or modify'
    assert sorted(p.name for p in outside.iterdir()) == ['private.txt']


def test_large_inventory_fails_loudly_and_preserves_all_files(tmp_path):
    assert call(tmp_path, '--task', 'one', '--init').returncode == 0
    base = tmp_path / '.harness-work/one/scratch'
    for i in range(1001):
        (base / str(i)).touch()
    result = call(tmp_path, '--task', 'one')
    assert result.returncode == 2 and 'limit' in result.stderr
    assert not result.stdout
    assert len(list(base.iterdir())) == 1001


def test_nonregular_and_incomplete_workspaces_do_not_mean_success(tmp_path):
    base = tmp_path / '.harness-work/one'
    base.mkdir(parents=True)
    (base / 'outputs').write_text('wrong type')
    assert call(tmp_path, '--task', 'one', '--init').returncode == 2
    assert (base / 'outputs').read_text() == 'wrong type'
    (base / 'outputs').unlink()
    assert call(tmp_path, '--task', 'one', '--init').returncode == 0
    if hasattr(os, 'mkfifo'):
        os.mkfifo(base / 'scratch/pipe')
        result = call(tmp_path, '--task', 'one')
        assert result.returncode == 2 and 'regular' in result.stderr


def test_scratch_warning_reports_but_never_prunes(tmp_path):
    assert call(tmp_path, '--task', 'one', '--init').returncode == 0
    log = tmp_path / '.harness-work/one/scratch/large.log'
    with log.open('wb') as stream:
        stream.truncate(33 * 1024 * 1024)
    result = call(tmp_path, '--task', 'one')
    assert result.returncode == 0, result.stderr
    assert 'SCRATCH_BUDGET_EXCEEDED' in json.loads(result.stdout)['warnings']
    assert log.stat().st_size == 33 * 1024 * 1024


def test_large_metadata_is_summarized_explicitly_not_flooded(tmp_path):
    assert call(tmp_path, '--task', 'one', '--init').returncode == 0
    base = tmp_path / '.harness-work/one/outputs'
    for i in range(200):
        (base / (f'{i:03}-' + 'x'*200)).write_bytes(b'xx')
    result = call(tmp_path, '--task', 'one')
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert body['file_count'] == 201
    assert len(body['files']) <= 40
    assert body['omitted_files'] == body['file_count'] - len(body['files'])
    assert 'INVENTORY_SUMMARIZED' in body['warnings']
    assert len(result.stdout.encode()) < 16384


def test_missing_index_is_incomplete_and_deep_tree_is_refused(tmp_path):
    base = tmp_path / '.harness-work/one'
    base.mkdir(parents=True)
    result = call(tmp_path, '--task', 'one')
    assert result.returncode == 0
    assert json.loads(result.stdout)['status'] == 'INCOMPLETE'
    assert not (base/'README.md').exists()
    assert call(tmp_path, '--task', 'one', '--init').returncode == 0
    deep = base/'scratch'
    for _ in range(17):
        deep = deep/'d'
        deep.mkdir()
    result = call(tmp_path, '--task', 'one')
    assert result.returncode == 2 and 'depth' in result.stderr


def test_new_project_scratch_is_ignored_without_changing_project_rules(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    rules = tmp_path / '.gitignore'
    rules.write_text('owner-pattern\n')
    assert call(tmp_path, '--task', 'one', '--init').returncode == 0
    base = tmp_path / '.harness-work/one'
    (base/'scratch/private.log').write_text('keep private')
    (base/'outputs/result.md').write_text('deliberate publication only')
    result = subprocess.run(['git', 'check-ignore', '.harness-work/one/README.md',
                             '.harness-work/one/scratch/private.log',
                             '.harness-work/one/outputs/result.md'], cwd=tmp_path,
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0 and len(result.stdout.splitlines()) == 3
    assert rules.read_text() == 'owner-pattern\n'


def test_existing_custom_workspace_ignore_is_preserved_and_not_certified(tmp_path):
    base = tmp_path / '.harness-work'
    base.mkdir()
    custom = base/'.gitignore'
    custom.write_text('!outputs/\n')
    result = call(tmp_path, '--task', 'one', '--init')
    assert result.returncode == 0, result.stderr
    assert custom.read_text() == '!outputs/\n'
    assert 'EXISTING_IGNORE_NOT_VERIFIED' in json.loads(result.stdout)['warnings']
