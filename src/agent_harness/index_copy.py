"""Bounded VACUUM of an explicitly disposable SQLite copy."""

import contextlib
import hashlib
import os
import sqlite3
import tempfile
import time
from pathlib import Path

DEFAULT_MAX_SOURCE_BYTES = 32 * 1024 * 1024
DEFAULT_MAX_SECONDS = 10


def _regular_file(path, label):
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    if not path.is_file():
        raise ValueError(f"{label} must be an existing regular file")
    return path


def _source_pin(source, max_bytes, check_deadline):
    """Hash the bounded main database and WAL, detecting changes during each read."""
    wal = Path(str(source) + "-wal")
    entries = []
    total = 0
    for path in (source, wal):
        if path.is_symlink():
            raise ValueError("source and WAL must not be symlinks")
        if not path.exists():
            if path == source:
                raise ValueError("source must be an existing regular file")
            entries.append((str(path), None, None))
            continue
        stat_before = path.stat()
        if not path.is_file():
            raise ValueError("source and WAL must be regular files")
        total += stat_before.st_size
        if total > max_bytes:
            raise ValueError("source plus WAL exceeds byte limit")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino) != (stat_before.st_dev, stat_before.st_ino):
                raise ValueError("source changed while opening")
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                check_deadline()
                digest.update(chunk)
            stat_after = os.fstat(stream.fileno())
        current = path.stat()
        identity = (stat_before.st_dev, stat_before.st_ino, stat_before.st_size, stat_before.st_mtime_ns)
        if identity != (stat_after.st_dev, stat_after.st_ino, stat_after.st_size, stat_after.st_mtime_ns):
            raise ValueError("source changed while hashing")
        if identity != (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns):
            raise ValueError("source changed while hashing")
        entries.append((str(path), stat_before.st_size, digest.hexdigest()))
    return tuple(entries), total


def _add_value(digest, value):
    if value is None:
        tag, payload = b"N", b""
    elif isinstance(value, bytes):
        tag, payload = b"B", value
    elif isinstance(value, str):
        tag, payload = b"S", value.encode("utf-8")
    elif isinstance(value, int):
        tag, payload = b"I", str(value).encode("ascii")
    elif isinstance(value, float):
        tag, payload = b"F", value.hex().encode("ascii")
    else:
        raise ValueError("unsupported SQLite value type")
    digest.update(tag)
    digest.update(len(payload).to_bytes(8, "big"))
    digest.update(payload)


def _fingerprint(connection, check_deadline):
    digest = hashlib.sha256()
    schema = connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name, tbl_name"
    )
    for row in schema:
        check_deadline()
        for value in row:
            _add_value(digest, value)
    tables = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    counts = {}
    for (name,) in tables:
        check_deadline()
        quoted = '"' + name.replace('"', '""') + '"'
        try:
            cursor = connection.execute(f"SELECT rowid, * FROM {quoted} ORDER BY rowid")
        except sqlite3.OperationalError as exc:
            if "no such column: rowid" not in str(exc):
                raise
            columns = connection.execute(f"PRAGMA table_info({quoted})").fetchall()
            order = ", ".join(str(column[0] + 1) for column in columns)
            cursor = connection.execute(f"SELECT * FROM {quoted} ORDER BY {order}")
        _add_value(digest, name)
        count = 0
        for row in cursor:
            check_deadline()
            for value in row:
                check_deadline()
                _add_value(digest, value)
            count += 1
        counts[name] = count
    return digest.hexdigest(), counts


def compact_copy(source, destination, max_source_bytes=DEFAULT_MAX_SOURCE_BYTES,
                 max_seconds=DEFAULT_MAX_SECONDS, *, offline=False):
    """Compact an offline disposable copy; never write to source or publish over destination."""
    if offline is not True:
        raise ValueError("offline=True is required for an explicitly disposable copy")
    if type(max_source_bytes) is not int or not 0 < max_source_bytes <= DEFAULT_MAX_SOURCE_BYTES:
        raise ValueError("byte limit must be positive and at most 32 MiB")
    if (type(max_seconds) not in (int, float)
            or not 0 < max_seconds <= DEFAULT_MAX_SECONDS):
        raise ValueError("time limit must be positive and at most 10 seconds")

    source = _regular_file(source, "source")
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    if not destination.parent.is_dir():
        raise ValueError("destination parent must exist")

    started = time.monotonic()
    deadline = started + max_seconds

    def check_deadline():
        if time.monotonic() >= deadline:
            raise TimeoutError("SQLite copy exceeded time limit")

    source_pin, source_total_bytes = _source_pin(source, max_source_bytes, check_deadline)
    source_bytes = source.stat().st_size
    wal = Path(str(source) + "-wal")
    wal_bytes = wal.stat().st_size if wal.exists() else 0
    temp_fd, temp_name = tempfile.mkstemp(
        prefix=".index-copy-", suffix=".sqlite", dir=destination.parent
    )
    os.close(temp_fd)
    temp_path = Path(temp_name)
    source_uri = source.absolute().as_uri() + "?mode=ro"
    try:
        with contextlib.closing(sqlite3.connect(source_uri, uri=True, timeout=0)) as original:
            original.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
            if original.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise ValueError("source integrity check failed")
            source_fingerprint, source_counts = _fingerprint(original, check_deadline)
            check_deadline()
            with contextlib.closing(sqlite3.connect(temp_path, timeout=0)) as compacted:
                compacted.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)

                def backup_progress(_status, _remaining, _total):
                    check_deadline()

                original.backup(compacted, pages=64, progress=backup_progress, sleep=0.001)
                check_deadline()
                checkpoint = compacted.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                if checkpoint[0] or (checkpoint[1] >= 0 and checkpoint[1] != checkpoint[2]):
                    raise ValueError("could not checkpoint compacted database")
                journal_mode = compacted.execute("PRAGMA journal_mode=DELETE").fetchone()
                if journal_mode != ("delete",):
                    raise ValueError("could not make compacted database self-contained")
                compacted.execute("VACUUM")
                check_deadline()
                if compacted.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                    raise ValueError("compacted integrity check failed")
                output_fingerprint, output_counts = _fingerprint(compacted, check_deadline)
                if output_fingerprint != source_fingerprint or output_counts != source_counts:
                    raise ValueError("VACUUM changed logical SQLite or FTS content")
                checkpoint = compacted.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                if checkpoint[0] or (checkpoint[1] >= 0 and checkpoint[1] != checkpoint[2]):
                    raise ValueError("could not checkpoint compacted database")

        temp_wal = Path(str(temp_path) + "-wal")
        temp_shm = Path(str(temp_path) + "-shm")
        if temp_wal.exists() and temp_wal.stat().st_size:
            raise ValueError("compacted database retained WAL content")
        temp_wal.unlink(missing_ok=True)
        temp_shm.unlink(missing_ok=True)
        check_deadline()
        output_bytes = temp_path.stat().st_size
        output_digest = hashlib.sha256()
        with temp_path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                check_deadline()
                output_digest.update(chunk)
        output_hash = output_digest.hexdigest()
        current_pin, current_total_bytes = _source_pin(source, max_source_bytes, check_deadline)
        if current_pin != source_pin or current_total_bytes != source_total_bytes:
            raise ValueError("source or WAL changed during compaction")
        os.link(temp_path, destination)
        return {
            "source_sha256": source_pin[0][2],
            "wal_sha256": source_pin[1][2],
            "destination_sha256": output_hash,
            "source_bytes": source_bytes,
            "wal_bytes": wal_bytes,
            "destination_bytes": output_bytes,
            "row_counts": source_counts,
            "integrity_check": "ok",
            "elapsed_seconds": round(time.monotonic() - started, 6),
        }
    finally:
        temp_path.unlink(missing_ok=True)
        Path(str(temp_path) + "-wal").unlink(missing_ok=True)
        Path(str(temp_path) + "-shm").unlink(missing_ok=True)
