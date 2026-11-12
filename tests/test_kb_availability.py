"""Unavailable sources are not complete misses or permission to reuse cached text."""
import json
import os
import builtins

import pytest

from agent_harness.mcp import kb as kbmod
from agent_harness.mcp.kb import KB
from agent_harness.mcp.server import Server


def rpc(server, name, arguments):
    response = server.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                              'params': {'name': name, 'arguments': arguments}})
    return response['result']


@pytest.mark.parametrize('fts', [False, True])
def test_partial_search_keeps_usable_hits_and_makes_revocation_visible(tmp_path, fts):
    docs = tmp_path / 'docs'
    docs.mkdir()
    allowed, revoked = docs / 'safe.md', docs / 'private.md'
    allowed.write_text('# Guide\nSafe rollback evidence.\n')
    revoked.write_text('# Guide\nREVOKED_ONLY rollback evidence.\n')
    server = Server(home=tmp_path / 'cache', kb_paths=[docs], fts=fts)
    try:
        warm = rpc(server, 'kb_search', {'query': 'rollback evidence'})
        assert 'REVOKED_ONLY' in json.dumps(warm)
        revoked.chmod(0)
        if os.access(revoked, os.R_OK):
            pytest.skip('effective user can still read permission-revoked file')
        partial = rpc(server, 'kb_search', {'query': 'rollback evidence'})
        text = '\n'.join(block['text'] for block in partial['content'])
        assert partial['isError'] is False  # usable work proceeds
        assert isinstance(json.loads(partial['content'][0]['text']), list)  # legacy list consumers
        assert 'Safe rollback evidence' in text
        assert 'REVOKED_ONLY' not in text
        assert 'private.md' not in text
        assert 'partial' in text.lower() and 'read_denied' in text
        assert 'unenumerated' not in text.lower()  # all selected directories were enumerable
        miss = rpc(server, 'kb_search', {'query': 'REVOKED_ONLY'})
        assert 'partial' in '\n'.join(block['text'] for block in miss['content']).lower()
        assert 'REVOKED_ONLY' not in json.dumps(miss)
        assert server.kb.availability == {'unavailable_sources': 1, 'reasons': {'read_denied': 1}, 'discovery_errors': 0}
        exact = rpc(server, 'kb_get', {'id': 'docs/private.md#guide'})
        assert exact['isError'] is True and 'unavailable' in exact['content'][0]['text']
        assert 'REVOKED_ONLY' not in json.dumps(exact)
        revoked.chmod(0o600)
        restored = rpc(server, 'kb_search', {'query': 'rollback evidence'})
        assert 'REVOKED_ONLY' in json.dumps(restored)
        assert 'partial' not in restored['content'][0]['text'].lower()
        assert server.kb.availability == {'unavailable_sources': 0, 'reasons': {}, 'discovery_errors': 0}
    finally:
        revoked.chmod(0o600)
        server.kb.close()


def test_oversize_replacement_cannot_be_a_complete_miss_or_return_old_cache(tmp_path, monkeypatch):
    docs = tmp_path / 'docs'
    docs.mkdir()
    page = docs / 'guide.md'
    page.write_text('# Guide\nOLD_BODY\n')
    server = Server(home=tmp_path / 'cache', kb_paths=[docs], fts=False)
    try:
        assert 'OLD_BODY' in json.dumps(rpc(server, 'kb_get', {'id': 'docs/guide.md#guide'}))
        monkeypatch.setattr(kbmod, 'MAX_FILE_BYTES', 32)
        page.write_text('# Guide\n' + 'new body ' * 10)
        result = rpc(server, 'kb_search', {'query': 'OLD_BODY'})
        assert 'OLD_BODY' not in json.dumps(result)
        notice = '\n'.join(block['text'] for block in result['content'])
        assert 'partial' in notice.lower() and 'size_limit' in notice
        page.write_text('# Guide\nNEW_BODY\n')
        assert 'NEW_BODY' in json.dumps(rpc(server, 'kb_get', {'id': 'docs/guide.md#guide'}))
        assert server.kb.availability['unavailable_sources'] == 0
    finally:
        server.kb.close()


def test_foreign_cached_permission_failure_does_not_change_own_status(tmp_path):
    own, foreign = tmp_path / 'own', tmp_path / 'foreign'
    own.mkdir()
    foreign.mkdir()
    page = foreign / 'hidden.md'
    page.write_text('# Hidden\nFOREIGN_ONLY\n')
    (own / 'guide.md').write_text('# Guide\nOwn evidence.\n')
    outside = KB(home=tmp_path / 'cache', paths=[foreign], fts=False)
    outside.search('FOREIGN_ONLY')
    outside.close()
    page.chmod(0)
    reader = Server(home=tmp_path / 'cache', kb_paths=[own], fts=False)
    try:
        result = rpc(reader, 'kb_search', {'query': 'missing-constellation'})
        assert result['isError'] is False
        assert json.loads(result['content'][0]['text']) == []
        assert reader.kb.availability == {'unavailable_sources': 0, 'reasons': {}, 'discovery_errors': 0}
    finally:
        page.chmod(0o600)
        reader.kb.close()


def test_unenumerable_subtree_is_unknown_extent_not_empty_or_cache_purge(tmp_path):
    docs = tmp_path / 'docs'
    blocked = docs / 'blocked'
    blocked.mkdir(parents=True)
    hidden = blocked / 'hidden.md'
    hidden.write_text('# Guide\nHIDDEN_ONLY rollback.\n')
    (docs / 'safe.md').write_text('# Guide\nSafe rollback.\n')
    reader = Server(home=tmp_path / 'cache', kb_paths=[docs], fts=False)
    try:
        assert 'HIDDEN_ONLY' in json.dumps(rpc(reader, 'kb_search', {'query': 'rollback'}))
        blocked.chmod(0)
        if os.access(blocked, os.R_OK | os.X_OK):
            pytest.skip('effective user can still traverse revoked directory')
        partial = rpc(reader, 'kb_search', {'query': 'rollback'})
        text = '\n'.join(block['text'] for block in partial['content'])
        assert 'Safe rollback' in text and 'HIDDEN_ONLY' not in text
        assert 'partial' in text.lower() and 'unknown' in text.lower()
        assert reader.kb.availability['discovery_errors'] == 1
        assert reader.kb.availability['unavailable_sources'] == 0  # known files, not unenumerated extent
        cached = reader.kb.con.execute('SELECT body FROM kb_sections WHERE path=?', (str(hidden),)).fetchone()
        assert cached is not None and 'HIDDEN_ONLY' in cached['body']
        unresolved = rpc(reader, 'kb_get', {'id': 'docs/blocked/hidden.md#guide'})
        assert unresolved['isError'] is True
        assert 'unknown' in unresolved['content'][0]['text'].lower()
        assert 'HIDDEN_ONLY' not in json.dumps(unresolved)
    finally:
        blocked.chmod(0o700)
        reader.kb.close()


def test_distinct_unavailable_files_with_same_virtual_page_are_counted(tmp_path):
    roots = [tmp_path / name / 'docs' for name in ('a', 'b')]
    for root in roots:
        root.mkdir(parents=True)
        (root / 'guide.md').write_text('# Guide\nExcluded body.\n')
    reader = Server(home=tmp_path / 'cache', kb_paths=roots, fts=False)
    try:
        for root in roots:
            (root / 'guide.md').chmod(0)
        if any(os.access(root / 'guide.md', os.R_OK) for root in roots):
            pytest.skip('effective user can read revoked files')
        result = rpc(reader, 'kb_search', {'query': 'missing-constellation'})
        assert json.loads(result['content'][0]['text']) == []
        assert reader.kb.availability['unavailable_sources'] == 2
        assert reader.kb.availability['reasons'] == {'read_denied': 2}
    finally:
        for root in roots:
            (root / 'guide.md').chmod(0o600)
        reader.kb.close()


def test_failed_open_is_visible_and_retryable_without_another_source_edit(tmp_path, monkeypatch):
    docs = tmp_path / 'docs'
    docs.mkdir()
    page = docs / 'guide.md'
    page.write_text('# Guide\nOLD_BODY\n')
    reader = Server(home=tmp_path / 'cache', kb_paths=[docs], fts=False)
    original_open = builtins.open
    try:
        rpc(reader, 'kb_get', {'id': 'docs/guide.md#guide'})
        page.write_text('# Guide\nNEW_BODY\n')

        def failed_open(path, *args, **kwargs):
            if str(path) == str(page):
                raise OSError('simulated transient read failure')
            return original_open(path, *args, **kwargs)

        with monkeypatch.context() as scoped:
            scoped.setattr(builtins, 'open', failed_open)
            failed = rpc(reader, 'kb_search', {'query': 'OLD_BODY'})
            assert 'OLD_BODY' not in json.dumps(failed)
            assert 'read_failed' in json.dumps(failed)
            assert reader.kb.con.execute('SELECT body FROM kb_sections').fetchone() is not None
        recovered = rpc(reader, 'kb_get', {'id': 'docs/guide.md#guide'})
        assert 'NEW_BODY' in json.dumps(recovered)
        assert reader.kb.availability['unavailable_sources'] == 0
    finally:
        reader.kb.close()


def test_growth_after_stat_has_a_bounded_read_and_explicit_exclusion(tmp_path, monkeypatch):
    docs = tmp_path / 'docs'
    docs.mkdir()
    page = docs / 'guide.md'
    page.write_text('# Guide\nshort\n')
    reader = Server(home=tmp_path / 'cache', kb_paths=[docs], fts=False)
    original_open = builtins.open
    sizes = []

    class ReadProbe:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def fileno(self):
            return self.stream.fileno()

        def read(self, size=-1):
            sizes.append(size)
            return self.stream.read(size)

    def growing_open(path, mode='r', *args, **kwargs):
        if str(path) == str(page) and mode == 'rb':
            with original_open(page, 'ab') as stream:
                stream.write(b'growth ' * 20)
            return ReadProbe(original_open(path, mode, *args, **kwargs))
        return original_open(path, mode, *args, **kwargs)

    try:
        monkeypatch.setattr(kbmod, 'MAX_FILE_BYTES', 32)
        monkeypatch.setattr(builtins, 'open', growing_open)
        result = rpc(reader, 'kb_search', {'query': 'short'})
        assert sizes == [33]
        assert 'size_limit' in json.dumps(result)
        assert json.loads(result['content'][0]['text']) == []
    finally:
        reader.kb.close()
