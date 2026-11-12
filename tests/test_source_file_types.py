"""Bounded source readers must reject streams before waiting for their contents."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_harness.vault_sources import SourceVault, initialize

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.integration


def env(tmp_path):
    return {'HOME': str(tmp_path / 'home'), 'PATH': os.defpath,
            'PYTHONPATH': str(ROOT / 'src'), 'PYTHONDONTWRITEBYTECODE': '1'}


@pytest.mark.skipif(not hasattr(os, 'mkfifo'), reason='POSIX named pipes unavailable')
@pytest.mark.parametrize('command', ['vault-read', 'vault-document'])
def test_shared_source_or_catalogue_pipe_is_refused_without_waiting(tmp_path, command):
    pipe = tmp_path / 'stream'
    os.mkfifo(pipe)
    arguments = (['--source', pipe.name, '--sha256', hashlib.sha256(b'').hexdigest()]
                 if command == 'vault-read' else
                 ['--manifest', pipe.name, '--manifest-sha256', hashlib.sha256(b'').hexdigest(),
                  '--document-id', 'fixture'])
    result = subprocess.run([sys.executable, str(ROOT / 'bin/harness'), command,
                             '--vault-root', str(tmp_path), '--vault-id', 'fixture', *arguments],
                            env=env(tmp_path), capture_output=True, text=True, timeout=2)
    assert result.returncode == 2, result.stdout + result.stderr
    assert 'regular file' in result.stderr and 'stream' in result.stderr
    assert pipe.is_fifo()
    assert not (tmp_path / 'home').exists()


@pytest.mark.skipif(not hasattr(os, 'mkfifo'), reason='POSIX named pipes unavailable')
@pytest.mark.parametrize('target', ['original', 'snapshot', 'project-manifest'])
def test_project_capture_and_resolution_refuse_streams(tmp_path, target):
    (tmp_path / 'source.txt').write_text('Recorded source evidence.\n')
    project_id = initialize(tmp_path)
    receipt = SourceVault(tmp_path, project_id).capture('source.txt')
    path = {'original': tmp_path / 'source.txt',
            'snapshot': tmp_path / '.harness/sources' / (receipt['source_id'] + '.json'),
            'project-manifest': tmp_path / '.harness/project.json'}[target]
    path.unlink()
    os.mkfifo(path)
    code = '''import json,sys
from agent_harness.vault_sources import SourceVault
try:
    vault=SourceVault(sys.argv[1],sys.argv[2])
    if sys.argv[4]=='original':vault.capture('source.txt')
    else:vault.resolve(json.loads(sys.argv[3]))
except ValueError as error:
    print(str(error),file=sys.stderr)
    raise SystemExit(2)
'''
    result = subprocess.run([sys.executable, '-c', code, str(tmp_path), project_id,
                             json.dumps(receipt), target], env=env(tmp_path),
                            capture_output=True, text=True, timeout=2)
    assert result.returncode == 2 and 'regular file' in result.stderr
    assert path.is_fifo()


def test_regular_source_still_returns_exact_bytes_and_bad_pin_still_fails(tmp_path):
    from agent_harness.vault_sources import read_shared_source
    raw = 'Actual source evidence.\r\n原始条件。\n'.encode()
    (tmp_path / 'source.md').write_bytes(raw)
    args = dict(vault_id='fixture', source='source.md', sha256=hashlib.sha256(raw).hexdigest())
    packet = read_shared_source(tmp_path, **args)
    assert packet['text'].encode() == raw
    with pytest.raises(ValueError, match='digest mismatch'):
        read_shared_source(tmp_path, **{**args, 'sha256': '0' * 64})
    assert (tmp_path / 'source.md').read_bytes() == raw


@pytest.mark.skipif(not hasattr(os, 'mkfifo'), reason='POSIX named pipes unavailable')
def test_source_replaced_with_pipe_before_open_does_not_block(tmp_path):
    path = tmp_path / 'source.md'
    path.write_text('A regular file before the read.\n')
    code = '''import hashlib,os,pathlib,sys
from agent_harness.vault_sources import read_shared_source
source=pathlib.Path(sys.argv[1])/'source.md'
pin=hashlib.sha256(source.read_bytes()).hexdigest()
original=os.open
def swap(path,flags,*args,**kwargs):
    if pathlib.Path(path)==source:
        source.unlink();os.mkfifo(source)
    return original(path,flags,*args,**kwargs)
os.open=swap
try:read_shared_source(source.parent,vault_id='fixture',source=source.name,sha256=pin)
except ValueError as error:
    print(str(error),file=sys.stderr)
    raise SystemExit(2)
'''
    result = subprocess.run([sys.executable, '-c', code, str(tmp_path)], env=env(tmp_path),
                            capture_output=True, text=True, timeout=2)
    assert result.returncode == 2 and 'regular file' in result.stderr
    assert path.is_fifo()


@pytest.mark.parametrize('failure', [None, 'type', 'size'])
def test_source_descriptors_close_after_success_or_refusal(tmp_path, monkeypatch, failure):
    from agent_harness import vault_sources
    path = tmp_path / 'source'
    raw = b'Exact source bytes.\n'
    if failure == 'type':
        path.mkdir()
    else:
        path.write_bytes(raw)
    opened = []
    original = os.open

    def tracked(*args, **kwargs):
        descriptor = original(*args, **kwargs)
        opened.append(descriptor)
        return descriptor

    monkeypatch.setattr(os, 'open', tracked)
    if failure == 'size':
        monkeypatch.setattr(vault_sources, 'SOURCE_LIMIT', 4)
    kwargs = dict(vault_id='fixture', source=path.name, sha256=hashlib.sha256(raw).hexdigest())
    if failure:
        with pytest.raises((OSError, ValueError)):
            vault_sources.read_shared_source(tmp_path, **kwargs)
    else:
        assert vault_sources.read_shared_source(tmp_path, **kwargs)['text'].encode() == raw
    if failure != 'type' or os.name != 'nt':
        assert len(opened) == 1
    for descriptor in opened:
        with pytest.raises(OSError):
            os.fstat(descriptor)
