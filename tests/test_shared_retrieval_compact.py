"""Compact omissions must retain every exact source, rank and reason under the same cap."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_harness import vault_retrieval as retrieval


def make_vault(root, count=100):
    docs = []
    for index in range(count):
        identity = 'd-' + hashlib.sha256(str(index).encode()).hexdigest()[:32]
        raw = f'id: {identity}\ntitle: Test note\nquartzledger remedy {index}\n'.encode()
        (root / f'{index}.md').write_bytes(raw)
        docs.append({'id': identity, 'title': 'Test note', 'path': f'{index}.md',
                     'sha256': hashlib.sha256(raw).hexdigest(), 'document_type': 'method_note',
                     'rights': {'redistribution': 'public', 'license': 'CC0-1.0',
                                'basis': 'Owned synthetic regression fixture.'},
                     'source_refs': [{'uri': f'urn:compact:{index}', 'kind': 'fixture', 'revision': 'v1'}]})
    raw = json.dumps({'schema': 'quant-shared-notes/v1', 'revision': 'v1', 'documents': docs}).encode()
    (root / 'manifest.json').write_bytes(raw)
    return docs, hashlib.sha256(raw).hexdigest()


def search(root, docs, pin, **options):
    return retrieval.search_shared_documents(root, vault_id='compact-fixture', manifest='manifest.json',
        manifest_sha256=pin, allowed_ids=[d['id'] for d in docs], query='quartzledger', **options)


def resolve(root, docs, pin, packet):
    return retrieval.read_shared_omissions(root, vault_id='compact-fixture', manifest='manifest.json',
        manifest_sha256=pin, allowed_ids=[d['id'] for d in docs], packet=packet)


@pytest.mark.parametrize('backend', ['lexical', 'fts5'])
def test_all_100_sources_remain_accounted_for_under_8k(tmp_path, backend):
    docs, pin = make_vault(tmp_path)
    with pytest.raises(ValueError, match='omission metadata'):
        search(tmp_path, docs, pin, backend=backend)
    packet = search(tmp_path, docs, pin, backend=backend, omission_format='manifest-index')
    assert packet['schema'] == 'harness.shared-search/v2'
    assert len(json.dumps(packet, ensure_ascii=False).encode()) <= 8192
    assert len(packet['hits']) == 5 and len(packet['omitted']) == 95
    expanded = resolve(tmp_path, docs, pin, packet)
    verbose = search(tmp_path, docs, pin, backend=backend, max_bytes=65536)
    assert packet['hits'] == verbose['hits']
    assert expanded == verbose['omitted']
    assert {d['document_id'] for d in packet['hits'] + expanded} == {d['id'] for d in docs}


def test_compact_and_full_default_remain_distinct_and_budget_is_not_raised(tmp_path):
    docs, pin = make_vault(tmp_path, 2)
    verbose = search(tmp_path, docs, pin, max_results=1)
    assert verbose['schema'] == 'harness.shared-search/v1'
    compact = search(tmp_path, docs, pin, max_results=1, omission_format='manifest-index')
    assert resolve(tmp_path, docs, pin, compact) == verbose['omitted']
    with pytest.raises(ValueError, match='budget'):
        search(tmp_path, docs, pin, omission_format='manifest-index', max_bytes=1)
    with pytest.raises(ValueError, match='omission format'):
        search(tmp_path, docs, pin, omission_format='unknown')


def test_budget_omissions_are_exactly_decodable_and_do_not_open_bodies(tmp_path, monkeypatch):
    docs, pin = make_vault(tmp_path, 5)
    whole = search(tmp_path, docs, pin, omission_format='manifest-index')
    size = len(json.dumps(whole, ensure_ascii=False).encode())
    packet = search(tmp_path, docs, pin, omission_format='manifest-index', max_bytes=size - 1)
    assert len(packet['hits']) < 5
    assert any(reason == 'budget' for _, reason in packet['omitted'])
    original = Path.open
    def no_bodies(path, *args, **kwargs):
        assert path.suffix != '.md', 'resolving a manifest reference must not read source bodies'
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', no_bodies)
    rows = resolve(tmp_path, docs, pin, packet)
    assert len(rows) + len(packet['hits']) == 5
    expected = {d['id']: d['sha256'] for d in docs}
    assert all(row['sha256'] == expected[row['document_id']] for row in rows)


@pytest.mark.parametrize('fault', ['wrong-pin', 'wrong-vault', 'duplicate', 'outside', 'boolean',
                                   'unknown-reason', 'negative', 'too-large', 'hit-duplicate', 'wrong-schema'])
def test_untrusted_omission_references_are_not_authority(tmp_path, fault):
    docs, pin = make_vault(tmp_path, 4)
    packet = search(tmp_path, docs[:3], pin, max_results=1, omission_format='manifest-index')
    packet = copy.deepcopy(packet)
    allowed = docs[:3]
    if fault == 'wrong-pin': packet['manifest_sha256'] = '0' * 64
    elif fault == 'wrong-vault': packet['vault_id'] = 'elsewhere'
    elif fault == 'duplicate': packet['omitted'].append(packet['omitted'][0])
    elif fault == 'outside':
        excluded = packet['omitted'][0][0]
        # Keep the same permitted count: only actual membership can catch this.
        allowed = [d for i, d in enumerate(docs) if i != excluded]
    elif fault == 'boolean': packet['omitted'][0][0] = True
    elif fault == 'unknown-reason': packet['omitted'][0][1] = 'approved'
    elif fault == 'negative': packet['omitted'][0][0] = -1
    elif fault == 'too-large': packet['omitted'][0][0] = 1000
    elif fault == 'hit-duplicate':
        packet['omitted'][0][0] = next(i for i, d in enumerate(docs) if d['id'] == packet['hits'][0]['document_id'])
    else: packet['schema'] = 'harness.shared-search/v1'
    with pytest.raises(ValueError):
        resolve(tmp_path, allowed, pin, packet)


def test_modified_manifest_does_not_resolve_old_indices(tmp_path):
    docs, pin = make_vault(tmp_path, 3)
    packet = search(tmp_path, docs, pin, max_results=1, omission_format='manifest-index')
    path = tmp_path / 'manifest.json'
    body = json.loads(path.read_bytes())
    body['documents'].reverse()
    path.write_text(json.dumps(body))
    with pytest.raises(ValueError):
        resolve(tmp_path, docs, pin, packet)


@pytest.mark.parametrize('backend', ['lexical', 'fts5'])
def test_compact_packing_retains_every_whole_window_that_already_fit(tmp_path, backend):
    docs, _ = make_vault(tmp_path, 10)
    for index, doc in enumerate(sorted(docs, key=lambda d: d['id'])):
        padding = 'x' * (2100 if index < 2 else 20)
        raw = f'id: {doc["id"]}\ntitle: Test note\nquartzledger {padding}\n'.encode()
        (tmp_path / doc['path']).write_bytes(raw)
        doc['sha256'] = hashlib.sha256(raw).hexdigest()
    raw = json.dumps({'schema': 'quant-shared-notes/v1', 'revision': 'packing-v1', 'documents': docs}).encode()
    (tmp_path / 'manifest.json').write_bytes(raw)
    pin = hashlib.sha256(raw).hexdigest()
    compared = 0
    for budget in range(1800, 8193, 256):
        try:
            old = search(tmp_path, docs, pin, backend=backend, max_bytes=budget)
        except ValueError:
            continue
        compact = search(tmp_path, docs, pin, backend=backend, max_bytes=budget,
                         omission_format='manifest-index')
        assert all(hit in compact['hits'] for hit in old['hits']), budget
        assert len(json.dumps(compact, ensure_ascii=False).encode()) <= budget
        compared += 1
    assert compared >= 20


@pytest.mark.parametrize('query', ['quartzledger', 'unmatchedterm'])
def test_v2_header_cannot_make_an_exactly_fitting_v1_packet_overflow(tmp_path, query):
    docs, pin = make_vault(tmp_path, 2)
    args = dict(vault_id='compact-fixture', manifest='manifest.json', manifest_sha256=pin,
                allowed_ids=[d['id'] for d in docs], query=query)
    old = retrieval.search_shared_documents(tmp_path, **args)
    size = len(json.dumps(old, ensure_ascii=False).encode())
    compact = retrieval.search_shared_documents(tmp_path, **args, max_bytes=size,
                                               omission_format='manifest-index')
    assert compact['hits'] == old['hits']
    assert len(json.dumps(compact, ensure_ascii=False).encode()) <= size


def test_fresh_cli_uses_requested_format_without_changing_native_config(tmp_path):
    docs, pin = make_vault(tmp_path, 8)
    root = Path(__file__).resolve().parents[1]
    args = [sys.executable, str(root / 'bin/harness'), 'vault-search', '--vault-root', str(tmp_path),
            '--vault-id', 'compact-fixture', '--manifest-sha256', pin, '--query', 'quartzledger',
            '--omission-format', 'manifest-index']
    for doc in docs:
        args += ['--allow-id', doc['id']]
    run = subprocess.run(args, cwd=root, capture_output=True, text=True, timeout=10,
        env={'PATH': os.defpath, 'HOME': str(tmp_path / 'home'), 'HARNESS_HOME': str(tmp_path / 'hh'),
             'PYTHONPATH': str(root / 'src'), 'PYTHONDONTWRITEBYTECODE': '1'})
    assert run.returncode == 0, run.stderr
    packet = json.loads(run.stdout)
    assert packet['schema'] == 'harness.shared-search/v2'
    assert len(packet['hits']) == 5 and len(resolve(tmp_path, docs, pin, packet)) == 3
    assert not (tmp_path / 'hh').exists()
