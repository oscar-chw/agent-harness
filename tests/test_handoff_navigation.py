"""Large task history stays available without mandatory whole-history injection."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def call(project, *args):
    return subprocess.run([sys.executable, str(ROOT / 'bin/harness'), 'handoff', *args],
                          cwd=project, capture_output=True, text=True, timeout=10,
                          env={**os.environ, 'HARNESS_HOME': str(project / 'absent-store')})


def history(project):
    directory = project / 'handoffs/task'
    directory.mkdir(parents=True)
    (directory / 'current.md').write_text('Done: parser gate PASS. Next: verify retrieval.\n')
    for i in range(6):
        (directory / f'past-{i}.md').write_text('private-history-not-selected\n' + 'x' * 14000)
    return directory


def test_inventory_lists_all_packets_without_reading_their_text(tmp_path):
    directory = history(tmp_path)
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    result = call(tmp_path, '--task', 'task', '--list')
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert body['status'] == 'HANDOFF_INDEX' and body['advisory']
    assert body['packets'] == []
    assert {p['path'] for p in body['available']} == {
        f'handoffs/task/{name}' for name in before}
    assert all(p['bytes'] == len(before[Path(p['path']).name]) for p in body['available'])
    assert 'private-history-not-selected' not in result.stdout
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == before
    assert not (tmp_path / 'absent-store').exists()


def test_cold_reader_selects_only_current_packet_from_large_task(tmp_path):
    directory = history(tmp_path)
    # Default whole-task read still fails closed. The bound is not relaxed.
    full = call(tmp_path, '--task', 'task')
    assert full.returncode == 2 and 'aggregate limit' in full.stderr
    assert '--packet' in full.stderr
    result = call(tmp_path, '--task', 'task', '--packet', 'current.md')
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert [p['path'] for p in body['packets']] == ['handoffs/task/current.md']
    assert body['packets'][0]['text'] == (directory / 'current.md').read_text()
    assert 'private-history-not-selected' not in result.stdout
    assert body['selection'] == ['current.md']


@pytest.mark.parametrize('name', ['../outside.md', '/tmp/outside.md', 'sub/peer.md',
                                 'current.txt', 'missing.md'])
def test_invalid_or_missing_selection_never_falls_back_to_other_packets(tmp_path, name):
    history(tmp_path)
    result = call(tmp_path, '--task', 'task', '--packet', name)
    assert result.returncode == 2 and not result.stdout


def test_selection_requires_task_and_rejects_duplicate_or_mixed_modes(tmp_path):
    history(tmp_path)
    for args in [('--packet', 'current.md'), ('--list',),
                 ('--task', 'task', '--packet', 'current.md', '--packet', 'current.md'),
                 ('--task', 'task', '--list', '--packet', 'current.md')]:
        result = call(tmp_path, *args)
        assert result.returncode == 2 and not result.stdout


def test_selected_packets_keep_original_byte_and_aggregate_bounds(tmp_path):
    directory = history(tmp_path)
    (directory / 'huge.md').write_text('x' * 17000)
    oversized = call(tmp_path, '--task', 'task', '--packet', 'huge.md')
    assert oversized.returncode == 2 and 'byte limit' in oversized.stderr
    args = ['--task', 'task']
    for i in range(6):
        args += ['--packet', f'past-{i}.md']
    large = call(tmp_path, *args)
    assert large.returncode == 2 and 'aggregate limit' in large.stderr


def test_selected_symlink_and_inventory_nonregular_packet_are_refused(tmp_path):
    directory = history(tmp_path)
    external = tmp_path / 'external.md'
    external.write_text('must not disclose')
    (directory / 'link.md').symlink_to(external)
    for args in [('--packet', 'link.md'), ('--list',)]:
        result = call(tmp_path, '--task', 'task', *args)
        assert result.returncode == 2 and 'symlink' in result.stderr
        assert 'must not disclose' not in result.stdout
    (directory / 'link.md').unlink()
    if hasattr(os, 'mkfifo'):
        os.mkfifo(directory / 'pipe.md')
    else:
        (directory / 'pipe.md').mkdir()
    result = call(tmp_path, '--task', 'task', '--list')
    assert result.returncode == 2 and 'regular' in result.stderr


def test_inventory_keeps_existing_directory_count_cap(tmp_path):
    directory = tmp_path / 'handoffs/task'
    directory.mkdir(parents=True)
    for i in range(101):
        (directory / f'{i}.md').write_text('bounded')
    result = call(tmp_path, '--task', 'task', '--list')
    assert result.returncode == 2 and 'entry limit' in result.stderr


def test_inventory_can_discover_unreadable_text_without_decoding_it(tmp_path):
    directory = tmp_path / 'handoffs/task'
    directory.mkdir(parents=True)
    (directory / 'bad-encoding.md').write_bytes(b'\xff' * 17000)
    index = call(tmp_path, '--task', 'task', '--list')
    assert index.returncode == 0, index.stderr
    assert json.loads(index.stdout)['available'] == [
        {'path': 'handoffs/task/bad-encoding.md', 'bytes': 17000}]
    selected = call(tmp_path, '--task', 'task', '--packet', 'bad-encoding.md')
    assert selected.returncode == 2 and 'byte limit' in selected.stderr
