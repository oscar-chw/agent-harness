"""Bounded advisory lifecycle observations from host-delivered hook payloads."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
from contextlib import contextmanager

from .operational_state import MAX_EVENTS, Conflict, OperationalState
from .redact import redact

MAX_CONTEXT_BYTES = 1000
MAX_TRACKING_BYTES = 2 * 1024 * 1024  # At most MAX_EVENTS task/hash receipts; no board text.
DELTA_LIMIT = 32
START_EVENTS = {"startup", "resume", "compact"}
EVENTS = START_EVENTS | {"prompt", "stop", "precompact"}
SUMMARY = "Advisory host lifecycle observation; task progress requires independent graph evidence."
PREFIX = "Current local operational state (advisory; recheck before action): "


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _hash(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


@contextmanager
def _tracking_lock(directory, session):
    import fcntl

    for parent in (directory.parent.parent, directory.parent, directory):
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if parent.is_symlink() or not parent.is_dir():
            raise ValueError("hook tracking directory is redirected")
    fd = os.open(directory / (session + ".lock"),
                 os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
            raise ValueError("hook tracking lock must be a private regular file")
        deadline = time.monotonic() + 0.5
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("hook tracking lock unavailable") from None
                time.sleep(0.01)
        yield
    finally:
        os.close(fd)


def _load_tracking(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_size > MAX_TRACKING_BYTES or info.st_mode & 0o077):
            raise ValueError("hook tracking must be a bounded private regular file")
        value = json.loads(stream.read(MAX_TRACKING_BYTES + 1))
    if (not isinstance(value, dict) or type(value.get("cursor")) is not int or value["cursor"] < 0):
        raise ValueError("invalid hook tracking")
    if set(value) == {"cursor", "signature", "status_signature"}:
        # The earlier cursor-only format could acknowledge omitted rows. Replay
        # once into per-row receipts rather than perpetuating that loss.
        return {"cursor": 0, "rows": {}}
    if (set(value) != {"cursor", "rows"} or not isinstance(value["rows"], dict)
            or len(value["rows"]) > MAX_EVENTS
            or any(not isinstance(part, str) or len(part) != 64
                   or any(char not in "0123456789abcdef" for char in part)
                   for pair in value["rows"].items() for part in pair)):
        raise ValueError("invalid hook tracking")
    return value


def _save_tracking(path, value):
    encoded = _json(value)
    if len(encoded.encode("utf-8")) > MAX_TRACKING_BYTES:
        raise ValueError("hook tracking exceeds the bounded receipt budget")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".hook-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _entry(row):
    entry = {"task": redact(row["task"]), "version": row["version"], "activity": row["activity"],
             "memory": row["memory_status"], "evidence": row["evidence_status"],
             "checkpoint_status": row["checkpoint_status"]}
    if row["memory_status"] != "stale":
        for field, limit in (("goal", 100), ("stage", 80), ("summary", 300),
                             ("checkpoint", 120), ("next", 120), ("blocked_on", 120),
                             ("resource", 160)):
            value = row["value"].get(field)
            if value:
                value = redact(value)
                entry[field] = (value if len(value) <= limit else
                                value[:limit // 2] + ' ... ' + value[-(limit // 2 - 5):])
                if len(value) > limit:
                    entry["truncated"] = True
    return entry


def _packet(rows, head, mode, previous_cursor):
    packet = {"mode": mode, "cursor": head, "head": head, "count": len(rows), "tasks": [],
              "omitted": len(rows), "read_more": "harness task status --json"}
    delivered = set()
    for identity, row in rows:
        proposal = {**packet, "tasks": packet["tasks"] + [row],
                    "omitted": len(rows) - len(packet["tasks"]) - 1}
        if len((PREFIX + _json(proposal) + "\n").encode("utf-8")) > MAX_CONTEXT_BYTES:
            if packet["tasks"]:
                continue
            # An individually oversized row still gets an explicit handle.
            # Its display fields are available through read_more, and later
            # rows cannot be starved by UTF-8 width or a large first row.
            handle = {key: row[key] for key in
                      ("task", "version", "activity", "memory", "evidence", "checkpoint_status")}
            proposal["tasks"] = [{**handle, "omitted_fields": True}]
            if len((PREFIX + _json(proposal) + "\n").encode("utf-8")) > MAX_CONTEXT_BYTES:
                raise ValueError("hook budget cannot fit a task handle")
        packet = proposal
        delivered.add(identity)
    if len(delivered) < len(rows):
        packet["cursor"] = previous_cursor
    return PREFIX + _json(packet) + "\n", delivered


def _observe(store, task, event):
    for attempt in range(3):
        snapshot = store.snapshot()
        row = next((row for row in snapshot["tasks"] if row["task"] == task), None)
        value = {**(row["value"] if row else {}), "stage": "observed_" + event, "summary": SUMMARY}
        if row and row["value"] == value:
            return snapshot
        expected = row["version"] if row else 0
        try:
            store.put(task, value, expected=expected,
                      request_id="hook-" + _hash([task, event, expected]),
                      memory_receipt=row["memory_receipt"] if row else None)
            return store.snapshot()
        except Conflict:
            if attempt == 2:
                raise


def _participate(data, event, deliver):
    if not isinstance(data, dict):
        raise ValueError("hook payload must be an object")
    # Older/native payloads without both host handles cannot identify a participant.
    if "cwd" not in data or "session_id" not in data:
        return ""
    scope, session = data["cwd"], data["session_id"]
    if (event not in EVENTS or not isinstance(scope, str) or len(scope.encode()) > 4096
            or not Path(scope).is_absolute() or not Path(scope).is_dir()
            or not isinstance(session, str) or not session.strip() or len(session.encode()) > 4096):
        raise ValueError("hook requires a bounded host project and actual session identity")
    expected_event = ("SessionStart" if event in START_EVENTS else
                      {"prompt": "UserPromptSubmit", "stop": "Stop", "precompact": "PreCompact"}[event])
    if data.get("hook_event_name", expected_event) != expected_event:
        raise ValueError("hook lifecycle event does not match its handler")
    session_hash = hashlib.sha256(session.encode("utf-8")).hexdigest()
    task = "hook-session-" + session_hash
    store = OperationalState.for_host(cwd=scope)
    directory = store.path.parent / "hook-tracking" / store.path.stem
    with _tracking_lock(directory, session_hash):
        tracking_path = directory / (session_hash + ".json")
        previous = _load_tracking(tracking_path)
        snapshot = _observe(store, task, event)
        # Stop/PreCompact stdout belongs to the host protocol. Leave delivery
        # cursors untouched so the next context-capable event still sees changes.
        if not deliver:
            return ""
        peers = sorted((row for row in snapshot["tasks"] if row["task"] != task
                        and not (row["value"].get("stage", "").startswith("observed_")
                                 and not any(row["value"].get(field) for field in
                                             ("goal", "checkpoint", "next", "evidence")))),
                       key=lambda row: (row["memory_status"] != "stale", row["task"]))
        entries = [(_hash(row["task"]), _entry(row)) for row in peers]
        # Fingerprint full semantic state before display clipping. A renewal
        # changes bookkeeping only, while an omitted STOP suffix still matters.
        current = {_hash(row['task']): _hash({key: value for key, value in row.items()
                   if key not in ('version', 'fence', 'until', 'updated_cursor')}) for row in peers}
        acknowledged = dict(previous["rows"]) if previous and event not in START_EVENTS else {}
        acknowledged = {identity: sha for identity, sha in acknowledged.items() if identity in current}
        selected = [(identity, entry) for identity, entry in entries
                    if acknowledged.get(identity) != current[identity]]
        previous_cursor = previous["cursor"] if previous else 0
        output = ""
        delivered = set()
        if selected:
            mode = ("snapshot" if event in START_EVENTS or previous is None
                    or snapshot["cursor"] - previous_cursor > DELTA_LIMIT else "delta")
            output, delivered = _packet(selected, snapshot["cursor"], mode, previous_cursor)
            acknowledged.update({identity: current[identity] for identity in delivered})
        tracking = {"cursor": (previous_cursor if len(delivered) < len(selected) else snapshot["cursor"]),
                    "rows": acknowledged}
        _save_tracking(tracking_path, tracking)
        return output


def participate(data, event, *, deliver=True):
    """Observe a lifecycle point; regular board failures remain advisory and visible."""
    if "op_state" in {name.strip() for name in os.environ.get("HARNESS_DISABLE", "").split(",")}:
        return ""
    try:
        return _participate(data, event, deliver)
    except Exception as exc:
        # This hook boundary must survive storage/host failures without echoing
        # exception text, which can contain private paths or source content.
        print("harness board hooks unavailable: " + type(exc).__name__, file=sys.stderr)
        return ""
