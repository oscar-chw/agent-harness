"""On-demand changed-candidate intake; never a scheduler or a method promoter.

The captured candidate file is atomically replaced after each turn. A byte
offset therefore cannot be its cursor. This small SQLite ledger records only
delivered candidate counts/digests and bounded content-free audit receipts.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import os
import re
import sqlite3
import time
from pathlib import Path

from .capture import RETENTION_PENDING, STORE, _recover_capture, _replace_capture
from .mcp.memory import _store_lock
from .redact import redact

MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_AUDIT = 52
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _source_bytes(path):
    if path.is_symlink():
        raise ValueError("source_redirected: candidate store must not be a symlink")
    if path.exists() and not path.is_file():
        raise ValueError("invalid_candidate: capture store is not a regular file")
    if not path.is_file():
        return b""
    with path.open("rb") as stream:
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError("invalid_candidate: source exceeds 2 MiB")
    return raw


def _rows(raw):
    rows, ids = [], set()
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            raise ValueError("invalid_candidate: unreadable JSON line") from None
        if (not isinstance(row, dict) or not isinstance(row.get("id"), str)
                or not ID.fullmatch(row["id"]) or row["id"] in ids
                or row.get("source") not in ("gate", "user")
                or type(row.get("count")) is not int or row["count"] < 1
                or not isinstance(row.get("summary"), str) or len(row["summary"]) > 512
                or not isinstance(row.get("evidence"), str) or len(row["evidence"]) > 300
                or not isinstance(row.get("last"), str) or len(row["last"]) > 64
                or ("project_sha256" in row and (not isinstance(row["project_sha256"], str)
                                                 or not SHA.fullmatch(row["project_sha256"])))
                or redact(row["summary"]) != row["summary"]
                or redact(row["evidence"]) != row["evidence"]):
            raise ValueError("invalid_candidate: missing, duplicate, untrusted or unsanitized row")
        ids.add(row["id"])
        rows.append((row, _sha(_json(row).encode("utf-8"))))
    return rows


def _size(result):
    # The count itself changes the length of the JSON; settle it before gating.
    result["output_bytes"] = 0
    for _ in range(4):
        length = len(_json(result).encode("utf-8")) + 1  # CLI writes one trailing newline
        if length == result["output_bytes"]:
            break
        result["output_bytes"] = length
    return result["output_bytes"]


def _database(home):
    store = home / "weekly-intake"
    store.mkdir(mode=0o700, parents=True, exist_ok=True)
    if store.is_symlink() or not store.is_dir():
        raise ValueError("intake storage is redirected")
    path = store / "intake.sqlite"
    if path.is_symlink():
        raise ValueError("intake storage is redirected")
    return path


def _retention_table(con):
    con.execute("CREATE TABLE IF NOT EXISTS retired (id TEXT PRIMARY KEY, count INTEGER NOT NULL, sha TEXT NOT NULL)")


def recover_retention(home):
    """Settle an interrupted, locked prune against the exact store on disk."""
    pending = home / RETENTION_PENDING
    if pending.is_symlink() or pending.parent.is_symlink():
        raise ValueError("retention evidence is redirected")
    if not pending.is_file() or pending.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("invalid retention evidence")
    receipt = json.loads(pending.read_bytes())
    if not isinstance(receipt, dict) or set(receipt) != {"schema", "before", "after", "retired", "sha256"}:
        raise ValueError("invalid retention evidence")
    seal = receipt.pop("sha256")
    entries = receipt["retired"]
    if (type(receipt["schema"]) is not int or receipt["schema"] != 1
            or any(not isinstance(receipt[key], str) or not SHA.fullmatch(receipt[key])
                   for key in ("before", "after"))
            or not isinstance(entries, list) or not entries
            or any(not isinstance(entry, list) or len(entry) != 3
                   or not isinstance(entry[0], str) or not ID.fullmatch(entry[0])
                   or type(entry[1]) is not int or entry[1] <= 0
                   or not isinstance(entry[2], str) or not SHA.fullmatch(entry[2]) for entry in entries)
            or len({entry[0] for entry in entries}) != len(entries)
            or seal != _sha(_json(receipt).encode()) or not (home / STORE).is_file()):
        raise ValueError("invalid retention evidence")
    current = _sha(_source_bytes(home / STORE))
    if current != receipt["before"]:
        if current != receipt["after"]:
            raise ValueError("retention_source_drift: pending prune cannot be verified")
        try:
            with closing(sqlite3.connect(_database(home), timeout=10)) as con, con:
                con.execute("BEGIN IMMEDIATE")
                _retention_table(con)
                for identity, count, digest in receipt["retired"]:
                    delivered = con.execute("SELECT count,sha FROM seen WHERE id=?", (identity,)).fetchone()
                    if delivered != (count, digest):
                        raise ValueError("retention receipt does not match delivered evidence")
                    con.execute("INSERT OR IGNORE INTO retired VALUES (?,?,?)", (identity, count, digest))
        except sqlite3.Error:
            raise ValueError("intake retention storage unavailable") from None
    pending.unlink()
    _sync_parent(pending)


def _sync_parent(path):
    if os.name == "posix":
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _durable_replace(path, data):
    _replace_capture(path, data)
    with path.open("rb") as stream:
        os.fsync(stream.fileno())
    _sync_parent(path)


def prune_candidates(home, limit):
    """Record only retirement of already delivered rows. The caller holds the capture lock."""
    raw = _source_bytes(home / STORE)
    if len(raw.splitlines()) <= limit:
        return
    rows = _rows(raw)
    if len(rows) <= limit:
        return
    retained = b"".join((_json(row) + "\n").encode() for row, _ in rows[-limit:])
    try:
        with closing(sqlite3.connect(_database(home), timeout=10)) as con:
            _retention_table(con)
            delivered = {identity: (count, sha) for identity, count, sha in con.execute(
                "SELECT id,count,sha FROM seen WHERE id NOT IN (SELECT id FROM retired)")}
    except sqlite3.Error:
        raise ValueError("intake retention storage unavailable") from None
    retired = []
    for row, digest in rows[:-limit]:
        known = delivered.get(row["id"])
        if known:
            count, sha = known
            if row["count"] < count or (row["count"] == count and digest != sha):
                raise ValueError("prune would retire rewound or changed evidence")
            retired.append((row["id"], count, sha))
    if retired:
        receipt = {"schema": 1, "before": _sha(raw), "after": _sha(retained), "retired": retired}
        receipt["sha256"] = _sha(_json(receipt).encode())
        _durable_replace(home / RETENTION_PENDING, _json(receipt).encode())
    _durable_replace(home / STORE, retained)
    if retired:
        recover_retention(home)


def take(home, *, since=None, max_items=10, max_output_bytes=2048, emit=None):
    """Return the bounded result, flushing it through emit before committing if supplied."""
    if (type(max_items) is not int or not 1 <= max_items <= 20
            or type(max_output_bytes) is not int or not 120 <= max_output_bytes <= 4096
            or (since is not None and (type(since) is not int or since < 0))):
        raise ValueError("budget: max-items 1..20, max-output-bytes 120..4096, since nonnegative")
    home = Path(home)
    with _store_lock(home, timeout=10):
        _recover_capture(home)
        return _take_locked(home, since, max_items, max_output_bytes, emit)


def _take_locked(home, since, max_items, max_output_bytes, emit):
    source = home / STORE
    raw = _source_bytes(source)
    rows = _rows(raw)
    try:
        con = sqlite3.connect(_database(home), timeout=10, isolation_level=None)
    except sqlite3.Error:
        raise ValueError("intake storage unavailable") from None
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY, count INTEGER NOT NULL, sha TEXT NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS receipts (seq INTEGER PRIMARY KEY AUTOINCREMENT, body TEXT NOT NULL)")
        cursor = con.execute("SELECT COALESCE(MAX(seq),0) FROM receipts").fetchone()[0]
        if since is not None and since != cursor:
            raise ValueError("stale_cursor: refresh the latest intake cursor")
        prior = {identity: (count, sha) for identity, count, sha in con.execute("SELECT id,count,sha FROM seen")}
        if prior and not source.is_file():
            raise ValueError("source_missing: captured evidence disappeared; cursor unchanged")
        _retention_table(con)
        retired = {identity: (count, sha) for identity, count, sha in con.execute("SELECT * FROM retired")}
        if any(prior.get(identity) != evidence for identity, evidence in retired.items()):
            raise ValueError("retention ledger differs from delivered evidence")
        for identity in retired:
            del prior[identity]
        current_ids = {row["id"] for row, _ in rows}
        if set(prior) - current_ids:
            raise ValueError("source_evicted: previously delivered candidate rows disappeared; cursor unchanged")
        changed = []
        for row, sha in rows:
            old = prior.get(row["id"])
            if old and row["count"] < old[0]:
                raise ValueError("count_rewind: captured evidence moved backward")
            if old is None or (row["count"], sha) != old:
                changed.append((row, sha))
        changed.sort(key=lambda item: (item[0]["last"], item[0]["id"]))
        result = {"status": "CHANGED" if changed or retired else "NO_CHANGE", "cursor": cursor,
                  "candidates": [], "remaining": len(changed), "promotion": "NOT_RUN",
                  "receipt_sha256": None, "output_bytes": 0}
        if retired:
            result["retired_count"] = len(retired)
        if not changed and not retired:
            if _size(result) > max_output_bytes:
                raise ValueError("budget: even an empty result exceeds the output cap")
            return _deliver(con, result, emit)
        receipt = {"source_sha256": _sha(raw), "previous_cursor": cursor,
                   "cursor": cursor + 1, "selected_ids": [], "at": int(time.time())}
        if retired:
            receipt.update(retired_count=len(retired), retired_sha256=_sha(_json(retired).encode()))
        result["cursor"] = cursor + 1
        selected = []
        for row, sha in changed[:max_items]:
            item = {"id": row["id"], "source": row["source"], "count": row["count"],
                    "summary": row["summary"][:120]}
            if "project_sha256" in row:
                item["project_sha256"] = row["project_sha256"]
            proposal = result["candidates"] + [item]
            audit = {**receipt, "selected_ids": [x[0]["id"] for x in selected] + [row["id"]]}
            result.update(candidates=proposal, remaining=len(changed) - len(proposal),
                          receipt_sha256=_sha(_json(audit).encode("utf-8")))
            if _size(result) > max_output_bytes:
                break
            selected.append((row, sha))
        if not selected and not retired:
            raise ValueError("budget: no candidate fits the output cap; cursor unchanged")
        result["candidates"] = result["candidates"][:len(selected)]
        result["remaining"] = len(changed) - len(selected)
        receipt["selected_ids"] = [row["id"] for row, _ in selected]
        result["receipt_sha256"] = _sha(_json(receipt).encode("utf-8"))
        if _size(result) > max_output_bytes:
            raise ValueError("budget: receipt exceeds the output cap; cursor unchanged")
        for identity in retired:
            con.execute("DELETE FROM seen WHERE id=?", (identity,))
        if retired:
            con.execute("DELETE FROM retired")
        for row, sha in selected:
            con.execute("INSERT INTO seen VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET count=excluded.count,sha=excluded.sha",
                        (row["id"], row["count"], sha))
        con.execute("INSERT INTO receipts(body) VALUES (?)", (_json(receipt),))
        con.execute("DELETE FROM receipts WHERE seq NOT IN (SELECT seq FROM receipts ORDER BY seq DESC LIMIT ?)",
                    (MAX_AUDIT,))
        return _deliver(con, result, emit)
    except sqlite3.Error:
        raise ValueError("intake storage unavailable") from None
    finally:
        con.close()


def _deliver(con, result, emit):
    # With a CLI writer, a failed flush must leave the old cursor eligible.
    if emit is not None:
        emit(_json(result))
    con.commit()
    return result
