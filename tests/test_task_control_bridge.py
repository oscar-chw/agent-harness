"""One human CLI and opt-in MCP view of the same project task state."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from .test_operational_process_flow import env_for, mcp
from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize


SRC = Path(__file__).resolve().parents[1] / "src"


def task_cli(root, env, *args):
    run = subprocess.run([sys.executable, "-m", "agent_harness.cli", "task", *args],
                         cwd=root, env=env, text=True, capture_output=True, timeout=10)
    return run.returncode, (json.loads(run.stdout) if "--json" in args else run.stdout) if run.stdout else run.stderr


def test_explicit_request_id_requires_pinned_expected_version(tmp_path):
    env = env_for(tmp_path)
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan/goal.md").write_text("## goal: verify release\n")
    code, message = task_cli(tmp_path, env, "checkpoint", "release", "--goal", "Verify release",
                             "--checkpoint", "plan/goal.md", "--next", "Run gate",
                             "--request-id", "replay-me")
    assert code != 0 and "--expected" in message
    status_code, status = task_cli(tmp_path, env, "status", "--json")
    assert status_code == 0 and status["tasks"] == []

    code, created = task_cli(tmp_path, env, "checkpoint", "release", "--goal", "Verify release",
                             "--checkpoint", "plan/goal.md", "--next", "Run gate",
                             "--request-id", "replay-me", "--expected", "0", "--json")
    assert code == 0 and created["version"] == 1
    code, replayed = task_cli(tmp_path, env, "checkpoint", "release", "--goal", "Verify release",
                              "--checkpoint", "plan/goal.md", "--next", "Run gate",
                              "--request-id", "replay-me", "--expected", "0", "--json")
    assert code == 0 and replayed == created


def test_human_and_agent_share_checkpoint_stop_resume_and_evidence(tmp_path):
    env = env_for(tmp_path)
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan/goal.md").write_text("## goal: verify release\n")
    (tmp_path / "plan/gate.txt").write_text("fixture gate receipt: PASS\n")
    sha = hashlib.sha256((tmp_path / "plan/gate.txt").read_bytes()).hexdigest()

    code, created = task_cli(tmp_path, env, "checkpoint", "release", "--goal", "Verify release",
                             "--checkpoint", "plan/goal.md", "--next", "Read the gate receipt",
                             "--stage", "evaluation", "--evidence", "plan/gate.txt", "--json")
    assert code == 0, created
    assert (created["task"], created["version"]) == ("release", 1)
    error, agent_status = mcp(tmp_path, env, "status", task="release")
    assert not error, agent_status
    row = agent_status["tasks"][0]
    assert row["activity"] == "idle_ready"
    assert row["evidence_status"] == "current" and row["value"]["evidence_sha256"] == sha
    assert row["value"]["checkpoint"] == "plan/goal.md"
    assert row["status"] == "open"  # a text receipt is never a completion mark
    code, human_status = task_cli(tmp_path, env, "status", "release", "--json")
    assert code == 0 and human_status == agent_status

    error, stopped = mcp(tmp_path, env, "stop", task="release", reason="Evaluator unavailable",
                         expected=1, request_id="agent-stop")
    assert not error and stopped["version"] == 2
    assert mcp(tmp_path, env, "stop", task="release", reason="Evaluator unavailable",
               expected=1, request_id="agent-stop") == (False, stopped)
    error, delta = mcp(tmp_path, env, "changes", cursor=1)
    assert not error and delta["events"] == [
        {"cursor": 2, "task": "release", "action": "stop", "version": 2}]
    stale_code, stale_write = task_cli(tmp_path, env, "checkpoint", "release",
                                      "--next", "Erase the evidence", "--expected", "1", "--json")
    assert stale_code != 0 and "refresh" in stale_write
    code, status = task_cli(tmp_path, env, "status", "release", "--json")
    assert code == 0 and status["tasks"][0]["activity"] == "blocked"
    assert status["tasks"][0]["value"]["blocked_on"] == "Evaluator unavailable"
    code, human = task_cli(tmp_path, env, "status", "release")
    assert code == 0 and all(part in human for part in (
        "release v2 blocked", "plan/goal.md", "Evaluator unavailable", "reference only"))
    error, refusal = mcp(tmp_path, env, "claim", task="release", expected=2,
                         request_id="must-stay-stopped")
    assert error and "blocked" in refusal

    code, resumed = task_cli(tmp_path, env, "resume", "release", "--expected", "2", "--json")
    assert code == 0 and resumed["version"] == 3
    error, evidence = mcp(tmp_path, env, "evidence", task="release")
    assert not error and evidence == {"task": "release", "path": "plan/gate.txt",
                                      "sha256": sha, "status": "current", "claim": "reference_only"}

    # A changed receipt cannot remain current or let another owner claim the task.
    (tmp_path / "plan/gate.txt").write_text("receipt changed after checkpoint\n")
    code, stale = task_cli(tmp_path, env, "status", "release", "--json")
    assert code == 0 and stale["tasks"][0]["evidence_status"] == "stale"
    assert stale["tasks"][0]["activity"] == "evidence_stale"
    error, refusal = mcp(tmp_path, env, "claim", task="release", expected=3,
                         request_id="stale-evidence-claim")
    assert error and "evidence" in refusal
    new_value = dict(stale["tasks"][0]["value"])
    new_value["evidence_sha256"] = hashlib.sha256((tmp_path / "plan/gate.txt").read_bytes()).hexdigest()
    error, updated = mcp(tmp_path, env, "checkpoint", task="release", value=new_value,
                         expected=3, request_id="agent-checkpoint")
    assert not error and updated["version"] == 4
    assert task_cli(tmp_path, env, "status", "release", "--json")[1]["tasks"][0]["activity"] == "idle_ready"


def test_task_control_refuses_fake_progress_and_active_lease_stop(tmp_path):
    env = env_for(tmp_path)
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan/goal.md").write_text("## goal: verify\n")
    assert task_cli(tmp_path, env, "status", "absent", "--json")[0] != 0
    assert task_cli(tmp_path, env, "checkpoint", "job", "--goal", "Verify",
                    "--checkpoint", "plan/missing.md", "--next", "Check", "--json")[0] != 0
    assert task_cli(tmp_path, env, "checkpoint", "job", "--goal", "Verify",
                    "--checkpoint", "plan/goal.md", "--next", "Check", "--json")[0] == 0
    error, claim = mcp(tmp_path, env, "claim", task="job", expected=1, request_id="worker", ttl=30)
    assert not error
    code, refusal = task_cli(tmp_path, env, "stop", "job", "--reason", "Stop now",
                             "--expected", "2", "--json")
    assert code != 0 and "lease" in refusal
    error, snapshot = mcp(tmp_path, env, "status", task="job")
    assert not error and snapshot["tasks"][0]["activity"] == "leased_unverified"
    assert snapshot["tasks"][0]["value"].get("blocked_on") is None
    assert claim["token"] not in json.dumps(snapshot)
    assert task_cli(tmp_path, env, "complete", "job", "--json")[0] != 0


def test_status_and_checkpoint_never_launch_a_model_worker(tmp_path):
    env = env_for(tmp_path)
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan/goal.md").write_text("## goal: check\n")
    commands = tmp_path / "commands"
    commands.mkdir()
    marker = tmp_path / "model-invoked"
    for name in ("claude", "codex"):
        binary = commands / name
        binary.write_text("#!/bin/sh\ntouch '" + str(marker) + "'\nexit 99\n")
        binary.chmod(0o755)
    env["PATH"] = str(commands) + ":" + env.get("PATH", "")
    assert task_cli(tmp_path, env, "checkpoint", "local", "--goal", "Check",
                    "--checkpoint", "plan/goal.md", "--next", "Read", "--json")[0] == 0
    assert task_cli(tmp_path, env, "status", "local", "--json")[0] == 0
    assert mcp(tmp_path, env, "status", task="local")[0] is False
    assert not marker.exists()


def test_changed_evidence_blocks_lease_renewal_but_not_release(tmp_path):
    env = env_for(tmp_path)
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan/goal.md").write_text("## goal: verify\n")
    (tmp_path / "plan/receipt.txt").write_text("original evidence\n")
    assert task_cli(tmp_path, env, "checkpoint", "job", "--goal", "Verify",
                    "--checkpoint", "plan/goal.md", "--next", "Inspect receipt",
                    "--evidence", "plan/receipt.txt", "--json")[0] == 0
    error, claim = mcp(tmp_path, env, "claim", task="job", expected=1, request_id="worker", ttl=30)
    assert not error
    (tmp_path / "plan/receipt.txt").write_text("changed evidence\n")
    error, denied = mcp(tmp_path, env, "renew", task="job", expected=2, request_id="renew",
                        token=claim["token"], fence=claim["fence"], ttl=30)
    assert error and "evidence" in denied
    error, released = mcp(tmp_path, env, "release", task="job", expected=2, request_id="release",
                          token=claim["token"], fence=claim["fence"])
    assert not error and released["status"] == "open"


def test_human_checkpoint_does_not_erase_a_source_memory_dependency(tmp_path):
    env = env_for(tmp_path)
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan/goal.md").write_text("## goal: verify\n")
    pid = initialize(tmp_path)
    (tmp_path / "basis.md").write_text("test fixture source\n")
    source = SourceVault(tmp_path, pid).capture("basis.md")
    item = {"id": "basis", "project_id": pid, "layer": "project_facts", "kind": "fact",
            "scope": "project", "text": "test fixture source",
            "provenance": [{"source": source, "start_line": 1, "end_line": 1}],
            "confidence": "verified", "sensitivity": "private", "access_boundary": "local_user",
            "owner": "project-owner", "freshness": "current"}
    facts = ProjectMemory(tmp_path, pid)
    receipt = facts.append(item, expected=None)
    error, created = mcp(tmp_path, env, "put", task="linked",
                         value={"goal": "Verify", "checkpoint": "plan/goal.md", "next": "Check"},
                         expected=0, request_id="source-bound", memory_receipt=receipt)
    assert not error and created["version"] == 1
    code, updated = task_cli(tmp_path, env, "checkpoint", "linked", "--stage", "evaluation",
                             "--expected", "1", "--json")
    assert code == 0 and updated["version"] == 2
    row = task_cli(tmp_path, env, "status", "linked", "--json")[1]["tasks"][0]
    assert row["memory_receipt"] == receipt and row["memory_status"] == "current"
    error, stopped = mcp(tmp_path, env, "stop", task="linked", reason="Await source review",
                         expected=2, request_id="linked-stop")
    assert not error and stopped["version"] == 3
    assert task_cli(tmp_path, env, "resume", "linked", "--expected", "3", "--json")[0] == 0
    assert task_cli(tmp_path, env, "status", "linked", "--json")[1]["tasks"][0]["memory_receipt"] == receipt
    facts.append({**item, "freshness": "withdrawn"}, expected=receipt)
    assert task_cli(tmp_path, env, "status", "linked", "--json")[1]["tasks"][0]["activity"] == "stale_memory"
    error, denied = mcp(tmp_path, env, "claim", task="linked", expected=4, request_id="stale-claim")
    assert error and "memory" in denied
