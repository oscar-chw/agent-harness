"""Host-delivered task state at startup/resume, without live client configuration."""
import io
import json
import os
import subprocess
from pathlib import Path

import pytest


from agent_harness.cli import context_hook
from agent_harness.operational_state import OperationalState
from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize


def fixture(tmp_path, monkeypatch):
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True)
    home = tmp_path / "home"
    monkeypatch.setenv("HARNESS_HOME", str(home))
    store = OperationalState(home, root)
    return root, home, store


def hook(root, source, capsys):
    event = {"hook_event_name": "SessionStart", "source": source,
             "cwd": str(root), "session_id": "fixture-session"}
    assert context_hook(io.StringIO(json.dumps(event))) == 0
    return capsys.readouterr()


def test_start_and_resume_read_current_snapshot_and_cursor(tmp_path, monkeypatch, capsys):
    root, _, store = fixture(tmp_path, monkeypatch)
    assert hook(root, "startup", capsys).out == ""
    store.put("build", {"stage": "analyse"}, expected=0, request_id="first")
    start = hook(root, "startup", capsys).out
    assert "build" in start and "analyse" in start and "cursor" in start
    store.put("build", {"stage": "verify"}, expected=1, request_id="second")
    resumed = hook(root, "resume", capsys).out
    assert "verify" in resumed and "analyse" not in resumed
    assert '"cursor":2' in resumed
    assert len(resumed.encode()) <= 1200


def test_hook_never_reads_another_project_or_presents_withdrawn_evidence_as_current(
        tmp_path, monkeypatch, capsys):
    root, home, store = fixture(tmp_path, monkeypatch)
    other = tmp_path / "other"
    (other / ".git").mkdir(parents=True)
    store.put("local", {"stage": "safe"}, expected=0, request_id="one")
    assert "local" not in hook(other, "startup", capsys).out
    pid = initialize(root)
    (root / "basis.md").write_text("now withdrawn\n")
    source = SourceVault(root, pid).capture("basis.md")
    item = {"id": "basis", "project_id": pid, "layer": "project_facts", "kind": "fact",
            "scope": "project", "text": "now withdrawn",
            "provenance": [{"source": source, "start_line": 1, "end_line": 1}],
            "confidence": "verified", "sensitivity": "private", "access_boundary": "local_user",
            "owner": "project-owner", "freshness": "current"}
    facts = ProjectMemory(root, pid)
    receipt = facts.append(item, expected=None)
    store.put("linked", {"stage": "sensitive work"}, expected=0,
              request_id="two", memory_receipt=receipt)
    facts.append({**item, "freshness": "withdrawn"}, expected=receipt)
    output = hook(root, "resume", capsys).out
    assert "linked" in output and "stale" in output
    assert "sensitive work" not in output
    assert "safe" in output


def test_unavailable_ledger_is_reported_without_false_freshness(tmp_path, monkeypatch, capsys):
    root, _, store = fixture(tmp_path, monkeypatch)
    store.put("build", {"stage": "current"}, expected=0, request_id="first")
    store.path.write_bytes(b"not a database")
    result = hook(root, "compact", capsys)
    assert "current" not in result.out
    assert "unavailable" in result.err


def test_large_memory_fallback_still_carries_current_operational_cursor(tmp_path, monkeypatch, capsys):
    from agent_harness.mcp.memory import Memory
    root, _, store = fixture(tmp_path, monkeypatch)
    store.put("resume", {"stage": "inspect"}, expected=0, request_id="seed")
    monkeypatch.setattr(Memory, "resume_context", lambda self, _session: "x" * 6200)
    output = hook(root, "compact", capsys).out
    assert "exceeds the hook budget" in output
    assert '"cursor":1' in output and "resume" in output
    assert len(output.encode()) <= 6000


def test_brief_budget_includes_prefix_and_never_overruns(tmp_path, monkeypatch):
    _, _, store = fixture(tmp_path, monkeypatch)
    store.put("build", {"stage": "test"}, expected=0, request_id="seed")
    with pytest.raises(ValueError):
        store.brief(max_bytes=100)
    assert len(store.brief(max_bytes=500).encode()) <= 500


def test_claude_session_start_hook_reads_same_project_ledger(tmp_path):
    from agent_harness import installer as I
    from agent_harness.adapters.claude_code import ClaudeCodeAdapter
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True)
    home, hh = tmp_path / "home", tmp_path / "home/.agent-harness"
    home.mkdir()
    repo = Path(__file__).resolve().parents[1]
    I.copy_harness(hh, repo, None)
    ctx = I.make_ctx(home, hh, repo / "content", None)
    changes = ClaudeCodeAdapter().plan(ctx)
    settings = next(change.content for change in changes if change.path.name == "settings.json")
    commands = [hook["command"] for group in settings["hooks"]["SessionStart"] for hook in group["hooks"]]
    command = next(command for command in commands if "_hook-op" in command)
    OperationalState(hh, root).put("handoff", {"stage": "ready"}, expected=0, request_id="seed")
    event = {"hook_event_name": "SessionStart", "source": "resume",
             "cwd": str(root), "session_id": "claude-fixture"}
    env = dict(os.environ, HOME=str(home), HARNESS_HOME=str(hh), PYTHONNOUSERSITE="1")
    proc = subprocess.run(["/bin/sh", "-c", command], input=json.dumps(event), text=True,
                          capture_output=True, cwd=tmp_path, env=env, timeout=10)
    assert proc.returncode == 0, proc.stderr
    assert "handoff" in proc.stdout and "ready" in proc.stdout and "cursor" in proc.stdout
