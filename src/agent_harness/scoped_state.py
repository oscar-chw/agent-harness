"""Opt-in local continuation slots with explicit scope and optimistic concurrency.

The host must construct Scope from authorized context, not model-supplied IDs.
This module does NOT authenticate a caller, isolate same-OS-user processes, or
replace the installed MCP state tool. No legacy state is read or migrated.
Shared views pin one current revision; updates/clear invalidate them. Clear is
logical deletion, not erasure of backups or already-delivered context.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

MAX_TEXT_BYTES = 4096


class Conflict(ValueError):
    """The caller must re-read before overwriting a newer continuation."""


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _hash(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Scope:
    tenant: str
    user: str
    project: str
    chat: str
    agent: str

    def __post_init__(self):
        for name, value in asdict(self).items():
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:@-]{1,128}", value):
                raise ValueError("scope %s must be an explicit bounded identifier" % name)

    @property
    def key(self):
        return _hash(asdict(self))


class ScopedState:
    def __init__(self, home, scope: Scope, *, max_scopes=1000, max_shares=1000):
        if not isinstance(scope, Scope):
            raise ValueError("host-provided Scope is required")
        if any(type(n) is not int or not 1 <= n <= 1000 for n in (max_scopes, max_shares)):
            raise ValueError("scope/share caps must be integers from 1 to 1000")
        self.scope = scope
        self.path = Path(home).expanduser().resolve() / "scoped-state" / "state.sqlite"
        self.max_scopes, self.max_shares = max_scopes, max_shares

    @contextmanager
    def _transaction(self):
        directory = self.path.parent
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("scoped-state directory must be a regular directory")
        try:
            fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        except OSError as exc:
            raise ValueError("scoped-state database cannot be opened safely") from exc
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError("scoped-state database must be a regular file")
        finally:
            os.close(fd)
        db = None
        try:
            db = sqlite3.connect(str(self.path), timeout=5)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA secure_delete=ON")
            db.execute("PRAGMA trusted_schema=OFF")
            db.execute("PRAGMA max_page_count=2048")
            db.execute("BEGIN IMMEDIATE")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("unsupported scoped-state database version")
            db.execute("CREATE TABLE IF NOT EXISTS states (id TEXT PRIMARY KEY, scope TEXT NOT NULL, "
                       "revision INTEGER NOT NULL, text TEXT, deleted INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS shares (source TEXT NOT NULL, target TEXT NOT NULL, "
                       "revision INTEGER NOT NULL, PRIMARY KEY(source,target))")
            db.execute("PRAGMA user_version=1")
            yield db
            db.commit()
        except sqlite3.Error as exc:
            # Database errors can embed row text; diagnostics must not echo a continuation.
            raise ValueError("scoped-state storage failed (%s)" % type(exc).__name__) from None
        finally:
            if db is not None:
                db.close()  # rolls back on any exception, including KeyboardInterrupt

    @staticmethod
    def _row(db, scope):
        row = db.execute("SELECT * FROM states WHERE id=?", (scope.key,)).fetchone()
        if row is None:
            revision, text, deleted = 0, None, False
        else:
            revision, text, deleted = row["revision"], row["text"], row["deleted"]
            if (row["scope"] != _json(asdict(scope)) or type(revision) is not int or revision < 1
                    or deleted not in (0, 1) or (deleted and text is not None)
                    or (not deleted and not isinstance(text, str))
                    or (isinstance(text, str) and len(text.encode("utf-8")) > MAX_TEXT_BYTES)):
                raise ValueError("invalid scoped-state row")
        data = {"scope": asdict(scope), "revision": revision, "text": text, "deleted": bool(deleted)}
        return {**data, "receipt": _hash(data), "authority": "advisory"}

    def load(self):
        with self._transaction() as db:
            return self._row(db, self.scope)

    @staticmethod
    def _check(row, expected):
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("an exact prior scoped-state receipt is required")
        if expected != row["receipt"]:
            raise Conflict("continuation changed or receipt belongs to a different scope; re-read")

    def _write(self, text, expected, deleted):
        if not deleted and (not isinstance(text, str) or len(text.encode("utf-8")) > MAX_TEXT_BYTES):
            raise ValueError("continuation must be UTF-8 text of at most 4096 bytes")
        with self._transaction() as db:
            row = self._row(db, self.scope)
            self._check(row, expected)
            if row["revision"] == 0 and db.execute("SELECT count(*) FROM states").fetchone()[0] >= self.max_scopes:
                raise ValueError("scope cap reached; no state was pruned")
            if row["revision"] >= 2**63 - 1:
                raise ValueError("continuation revision exhausted")
            db.execute("INSERT INTO states VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                       "revision=excluded.revision, text=excluded.text, deleted=excluded.deleted",
                       (self.scope.key, _json(asdict(self.scope)), row["revision"] + 1, text, int(deleted)))
            # A shared view is authorization to one revision, never to future private notes.
            db.execute("DELETE FROM shares WHERE source=?", (self.scope.key,))
            return self._row(db, self.scope)

    def save(self, text, *, expected):
        return self._write(text, expected, False)

    def clear(self, *, expected):
        return self._write(None, expected, True)

    def _peer(self, other):
        if not isinstance(other, Scope):
            raise ValueError("explicit peer Scope is required")
        if (self.scope.tenant, self.scope.project) != (other.tenant, other.project):
            raise PermissionError("sharing outside this tenant/project is not supported")

    def share(self, target: Scope, *, expected):
        """Host-authorized explicit sharing, without copying the source text."""
        self._peer(target)
        with self._transaction() as db:
            row = self._row(db, self.scope)
            self._check(row, expected)
            if row["text"] is None:
                raise ValueError("there is no current continuation to share")
            exists = db.execute("SELECT 1 FROM shares WHERE source=? AND target=?",
                                (self.scope.key, target.key)).fetchone()
            if not exists and db.execute("SELECT count(*) FROM shares").fetchone()[0] >= self.max_shares:
                raise ValueError("share cap reached; no existing grant was pruned")
            db.execute("INSERT INTO shares VALUES (?,?,?) ON CONFLICT(source,target) DO UPDATE "
                       "SET revision=excluded.revision", (self.scope.key, target.key, row["revision"]))
            return {"source_receipt": row["receipt"], "target": asdict(target)}

    def revoke(self, target: Scope, *, expected):
        self._peer(target)
        with self._transaction() as db:
            self._check(self._row(db, self.scope), expected)
            db.execute("DELETE FROM shares WHERE source=? AND target=?", (self.scope.key, target.key))

    def read_shared(self, source: Scope):
        self._peer(source)
        with self._transaction() as db:
            grant = db.execute("SELECT revision FROM shares WHERE source=? AND target=?",
                               (source.key, self.scope.key)).fetchone()
            if grant is None:
                raise PermissionError("no current explicit grant")
            row = self._row(db, source)
            if row["revision"] != grant["revision"] or row["text"] is None:
                raise PermissionError("shared continuation is no longer current")
            return row
