"""Cache inventory is read-only, scoped, and never mistakes cached text for source truth."""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from agent_harness.mcp.kb import KB


def inventory():
    from agent_harness.cache_status import inspect_cache
    return inspect_cache


def test_missing_index_does_not_create_a_harness_directory(tmp_path):
    home = tmp_path / "missing"
    result = inventory()(home, paths=[])
    assert result["status"] == "ABSENT"
    assert not home.exists()


def test_inventory_separates_current_scope_retained_cache_and_sessions(tmp_path):
    own = tmp_path / "docs"
    other = tmp_path / "other"
    own.mkdir()
    other.mkdir()
    first = own / "a.md"
    second = other / "b.md"
    first.write_text("# Current\nCURRENT-CONTENT-CANARY\n")
    second.write_text("# Other\nOTHER-CONTENT-CANARY\n")
    hh = tmp_path / "hh"
    for root in (own, other):
        kb = KB(home=hh, paths=[root])
        kb.refresh()
        kb.close()
    db = hh / "index.sqlite"
    with sqlite3.connect(db) as con:
        con.executescript("CREATE TABLE sess_files(path TEXT); CREATE TABLE sess_msgs(text TEXT);")
        con.execute("INSERT INTO sess_files VALUES ('PRIVATE-PATH-CANARY')")
        con.execute("INSERT INTO sess_msgs VALUES ('SESSION-CONTENT-CANARY')")
        con.commit()
    before = db.read_bytes()
    sources = (first.read_bytes(), second.read_bytes())
    result = inventory()(hh, paths=[own])
    assert result["status"] == "PRESENT"
    assert result["scope"]["discovered_files"] == 1
    assert result["kb"]["current_discovery"]["files"] == 1
    assert result["kb"]["outside_current_discovery"]["files"] == 1
    assert result["kb"]["current_discovery"]["sections"] == 1
    assert result["sessions"] == {"files": 1, "messages": 1}
    assert result["database"]["page_bytes"] >= result["database"]["free_page_bytes"] >= 0
    assert result["eviction_authorized"] is False
    assert "CANARY" not in json.dumps(result)
    assert str(tmp_path) not in json.dumps(result)
    assert db.read_bytes() == before
    assert (first.read_bytes(), second.read_bytes()) == sources
    # Changing the query scope changes counts, not cached rows or either source.
    again = inventory()(hh, paths=[])
    assert again["kb"]["outside_current_discovery"]["files"] == 2
    assert db.read_bytes() == before


def test_corrupt_database_is_unreadable_not_empty_and_is_preserved(tmp_path):
    hh = tmp_path / "hh"
    hh.mkdir()
    db = hh / "index.sqlite"
    db.write_bytes(b"CORRUPT-PRIVATE-CANARY")
    result = inventory()(hh, paths=[])
    assert result["status"] == "UNREADABLE"
    assert "CANARY" not in json.dumps(result)
    assert db.read_bytes() == b"CORRUPT-PRIVATE-CANARY"


def test_cli_uses_the_current_scope_and_fails_on_unreadable_index(tmp_path):
    hh = tmp_path / "hh"
    hh.mkdir()
    (hh / "index.sqlite").write_bytes(b"corrupt")
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "HARNESS_HOME": str(hh), "HARNESS_KB_PATHS": str(tmp_path / "empty")}
    run = subprocess.run([sys.executable, str(root / "bin/harness"), "cache-status"],
                         capture_output=True, text=True, env=env, timeout=10)
    assert run.returncode == 2
    assert json.loads(run.stdout)["status"] == "UNREADABLE"
    assert not run.stderr
