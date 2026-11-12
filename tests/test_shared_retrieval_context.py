"""An excerpt must disclose its document-local omissions without widening scope."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_harness.vault_retrieval import search_shared_documents
from agent_harness.vault_sources import read_shared_document

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def vault(tmp_path):
    content = ('id: deployment-note\ntitle: Quartzledger policy\n'
               'Checks must pass before deployment.\n'
               'Ticket-owner approval is also required.\n'
               'UNRELATED_APPENDIX_CANARY\n')
    raw = content.encode()
    (tmp_path / 'note.md').write_bytes(raw)
    row = {'id': 'deployment-note', 'title': 'Quartzledger policy', 'path': 'note.md',
           'sha256': hashlib.sha256(raw).hexdigest(), 'document_type': 'method_note',
           'rights': {'redistribution': 'public', 'license': 'CC0-1.0', 'basis': 'Owned synthetic fixture.'},
           'source_refs': [{'uri': 'urn:context:note', 'kind': 'fixture', 'revision': 'v1'}]}
    manifest = json.dumps({'schema': 'quant-shared-notes/v1', 'revision': 'fixture-v1',
                           'documents': [row]}).encode()
    (tmp_path / 'manifest.json').write_bytes(manifest)
    return tmp_path, hashlib.sha256(manifest).hexdigest(), row, content


def search(vault, backend='lexical', **kwargs):
    root, pin, _, _ = vault
    return search_shared_documents(root, vault_id='context-fixture', manifest='manifest.json',
        manifest_sha256=pin, allowed_ids=['deployment-note'], backend=backend,
        query=kwargs.pop('query', 'checks'), **kwargs)


@pytest.mark.parametrize('backend', ['lexical', 'fts5'])
def test_omitted_condition_is_visible_as_missing_context_and_can_be_read(vault, backend):
    result = search(vault, backend)
    hit = result['hits'][0]
    assert hit['text'] == 'Checks must pass before deployment.\n'
    assert hit['source_window'] == {'document_lines': 5, 'omitted_before': 2, 'omitted_after': 2}
    assert hit['citation']['start_line'] == hit['citation']['end_line'] == 3
    assert 'Ticket-owner' not in json.dumps(result)
    root, pin, row, original = vault
    next_part = read_shared_document(root, vault_id='context-fixture', manifest='manifest.json',
        manifest_sha256=pin, document_id=hit['document_id'], start_line=4, end_line=4)
    assert next_part['content'] == 'Ticket-owner approval is also required.\n'
    assert next_part['source_sha256'] == hit['citation']['sha256'] == row['sha256']
    assert 'UNRELATED_APPENDIX_CANARY' not in json.dumps(next_part)
    assert (root / 'note.md').read_text() == original


@pytest.mark.parametrize('backend', ['lexical', 'fts5'])
@pytest.mark.parametrize('radius,expected', [(1, (1, 1)), (8, (0, 0))])
def test_counts_follow_requested_bounds_not_a_claim_of_answer_completeness(vault, backend, radius, expected):
    hit = search(vault, backend, context_lines=radius)['hits'][0]
    assert hit['source_window'] == {'document_lines': 5, 'omitted_before': expected[0],
                                    'omitted_after': expected[1]}
    assert hit['source_window']['document_lines'] == (hit['source_window']['omitted_before']
        + hit['citation']['end_line'] - hit['citation']['start_line'] + 1 + hit['source_window']['omitted_after'])


@pytest.mark.parametrize('backend', ['lexical', 'fts5'])
@pytest.mark.parametrize('query,line', [('deployment-note', 1), ('Quartzledger', 2)])
def test_exact_identity_and_title_header_remain_valid_discovery_hits(vault, backend, query, line):
    hit = search(vault, backend, query=query)['hits'][0]
    assert hit['citation']['start_line'] == hit['citation']['end_line'] == line
    assert hit['source_window'] == {'document_lines': 5, 'omitted_before': line - 1,
                                    'omitted_after': 5 - line}


def test_new_metadata_is_inside_existing_byte_budget_not_silently_clipped(vault):
    whole = search(vault)
    size = len(json.dumps(whole, ensure_ascii=False).encode())
    assert search(vault, max_bytes=size) == whole
    omitted = search(vault, max_bytes=size - 1)
    assert omitted['hits'] == []
    assert omitted['omitted'][0]['reason'] == 'budget'
    assert len(json.dumps(omitted, ensure_ascii=False).encode()) <= size - 1


def test_lf_line_counts_preserve_crlf_and_unicode(vault):
    root, _, row, _ = vault
    raw = 'id: deployment-note\r\ntitle: Quartzledger policy\r\n檢查 checks\r\n'.encode()
    (root / 'note.md').write_bytes(raw)
    row['sha256'] = hashlib.sha256(raw).hexdigest()
    body = json.dumps({'schema': 'quant-shared-notes/v1', 'revision': 'fixture-v2', 'documents': [row]}).encode()
    (root / 'manifest.json').write_bytes(body)
    updated = root, hashlib.sha256(body).hexdigest(), row, raw.decode()
    hit = search(updated)['hits'][0]
    assert hit['source_window'] == {'document_lines': 3, 'omitted_before': 2, 'omitted_after': 0}
    assert hit['text'] == '檢查 checks\r\n'


def test_fresh_cli_exposes_the_same_context_counts(vault, tmp_path):
    root, pin, _, _ = vault
    result = subprocess.run([sys.executable, str(ROOT / 'bin/harness'), 'vault-search',
        '--vault-root', str(root), '--vault-id', 'context-fixture', '--manifest', 'manifest.json',
        '--manifest-sha256', pin, '--allow-id', 'deployment-note', '--query', 'checks'],
        env={'PATH': os.defpath, 'HOME': str(tmp_path / 'home'), 'HARNESS_HOME': str(tmp_path / 'hh'),
             'PYTHONPATH': str(ROOT / 'src'), 'PYTHONDONTWRITEBYTECODE': '1'},
        capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['hits'][0]['source_window'] == {
        'document_lines': 5, 'omitted_before': 2, 'omitted_after': 2}
    assert not (tmp_path / 'hh').exists()
