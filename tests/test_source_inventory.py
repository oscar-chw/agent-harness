"""Metadata coverage is not semantic migration; originals must never be edited."""
import builtins
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def api():
    from agent_harness.source_inventory import inventory_sources
    return inventory_sources


def source(root, name, text='{"type":"user"}\n'):
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    os.utime(p, (1700000000, 1700000000))
    return p


def index(path, rows):
    with sqlite3.connect(path) as con:
        con.execute('CREATE TABLE sess_files(path TEXT PRIMARY KEY, offset INTEGER, size INTEGER, mtime REAL, dropped INTEGER)')
        con.executemany('INSERT INTO sess_files VALUES (?,?,?,?,?)', rows)


def spec(root, kind='codex', supported=True):
    return {'kind': kind, 'path': root, 'reader_supported': supported}


def test_denominator_is_source_files_not_index_rows_and_offsets_are_not_extraction(tmp_path):
    root = tmp_path / 'sessions'
    files = [source(root, f'rollout-{i}.jsonl', 'NOT VALID JSON\n') for i in range(6)]
    n = files[0].stat().st_size
    db = tmp_path / 'index.sqlite'
    index(db, [(str(files[0]), n, n, 1700000000, 0),
               (str(files[1]), 2, n, 1700000000, 0),
               (str(files[2]), n, n, 1700000000, 1),
               (str(files[3]), n, n, 1699999999, 0),
               (str(files[4]), n+1, n, 1700000000, 0),
               ('INDEX-ONLY-PRIVATE-PATH', 10, 10, 1, 0)])
    before = db.read_bytes()
    result = api()([spec(root)], db)
    assert result['scan_status'] == 'COMPLETE'
    assert result['eligible_files'] == 6
    assert result['eligible_bytes'] == 6*n
    assert result['coverage'] == {'BYTE_OFFSET_COVERED': 1, 'PARTIAL': 1, 'EVICTED': 1,
                                   'STALE': 1, 'INVALID_OFFSET': 1, 'UNINDEXED': 1}
    assert result['indexed_paths_not_observed'] == 1
    assert result['complete_migration'] is False
    assert result['semantic_extraction'] == 'NOT_EVALUATED'
    assert db.read_bytes() == before
    assert all(p.read_text() == 'NOT VALID JSON\n' for p in files)
    assert 'PRIVATE' not in json.dumps(result)
    assert str(tmp_path) not in json.dumps(result)


def test_claude_children_symlinks_and_unrecognized_names_are_explicit(tmp_path):
    root = tmp_path / 'claude'
    source(root, 'project/session.jsonl')
    source(root, 'project/subagents/child.jsonl')
    source(root, 'project/notes.md')
    other = source(tmp_path, 'elsewhere/private.jsonl')
    (root / 'project/link.jsonl').symlink_to(other)
    result = api()([spec(root, 'claude-code')], tmp_path / 'absent.sqlite')
    assert result['eligible_files'] == 1
    assert result['excluded']['symlink'] == 1
    assert result['excluded']['non_transcript'] == 1
    assert result['excluded']['claude_child_subtree'] == 1
    assert result['excluded_descendant_count'] == 'UNKNOWN'
    assert result['scan_status'] == 'COMPLETE'
    assert not (tmp_path / 'absent.sqlite').exists()


def test_archive_candidates_are_not_falsely_called_native_imports(tmp_path):
    root = tmp_path / 'archive'
    source(root, 'old-thread.jsonl')
    result = api()([spec(root, 'archive-jsonl', False)], tmp_path / 'absent.sqlite')
    assert result['eligible_files'] == 1
    assert result['coverage'] == {'READER_UNSUPPORTED': 1}
    assert result['content_deduplication'] == 'NOT_RUN'
    assert result['complete_migration'] is False


def test_body_is_not_read_and_duplicate_root_does_not_double_denominator(tmp_path, monkeypatch):
    root = tmp_path / 'sessions'
    p = source(root, 'rollout-canary.jsonl', 'PRIVATE-BODY-CANARY\n')
    original = builtins.open
    def no_body(file, *args, **kwargs):
        assert Path(file) != p, 'inventory must not read source bodies'
        return original(file, *args, **kwargs)
    monkeypatch.setattr(builtins, 'open', no_body)
    result = api()([spec(root), spec(root)], tmp_path / 'absent.sqlite')
    assert result['eligible_files'] == 1
    assert result['duplicate_observations'] == 1
    assert 'CANARY' not in json.dumps(result)


def test_limit_reports_incomplete_and_never_invents_a_full_total(tmp_path):
    root = tmp_path / 'sessions'
    for i in range(10): source(root, f'rollout-{i}.jsonl')
    result = api()([spec(root)], tmp_path / 'absent.sqlite', max_entries=3)
    assert result['scan_status'] == 'INCOMPLETE'
    assert result['stop_reason'] == 'entry_limit'
    assert result['eligible_files'] <= 3
    assert result['remaining_entries'] is None
    assert result['complete_migration'] is False


def test_unreadable_index_is_not_a_clean_empty_index(tmp_path):
    root = tmp_path / 'sessions'
    source(root, 'rollout-a.jsonl')
    db = tmp_path / 'index.sqlite'
    db.write_bytes(b'PRIVATE-CORRUPT-CANARY')
    result = api()([spec(root)], db)
    assert result['index_status'] == 'UNREADABLE'
    assert result['coverage'] == {'INDEX_UNKNOWN': 1}
    assert db.read_bytes() == b'PRIVATE-CORRUPT-CANARY'
    assert 'CANARY' not in json.dumps(result)


def test_missing_and_symlink_roots_are_distinct(tmp_path):
    real = tmp_path / 'real'; real.mkdir()
    linked = tmp_path / 'linked'; linked.symlink_to(real, target_is_directory=True)
    result = api()([spec(tmp_path / 'missing'), spec(linked)], tmp_path / 'absent.sqlite')
    assert [r['status'] for r in result['roots']] == ['MISSING', 'EXCLUDED_SYMLINK']
    assert result['scan_status'] == 'INCOMPLETE'


def test_cli_defaults_report_registered_native_and_unindexed_archive_scope(tmp_path):
    source(tmp_path, '.codex/sessions/rollout-a.jsonl')
    source(tmp_path, '.codex/archived_sessions/rollout-b.jsonl')
    repo = Path(__file__).resolve().parents[1]
    env = {**os.environ, 'HARNESS_HOME': str(tmp_path / 'harness')}
    run = subprocess.run([sys.executable, str(repo/'bin/harness'), '--home', str(tmp_path),
                          'source-inventory'], env=env, capture_output=True, text=True, timeout=10)
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result['eligible_files'] == 2
    assert result['coverage'] == {'UNINDEXED': 1, 'READER_UNSUPPORTED': 1}
    assert 'entries' not in result
    assert not (tmp_path / 'harness').exists()


def test_walk_errors_and_time_budget_keep_the_denominator_incomplete(tmp_path, monkeypatch):
    from agent_harness import source_inventory as module
    root = tmp_path / 'sessions'; root.mkdir()
    def broken_walk(path, followlinks, onerror):
        onerror(PermissionError('PRIVATE-ERROR-CANARY'))
        return iter(())
    monkeypatch.setattr(module.os, 'walk', broken_walk)
    result = api()([spec(root)], tmp_path / 'absent.sqlite')
    assert result['scan_status'] == 'INCOMPLETE'
    assert result['roots'][0]['status'] == 'PARTIAL'
    assert result['excluded']['unreadable_subtree'] == 1
    assert 'CANARY' not in json.dumps(result)
    ticks = iter([0, 2])
    monkeypatch.setattr(module.time, 'monotonic', lambda: next(ticks))
    monkeypatch.setattr(module.os, 'walk', lambda *a, **k: iter([(str(root), [], ['rollout-a.jsonl'])]))
    result = api()([spec(root)], tmp_path / 'absent.sqlite', max_seconds=1)
    assert result['stop_reason'] == 'time_limit'
    assert result['scan_status'] == 'INCOMPLETE'


def test_inventory_sees_committed_wal_metadata_without_checkpointing(tmp_path):
    root = tmp_path / 'sessions'
    p = source(root, 'rollout-a.jsonl')
    db = tmp_path / 'index.sqlite'
    con = sqlite3.connect(db)
    try:
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('CREATE TABLE sess_files(path TEXT PRIMARY KEY, offset INTEGER, size INTEGER, mtime REAL, dropped INTEGER)')
        n = p.stat().st_size
        con.execute('INSERT INTO sess_files VALUES (?,?,?,?,?)', (str(p),n,n,p.stat().st_mtime,0))
        con.commit()
        before = db.read_bytes()
        result = api()([spec(root)], db)
        assert result['coverage'] == {'BYTE_OFFSET_COVERED': 1}
        assert db.read_bytes() == before
    finally:
        con.close()
