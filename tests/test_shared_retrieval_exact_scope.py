"""Out-of-scope catalogue identities must not suppress eligible source text."""
import hashlib
import json

import pytest

from agent_harness.vault_retrieval import search_shared_documents


def manifest(root, rows):
    raw = json.dumps({'schema': 'quant-shared-notes/v1', 'revision': 'fixture-v1', 'documents': rows}).encode()
    (root / 'manifest.json').write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def document(root, identity, body):
    raw = f'id: {identity}\ntitle: Selected note\n{body}\n'.encode()
    name = identity + '.md'; (root / name).write_bytes(raw)
    return {'id': identity, 'title': 'Selected note', 'path': name,
            'sha256': hashlib.sha256(raw).hexdigest(), 'document_type': 'method_note',
            'rights': {'redistribution': 'public', 'license': 'CC0-1.0', 'basis': 'Owned synthetic fixture.'},
            'source_refs': [{'uri': 'urn:selection:' + identity, 'kind': 'fixture', 'revision': 'v1'}]}


def search(root, pin, identity, query, backend):
    return search_shared_documents(root, vault_id='fixture', manifest='manifest.json',
        manifest_sha256=pin, allowed_ids=[identity], query=query, backend=backend)


@pytest.mark.parametrize('backend', ['lexical', 'fts5'])
@pytest.mark.parametrize('query', ['quartzterm', ' quartzterm '])
def test_excluded_id_metadata_cannot_shadow_allowed_text(tmp_path, backend, query):
    approved = document(tmp_path, 'allowed-note', 'quartzterm remains supported by the eligible source.')
    before = search(tmp_path, manifest(tmp_path, [approved]), 'allowed-note', query, backend)
    assert [h['document_id'] for h in before['hits']] == ['allowed-note']
    outside = document(tmp_path, 'quartzterm', 'EXCLUDED_ID_BODY_CANARY')
    # Stale and nonpublic excluded data remain unselected; no fallback reads it.
    outside['rights']['redistribution'] = 'private'
    (tmp_path / outside['path']).write_text('Stale EXCLUDED_ID_BODY_CANARY\n')
    after = search(tmp_path, manifest(tmp_path, [approved, outside]), 'allowed-note', query, backend)
    assert after['hits'] == before['hits']
    assert after['status'] == 'matches' and after['omitted'] == []
    assert 'EXCLUDED_ID_BODY_CANARY' not in json.dumps(after)
    assert all(hit['document_id'] != outside['id'] for hit in after['hits'])


@pytest.mark.parametrize('backend', ['lexical', 'fts5'])
def test_selected_opaque_exact_id_still_works_when_lexical_terms_are_empty(tmp_path, backend):
    approved = document(tmp_path, 'a', 'Selected opaque ID remains resolvable.')
    pin = manifest(tmp_path, [approved])
    hit = search(tmp_path, pin, 'a', 'a', backend)
    assert [h['document_id'] for h in hit['hits']] == ['a']
    assert hit['hits'][0]['score'] == 1.0
    miss = search(tmp_path, pin, 'a', 'unrelated-quasar', backend)
    assert miss['status'] == 'no_match' and miss['hits'] == miss['omitted'] == []
