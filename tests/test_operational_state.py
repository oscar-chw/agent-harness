"""The project-owned operational ledger is exercised through separate processes too."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from agent_harness.operational_state import Conflict, OperationalState


def ledger(tmp_path, clock=None):
    (tmp_path / ".git").mkdir(exist_ok=True)
    return OperationalState(tmp_path / "home", tmp_path, clock=clock)


def test_atomic_event_projection_and_idempotent_retry(tmp_path):
    db = ledger(tmp_path)
    first = db.put("build", {"stage": "test"}, expected=0, request_id="put-1")
    assert first["version"] == first["cursor"] == 1
    assert db.put("build", {"stage": "test"}, expected=0, request_id="put-1") == first
    with pytest.raises(Conflict):
        db.put("build", {"stage": "other"}, expected=0, request_id="put-1")
    snap = db.snapshot()
    assert snap["cursor"] == 1
    assert snap["tasks"][0]["value"] == {"stage": "test"}
    assert db.changes(0)["events"] == [{"cursor": 1, "task": "build", "action": "put", "version": 1}]
    assert db.changes(1)["events"] == []


def test_cas_lease_expiry_and_fencing(tmp_path):
    now = [1000.0]
    db = ledger(tmp_path, clock=lambda: now[0])
    db.put("job", {}, expected=0, request_id="p")
    a = db.claim("job", expected=1, request_id="a", ttl=10)
    assert a["fence"] == 1
    with pytest.raises(Conflict):
        db.claim("job", expected=1, request_id="b", ttl=10)
    now[0] += 11
    b = db.claim("job", expected=2, request_id="b", ttl=10)
    assert b["fence"] == 2 and b["token"] != a["token"]
    with pytest.raises(Conflict):
        db.release("job", expected=3, request_id="old", token=a["token"], fence=1)
    assert db.snapshot()["tasks"][0]["fence"] == 2
    done = db.release("job", expected=3, request_id="release", token=b["token"], fence=2)
    assert done["version"] == 4 and done["status"] == "open"


def test_stale_snapshot_and_change_cursor_reconcile(tmp_path):
    db = ledger(tmp_path)
    db.put("a", {"stage": "one"}, expected=0, request_id="a1")
    old = db.snapshot()
    db.put("a", {"stage": "two"}, expected=1, request_id="a2")
    with pytest.raises(Conflict):
        db.put("a", {"stage": "offline"}, expected=old["tasks"][0]["version"], request_id="a3")
    delta = db.changes(old["cursor"])
    assert delta["events"] == [{"cursor": 2, "task": "a", "action": "put", "version": 2}]
    assert db.snapshot()["tasks"][0]["value"] == {"stage": "two"}


def test_sourced_facts_are_not_last_write_wins_task_state(tmp_path):
    db = ledger(tmp_path)
    db.put("investigate", {"stage": "compare evidence"}, expected=0, request_id="p")
    with pytest.raises(ValueError):
        db.put("investigate", {"fact": "source A wins"}, expected=1, request_id="f")
    assert db.snapshot()["tasks"][0]["value"] == {"stage": "compare evidence"}


def test_independent_processes_race_and_recover(tmp_path):
    db = ledger(tmp_path)
    db.put("job", {}, expected=0, request_id="seed")
    script = """
import json,sys
from agent_harness.operational_state import OperationalState,Conflict
db=OperationalState(sys.argv[1],sys.argv[2])
try:
 print(json.dumps({'won':db.claim('job',expected=1,request_id=sys.argv[3],ttl=60)}))
except Conflict:
 print(json.dumps({'lost':True}))
"""
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    ps = [subprocess.Popen([sys.executable, "-c", script, str(tmp_path / "home"), str(tmp_path), f"race-{i}"],
                           env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(5)]
    rows = []
    for p in ps:
        out, err = p.communicate(timeout=15)
        assert p.returncode == 0, err
        rows.append(json.loads(out))
    assert sum("won" in row for row in rows) == 1
    assert db.snapshot()["tasks"][0]["status"] == "leased"


def test_dead_worker_lease_expires_and_new_process_fences_it(tmp_path):
    import time
    db = ledger(tmp_path)
    db.put("job", {}, expected=0, request_id="seed")
    script = """
import json,sys
from agent_harness.operational_state import OperationalState
db=OperationalState(sys.argv[1],sys.argv[2])
print(json.dumps(db.claim('job',expected=int(sys.argv[3]),request_id=sys.argv[4],ttl=1)))
"""
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    def claim(expected, request):
        p = subprocess.run([sys.executable, "-c", script, str(tmp_path / "home"), str(tmp_path),
                            str(expected), request], capture_output=True, text=True, env=env, timeout=10)
        assert p.returncode == 0, p.stderr
        return json.loads(p.stdout)
    dead = claim(1, "dead")  # the process exits without releasing its lease
    time.sleep(max(0, dead["until"] - time.time()) + 0.06)
    replacement = claim(2, "replacement")
    assert replacement["fence"] == dead["fence"] + 1
    with pytest.raises(Conflict):
        db.release("job", expected=3, request_id="old", token=dead["token"], fence=dead["fence"])


def test_cli_and_mcp_use_the_same_host_project_without_model_supplied_scope(tmp_path, monkeypatch):
    from agent_harness.mcp.server import Server, tool_list
    ledger(tmp_path)
    home = tmp_path / "home"
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"), HARNESS_HOME=str(home))
    p = subprocess.run([sys.executable, "-m", "agent_harness.cli", "op", "put"], cwd=tmp_path,
                       input=json.dumps({"task": "shared", "value": {"stage": "analyse"},
                                         "expected": 0, "request_id": "cli-1"}), text=True,
                       capture_output=True, env=env, timeout=10)
    assert p.returncode == 0, p.stderr
    monkeypatch.chdir(tmp_path)
    assert "op_state" not in {tool["name"] for tool in tool_list()}
    monkeypatch.setenv("HARNESS_ENABLE", "op_state")
    assert "op_state" in {tool["name"] for tool in tool_list()}
    server = Server(home=home)
    found = server.call_tool("op_state", {"action": "snapshot"})
    assert found["tasks"][0]["task"] == "shared"
    assert found["tasks"][0]["value"]["stage"] == "analyse"
    with pytest.raises(ValueError):
        server.call_tool("op_state", {"action": "snapshot", "project": str(tmp_path / "other")})


def test_real_mcp_stdio_process_reads_cli_commit(tmp_path):
    ledger(tmp_path)
    source = Path(__file__).resolve().parents[1] / "src"
    env = dict(os.environ, PYTHONPATH=str(source), HARNESS_HOME=str(tmp_path / "home"),
               HARNESS_ENABLE="op_state")
    cli = subprocess.run([sys.executable, "-m", "agent_harness.cli", "op", "put"], cwd=tmp_path,
                         input=json.dumps({"task": "handoff", "value": {"stage": "ready"},
                                           "expected": 0, "request_id": "cli-write"}), text=True,
                         capture_output=True, env=env, timeout=10)
    assert cli.returncode == 0, cli.stderr
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "fixture"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "op_state", "arguments": {"action": "snapshot"}}},
    ]
    server = source / "agent_harness" / "mcp" / "server.py"
    proc = subprocess.run([sys.executable, str(server)], cwd=tmp_path,
                          input="".join(json.dumps(x) + "\n" for x in messages),
                          text=True, capture_output=True, env=env, timeout=10)
    assert proc.returncode == 0, proc.stderr
    replies = [json.loads(line) for line in proc.stdout.splitlines()]
    assert replies[1]["result"]["isError"] is False
    found = json.loads(replies[1]["result"]["content"][0]["text"])
    assert found["tasks"][0]["task"] == "handoff"
    assert found["tasks"][0]["value"] == {"stage": "ready"}


def test_conflicting_sourced_facts_remain_separate_and_withdrawal_invalidates(tmp_path):
    from agent_harness.project_memory import ProjectMemory
    from agent_harness.vault_sources import SourceVault, initialize

    db = ledger(tmp_path)
    project_id = initialize(tmp_path)
    (tmp_path / "observations.md").write_text("site reports on\noperator reports off\n")
    source = SourceVault(tmp_path, project_id).capture("observations.md")
    facts = ProjectMemory(tmp_path, project_id)
    def item(identity, text, line):
        return {"id": identity, "project_id": project_id, "layer": "project_facts", "kind": "fact",
                "scope": "project", "text": text,
                "provenance": [{"source": source, "start_line": line, "end_line": line}],
                "confidence": "verified", "sensitivity": "private", "access_boundary": "local_user",
                "owner": "project-owner", "freshness": "current"}
    first = item("site", "service on", 1)
    second = item("operator", "service off", 2)
    first_receipt = facts.append(first, expected=None)
    second_receipt = facts.append(second, expected=None)
    db.put("inspect", {"stage": "resolve conflict"}, expected=0, request_id="p", memory_receipt=first_receipt)
    assert db.snapshot()["tasks"][0]["memory_status"] == "current"
    facts.append({**first, "freshness": "withdrawn"}, expected=first_receipt)
    assert db.snapshot()["tasks"][0]["memory_status"] == "stale"
    assert db.changes(1)["memory_invalidations"] == ["inspect"]
    assert db.put("inspect", {"stage": "resolve conflict"}, expected=0,
                  request_id="p", memory_receipt=first_receipt)["version"] == 1
    with pytest.raises(Conflict):
        db.claim("inspect", expected=1, request_id="blocked", ttl=10)
    with pytest.raises(ValueError):
        db.put("new", {}, expected=0, request_id="no", memory_receipt=first_receipt)
    assert facts.read(second_receipt, allowed_sensitivities=["private"])["item"]["text"] == "service off"


def test_withdrawal_blocks_lease_renewal_but_not_exact_prior_replay(tmp_path):
    from agent_harness.project_memory import ProjectMemory
    from agent_harness.vault_sources import SourceVault, initialize

    db = ledger(tmp_path)
    project_id = initialize(tmp_path)
    (tmp_path / "evidence.md").write_text("current evidence\n")
    source = SourceVault(tmp_path, project_id).capture("evidence.md")
    item = {"id": "basis", "project_id": project_id, "layer": "project_facts", "kind": "fact",
            "scope": "project", "text": "current evidence",
            "provenance": [{"source": source, "start_line": 1, "end_line": 1}],
            "confidence": "verified", "sensitivity": "private", "access_boundary": "local_user",
            "owner": "project-owner", "freshness": "current"}
    facts = ProjectMemory(tmp_path, project_id)
    receipt = facts.append(item, expected=None)
    db.put("task", {}, expected=0, request_id="put", memory_receipt=receipt)
    claim = db.claim("task", expected=1, request_id="claim", ttl=60)
    facts.append({**item, "freshness": "withdrawn"}, expected=receipt)
    assert db.claim("task", expected=1, request_id="claim", ttl=60) == claim
    with pytest.raises(Conflict):
        db.renew("task", expected=2, request_id="renew", token=claim["token"], fence=claim["fence"])
    assert db.snapshot()["tasks"][0]["version"] == 2
    assert db.release("task", expected=2, request_id="release", token=claim["token"],
                      fence=claim["fence"])["status"] == "open"


def test_failed_transaction_has_no_event_or_request_replay(tmp_path):
    import sqlite3
    db = ledger(tmp_path)
    db.put("job", {}, expected=0, request_id="p")
    with sqlite3.connect(db.path) as connection:
        connection.execute("CREATE TRIGGER deny BEFORE UPDATE ON tasks BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END")
    with pytest.raises(ValueError):
        db.put("job", {"stage": "later"}, expected=1, request_id="failed")
    assert db.snapshot()["cursor"] == 1
    with sqlite3.connect(db.path) as connection:
        assert connection.execute("SELECT count(*) FROM requests WHERE id='failed'").fetchone()[0] == 0


def test_invalid_projection_is_not_reported_as_healthy(tmp_path):
    import sqlite3
    db = ledger(tmp_path)
    db.put("job", {}, expected=0, request_id="p")
    with sqlite3.connect(db.path) as connection:
        connection.execute("UPDATE tasks SET status='done' WHERE id='job'")
    with pytest.raises(ValueError):
        db.snapshot()
    with pytest.raises(ValueError):
        db.claim("job", expected=1, request_id="c")
    with sqlite3.connect(db.path) as connection:
        connection.execute("UPDATE tasks SET status='open', token_hash='orphaned' WHERE id='job'")
    with pytest.raises(ValueError):
        db.snapshot()


def test_colliding_legacy_project_keys_cannot_share_a_ledger(tmp_path, monkeypatch):
    import agent_harness.operational_state as module
    a, b = tmp_path / "a", tmp_path / "b"
    for root in (a, b):
        (root / ".git").mkdir(parents=True)
    # The old key's 32-bit suffix really can collide; force that condition
    # without a probabilistic birthday search in the test suite.
    monkeypatch.setattr(module, "project_key", lambda _root: "same-key", raising=False)
    one = module.OperationalState(tmp_path / "home", a)
    other = module.OperationalState(tmp_path / "home", b)
    one.put("private-task", {}, expected=0, request_id="p")
    assert other.snapshot()["tasks"] == []
