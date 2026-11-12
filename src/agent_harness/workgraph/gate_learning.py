"""Bounded gate observations; no model calls, trusted lessons or rule promotion."""

from contextlib import contextmanager
import hashlib
from pathlib import Path
import sqlite3
import uuid

MAX_RECORDS = 256
MAX_BYTES = 2 * 1024 * 1024


def digest(text):
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


@contextmanager
def store(root, create=False):
    base = Path(root).resolve(strict=True) / ".harness-work"
    folder = base / "gate-learning"
    path = folder / "observations.sqlite"
    for directory in (base, folder):
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise ValueError("learning store directory is redirected or not a directory")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("learning store is redirected or not a regular file")
    if not create and not path.exists():
        yield None
        return
    if path.exists() and path.stat().st_size > MAX_BYTES:
        raise ValueError("learning store exceeds 2 MiB; existing evidence retained")
    if create:
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        ignore = base / ".gitignore"
        try:
            with ignore.open("x", encoding="utf-8") as stream:
                stream.write("*\n")
        except FileExistsError:
            pass  # Existing owner policy is not ours to replace.
    uri = path.as_uri() + ("?mode=rwc" if create else "?mode=ro")
    con = sqlite3.connect(uri, uri=True, timeout=3)
    con.row_factory = sqlite3.Row
    try:
        if create:
            con.execute("BEGIN IMMEDIATE")
            con.execute("CREATE TABLE IF NOT EXISTS gate_observations "
                        "(plan TEXT, node INTEGER, definition_sha256 TEXT, pending TEXT, "
                        "pending_code INTEGER, pending_output TEXT, failure_code INTEGER, "
                        "failure_output_sha256 TEXT, count INTEGER, "
                        "success_code INTEGER, success_output_sha256 TEXT, acceptance_scope TEXT, "
                        "PRIMARY KEY(plan,node,definition_sha256))")
        yield con
        if create:
            con.commit()
    finally:
        con.close()


def observe(root, plan, node, gate, code, output, acceptance=None):
    """Call only for an executed, accepted result, never NOT_RUN/conflict/stale."""
    definition = acceptance or digest(gate)
    scope = "DECLARED_ACCEPTANCE" if acceptance else "COMMAND_ONLY_NOT_CHECK_EQUIVALENCE"
    path = Path(root) / ".harness-work/gate-learning/observations.sqlite"
    if code == 0 and not path.exists():
        return  # Routine successful work creates no extra artifacts.
    with store(root, create=True) as con:
        row = con.execute("SELECT * FROM gate_observations WHERE plan=? AND node=? "
                          "AND definition_sha256=?", (plan, node, definition)).fetchone()
        # A new bound identity (or legacy command) cannot borrow a pending failure.
        con.execute("UPDATE gate_observations SET pending=NULL WHERE plan=? AND node=? "
                    "AND definition_sha256<>?", (plan, node, definition))
        if code != 0:
            if row is None and con.execute("SELECT count(*) FROM gate_observations").fetchone()[0] >= MAX_RECORDS:
                raise ValueError("learning record cap reached; existing evidence retained")
            con.execute("INSERT INTO gate_observations VALUES (?,?,?,?,?,?,NULL,NULL,0,NULL,NULL,?) "
                        "ON CONFLICT(plan,node,definition_sha256) DO UPDATE SET "
                        "pending=excluded.pending,pending_code=excluded.pending_code,"
                        "pending_output=excluded.pending_output",
                        (plan, node, definition, uuid.uuid4().hex, code, digest(output), scope))
        elif row is not None and row["pending"]:
            con.execute("UPDATE gate_observations SET failure_code=pending_code,"
                        "failure_output_sha256=pending_output,pending=NULL,count=count+1,"
                        "success_code=0,success_output_sha256=? WHERE plan=? AND node=? "
                        "AND definition_sha256=?", (digest(output), plan, node, definition))


def inspect(root, plan, node=None, gate=None, acceptance=None):
    with store(root) as con:
        rows = []
        if con is not None:
            sql, args = "SELECT * FROM gate_observations WHERE plan=? AND count>0", [plan]
            if node is not None:
                sql += " AND node=?"
                args.append(node)
            if gate is not None:
                sql += " AND definition_sha256=?"
                args.append(acceptance or digest(gate))
            for row in con.execute(sql + " ORDER BY rowid DESC LIMIT 20", args):
                item = dict(row)
                item.setdefault("acceptance_scope", "UNBOUND_PREQUALIFICATION_FORMAT")
                item["new_failure_pending"] = item.pop("pending") is not None
                item.pop("pending_code")
                item.pop("pending_output")
                item["status"] = "OBSERVED_ONLY"
                item["evidence_command"] = f"plan record {item['plan']} {item['node']}"
                rows.append(item)
    return {"schema": "harness.gate-learning/v1", "observations": rows,
            "promotion": "NOT_RUN", "claim": "outcome sequence only; cause and benefit unverified"}
