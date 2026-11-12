"""Remaining Kimi capture, bounded delegation and warmed-install contracts."""
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_harness import capture, cli, installer as I, routing  # noqa: E402
from agent_harness.adapters.base import Ctx  # noqa: E402
from agent_harness.adapters.kimi import KimiAdapter  # noqa: E402
from agent_harness.matrix import matrix  # noqa: E402


def write_wire(path, events):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(event) for event in events) + "\n")


def prompt(turn, text):
    return {"type": "turn.prompt", "turnId": turn, "promptId": f"prompt-{turn}",
            "input": [{"type": "text", "text": text}]}


def call(turn, uid, command, name="Bash"):
    return {"type": "context.append_loop_event", "event": {
        "type": "tool.call", "turnId": str(turn), "toolCallId": uid, "name": name,
        "args": {"command": command} if name == "Bash" else {}}}


def result(uid, output):
    return {"type": "context.append_loop_event", "event": {
        "type": "tool.result", "toolCallId": uid, "result": {"output": output, "durationMs": 1}}}


def candidates(hh):
    path = hh / "candidates.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.is_file() else []


def test_kimi_capture_records_native_fail_then_pass_and_deduplicates_replay(tmp_path):
    assert hasattr(capture, "capture_kimi_turn")
    command = "python3 -m pytest -q tests/test_sample.py"
    wire = tmp_path / "wire.jsonl"
    write_wire(wire, [
        prompt(4, "Fix the sample test"),
        call(4, "call-fail", command),
        result("call-fail", "Command failed with exit code: 1\nFAILED tests/test_sample.py::test_value"),
        call(4, "call-pass", command),
        result("call-pass", "Command executed successfully\n1 passed"),
    ])
    hh = tmp_path / "harness"
    capture.capture_kimi_turn(hh, wire, "session-native", project=tmp_path)
    rows = candidates(hh)
    assert len(rows) == 1 and rows[0]["source"] == "gate"
    assert rows[0]["count"] == 1 and "test_sample.py" in rows[0]["evidence"]
    capture.capture_kimi_turn(hh, wire, "session-native", project=tmp_path)
    replayed = candidates(hh)
    assert len(replayed) == 1 and replayed[0]["count"] == 1


def test_kimi_capture_keeps_an_explicit_user_correction(tmp_path):
    wire = tmp_path / "wire.jsonl"
    write_wire(wire, [prompt(8, "No, use the existing helper instead")])
    capture.capture_kimi_turn(tmp_path / "harness", wire, "session-correction", project=tmp_path)
    rows = candidates(tmp_path / "harness")
    assert [row["source"] for row in rows] == ["user"]
    assert "existing helper" in rows[0]["summary"]


def test_kimi_capture_ignores_signals_from_an_older_turn(tmp_path):
    wire = tmp_path / "wire.jsonl"
    write_wire(wire, [prompt(1, "No, use the old helper instead"), prompt(2, "Continue with the current approach")])
    capture.capture_kimi_turn(tmp_path / "harness", wire, "session-latest", project=tmp_path)
    assert candidates(tmp_path / "harness") == []


def test_kimi_stop_hook_invokes_native_capture_before_its_reminder_exit(tmp_path, monkeypatch):
    home = tmp_path / "home"
    kimi = home / ".kimi-code"
    session_dir = tmp_path / "session"
    session = "session-hook-capture"
    wire = session_dir / "agents/main/wire.jsonl"
    command = "python3 -m pytest -q tests/test_hook.py"
    write_wire(wire, [prompt(11, "Fix the hook test"), call(11, "failed", command),
                      result("failed", "Command failed with exit code: 1\nFAILED tests/test_hook.py"),
                      call(11, "passed", command), result("passed", "Command executed successfully\n1 passed")])
    kimi.mkdir(parents=True)
    (kimi / "session_index.jsonl").write_text(json.dumps({
        "sessionId": session, "sessionDir": str(session_dir)}) + "\n")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HARNESS_HOME", str(home / ".agent-harness"))
    monkeypatch.setenv("KIMI_CODE_HOME", str(kimi))
    payload = {"session_id": session, "cwd": str(tmp_path)}
    assert cli.kimi_stop_hook(io.StringIO(json.dumps(payload))) == 0
    rows = candidates(home / ".agent-harness")
    assert len(rows) == 1 and rows[0]["source"] == "gate"


def test_kimi_matrix_reports_native_capture():
    assert matrix(["kimi"])["kimi"]["capture"] == "yes"


def test_kimi_delegation_profile_preserves_base_prompt_and_bounds_depth():
    assert hasattr(routing, "kimi_orchestrator")
    text = routing.kimi_orchestrator()
    assert "${base_prompt}" in text
    assert 'subagents: ["coder", "explore", "plan"]' in text
    allowlist = next(line for line in text.splitlines() if line.startswith("subagents:"))
    assert "harness-" not in allowlist and "*" not in allowlist


def test_kimi_delegation_adapter_installs_the_bounded_orchestrator_at_user_scope(tmp_path):
    home = tmp_path / "home"
    ctx = Ctx(home=home, harness_home=home / ".agent-harness", content=ROOT / "content",
              profile={}, rules="# Rules\n", mcp_cmd=["python3", "server.py"])
    changes = KimiAdapter().plan(ctx)
    orchestrator = next(change for change in changes
                        if change.path == home / ".kimi-code/agents/harness-orchestrator.md")
    assert orchestrator.kind == "replace"
    assert 'subagents: ["coder", "explore", "plan"]' in orchestrator.content


def doctor_fixture(tmp_path, monkeypatch, base_bytes, index_bytes):
    monkeypatch.delenv("HARNESS_HOME", raising=False)
    home = tmp_path / "home"
    hh = home / ".agent-harness"
    server = hh / "lib/agent_harness/mcp/server.py"
    server.parent.mkdir(parents=True)
    server.write_text("")
    (hh / "lib/base.bin").write_bytes(b"b" * base_bytes)
    (hh / "index.sqlite").write_bytes(b"i" * index_bytes)
    I.save_state(hh, {"entries": [], "tools": [], "extra_mcp": {}})
    monkeypatch.setattr(cli, "BASE_CAP", 4096)
    monkeypatch.setattr(cli, "WARM_CAP", 8192)
    monkeypatch.setattr(cli, "mcp_probe", lambda *args, **kwargs: ["harness"])
    rc = cli.main(["--home", str(home), "doctor"])
    return rc


def test_disk_accounting_warms_a_large_index_without_failing_the_base_cap(tmp_path, monkeypatch, capsys):
    rc = doctor_fixture(tmp_path, monkeypatch, base_bytes=1000, index_bytes=5000)
    output = capsys.readouterr().out
    assert rc == 0
    assert "[ok] base disk footprint" in output
    assert "[ok] warmed disk footprint" in output


def test_disk_accounting_still_rejects_an_over_cap_base_install(tmp_path, monkeypatch, capsys):
    rc = doctor_fixture(tmp_path, monkeypatch, base_bytes=5000, index_bytes=100)
    output = capsys.readouterr().out
    assert rc == 1 and "[FAIL] base disk footprint" in output


def test_disk_accounting_still_rejects_an_over_cap_warmed_install(tmp_path, monkeypatch, capsys):
    rc = doctor_fixture(tmp_path, monkeypatch, base_bytes=1000, index_bytes=8000)
    output = capsys.readouterr().out
    assert rc == 1 and "[FAIL] warmed disk footprint" in output


def test_kimi_precompact_preserves_a_full_existing_state_and_logs_the_checkpoint(tmp_path, monkeypatch):
    from agent_harness.mcp.state import STATE_MAX_BYTES, State

    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HARNESS_HOME", str(home / ".agent-harness"))
    tail = "TAIL-MUST-SURVIVE"
    text = "## Goal\n" + "w" * (STATE_MAX_BYTES - len("## Goal\n") - len(tail) - 2) + "\n" + tail + "\n"
    assert len(text.encode()) == STATE_MAX_BYTES
    State().state_save(text, project=str(tmp_path))
    payload = json.dumps({"session_id": "long-state-session", "cwd": str(tmp_path)})
    assert cli.kimi_precompact_hook(io.StringIO(payload)) == 0
    assert State().state_load(str(tmp_path)) == text
    recent = State().session_recent(k=1, project=str(tmp_path))
    assert "long-state-session" in recent[0]["summary"]


def test_kimi_precompact_does_not_truncate_an_oversized_legacy_state(tmp_path, monkeypatch):
    from agent_harness.mcp.state import STATE_MAX_BYTES, State

    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HARNESS_HOME", str(home / ".agent-harness"))
    text = "w" * STATE_MAX_BYTES + "\nLEGACY-TAIL-MUST-SURVIVE\n"
    State().state_save("seed", project=str(tmp_path))
    Path(State().state_path(str(tmp_path))).write_text(text)
    payload = json.dumps({"session_id": "legacy-state-session", "cwd": str(tmp_path)})
    assert cli.kimi_precompact_hook(io.StringIO(payload)) == 0
    assert State().state_load(str(tmp_path)) == text
    recent = State().session_recent(k=1, project=str(tmp_path))
    assert "legacy-state-session" in recent[0]["summary"]
