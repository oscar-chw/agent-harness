"""One isolated ledger shared by actual CLI and MCP stdio processes."""
import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path

from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "src/agent_harness/mcp/server.py"


def env_for(tmp_path):
    (tmp_path / ".git").mkdir(exist_ok=True)
    return dict(os.environ, PYTHONPATH=str(ROOT / "src"), HARNESS_HOME=str(tmp_path / "home"),
                HARNESS_ENABLE="op_state", PYTHONNOUSERSITE="1")


def cli(tmp_path, env, action, payload):
    p = subprocess.run([sys.executable, "-m", "agent_harness.cli", "op", action], cwd=tmp_path,
                       input=json.dumps(payload), capture_output=True, text=True, env=env, timeout=10)
    return p.returncode, json.loads(p.stdout) if p.stdout else p.stderr


def mcp(tmp_path, env, action, **args):
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "other-client"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "op_state", "arguments": {"action": action, **args}}},
    ]
    p = subprocess.run([sys.executable, str(SERVER)], cwd=tmp_path,
                       input="".join(json.dumps(row) + "\n" for row in messages),
                       capture_output=True, text=True, env=env, timeout=10)
    assert p.returncode == 0, p.stderr
    rows = [json.loads(line) for line in p.stdout.splitlines()]
    result = rows[1]["result"]
    return result["isError"], json.loads(result["content"][0]["text"]) if not result["isError"] else result["content"][0]["text"]


def test_cli_and_mcp_reconcile_stale_retry_crash_and_fencing(tmp_path):
    env = env_for(tmp_path)
    rc, first = cli(tmp_path, env, "put", {"task": "build", "value": {"stage": "analyse"},
                                        "expected": 0, "request_id": "put-a"})
    assert rc == 0 and first["cursor"] == 1
    error, start = mcp(tmp_path, env, "snapshot")
    assert not error and start["cursor"] == 1 and start["tasks"][0]["version"] == 1

    rc, second = cli(tmp_path, env, "put", {"task": "build", "value": {"stage": "implement"},
                                         "expected": 1, "request_id": "put-b"})
    assert rc == 0 and second["cursor"] == 2
    error, stale = mcp(tmp_path, env, "put", task="build", value={"stage": "offline"},
                       expected=1, request_id="offline")
    assert error and "refresh" in stale
    error, delta = mcp(tmp_path, env, "changes", cursor=start["cursor"])
    assert not error and delta["events"] == [
        {"cursor": 2, "task": "build", "action": "put", "version": 2}]
    assert mcp(tmp_path, env, "snapshot")[1]["tasks"][0]["value"] == {"stage": "implement"}

    # Multiple real process startups can consume over a second under load;
    # keep the lease live through the race, then still wait for true expiry.
    error, claim = mcp(tmp_path, env, "claim", task="build", expected=2, request_id="claim-a", ttl=5)
    assert not error and claim["fence"] == 1
    assert mcp(tmp_path, env, "claim", task="build", expected=2, request_id="claim-a", ttl=5) == (False, claim)
    assert mcp(tmp_path, env, "snapshot")[1]["cursor"] == 3  # duplicate emitted no event
    rc, live_race = cli(tmp_path, env, "claim", {"task": "build", "expected": 3,
                                             "request_id": "race", "ttl": 1})
    assert rc == 2 and "lease" in live_race
    # The first MCP process has exited without releasing the lease.
    time.sleep(max(0, claim["until"] - time.time()) + 0.06)
    rc, takeover = cli(tmp_path, env, "claim", {"task": "build", "expected": 3,
                                            "request_id": "takeover", "ttl": 10})
    assert rc == 0 and takeover["fence"] == 2
    error, old = mcp(tmp_path, env, "release", task="build", expected=4, request_id="old",
                     token=claim["token"], fence=claim["fence"])
    assert error and "fenced" in old
    rc, released = cli(tmp_path, env, "release", {"task": "build", "expected": 4,
                                               "request_id": "released", "token": takeover["token"],
                                               "fence": takeover["fence"]})
    assert rc == 0 and released["status"] == "open"


def test_mcp_detects_external_memory_withdrawal_without_operational_event(tmp_path):
    env = env_for(tmp_path)
    project_id = initialize(tmp_path)
    (tmp_path / "source.md").write_text("temporary assertion\n")
    source = SourceVault(tmp_path, project_id).capture("source.md")
    item = {"id": "claim", "project_id": project_id, "layer": "project_facts", "kind": "fact",
            "scope": "project", "text": "temporary assertion",
            "provenance": [{"source": source, "start_line": 1, "end_line": 1}],
            "confidence": "verified", "sensitivity": "private", "access_boundary": "local_user",
            "owner": "project-owner", "freshness": "current"}
    facts = ProjectMemory(tmp_path, project_id)
    receipt = facts.append(item, expected=None)
    rc, created = cli(tmp_path, env, "put", {"task": "linked", "value": {"stage": "use claim"},
                                            "expected": 0, "request_id": "linked", "memory_receipt": receipt})
    assert rc == 0 and created["cursor"] == 1
    facts.append({**item, "freshness": "withdrawn"}, expected=receipt)
    error, snapshot = mcp(tmp_path, env, "snapshot")
    assert not error and snapshot["tasks"][0]["memory_status"] == "stale"
    error, changes = mcp(tmp_path, env, "changes", cursor=1)
    assert not error and changes["events"] == [] and changes["memory_invalidations"] == ["linked"]
    error, refused = mcp(tmp_path, env, "claim", task="linked", expected=1, request_id="bad", ttl=10)
    assert error and "memory dependency" in refused


def test_sigkill_after_committed_claim_can_be_recovered_after_expiry(tmp_path):
    env = env_for(tmp_path)
    assert cli(tmp_path, env, "put", {"task": "killed", "value": {}, "expected": 0,
                                  "request_id": "seed"})[0] == 0
    script = """
import json,signal,sys
from agent_harness.operational_state import OperationalState
claim=OperationalState.for_host().claim('killed',expected=1,request_id='victim',ttl=1)
print(json.dumps(claim),flush=True)
signal.pause()
"""
    proc = subprocess.Popen([sys.executable, "-c", script], cwd=tmp_path, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert select.select([proc.stdout], [], [], 5)[0], "child did not commit a claim within five seconds"
        line = proc.stdout.readline()
        assert line, "child exited without a claim"
        first = json.loads(line)
    finally:
        proc.kill()
        proc.wait(timeout=5)
    assert proc.returncode < 0
    time.sleep(max(0, first["until"] - time.time()) + 0.06)
    error, replacement = mcp(tmp_path, env, "claim", task="killed", expected=2,
                             request_id="replacement", ttl=10)
    assert not error and replacement["fence"] == first["fence"] + 1
    error, stale = mcp(tmp_path, env, "release", task="killed", expected=3,
                       request_id="stale", token=first["token"], fence=first["fence"])
    assert error and "fenced" in stale
