"""Cold stdio clients on synthetic copies: retrieval evidence, not model-memory proof."""
import json
import os
import sqlite3

import pytest

from . import test_memory_transport as transport
from .test_memory_transport import exchange
from agent_harness.source_inventory import default_roots, inventory_sources

lab = transport.lab


def text(response):
    assert response['isError'] is False, response
    return response['content'][0]['text']


def test_cold_clients_find_scoped_history_without_claiming_complete_migration(lab):
    home, projects = lab
    alpha, bravo = projects[1:]
    secret = 'ghp_' + 'X'*36  # secret-scan: allow
    a = home/'.claude/projects/alpha/alpha.jsonl'
    b = home/'.codex/sessions/2026/01/rollout-bravo.jsonl'
    archived = home/'.codex/archived_sessions/rollout-hidden.jsonl'
    for p in (a, b, archived): p.parent.mkdir(parents=True, exist_ok=True)
    a.write_text(json.dumps({'type':'user','timestamp':'2026-01-01T00:00:00Z','cwd':str(alpha),
                            'message':{'content':'Alpha cutoff Tuesday. Access token '+secret}})+'\n')
    b.write_text(json.dumps({'type':'session_meta','payload':{'id':'bravo-session','cwd':str(bravo)}})+'\n'+
                 json.dumps({'type':'response_item','timestamp':'2026-01-01T00:00:00Z',
                             'payload':{'type':'message','role':'assistant','content':[
                                 {'type':'output_text','text':'Bravo cutoff Friday.'}]}})+'\n')
    archived.write_text(b.read_text().replace('Friday','Sunday'))
    originals = {p: p.read_bytes() for p in (a, b, archived)}
    db = home/'harness/index.sqlite'
    before = inventory_sources(default_roots(home), db)
    assert before['coverage'] == {'UNINDEXED':2,'READER_UNSUPPORTED':1}
    first = text(exchange(lab, [('session_search', {'query':'cutoff','project':str(alpha)})])[0])
    assert 'Tuesday' in first and 'Friday' not in first and secret not in first
    second = text(exchange(lab, [('session_search', {'query':'cutoff','project':str(bravo)})])[0])
    assert 'Friday' in second and 'Tuesday' not in second and 'Sunday' not in second
    after = inventory_sources(default_roots(home), db)
    assert after['coverage'] == {'BYTE_OFFSET_COVERED':2,'READER_UNSUPPORTED':1}
    assert after['complete_migration'] is False and after['semantic_extraction']=='NOT_EVALUATED'
    with sqlite3.connect(db) as con:
        cached = '\n'.join(r[0] for r in con.execute('SELECT text FROM sess_msgs'))
    assert secret not in cached
    assert {p: p.read_bytes() for p in originals} == originals


def test_cold_kb_client_gets_the_correct_same_named_page_and_new_revision(lab, monkeypatch):
    home, projects = lab
    alpha, bravo = projects[1:]
    for project, policy in ((alpha,'SOURCE-A cutoff Tuesday'),(bravo,'SOURCE-B cutoff Friday')):
        (project/'docs').mkdir()
        (project/'docs/policy.md').write_text('# Policy\n'+policy+'\n')
    def read(project):
        monkeypatch.setenv('HARNESS_KB_PATHS', str(project/'docs'))
        return text(exchange(lab, [('kb_get', {'id':'docs/policy.md#policy'})])[0])
    assert 'SOURCE-A' in read(alpha)
    assert 'SOURCE-B' in read(bravo)
    current = alpha/'docs/policy.md'
    previous = current.read_bytes()
    (home/'original-policy.md').write_bytes(previous)
    old = current.stat()
    current.write_text('# Policy\nSOURCE-A cutoff Monday\n')
    os.utime(current, (old.st_atime, old.st_mtime+1))
    recovered = read(alpha)
    assert 'Monday' in recovered and 'Tuesday' not in recovered and 'SOURCE-B' not in recovered
    assert (home/'original-policy.md').read_bytes() == previous


def test_revoked_source_read_permission_cannot_be_bypassed_by_the_cache(lab, monkeypatch):
    _, projects = lab
    docs = projects[1]/'docs'; docs.mkdir()
    source = docs/'policy.md'
    source.write_text('# Policy\nREVOKED-SOURCE-CANARY\n')
    monkeypatch.setenv('HARNESS_KB_PATHS', str(docs))
    assert 'REVOKED-SOURCE-CANARY' in text(exchange(lab, [('kb_get', {'id':'docs/policy.md#policy'})])[0])
    source.chmod(0)
    try:
        if os.access(source, os.R_OK):
            pytest.skip('root reads permission-revoked files')
        result = exchange(lab, [('kb_get', {'id':'docs/policy.md#policy'})])[0]
        assert result['isError'] is True
        assert 'REVOKED-SOURCE-CANARY' not in json.dumps(result)
    finally:
        source.chmod(0o600)
