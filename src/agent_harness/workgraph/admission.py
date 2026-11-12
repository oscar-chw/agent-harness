"""Shared admission for cooperating runners, not filesystem isolation or auth.

Reservations have no expiry: an exited orchestrator may have live children.
Only the acquiring instance releases its own returned reservation explicitly.
"""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import stat
import uuid

MAX_CAPACITY = 256
MAX_WRITES = 64
MAX_PATH_BYTES = 4096
MAX_SCOPE_BYTES = 65536
MAX_DATABASE_BYTES = 32 * 1024 * 1024
APPLICATION_ID = 0x41444D31


def _text(value, label, limit):
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value.encode("utf-8")) > limit
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise ValueError(f"invalid admission {label}")
    return value


def _scopes(root, writes):
    try:
        root = Path(root).resolve(strict=True)
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        raise ValueError("admission root must be an existing directory") from exc
    if not root.is_dir():
        raise ValueError("admission root must be an existing directory")
    _text(str(root), "root path", MAX_PATH_BYTES)
    if writes is None:
        return [str(root)]
    if not isinstance(writes, list) or len(writes) > MAX_WRITES:
        raise ValueError("admission writes must be None or a list of at most 64 paths")
    result = set()
    for name in writes:
        _text(name, "write path", MAX_PATH_BYTES)
        if Path(name).is_absolute():
            raise ValueError("admission write paths must be project-relative")
        candidate = root / name
        try:
            parts = candidate.relative_to(root).parts
        except ValueError:
            raise ValueError("admission write path is outside the project") from None
        current = root
        for part in parts:
            current = current.parent if part == ".." else current / part
            try:
                current = current.resolve(strict=False)
                current.relative_to(root)
            except (OSError, ValueError, RuntimeError):
                raise ValueError("admission write path escapes the project") from None
        try:
            canonical = candidate.resolve(strict=False)
            canonical.relative_to(root)
        except (OSError, ValueError, RuntimeError) as exc:
            raise ValueError(
                "admission write path cannot be resolved inside the project"
            ) from exc
        _text(str(canonical), "canonical write path", MAX_PATH_BYTES)
        result.add(str(canonical))
    encoded = json.dumps(sorted(result), ensure_ascii=False)
    if len(encoded.encode("utf-8")) > MAX_SCOPE_BYTES:
        raise ValueError("admission write scope exceeds 64 KiB")
    return sorted(result)


def _overlap(left, right):
    a, b = Path(left), Path(right)
    return a == b or a in b.parents or b in a.parents


class Admission:
    def __init__(self, home: Path, capacity: int):
        if type(capacity) is not int or not 1 <= capacity <= MAX_CAPACITY:
            raise ValueError("admission capacity must be an integer in 1..256")
        self.capacity = capacity
        self.path = (
            Path(home).expanduser().resolve() / "admission" / "reservations.sqlite"
        )
        self._owned = set()
        with self._db():
            pass

    @contextmanager
    def _db(self):
        directory = self.path.parent
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("admission store directory is redirected")
        if stat.S_IMODE(directory.stat().st_mode) & 0o077:
            raise ValueError("admission store directory must be private")
        try:
            fd = os.open(
                self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600
            )
        except OSError as exc:
            raise ValueError("admission database cannot be opened safely") from exc
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError(
                    "admission database must be a single-link regular file"
                )
            if stat.S_IMODE(info.st_mode) & 0o077:
                raise ValueError("admission database must be private")
            if info.st_size > MAX_DATABASE_BYTES:
                raise ValueError("admission database exceeds 32 MiB")
        finally:
            os.close(fd)
        db = None
        try:
            db = sqlite3.connect(str(self.path), timeout=30, isolation_level=None)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA trusted_schema=OFF")
            db.execute("BEGIN IMMEDIATE")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            application = db.execute("PRAGMA application_id").fetchone()[0]
            if version == 0 and application == 0:
                if db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' LIMIT 1"
                ).fetchone():
                    raise ValueError(
                        "unrecognized admission database; existing tables retained"
                    )
                db.execute(
                    "CREATE TABLE settings (id INTEGER PRIMARY KEY CHECK(id=1), capacity INTEGER NOT NULL)"
                )
                db.execute("INSERT INTO settings VALUES (1,?)", (self.capacity,))
                db.execute(
                    "CREATE TABLE reservations (id TEXT PRIMARY KEY, owner TEXT NOT NULL, "
                    "task TEXT NOT NULL, writes TEXT NOT NULL)"
                )
                db.execute(f"PRAGMA application_id={APPLICATION_ID}")
                db.execute("PRAGMA user_version=1")
            elif version != 1 or application != APPLICATION_ID:
                raise ValueError("unsupported admission database identity or version")
            if db.execute("PRAGMA page_size").fetchone()[0] != 4096:
                raise ValueError("unsupported admission database page size")
            db.execute("PRAGMA max_page_count=8192")
            settings = db.execute("SELECT id,capacity FROM settings").fetchall()
            if len(settings) != 1 or settings[0]["id"] != 1:
                raise ValueError("admission capacity record is invalid")
            if settings[0]["capacity"] != self.capacity:
                raise ValueError(
                    "admission capacity conflicts with the persisted capacity"
                )
            yield db
            db.commit()
        except sqlite3.Error as exc:
            # SQLite messages may contain private stored labels or paths.
            raise ValueError(
                "admission storage failed (%s)" % type(exc).__name__
            ) from None
        finally:
            if db is not None:
                db.close()

    def _rows(self, db):
        rows = db.execute(
            "SELECT id,owner,task,writes FROM reservations ORDER BY id LIMIT ?",
            (self.capacity + 1,),
        ).fetchall()
        if len(rows) > self.capacity:
            raise ValueError("admission reservations exceed persisted capacity")
        result = []
        for row in rows:
            item = dict(row)
            if (
                not isinstance(item["id"], str)
                or len(item["id"]) != 32
                or any(char not in "0123456789abcdef" for char in item["id"])
            ):
                raise ValueError("invalid admission reservation identity")
            _text(item["owner"], "stored owner", 256)
            _text(item["task"], "stored task", 256)
            raw = item["writes"]
            if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_SCOPE_BYTES:
                raise ValueError("invalid stored admission write scope")
            try:
                writes = json.loads(raw)
            except ValueError:
                raise ValueError("invalid stored admission write scope") from None
            if not isinstance(writes, list) or len(writes) > MAX_WRITES:
                raise ValueError("invalid stored admission write scope")
            for name in writes:
                _text(name, "stored write path", MAX_PATH_BYTES)
                path = Path(name)
                if not path.is_absolute() or ".." in path.parts or str(path) != name:
                    raise ValueError("stored admission write path is not canonical")
            item["writes"] = writes
            result.append(item)
        return result

    def acquire(
        self, root: Path, writes: list[str] | None, owner: str, task: str
    ) -> dict:
        _text(owner, "owner", 256)
        _text(task, "task", 256)
        with self._db() as db:
            canonical = _scopes(root, writes)
            rows = self._rows(db)
            if any(
                _overlap(wanted, held)
                for wanted in canonical
                for row in rows
                for held in row["writes"]
            ):
                return {"admitted": False, "reason": "write_overlap"}
            if len(rows) >= self.capacity:
                return {"admitted": False, "reason": "capacity"}
            reservation = uuid.uuid4().hex
            db.execute(
                "INSERT INTO reservations VALUES (?,?,?,?)",
                (reservation, owner, task, json.dumps(canonical, ensure_ascii=False)),
            )
        self._owned.add(reservation)
        return {"admitted": True, "reason": "admitted", "reservation": reservation}

    def release(self, reservation: str) -> bool:
        _text(reservation, "reservation", 128)
        if reservation not in self._owned:
            return False
        with self._db() as db:
            deleted = (
                db.execute(
                    "DELETE FROM reservations WHERE id=?", (reservation,)
                ).rowcount
                == 1
            )
        self._owned.discard(reservation)
        return deleted

    def inspect(self) -> list[dict]:
        with self._db() as db:
            return self._rows(db)
