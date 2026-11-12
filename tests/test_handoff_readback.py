"""Project-local inspection works without opening the global task database."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def call(project, *args):
    return subprocess.run([sys.executable, str(ROOT / 'bin/harness'), 'handoff', *args],
                          cwd=project, capture_output=True, text=True, timeout=10,
                          env={**os.environ, 'HARNESS_HOME': str(project / 'unavailable-store')})


def test_reads_an_unregistered_peer_packet_without_global_storage(tmp_path):
    packet = tmp_path / 'handoffs/summary/peer.md'
    packet.parent.mkdir(parents=True)
    packet.write_text('Done: original gate PASS\nNext: no further code work\n')
    before = packet.read_bytes()
    result = call(tmp_path, '--task', 'summary')
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert body['advisory'] is True
    assert body['packets'][0]['path'] == 'handoffs/summary/peer.md'
    assert body['packets'][0]['text'] == before.decode()
    assert len(body['packets'][0]['sha256']) == 64
    assert packet.read_bytes() == before
    assert not (tmp_path / 'unavailable-store').exists()


def test_empty_and_other_task_never_mean_done(tmp_path):
    result = call(tmp_path, '--task', 'unknown')
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert body['status'] == 'NO_HANDOFF' and body['packets'] == [] and body['advisory']
    assert call(tmp_path, '--task', '../escape').returncode != 0


def test_symlinked_packet_and_oversized_packet_are_refused(tmp_path):
    directory = tmp_path / 'handoffs/task'
    directory.mkdir(parents=True)
    outside = tmp_path / 'private.txt'
    outside.write_text('must not disclose')
    packet = directory / 'peer.md'
    packet.symlink_to(outside)
    blocked = call(tmp_path, '--task', 'task')
    assert blocked.returncode != 0 and 'must not disclose' not in blocked.stdout
    assert 'symlink' in blocked.stderr
    packet.unlink()
    packet.write_text('x' * 17000)
    oversized = call(tmp_path, '--task', 'task')
    assert oversized.returncode != 0 and 'limit' in oversized.stderr


def test_nonregular_packet_does_not_hang_the_reader(tmp_path):
    directory = tmp_path / 'handoffs/task'
    directory.mkdir(parents=True)
    if hasattr(os, 'mkfifo'):
        os.mkfifo(directory / 'peer.md')
    else:
        (directory / 'peer.md').mkdir()
    result = call(tmp_path, '--task', 'task')
    assert result.returncode != 0 and 'regular' in result.stderr


def test_directory_and_aggregate_limits_are_not_silent_truncation(tmp_path):
    directory = tmp_path / 'handoffs/task'
    directory.mkdir(parents=True)
    for i in range(5):
        (directory / f'{i}.md').write_text('x' * 14000)
    result = call(tmp_path, '--task', 'task')
    assert result.returncode != 0 and 'aggregate limit' in result.stderr
    assert not result.stdout
