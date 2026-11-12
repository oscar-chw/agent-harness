"""Read-only declared-source denominator and index reconciliation, never a migration verdict."""
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import stat
import time


def default_roots(home):
    home = Path(home)
    return [
        {'kind': 'claude-code', 'path': home/'.claude/projects', 'reader_supported': True},
        {'kind': 'codex', 'path': home/'.codex/sessions', 'reader_supported': True},
        {'kind': 'codex', 'path': home/'.codex/archived_sessions', 'reader_supported': False},
    ]


def _id(path):
    return hashlib.sha256(str(path).encode()).hexdigest()


def _index(path):
    con = None
    try:
        Path(path).stat()
        con = sqlite3.connect(Path(path).absolute().as_uri()+'?mode=ro', uri=True, timeout=3)
        con.execute('PRAGMA query_only=ON')
        con.execute('BEGIN')
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sess_files'").fetchone():
            return 'ABSENT', {}
        rows = {}
        for key, offset, size, mtime, dropped in con.execute('SELECT path,offset,size,mtime,dropped FROM sess_files'):
            if (not isinstance(key, str) or not key or type(offset) is not int or type(size) is not int
                    or not isinstance(mtime, (int, float)) or not math.isfinite(mtime)
                    or dropped not in (0, 1)):
                return 'UNREADABLE', {}
            rows[key] = (offset, size, mtime, dropped)
        return 'READABLE', rows
    except FileNotFoundError:
        return 'ABSENT', {}
    except (OSError, sqlite3.Error):
        return 'UNREADABLE', {}
    finally:
        if con is not None:
            con.close()


def _coverage(row, st, supported, index_status):
    if not supported:
        return 'READER_UNSUPPORTED'
    if index_status == 'UNREADABLE':
        return 'INDEX_UNKNOWN'
    if row is None:
        return 'UNINDEXED'
    offset, size, mtime, dropped = row
    if offset < 0 or offset > st.st_size or size < 0:
        return 'INVALID_OFFSET'
    if dropped:
        return 'EVICTED'
    if size != st.st_size or mtime != st.st_mtime:
        return 'STALE'
    return 'BYTE_OFFSET_COVERED' if offset == st.st_size else 'PARTIAL'


def inventory_sources(specs, index_path, max_entries=100_000, max_seconds=10):
    if type(max_entries) is not int or not 1 <= max_entries <= 1_000_000:
        raise ValueError('max_entries must be an integer from 1 to 1000000')
    if not isinstance(max_seconds, (int, float)) or not math.isfinite(max_seconds) or not 0 < max_seconds <= 300:
        raise ValueError('max_seconds must be finite, positive and at most 300')
    started = time.monotonic()
    roots = []
    prepared = []
    for item in specs:
        kind = item['kind']
        if kind not in ('claude-code', 'codex', 'archive-jsonl'):
            raise ValueError('unsupported source kind')
        path = Path(item['path']).expanduser().absolute()
        supported = item['reader_supported']
        if type(supported) is not bool:
            raise ValueError('reader_supported must be boolean')
        row = {'id': _id(path), 'kind': kind, 'reader_supported': supported,
               'status': 'NOT_SCANNED', 'eligible_files': 0}
        roots.append(row)
        prepared.append((path, kind, supported, row))
    index_status, known = _index(index_path)
    excluded = Counter()
    coverage = Counter()
    entries = []
    seen = set()
    examined = duplicates = 0
    stop = None
    incomplete = False
    uid = os.getuid() if hasattr(os, 'getuid') else None

    def admitted():
        nonlocal examined, stop
        if time.monotonic()-started >= max_seconds:
            stop = 'time_limit'
            return False
        if examined >= max_entries:
            stop = 'entry_limit'
            return False
        examined += 1
        return True

    for root, kind, supported, root_row in prepared:
        if stop:
            break
        try:
            st = root.lstat()
            if stat.S_ISLNK(st.st_mode):
                root_row['status'] = 'EXCLUDED_SYMLINK'
                incomplete = True
                continue
            if not stat.S_ISDIR(st.st_mode):
                root_row['status'] = 'NOT_DIRECTORY'
                incomplete = True
                continue
        except FileNotFoundError:
            root_row['status'] = 'MISSING'
            continue
        except OSError:
            root_row['status'] = 'UNREADABLE'
            incomplete = True
            continue
        root_row['status'] = 'SCANNED'

        def walk_error(_):
            nonlocal incomplete
            incomplete = True
            root_row['status'] = 'PARTIAL'
            excluded['unreadable_subtree'] += 1

        for directory, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
            depth = len(Path(directory).relative_to(root).parts)
            keep = []
            for name in sorted(dirs):
                if not admitted():
                    break
                p = Path(directory)/name
                if p.is_symlink():
                    excluded['symlink'] += 1
                elif kind == 'claude-code' and depth >= 1:
                    excluded['claude_child_subtree'] += 1
                elif name.startswith('.'):
                    excluded['hidden_subtree'] += 1
                else:
                    keep.append(name)
            dirs[:] = keep
            if stop:
                break
            for name in sorted(names):
                if not admitted():
                    break
                p = Path(directory)/name
                try:
                    st = p.lstat()
                except OSError:
                    incomplete = True
                    excluded['unreadable_entry'] += 1
                    continue
                if stat.S_ISLNK(st.st_mode):
                    excluded['symlink'] += 1
                    continue
                if not stat.S_ISREG(st.st_mode):
                    excluded['non_regular'] += 1
                    continue
                if uid is not None and st.st_uid != uid:
                    excluded['foreign_owner'] += 1
                    continue
                if not name.endswith('.jsonl') or (kind == 'codex' and not name.startswith('rollout-')):
                    excluded['non_transcript'] += 1
                    continue
                if kind == 'claude-code' and depth != 1:
                    excluded['unsupported_layout'] += 1
                    continue
                key = str(p)
                if key in seen:
                    duplicates += 1
                    continue
                seen.add(key)
                status = _coverage(known.get(key), st, supported, index_status)
                coverage[status] += 1
                root_row['eligible_files'] += 1
                entries.append({'id': _id(p), 'root': root_row['id'], 'kind': kind,
                                'bytes': st.st_size, 'mtime_ns': st.st_mtime_ns, 'coverage': status})
            if stop:
                break
        if stop:
            root_row['status'] = 'PARTIAL'
    entries.sort(key=lambda x: x['id'])
    return {'schema': 'harness.source-inventory/v1',
            'scan_status': 'INCOMPLETE' if incomplete or stop else 'COMPLETE',
            'stop_reason': stop, 'examined_entries': examined, 'remaining_entries': None,
            'roots': roots, 'eligible_files': len(entries),
            'eligible_bytes': sum(e['bytes'] for e in entries), 'duplicate_observations': duplicates,
            'excluded': dict(excluded), 'excluded_descendant_count': 'UNKNOWN',
            'index_status': index_status, 'coverage': dict(coverage),
            'indexed_paths_not_observed': len(set(known)-seen),
            'metadata_manifest_sha256': hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest(),
            'entries': entries, 'identity': 'metadata_only_not_a_content_snapshot',
            'complete_migration': False, 'semantic_extraction': 'NOT_EVALUATED',
            'content_deduplication': 'NOT_RUN', 'eviction_authorized': False}
