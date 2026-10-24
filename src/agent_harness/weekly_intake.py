"""On-demand changed-candidate intake; never a scheduler or a method promoter.

The captured candidate file is atomically replaced after each turn. A byte
offset therefore cannot be its cursor. This small SQLite ledger records only
delivered candidate counts/digests and bounded content-free audit receipts.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path

from .capture import STORE
from .redact import redact

MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_AUDIT = 52
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _source(path):
    if path.is_symlink():
        raise ValueError("source_redirected: candidate store must not be a symlink")
    if path.exists() and not path.is_file():
        raise ValueError("invalid_candidate: capture store is not a regular file")
    if not path.is_file():
        return b"", []
    with path.open("rb") as stream:
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError("invalid_candidate: source exceeds 2 MiB")
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
                or redact(row["summary"]) != row["summary"]
                or redact(row["evidence"]) != row["evidence"]):
            raise ValueError("invalid_candidate: missing, duplicate, untrusted or unsanitized row")
        ids.add(row["id"])
        rows.append((row, _sha(_json(row).encode("utf-8"))))
    return raw, rows


def _size(result):
    # The count itself changes the length of the JSON; settle it before gating.
    result["output_bytes"] = 0
    for _ in range(4):
        length = len(_json(result).encode("utf-8")) + 1  # CLI writes one trailing newline
        if length == result["output_bytes"]:
            break
        result["output_bytes"] = length
    return result["output_bytes"]


def take(home, *, since=None, max_items=10, max_output_bytes=2048):
    if (type(max_items) is not int or not 1 <= max_items <= 20
            or type(max_output_bytes) is not int or not 120 <= max_output_bytes <= 4096
            or (since is not None and (type(since) is not int or since < 0))):
        raise ValueError("budget: max-items 1..20, max-output-bytes 120..4096, since nonnegative")
    home = Path(home)
    source = home / STORE
    raw, rows = _source(source)
    store = home / "weekly-intake"
    store.mkdir(mode=0o700, parents=True, exist_ok=True)
    if store.is_symlink() or not store.is_dir():
        raise ValueError("intake storage is redirected")
    db_path = store / "intake.sqlite"
    if db_path.is_symlink():
        raise ValueError("intake storage is redirected")
    try:
        con = sqlite3.connect(str(db_path), timeout=10, isolation_level=None)
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
        result = {"status": "NO_CHANGE" if not changed else "CHANGED", "cursor": cursor,
                  "candidates": [], "remaining": len(changed), "promotion": "NOT_RUN",
                  "receipt_sha256": None, "output_bytes": 0}
        if not changed:
            if _size(result) > max_output_bytes:
                raise ValueError("budget: even an empty result exceeds the output cap")
            con.commit()
            return result
        receipt = {"source_sha256": _sha(raw), "previous_cursor": cursor,
                   "cursor": cursor + 1, "selected_ids": [], "at": int(time.time())}
        result["cursor"] = cursor + 1
        selected = []
        for row, sha in changed[:max_items]:
            item = {"id": row["id"], "source": row["source"], "count": row["count"],
                    "summary": row["summary"][:120]}
            proposal = result["candidates"] + [item]
            audit = {**receipt, "selected_ids": [x[0]["id"] for x in selected] + [row["id"]]}
            result.update(candidates=proposal, remaining=len(changed) - len(proposal),
                          receipt_sha256=_sha(_json(audit).encode("utf-8")))
            if _size(result) > max_output_bytes:
                break
            selected.append((row, sha))
        if not selected:
            raise ValueError("budget: no candidate fits the output cap; cursor unchanged")
        result["candidates"] = result["candidates"][:len(selected)]
        result["remaining"] = len(changed) - len(selected)
        receipt["selected_ids"] = [row["id"] for row, _ in selected]
        result["receipt_sha256"] = _sha(_json(receipt).encode("utf-8"))
        if _size(result) > max_output_bytes:
            raise ValueError("budget: receipt exceeds the output cap; cursor unchanged")
        for row, sha in selected:
            con.execute("INSERT INTO seen VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET count=excluded.count,sha=excluded.sha",
                        (row["id"], row["count"], sha))
        con.execute("INSERT INTO receipts(body) VALUES (?)", (_json(receipt),))
        con.execute("DELETE FROM receipts WHERE seq NOT IN (SELECT seq FROM receipts ORDER BY seq DESC LIMIT ?)",
                    (MAX_AUDIT,))
        con.commit()
        return result
    except sqlite3.Error:
        raise ValueError("intake storage unavailable") from None
    finally:
        con.close()
