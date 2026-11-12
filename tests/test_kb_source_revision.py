"""Timestamp-preserving corrections must not leave warm or cold readers stale."""
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from agent_harness.mcp.kb import KB, fts5_available


@pytest.mark.parametrize('fts', [False, pytest.param(True, marks=pytest.mark.skipif(
    not fts5_available(), reason='SQLite build has no FTS5'))])
@pytest.mark.parametrize('replace', [False, True])
def test_preserved_timestamp_correction_reaches_warm_and_cold_readers(tmp_path, fts, replace):
    docs = tmp_path / 'project/docs'
    docs.mkdir(parents=True)
    page = docs / 'state.md'
    page.write_text('# State\nSource revision: r2\n')
    home = tmp_path / 'store'
    kb = KB(home=home, paths=[docs], fts=fts)
    try:
        assert 'revision: r2' in kb.get('docs/state.md#state')['text']
        before = page.stat()
        if replace:
            updated = docs / 'replacement.tmp'
            updated.write_text('# State\nSource revision: r3\n')
            os.utime(updated, ns=(before.st_atime_ns, before.st_mtime_ns))
            updated.replace(page)
        else:
            page.write_text('# State\nSource revision: r3\n')
            os.utime(page, ns=(before.st_atime_ns, before.st_mtime_ns))
        after = page.stat()
        assert after.st_mtime_ns == before.st_mtime_ns and after.st_size == before.st_size
        assert 'revision: r3' in kb.get('docs/state.md#state')['text']
        assert 'revision: r2' not in kb.get('docs/state.md#state')['text']
        matches = kb.search('revision r3', k=5, min_score=0)
        assert matches and 'revision: r3' in str(matches)
    finally:
        kb.close()
    cold = KB(home=home, paths=[docs], fts=fts)
    try:
        assert 'revision: r3' in cold.get('docs/state.md#state')['text']
    finally:
        cold.close()


def test_old_cache_schema_reindexes_without_erasing_source_or_unrelated_records(tmp_path):
    docs = tmp_path / 'docs'
    docs.mkdir()
    page = docs / 'state.md'
    page.write_text('# State\nCurrent source revision: r3\n')
    home = tmp_path / 'store'
    kb = KB(home=home, paths=[docs], fts=False)
    kb.get('docs/state.md#state')
    database = kb.db_path
    kb.close()
    with sqlite3.connect(database) as connection:
        # A real pre-upgrade table, including an incorrect old cached body.
        connection.execute('DROP TABLE kb_files')
        connection.execute('CREATE TABLE kb_files(path TEXT PRIMARY KEY, rel TEXT, mtime REAL, size INTEGER)')
        st = page.stat()
        connection.execute('INSERT INTO kb_files VALUES(?,?,?,?)',
                           (str(page), 'docs/state.md', st.st_mtime, st.st_size))
        connection.execute("UPDATE kb_sections SET body='Stale cached revision: r2'")
        connection.execute('CREATE TABLE unrelated(value TEXT)')
        connection.execute("INSERT INTO unrelated VALUES('keep me')")
    original = page.read_bytes()
    upgraded = KB(home=home, paths=[docs], fts=False)
    try:
        assert 'revision: r3' in upgraded.get('docs/state.md#state')['text']
        assert 'Stale cached' not in upgraded.get('docs/state.md#state')['text']
        assert upgraded.con.execute('SELECT value FROM unrelated').fetchone()[0] == 'keep me'
        assert page.read_bytes() == original
    finally:
        upgraded.close()


def test_unchanged_sources_keep_the_incremental_cache(tmp_path):
    docs = tmp_path / 'docs'
    docs.mkdir()
    (docs / 'state.md').write_text('# State\nCurrent evidence.\n')
    kb = KB(home=tmp_path / 'store', paths=[docs], fts=False)
    try:
        assert kb.refresh()['changed'] == 1
        assert 'Current evidence.' in kb.get('docs/state.md#state')['text']
        assert kb.refresh()['changed'] == 0
    finally:
        kb.close()
    cold = KB(home=tmp_path / 'store', paths=[docs], fts=False)
    try:
        assert cold.refresh()['changed'] == 0
        assert 'Current evidence.' in cold.get('docs/state.md#state')['text']
    finally:
        cold.close()


def test_simultaneous_cold_clients_upgrade_legacy_schema(tmp_path):
    home = tmp_path / 'store'
    home.mkdir()
    database = home / 'index.sqlite'
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE kb_files(path TEXT PRIMARY KEY, rel TEXT, mtime REAL, size INTEGER)')
        connection.execute('CREATE TABLE unrelated(value TEXT)')
        connection.execute("INSERT INTO unrelated VALUES('keep me')")
    barrier = Barrier(4)

    def open_client(_):
        barrier.wait(timeout=10)
        kb = KB(home=home, paths=[], fts=False)
        try:
            assert kb.con.execute('SELECT value FROM unrelated').fetchone()[0] == 'keep me'
        finally:
            kb.close()

    with ThreadPoolExecutor(max_workers=4) as workers:
        list(workers.map(open_client, range(4)))
    with sqlite3.connect(database) as connection:
        columns = [row[1] for row in connection.execute('PRAGMA table_info(kb_files)')]
        assert columns.count('stat_token') == 1
