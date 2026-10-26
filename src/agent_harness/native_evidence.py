"""Opt-in Codex JSONL evidence pointers in the harness's existing derived SQLite index.

This adapter observes lifecycle records; it does not authenticate user authority, interpret
messages, infer task success, or promote lessons. No message/tool bodies are copied. Incremental
checks cover file identity and bounded prefix/checkpoint anchors, NOT arbitrary historical edits.
Call check on each selected receipt before curation; it hashes the original cited bytes again.
The source is retained by its owner. Deleting it makes its receipts unavailable, not verified.
"""
import hashlib
import json
import os
import re
import sqlite3
import stat
from pathlib import Path

from .mcp.kb import connect

ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}\Z")
KINDS = {"UserMessage": "user", "AgentMessage": "assistant"}
RECEIPT = ("source_id", "turn_id", "offset", "length", "sha256", "kind", "timestamp")
ANCHOR_BYTES = 1024


def _positive(value, name, ceiling):
    if type(value) is not int or not 0 < value <= ceiling:
        raise ValueError(f"{name} must be a positive integer at most {ceiling}")


def _identity(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError("invalid evidence source/turn identity")
    return value


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _span(stream, offset, length):
    stream.seek(offset)
    return stream.read(length)


class NativeEvidence:
    def __init__(self, db_path, *, readonly=False):
        self.db_path = Path(db_path).resolve()
        if readonly:
            self.con = sqlite3.connect(self.db_path.as_uri() + "?mode=ro", uri=True)
            self.con.row_factory = sqlite3.Row
            return
        self.con = connect(self.db_path)
        self.con.executescript("""
            CREATE TABLE IF NOT EXISTS native_sources(
                id TEXT PRIMARY KEY, path TEXT NOT NULL, dev INTEGER, ino INTEGER,
                cursor INTEGER, active TEXT, head_length INTEGER, head_hash TEXT,
                anchor_length INTEGER, anchor_hash TEXT);
            CREATE TABLE IF NOT EXISTS native_turns(
                source_id TEXT, turn_id TEXT, status TEXT,
                PRIMARY KEY(source_id, turn_id));
            CREATE TABLE IF NOT EXISTS native_records(
                source_id TEXT, turn_id TEXT, offset INTEGER, length INTEGER,
                sha256 TEXT, kind TEXT, timestamp TEXT,
                PRIMARY KEY(source_id, offset));
            CREATE INDEX IF NOT EXISTS native_turn_records
                ON native_records(source_id, turn_id, offset);
        """)
        self.con.commit()

    def close(self):
        self.con.close()

    def _commit(self):
        self.con.commit()

    def _source(self, source_id):
        return self.con.execute("SELECT * FROM native_sources WHERE id=?", (source_id,)).fetchone()

    @staticmethod
    def _open(path):
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise ValueError("evidence source must be a regular file")
        return os.fdopen(fd, "rb")

    @staticmethod
    def _verify(stream, source, path):
        info = os.fstat(stream.fileno())
        if ((info.st_dev, info.st_ino) != (source["dev"], source["ino"])
                or str(path) != source["path"] or info.st_size < source["cursor"]):
            raise ValueError("evidence source identity changed or source was truncated")
        head = _span(stream, 0, source["head_length"])
        tail = _span(stream, source["cursor"] - source["anchor_length"], source["anchor_length"])
        if _digest(head) != source["head_hash"] or _digest(tail) != source["anchor_hash"]:
            raise ValueError("evidence source checkpoint changed")
        return len(head) + len(tail)

    def observe(self, source_id, path, *, max_records=1000, max_bytes=32 * 1024 * 1024,
                max_record_bytes=8 * 1024 * 1024, max_pointers=100000, stop_offset=None):
        """Commit one bounded chunk and cursor atomically; a failed chunk is safe to replay.

        max_bytes counts source bytes read, including an incomplete tail; integrity_bytes is
        reported separately (at most 8192). A record too large for a fresh chunk fails loudly.
        The pointer cap never deletes evidence or rewrites existing memory to make room.
        """
        _identity(source_id)
        if stop_offset is not None and (type(stop_offset) is not int or stop_offset < 0):
            raise ValueError("stop_offset must be a nonnegative integer")
        for value, name, cap in ((max_records, "max_records", 100000),
                                 (max_bytes, "max_bytes", 64 * 1024 * 1024),
                                 (max_record_bytes, "max_record_bytes", 16 * 1024 * 1024),
                                 (max_pointers, "max_pointers", 1000000)):
            _positive(value, name, cap)
        path = Path(path).absolute()
        if path.is_symlink() or path.resolve() == self.db_path:
            raise ValueError("evidence source cannot be redirected or be the index")
        path = path.resolve(strict=True)
        self.con.execute("BEGIN IMMEDIATE")
        try:
            with self._open(path) as stream:
                info = os.fstat(stream.fileno())
                source = self._source(source_id)
                integrity = self._verify(stream, source, path) if source else 0
                cursor = source["cursor"] if source else 0
                end = info.st_size if stop_offset is None else stop_offset
                if not cursor <= end <= info.st_size:
                    raise ValueError("stop_offset is outside the available source interval")
                if not source and self.con.execute("SELECT count(*) FROM native_sources").fetchone()[0] >= 1000:
                    raise ValueError("native evidence source cap exceeded")
                active = source["active"] if source else None
                scanned, count, completed, added, excluded, partial = 0, 0, 0, 0, 0, False
                stream.seek(cursor)
                while count < max_records and scanned < max_bytes and cursor < end:
                    allowance = min(max_bytes - scanned, max_record_bytes + 1, end - cursor)
                    raw = stream.readline(allowance)
                    scanned += len(raw)
                    if not raw.endswith(b"\n"):
                        if len(raw) > max_record_bytes:
                            raise ValueError(f"source record at offset {cursor} exceeds max_record_bytes")
                        if cursor + len(raw) < end:
                            if count == 0:
                                raise ValueError(f"source record at offset {cursor} exceeds chunk budget")
                            break
                        partial = True
                        break
                    if len(raw) > max_record_bytes:
                        raise ValueError(f"source record at offset {cursor} exceeds max_record_bytes")
                    try:
                        record = json.loads(raw)
                    except (ValueError, UnicodeError):
                        raise ValueError(f"invalid source record at offset {cursor}") from None
                    if not isinstance(record, dict) or not isinstance(record.get("payload"), dict):
                        raise ValueError(f"invalid source record schema at offset {cursor}")
                    payload = record["payload"]
                    event = payload.get("type") if record.get("type") == "event_msg" else None
                    kind, turn = None, payload.get("turn_id", active)
                    if event == "task_started":
                        active = _identity(payload.get("turn_id"))
                        if active.startswith("external-import-turn-"):
                            active = None
                        else:
                            self.con.execute("INSERT OR IGNORE INTO native_turns VALUES (?, ?, 'open')",
                                             (source_id, active))
                    elif isinstance(turn, str) and ID.fullmatch(turn) and not turn.startswith("external-import-turn-"):
                        state = self.con.execute("SELECT status FROM native_turns WHERE source_id=? AND turn_id=?",
                                                 (source_id, turn)).fetchone()
                        if state and state[0] == "open":
                            if event in ("task_complete", "turn_aborted"):
                                status = "completed" if event == "task_complete" else "aborted"
                                kind = "completion" if status == "completed" else "abort"
                                self.con.execute("UPDATE native_turns SET status=? WHERE source_id=? AND turn_id=?",
                                                 (status, source_id, turn))
                                completed += status == "completed"
                            elif event == "item_completed":
                                item = payload.get("item")
                                kind = KINDS.get(item.get("type")) if isinstance(item, dict) else None
                            elif record.get("type") == "compacted":
                                kind = "compaction"
                    if kind:
                        timestamp = record.get("timestamp", "")
                        if not isinstance(timestamp, str) or len(timestamp) > 80:
                            raise ValueError(f"invalid record timestamp at offset {cursor}")
                        self.con.execute("INSERT INTO native_records VALUES (?, ?, ?, ?, ?, ?, ?)",
                                         (source_id, turn, cursor, len(raw), _digest(raw), kind, timestamp))
                        added += 1
                    else:
                        excluded += 1
                    cursor += len(raw)
                    count += 1
                total = self.con.execute("SELECT (SELECT count(*) FROM native_records) + "
                                         "(SELECT count(*) FROM native_turns)").fetchone()[0]
                if total > max_pointers:
                    raise ValueError("native evidence pointer storage cap exceeded; no records were pruned")
                current = path.stat()
                if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino) or current.st_size < info.st_size:
                    raise ValueError("evidence source changed during observation")
                # Existing checkpoint is rechecked before publishing a new one. Appending is allowed.
                if source:
                    integrity += self._verify(stream, source, path)
                head_length, anchor_length = min(cursor, ANCHOR_BYTES), min(cursor, ANCHOR_BYTES)
                head = _digest(_span(stream, 0, head_length))
                anchor = _digest(_span(stream, cursor - anchor_length, anchor_length))
                integrity += head_length + anchor_length
                self.con.execute("INSERT OR REPLACE INTO native_sources VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                 (source_id, str(path), info.st_dev, info.st_ino, cursor, active,
                                  head_length, head, anchor_length, anchor))
                self._commit()
                return {"source_id": source_id, "cursor": cursor, "snapshot_bytes": end,
                        "scanned_bytes": scanned, "integrity_bytes": integrity,
                        "scanned_records": count, "added_pointers": added, "excluded_records": excluded,
                        "completed_turns": completed, "partial_tail": partial, "caught_up": cursor == end}
        except BaseException:
            self.con.rollback()
            raise

    def page(self, source_id, *, status="completed", after=-1, limit=20, max_bytes=16384):
        """Page pointers in source order. A lifecycle completion is not task-quality evidence."""
        _identity(source_id)
        _positive(limit, "limit", 100)
        _positive(max_bytes, "max_bytes", 1024 * 1024)
        if status not in ("completed", "aborted", "open") or type(after) is not int or after < -1:
            raise ValueError("invalid status or offset")
        rows = self.con.execute("""SELECT r.* FROM native_records r JOIN native_turns t
            ON r.source_id=t.source_id AND r.turn_id=t.turn_id
            WHERE r.source_id=? AND t.status=? AND r.offset>? ORDER BY r.offset LIMIT ?""",
                                (source_id, status, after, limit + 1)).fetchall()
        result = {"schema": "harness.native-evidence/v1", "source_id": source_id, "status": status,
                  "records": [], "next_offset": None}
        for row in rows[:limit]:
            result["records"].append(dict(row))
            result["next_offset"] = row["offset"]
            if len(json.dumps(result, ensure_ascii=False).encode()) > max_bytes:
                result["records"].pop()
                break
        if rows and not result["records"]:
            raise ValueError("evidence pointer exceeds page budget")
        result["next_offset"] = (result["records"][-1]["offset"]
                                 if len(result["records"]) < len(rows) else None)
        if len(json.dumps(result, ensure_ascii=False).encode()) > max_bytes:
            raise ValueError("evidence envelope exceeds page budget")
        return result

    def check(self, receipt):
        """Read back a single original span. Does not expose text or validate its meaning."""
        if not isinstance(receipt, dict) or set(receipt) != set(RECEIPT):
            raise ValueError("invalid native evidence receipt")
        _identity(receipt["source_id"])
        row = self.con.execute("SELECT * FROM native_records WHERE source_id=? AND offset=?",
                               (receipt["source_id"], receipt["offset"])).fetchone()
        if not row or dict(row) != receipt:
            raise ValueError("receipt does not match indexed source evidence")
        source = self._source(receipt["source_id"])
        with self._open(source["path"]) as stream:
            self._verify(stream, source, Path(source["path"]))
            raw = _span(stream, row["offset"], row["length"])
        if len(raw) != row["length"] or _digest(raw) != row["sha256"]:
            raise ValueError("cited source record changed")
        return {"verified": True, "receipt": receipt, "claim": "original-record-bytes-only"}


def add_parser(subparsers):
    parser = subparsers.add_parser("evidence", help="opt-in native transcript pointers; no message copying or lesson promotion")
    actions = parser.add_subparsers(dest="evidence_action", required=True)
    for action in ("scan", "page", "check"):
        sub = actions.add_parser(action)
        sub.add_argument("--index", required=True, help="explicit existing harness index.sqlite, or an isolated pilot index")
        if action != "check":
            sub.add_argument("--source-id", required=True)
        if action == "scan":
            sub.add_argument("--source", required=True)
            sub.add_argument("--max-records", type=int, default=1000)
            sub.add_argument("--max-bytes", type=int, default=32 * 1024 * 1024)
            sub.add_argument("--stop-offset", type=int)
        elif action == "page":
            sub.add_argument("--status", choices=("completed", "aborted", "open"), default="completed")
            sub.add_argument("--after", type=int, default=-1)
            sub.add_argument("--limit", type=int, default=20)
            sub.add_argument("--max-bytes", type=int, default=16384)
        else:
            sub.add_argument("--receipt", required=True)


def command(args):
    import sys
    index = None
    try:
        reading = args.evidence_action != "scan"
        if reading and not Path(args.index).is_file():
            raise ValueError("evidence index is missing")
        index = NativeEvidence(args.index, readonly=reading)
        if args.evidence_action == "scan":
            result = index.observe(args.source_id, args.source, max_records=args.max_records,
                                   max_bytes=args.max_bytes, stop_offset=args.stop_offset)
        elif args.evidence_action == "page":
            if not index._source(args.source_id):
                raise ValueError("source is absent from evidence index")
            result = index.page(args.source_id, status=args.status, after=args.after,
                                limit=args.limit, max_bytes=args.max_bytes)
        else:
            if len(args.receipt.encode()) > 4096:
                raise ValueError("evidence receipt exceeds input budget")
            result = index.check(json.loads(args.receipt))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"harness evidence: {error}", file=sys.stderr)
        return 2
    finally:
        if index:
            index.close()
