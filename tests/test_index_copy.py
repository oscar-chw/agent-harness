import hashlib
import sqlite3
from contextlib import closing

import pytest

import agent_harness.index_copy as index_copy
from agent_harness.index_copy import compact_copy


def make_fragmented_index(path):
    with closing(sqlite3.connect(path)) as db:
        with db:
            db.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, body TEXT NOT NULL)")
            db.execute("CREATE VIRTUAL TABLE documents_fts USING fts5(body, content='documents', content_rowid='id')")
            db.execute("CREATE TRIGGER documents_ai AFTER INSERT ON documents BEGIN INSERT INTO documents_fts(rowid, body) VALUES (new.id, new.body); END")
            db.execute("CREATE TRIGGER documents_ad AFTER DELETE ON documents BEGIN INSERT INTO documents_fts(documents_fts, rowid, body) VALUES ('delete', old.id, old.body); END")
            db.executemany("INSERT INTO documents(id, body) VALUES (?, ?)", ((i, f"entry {i} unique token") for i in range(1, 801)))
            db.execute("DELETE FROM documents WHERE id % 2 = 0")
            db.execute("INSERT INTO documents(id, body) VALUES (9001, 'high rowid sentinel')")
            db.commit()


def rows(path, query):
    with closing(sqlite3.connect(path)) as db:
        return db.execute(query).fetchall()


def test_compacts_disposable_copy_preserving_rows_rowids_and_fts(tmp_path):
    source, destination = tmp_path / "source.sqlite", tmp_path / "compact.sqlite"
    make_fragmented_index(source)
    original = source.read_bytes()

    result = compact_copy(source, destination, offline=True)

    assert source.read_bytes() == original
    assert destination.stat().st_size < len(original)
    assert result["source_bytes"] == len(original)
    assert result["destination_bytes"] == destination.stat().st_size
    assert result["source_sha256"] == hashlib.sha256(original).hexdigest()
    assert rows(source, "SELECT id, body FROM documents ORDER BY id") == rows(destination, "SELECT id, body FROM documents ORDER BY id")
    assert rows(source, "SELECT rowid, body FROM documents_fts ORDER BY rowid") == rows(destination, "SELECT rowid, body FROM documents_fts ORDER BY rowid")
    assert rows(destination, "SELECT rowid FROM documents_fts WHERE documents_fts MATCH 'sentinel'") == [(9001,)]
    assert result["row_counts"]["documents"] == 401
    assert result["integrity_check"] == "ok"


def test_compacts_uncheckpointed_wal_into_closed_self_contained_database(tmp_path):
    source, destination = tmp_path / "wal-source.sqlite", tmp_path / "wal-compact.sqlite"
    writer = sqlite3.connect(source, isolation_level=None)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("PRAGMA wal_autocheckpoint=0")
    writer.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, body TEXT NOT NULL)")
    writer.execute("CREATE VIRTUAL TABLE documents_fts USING fts5(body, content='documents', content_rowid='id')")
    writer.execute("CREATE TRIGGER documents_ai AFTER INSERT ON documents BEGIN INSERT INTO documents_fts(rowid, body) VALUES (new.id, new.body); END")
    writer.executemany("INSERT INTO documents(id, body) VALUES (?, ?)", ((i, f"wal row {i} searchable") for i in range(1, 120)))
    wal = tmp_path / "wal-source.sqlite-wal"
    assert wal.stat().st_size > 32
    source_before, wal_before = source.read_bytes(), wal.read_bytes()

    result = compact_copy(source, destination, offline=True)

    assert source.read_bytes() == source_before
    assert wal.read_bytes() == wal_before
    assert result["wal_bytes"] == len(wal_before)
    assert result["wal_sha256"] == hashlib.sha256(wal_before).hexdigest()
    writer.close()
    assert not (tmp_path / "wal-compact.sqlite-wal").exists()
    assert not (tmp_path / "wal-compact.sqlite-shm").exists()
    with closing(sqlite3.connect(destination)) as verify:
        assert verify.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert verify.execute("SELECT count(*) FROM documents").fetchone() == (119,)
        assert verify.execute("SELECT rowid FROM documents_fts WHERE documents_fts MATCH 'searchable'").fetchall() == [(i,) for i in range(1, 120)]


def test_requires_explicit_offline_disposable_copy(tmp_path):
    source = tmp_path / "source.sqlite"
    make_fragmented_index(source)
    with pytest.raises(ValueError, match="offline"):
        compact_copy(source, tmp_path / "out.sqlite")


def test_rejects_missing_corrupt_symlink_and_existing_destination(tmp_path):
    missing = tmp_path / "missing.sqlite"
    with pytest.raises((OSError, ValueError)):
        compact_copy(missing, tmp_path / "missing-out.sqlite", offline=True)

    corrupt = tmp_path / "corrupt.sqlite"
    corrupt.write_bytes(b"not sqlite")
    with pytest.raises((OSError, ValueError, sqlite3.Error)):
        compact_copy(corrupt, tmp_path / "corrupt-out.sqlite", offline=True)
    assert not (tmp_path / "corrupt-out.sqlite").exists()

    source = tmp_path / "source.sqlite"
    make_fragmented_index(source)
    alias = tmp_path / "alias.sqlite"
    alias.symlink_to(source)
    with pytest.raises(ValueError, match="symlink"):
        compact_copy(alias, tmp_path / "alias-out.sqlite", offline=True)

    destination = tmp_path / "existing.sqlite"
    destination.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        compact_copy(source, destination, offline=True)
    assert destination.read_bytes() == b"keep"


def test_rejects_source_and_source_plus_wal_over_budget(tmp_path):
    source = tmp_path / "source.sqlite"
    make_fragmented_index(source)
    with pytest.raises(ValueError, match="byte limit"):
        compact_copy(source, tmp_path / "too-small.sqlite", offline=True, max_source_bytes=1)
    assert not (tmp_path / "too-small.sqlite").exists()

    wal_source = tmp_path / "wal.sqlite"
    with closing(sqlite3.connect(wal_source)) as db:
        with db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE t (value TEXT)")
            db.execute("INSERT INTO t VALUES ('wal payload')")
    wal = tmp_path / "wal.sqlite-wal"
    wal.write_bytes(b"x" * 256)
    with pytest.raises(ValueError, match="byte limit"):
        compact_copy(wal_source, tmp_path / "wal-out.sqlite", offline=True, max_source_bytes=wal_source.stat().st_size + 10)
    assert not (tmp_path / "wal-out.sqlite").exists()


def test_rejects_nonpositive_time_budget(tmp_path):
    source = tmp_path / "source.sqlite"
    make_fragmented_index(source)
    with pytest.raises(ValueError, match="time limit"):
        compact_copy(source, tmp_path / "timeout.sqlite", offline=True, max_seconds=0)
    assert not (tmp_path / "timeout.sqlite").exists()
    with pytest.raises(ValueError, match="10 seconds"):
        compact_copy(source, tmp_path / "unbounded-time.sqlite", offline=True, max_seconds=10.01)
    with pytest.raises(ValueError, match="32 MiB"):
        compact_copy(source, tmp_path / "unbounded-size.sqlite", offline=True,
                     max_source_bytes=32 * 1024 * 1024 + 1)


def test_rejects_source_change_before_publication(tmp_path, monkeypatch):
    source, destination = tmp_path / "source.sqlite", tmp_path / "changed.sqlite"
    make_fragmented_index(source)
    original_pin = index_copy._source_pin
    calls = 0

    def change_before_recheck(path, limit, check_deadline):
        nonlocal calls
        calls += 1
        if calls == 2:
            path.write_bytes(path.read_bytes() + b"changed")
        return original_pin(path, limit, check_deadline)

    monkeypatch.setattr(index_copy, "_source_pin", change_before_recheck)
    with pytest.raises(ValueError, match="changed during compaction"):
        compact_copy(source, destination, offline=True)
    assert not destination.exists()


def test_deadline_interrupts_streaming_fingerprint(tmp_path, monkeypatch):
    source, destination = tmp_path / "source.sqlite", tmp_path / "timeout.sqlite"
    make_fragmented_index(source)

    class AdvancingClock:
        current = 0.0

        def monotonic(self):
            self.current += 0.1
            return self.current

    monkeypatch.setattr(index_copy, "time", AdvancingClock())
    with pytest.raises(TimeoutError, match="time limit"):
        compact_copy(source, destination, offline=True)
    assert not destination.exists()
