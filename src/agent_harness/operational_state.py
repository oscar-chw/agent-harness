"""Local project task coordination shared by CLI and MCP processes.

This is operational state, not a fact store or an authorization boundary. The
workgraph's gate remains the authority for completion. Knowledge stays in
ProjectMemory, with its own source receipts and terminal withdrawal semantics.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import sqlite3
import stat
import time
from contextlib import contextmanager
from pathlib import Path

from .mcp.state import project_root

KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
VALUE_FIELDS = {"goal", "stage", "summary", "next", "resource", "checkpoint", "blocked_on",
                "evidence", "evidence_sha256"}
MAX_EVENTS = 10000
MAX_EVIDENCE_BYTES = 1024 * 1024


class Conflict(ValueError):
    """The caller must refresh the project snapshot before retrying."""


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _digest(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


class OperationalState:
    def __init__(self, home, root, *, clock=None):
        # A CLI/MCP host passes its own cwd, not a project label supplied by a model.
        self.root = project_root(Path(root).resolve(strict=True))
        # The older human-readable project_key has only a 32-bit hash suffix;
        # a collision would expose another project's tasks under the same home.
        identity = hashlib.sha256(os.fsencode(self.root)).hexdigest()
        self.path = Path(home).expanduser().resolve() / "operational" / (identity + ".sqlite")
        self.clock = clock or time.time

    @classmethod
    def for_host(cls, home=None, *, cwd=None):
        from .mcp.kb import harness_home
        return cls(harness_home(home), cwd or Path.cwd())

    @contextmanager
    def _db(self, *, write=False):
        directory = self.path.parent
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("operational store directory is redirected")
        try:
            fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        except OSError as exc:
            raise ValueError("operational database cannot be opened safely") from exc
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError("operational database must be a regular file")
        finally:
            os.close(fd)
        db = None
        try:
            db = sqlite3.connect(str(self.path), timeout=30, isolation_level=None)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA trusted_schema=OFF")
            db.execute("PRAGMA max_page_count=8192")
            # Serialize first-use schema creation too; a read racing a writer
            # must see either the old complete state or the new complete state.
            db.execute("BEGIN IMMEDIATE")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("unsupported operational database version")
            if version == 0:
                db.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY, version INTEGER NOT NULL, value TEXT NOT NULL, "
                           "status TEXT NOT NULL, fence INTEGER NOT NULL, token_hash TEXT, until REAL, memory TEXT)")
                db.execute("CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT NOT NULL, "
                           "action TEXT NOT NULL, version INTEGER NOT NULL)")
                db.execute("CREATE TABLE requests (id TEXT PRIMARY KEY, digest TEXT NOT NULL, result TEXT NOT NULL)")
                db.execute("PRAGMA user_version=1")
            yield db
            db.commit()
        except sqlite3.Error as exc:
            # SQLite errors can embed private row content.
            raise ValueError("operational storage failed (%s)" % type(exc).__name__) from None
        finally:
            if db is not None:
                db.close()  # an exception rolls back the event, projection and request together

    @staticmethod
    def _check_key(value, label):
        if not isinstance(value, str) or not KEY.fullmatch(value):
            raise ValueError("invalid %s identifier" % label)

    @staticmethod
    def _check_version(value):
        if type(value) is not int or value < 0:
            raise ValueError("expected version must be a nonnegative integer")

    def _memory_status(self, receipt):
        if receipt is None:
            return "none"
        try:
            from .project_memory import ProjectMemory
            from .vault_sources import _project
            store = ProjectMemory(self.root, _project(self.root))
            result = store.read(receipt, allowed_sensitivities=["public", "internal", "private"])
            if result["item"]["freshness"] != "current":
                return "stale"
        except (OSError, ValueError, KeyError, PermissionError):
            return "stale"
        return "current"

    def _checkpoint_status(self, value):
        """Check only the project-local file handle; the file's gate remains authoritative."""
        name = value.get("checkpoint")
        if not name:
            return "none"
        try:
            path = Path(name)
            if not path.parts or path.is_absolute() or any(part == ".." for part in path.parts):
                return "invalid"
            candidate = (self.root / path).resolve()
            candidate.relative_to(self.root)
            return "present" if candidate.is_file() else "missing"
        except (OSError, ValueError):
            return "invalid"

    def bind_evidence(self, name):
        """Hash a bounded project-local reference, without reading its text into task state."""
        if not isinstance(name, str) or not name or Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError("evidence must name a project-local file")
        try:
            path = (self.root / name).resolve(strict=True)
            path.relative_to(self.root)
            if not path.is_file() or path.stat().st_size > MAX_EVIDENCE_BYTES:
                raise ValueError("evidence must be a file of at most 1 MiB")
            with path.open("rb") as stream:
                raw = stream.read(MAX_EVIDENCE_BYTES + 1)
            if len(raw) > MAX_EVIDENCE_BYTES:
                raise ValueError("evidence exceeds 1 MiB")
            return hashlib.sha256(raw).hexdigest()
        except (OSError, ValueError) as exc:
            raise ValueError("evidence is missing, outside the project, or too large") from exc

    def _evidence_status(self, value):
        name, sha = value.get("evidence"), value.get("evidence_sha256")
        if name is None and sha is None:
            return "none"
        if not isinstance(name, str) or not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
            return "invalid"
        try:
            return "current" if self.bind_evidence(name) == sha else "stale"
        except ValueError:
            return "missing_or_invalid"

    def _activity(self, row):
        if row["status"] == "withdrawn":
            return "withdrawn"
        if row["memory_status"] == "stale":
            return "stale_memory"
        if row["status"] == "leased":
            return "leased_unverified" if row["until"] > self.clock() else "expired_reclaimable"
        if row["value"].get("blocked_on"):
            return "blocked"
        if row["checkpoint_status"] in ("missing", "invalid"):
            return "checkpoint_missing"
        if row["evidence_status"] not in ("none", "current"):
            return "evidence_stale"
        if not all(row["value"].get(field) for field in ("goal", "checkpoint", "next")):
            return "idle_unprepared"
        return "idle_ready"

    @staticmethod
    def _row(row):
        try:
            value = json.loads(row["value"])
            memory = json.loads(row["memory"]) if row["memory"] else None
        except (TypeError, ValueError):
            raise ValueError("invalid operational projection") from None
        if (not isinstance(row["id"], str) or not KEY.fullmatch(row["id"])
                or type(row["version"]) is not int or row["version"] < 1
                or row["status"] not in ("open", "leased", "withdrawn")
                or type(row["fence"]) is not int or row["fence"] < 0
                or not isinstance(value, dict) or not set(value) <= VALUE_FIELDS
                or any(not isinstance(v, str) for v in value.values())
                or (row["status"] == "leased" and (
                    not isinstance(row["token_hash"], str)
                    or not re.fullmatch(r"[0-9a-f]{64}", row["token_hash"])
                    or not isinstance(row["until"], (int, float)) or not math.isfinite(row["until"])))
                or (row["status"] != "leased" and (row["token_hash"] is not None or row["until"] is not None))
                or (memory is not None and not isinstance(memory, dict))):
            raise ValueError("invalid operational projection")
        return {"task": row["id"], "version": row["version"], "value": value,
                "status": row["status"], "fence": row["fence"], "until": row["until"],
                "memory_receipt": memory}

    def snapshot(self):
        with self._db() as db:
            cursor = db.execute("SELECT COALESCE(MAX(seq),0) FROM events").fetchone()[0]
            rows = [self._row(row) for row in db.execute("SELECT * FROM tasks ORDER BY id")]
        for row in rows:
            row["memory_status"] = self._memory_status(row["memory_receipt"])
            row["checkpoint_status"] = self._checkpoint_status(row["value"])
            row["evidence_status"] = self._evidence_status(row["value"])
            row["activity"] = self._activity(row)
        return {"project": str(self.root), "cursor": cursor, "tasks": rows,
                "consistency": "one operational transaction; memory receipts revalidated separately"}

    def brief(self, *, max_bytes=1000):
        """Small current-state handle for a host SessionStart, never a lease token."""
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("operational brief budget must be positive")
        if not self.path.is_file() and not self.path.is_symlink():
            return ""
        snapshot = self.snapshot()
        rows = snapshot["tasks"]
        if not rows:
            return ""
        rows = sorted(rows, key=lambda row: (row["memory_status"] != "stale", row["task"]))
        prefix = "Current local operational state (advisory; recheck before action): "
        packet = {"cursor": snapshot["cursor"], "count": len(rows),
                  "stale": sum(row["memory_status"] == "stale" for row in rows),
                  "tasks": [], "omitted": len(rows)}
        if len((prefix + _json(packet) + "\n").encode("utf-8")) > max_bytes:
            raise ValueError("operational brief budget cannot fit omission metadata")
        for row in rows:
            entry = {"task": row["task"], "version": row["version"], "activity": row["activity"],
                     "memory": row["memory_status"], "evidence": row["evidence_status"]}
            if row["memory_status"] != "stale":
                for field, limit in (("goal", 100), ("stage", 80), ("checkpoint", 120),
                                     ("next", 120), ("blocked_on", 120)):
                    if row["value"].get(field):
                        entry[field] = row["value"][field][:limit]
            proposal = {**packet, "tasks": packet["tasks"] + [entry],
                        "omitted": len(rows) - len(packet["tasks"]) - 1}
            if len((prefix + _json(proposal) + "\n").encode("utf-8")) > max_bytes:
                break
            packet = proposal
        return prefix + _json(packet) + "\n"

    def changes(self, cursor, *, limit=100):
        if type(cursor) is not int or cursor < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("cursor or limit is invalid")
        with self._db() as db:
            head = db.execute("SELECT COALESCE(MAX(seq),0) FROM events").fetchone()[0]
            if cursor > head:
                raise Conflict("cursor is ahead of this project; take a new snapshot")
            events = [dict(row) for row in db.execute(
                "SELECT seq AS cursor, task, action, version FROM events WHERE seq>? ORDER BY seq LIMIT ?",
                (cursor, limit))]
            linked = [(row["id"], json.loads(row["memory"])) for row in db.execute(
                "SELECT id,memory FROM tasks WHERE memory IS NOT NULL")]
        invalid = [task for task, receipt in linked if self._memory_status(receipt) != "current"]
        return {"cursor": events[-1]["cursor"] if events else cursor, "head": head,
                "events": events, "memory_invalidations": invalid}

    def _mutate(self, task, expected, request_id, action, args, transition):
        self._check_key(task, "task")
        self._check_key(request_id, "request")
        self._check_version(expected)
        digest = _digest({"task": task, "expected": expected, "action": action, "args": args})
        with self._db(write=True) as db:
            replay = db.execute("SELECT digest,result FROM requests WHERE id=?", (request_id,)).fetchone()
            if replay:
                if replay["digest"] != digest:
                    raise Conflict("request id was used for different inputs")
                return json.loads(replay["result"])
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task,)).fetchone()
            if row is not None:
                self._row(row)
            version = row["version"] if row else 0
            if version != expected:
                raise Conflict("task version changed; refresh snapshot and changes")
            if db.execute("SELECT count(*) FROM events").fetchone()[0] >= MAX_EVENTS:
                raise ValueError("operational event cap reached; no history was pruned")
            fields, extra = transition(row)
            version += 1
            db.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                       "version=excluded.version,value=excluded.value,status=excluded.status,"
                       "fence=excluded.fence,token_hash=excluded.token_hash,until=excluded.until,"
                       "memory=excluded.memory", (task, version, *fields))
            db.execute("INSERT INTO events(task,action,version) VALUES (?,?,?)", (task, action, version))
            cursor = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            result = {"task": task, "version": version, "cursor": cursor, **extra}
            db.execute("INSERT INTO requests VALUES (?,?,?)", (request_id, digest, _json(result)))
            return result

    def _validate_value(self, value):
        if (not isinstance(value, dict) or not set(value) <= VALUE_FIELDS
                or any(not isinstance(v, str) or len(v) > 1024 for v in value.values())
                or len(_json(value).encode("utf-8")) > 4096):
            raise ValueError("operational value must contain only bounded task fields, not sourced facts")
        if "checkpoint" in value and self._checkpoint_status(value) == "invalid":
            raise ValueError("checkpoint must name a project-local file")
        if self._evidence_status(value) not in ("none", "current"):
            raise ValueError("evidence must match a bounded project-local file")
        if any(field in value and not value[field].strip() for field in ("goal", "next", "blocked_on")):
            raise ValueError("goal, next and blocked_on must be nonempty when supplied")

    def put(self, task, value, *, expected, request_id, memory_receipt=None):
        self._validate_value(value)
        def change(row):
            if memory_receipt is not None and self._memory_status(memory_receipt) != "current":
                raise ValueError("memory dependency is not a current source-backed receipt")
            if row and row["status"] == "withdrawn":
                raise Conflict("withdrawal is terminal; choose a new task id")
            if row and row["status"] == "leased" and row["until"] > self.clock():
                raise Conflict("active lease prevents an unowned task update")
            fence = row["fence"] if row else 0
            return (_json(value), "open", fence, None, None,
                    _json(memory_receipt) if memory_receipt is not None else None), {"status": "open"}
        return self._mutate(task, expected, request_id, "put", [value, memory_receipt], change)

    def checkpoint(self, task, value, *, expected, request_id):
        if (not isinstance(value, dict) or not all(value.get(field) for field in ("goal", "checkpoint", "next"))
                or self._checkpoint_status(value) != "present"):
            raise ValueError("checkpoint needs a goal, existing project-local file and next action")
        self._validate_value(value)
        def change(row):
            if row and row["status"] == "withdrawn":
                raise Conflict("withdrawal is terminal; choose a new task id")
            if row and row["status"] == "leased" and row["until"] > self.clock():
                raise Conflict("active lease prevents an unowned task update")
            return (_json(value), "open", row["fence"] if row else 0, None, None,
                    row["memory"] if row else None), {"status": "open"}
        return self._mutate(task, expected, request_id, "checkpoint", [value], change)

    def status(self, task=None):
        snapshot = self.snapshot()
        if task is not None:
            self._check_key(task, "task")
            snapshot["tasks"] = [row for row in snapshot["tasks"] if row["task"] == task]
            if not snapshot["tasks"]:
                raise ValueError("task is absent from this project")
        return snapshot

    def evidence(self, task):
        row = self.status(task)["tasks"][0]
        return {"task": task, "path": row["value"].get("evidence"),
                "sha256": row["value"].get("evidence_sha256"),
                "status": row["evidence_status"], "claim": "reference_only"}

    def stop(self, task, reason, *, expected, request_id):
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 1024:
            raise ValueError("stop needs a bounded reason")
        def change(row):
            if row is None or row["status"] == "withdrawn":
                raise Conflict("task is absent or withdrawn")
            if row["status"] == "leased" and row["until"] > self.clock():
                raise Conflict("active lease cannot be stopped by a ledger flag; stop the worker separately")
            value = json.loads(row["value"])
            value["blocked_on"] = reason
            return (_json(value), "open", row["fence"], None, None, row["memory"]), {
                "status": "open", "blocked_on": reason}
        return self._mutate(task, expected, request_id, "stop", [reason], change)

    def resume(self, task, *, expected, request_id):
        def change(row):
            if row is None or row["status"] == "withdrawn":
                raise Conflict("task is absent or withdrawn")
            if row["status"] == "leased" and row["until"] > self.clock():
                raise Conflict("active lease prevents an unowned resume")
            value = json.loads(row["value"])
            if not value.get("blocked_on"):
                raise Conflict("task is not stopped or blocked")
            if self._checkpoint_status(value) != "present" or self._evidence_status(value) not in ("none", "current"):
                raise Conflict("checkpoint or evidence changed; update it before resuming")
            if row["memory"] and self._memory_status(json.loads(row["memory"])) != "current":
                raise Conflict("memory dependency changed; revalidate before resuming")
            del value["blocked_on"]
            return (_json(value), "open", row["fence"], None, None, row["memory"]), {"status": "open"}
        return self._mutate(task, expected, request_id, "resume", [], change)

    def claim(self, task, *, expected, request_id, ttl=300):
        if type(ttl) is not int or not 1 <= ttl <= 3600:
            raise ValueError("lease duration must be 1..3600 seconds")
        token = secrets.token_urlsafe(32)
        def change(row):
            if row is None or row["status"] == "withdrawn":
                raise Conflict("task is absent or withdrawn")
            value = json.loads(row["value"])
            if value.get("blocked_on"):
                raise Conflict("task is blocked; update the checkpoint after resolving the reason")
            if self._checkpoint_status(value) in ("missing", "invalid"):
                raise Conflict("task checkpoint is missing or outside the project")
            if self._evidence_status(value) not in ("none", "current"):
                raise Conflict("task evidence changed; update the checkpoint before claiming")
            if row["memory"] and self._memory_status(json.loads(row["memory"])) != "current":
                raise Conflict("memory dependency changed; revalidate before claiming")
            if row["status"] == "leased" and row["until"] > self.clock():
                raise Conflict("task lease is held until expiry")
            fence = row["fence"] + 1
            until = self.clock() + ttl
            return (row["value"], "leased", fence, _digest(token), until, row["memory"]), {
                "status": "leased", "fence": fence, "token": token, "until": until}
        return self._mutate(task, expected, request_id, "claim", [ttl], change)

    def _owned(self, row, token, fence):
        if (row is None or row["status"] != "leased" or row["until"] <= self.clock()
                or type(fence) is not int or row["fence"] != fence
                or not isinstance(token, str) or row["token_hash"] != _digest(token)):
            raise Conflict("lease is absent, expired or fenced out")

    def renew(self, task, *, expected, request_id, token, fence, ttl=300):
        if type(ttl) is not int or not 1 <= ttl <= 3600:
            raise ValueError("lease duration must be 1..3600 seconds")
        def change(row):
            self._owned(row, token, fence)
            if row["memory"] and self._memory_status(json.loads(row["memory"])) != "current":
                raise Conflict("memory dependency changed; lease cannot be renewed")
            if self._evidence_status(json.loads(row["value"])) not in ("none", "current"):
                raise Conflict("evidence changed; lease cannot be renewed")
            until = self.clock() + ttl
            return (row["value"], "leased", fence, row["token_hash"], until, row["memory"]), {
                "status": "leased", "fence": fence, "until": until}
        return self._mutate(task, expected, request_id, "renew", [token, fence, ttl], change)

    def release(self, task, *, expected, request_id, token, fence):
        def change(row):
            self._owned(row, token, fence)
            return (row["value"], "open", fence, None, None, row["memory"]), {"status": "open"}
        return self._mutate(task, expected, request_id, "release", [token, fence], change)

    def withdraw(self, task, *, expected, request_id):
        def change(row):
            if row is None or row["status"] == "withdrawn":
                raise Conflict("task is absent or already withdrawn")
            if row["status"] == "leased" and row["until"] > self.clock():
                raise Conflict("active lease prevents an unowned withdrawal")
            return (row["value"], "withdrawn", row["fence"], None, None, row["memory"]), {
                "status": "withdrawn"}
        return self._mutate(task, expected, request_id, "withdraw", [], change)


def dispatch(store, request):
    """One checked surface for CLI and MCP; scope always comes from the host."""
    if not isinstance(request, dict):
        raise ValueError("operational request must be an object")
    action = request.get("action")
    fields = {
        "snapshot": {"action"}, "changes": {"action", "cursor", "limit"},
        "status": {"action", "task"}, "evidence": {"action", "task"},
        "checkpoint": {"action", "task", "value", "expected", "request_id"},
        "stop": {"action", "task", "reason", "expected", "request_id"},
        "resume": {"action", "task", "expected", "request_id"},
        "put": {"action", "task", "value", "expected", "request_id", "memory_receipt"},
        "claim": {"action", "task", "expected", "request_id", "ttl"},
        "renew": {"action", "task", "expected", "request_id", "token", "fence", "ttl"},
        "release": {"action", "task", "expected", "request_id", "token", "fence"},
        "withdraw": {"action", "task", "expected", "request_id"},
    }
    required = {
        "snapshot": {"action"}, "changes": {"action", "cursor"},
        "status": {"action"}, "evidence": {"action", "task"},
        "checkpoint": {"action", "task", "value", "expected", "request_id"},
        "stop": {"action", "task", "reason", "expected", "request_id"},
        "resume": {"action", "task", "expected", "request_id"},
        "put": {"action", "task", "value", "expected", "request_id"},
        "claim": {"action", "task", "expected", "request_id"},
        "renew": {"action", "task", "expected", "request_id", "token", "fence"},
        "release": {"action", "task", "expected", "request_id", "token", "fence"},
        "withdraw": {"action", "task", "expected", "request_id"},
    }
    if action not in fields or not required[action] <= set(request) or not set(request) <= fields[action]:
        raise ValueError("invalid operational action or fields")
    args = {k: v for k, v in request.items() if k != "action"}
    return getattr(store, action)(**args)
