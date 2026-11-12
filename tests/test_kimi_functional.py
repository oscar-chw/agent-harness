"""Kimi's harness tiers, workers, hooks and read-only plugin discovery."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_harness import discover, installer as I, review, routing  # noqa: E402
from agent_harness.adapters.base import Ctx  # noqa: E402
from agent_harness.adapters.kimi import KimiAdapter  # noqa: E402
from agent_harness.matrix import matrix  # noqa: E402

_spec = importlib.util.spec_from_file_location("kimi_plan", ROOT / "src/agent_harness/workgraph/plan.py")
plan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plan)

CONFIG = '''default_model = "kimi-code/k3.1-pro"

[models."kimi-code/k3.1-pro"]
provider = "managed:kimi-code"
model = "k3.1-pro"
support_efforts = ["low", "high", "max"]
default_effort = "max"
'''


def kimi_home(home, config=CONFIG):
    root = home / ".kimi-code"
    root.mkdir(parents=True, exist_ok=True)
    (root / "config.toml").write_text(config)
    return root


def context(home):
    return Ctx(home=home, harness_home=home / ".agent-harness", content=ROOT / "content",
               profile={}, rules="# Rules\n", mcp_cmd=["python3", "server.py"])


def install_tier(home, tier="quick"):
    root = kimi_home(home)
    resolved = routing.resolve(ROOT / "content", home)[tier]
    agents = root / "agents"
    agents.mkdir(exist_ok=True)
    (agents / f"harness-{tier}.md").write_text(routing.kimi_agent(tier, resolved))
    return resolved


def fake_kimi(path, body):
    path.write_text("#!/usr/bin/env python3\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def git_repo(root):
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Fixture"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "fixture@example.invalid"], check=True)
    (root / "a.py").write_text("value = 1\n")
    subprocess.run(["git", "-C", str(root), "add", "a.py"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "base"], check=True)


def test_kimi_routing_uses_the_configured_non_highspeed_model_and_supported_efforts(tmp_path):
    kimi_home(tmp_path)
    resolved = routing.resolve(ROOT / "content", tmp_path)
    assert resolved["quick"]["kimi"] == {
        "model": "kimi-code/k3.1-pro", "effort": "low", "why": "your config.toml default_model"}
    assert resolved["deep"]["kimi"]["effort"] == "high"
    assert resolved["review"]["kimi"]["model"] == "kimi-code/k3.1-pro"


def test_kimi_routing_holds_when_the_model_or_effort_is_unavailable(tmp_path):
    kimi_home(tmp_path, CONFIG.replace('["low", "high", "max"]', '["low"]'))
    resolved = routing.resolve(ROOT / "content", tmp_path)
    assert resolved["deep"]["kimi"]["effort"] == "low"
    assert resolved["deep"]["kimi"]["model"] == "kimi-code/k3.1-pro"
    assert routing.kimi_pair_supported(dict(resolved["deep"]["kimi"], effort="high"), tmp_path) is False
    assert routing.kimi_pair_supported(resolved["deep"]["kimi"], tmp_path) is True
    assert routing.kimi_pair_supported(resolved["quick"]["kimi"], tmp_path) is True


def test_kimi_agent_exposes_harness_metadata_without_unsupported_native_fields(tmp_path):
    tier = install_tier(tmp_path, "deep")
    text = (tmp_path / ".kimi-code/agents/harness-deep.md").read_text()
    assert "name: harness-deep" in text
    assert "x-harness-model: kimi-code/k3.1-pro" in text
    assert "x-harness-effort: high" in text
    assert "\nmodel:" not in text and "\neffort:" not in text
    assert routing.kimi_tier("deep", tmp_path) == ("kimi-code/k3.1-pro", "high")
    assert tier["kimi"]["effort"] == "high"


def test_kimi_worker_command_and_stream_envelope(tmp_path, monkeypatch):
    tier = install_tier(tmp_path)
    cmd = plan.kimi_cmd("P", "quick", home=tmp_path)
    assert cmd[:2] == ["kimi", "-p"]
    assert cmd[cmd.index("--agent-file") + 1].endswith("/harness-quick.md")
    assert cmd[cmd.index("--model") + 1] == tier["kimi"]["model"]
    monkeypatch.setenv("KIMI_MODEL_THINKING_EFFORT", "stale")
    env = plan.kimi_env("quick", home=tmp_path)
    assert env["KIMI_MODEL_THINKING_EFFORT"] == "low"
    events = [
        {"role": "meta", "type": "system.version", "version": "2.5.2"},
        {"role": "assistant", "tool_calls": [{"type": "function", "function": {"name": "Bash"}}]},
        {"role": "assistant", "content": "done"},
        {"role": "meta", "type": "session.resume_hint", "session_id": "s1"},
    ]
    info = plan.kimi_info(0, "\n".join(json.dumps(e) for e in events), "")
    assert info["result"] == "done" and info["is_error"] is False
    assert info["observed_tool_calls"] == 1
    assert info["tool_calls_status"] == "COMPLETE_EVENT_STREAM"
    assert info["usage"]["status"] == "NOT_OBSERVABLE"
    assert plan.kimi_info(1, "", "not logged in")["is_error"] is True


def test_runner_supports_kimi_without_changing_existing_preference(monkeypatch):
    monkeypatch.setenv("PLAN_RUNNER", "kimi")
    assert plan.runner() == "kimi"
    monkeypatch.setenv("PLAN_RUNNER", "")
    monkeypatch.setattr(plan.shutil, "which", lambda name: "/x/kimi" if name == "kimi" else None)
    assert plan.runner() == "kimi"
    monkeypatch.setattr(plan.shutil, "which", lambda name: "/x/" + name)
    assert plan.runner() == "claude"


def test_plan_run_dispatches_a_real_kimi_command_and_controller_gate(tmp_path):
    repo = tmp_path / "repo"
    (repo / "plan").mkdir(parents=True)
    (repo / "plan/g.md").write_text(
        "## goal: g\n- [ ] 1. make it | tier: quick | gate: test -f done.txt\n")
    install_tier(tmp_path)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    argv = tmp_path / "argv.json"
    effort = tmp_path / "effort.txt"
    fake_kimi(bindir / "kimi", f'''import json, os, pathlib, sys
if sys.argv[1:] == ["provider", "list", "--json"]:
    print(json.dumps({{"models": {{"kimi-code/k3.1-pro": {{"supportEfforts": ["low", "high", "max"]}}}}}}))
    raise SystemExit(0)
pathlib.Path({str(argv)!r}).write_text(json.dumps(sys.argv))
pathlib.Path({str(effort)!r}).write_text(os.environ.get("KIMI_MODEL_THINKING_EFFORT", ""))
pathlib.Path("done.txt").write_text("done")
print(json.dumps({{"role": "assistant", "content": "done"}}))
print(json.dumps({{"role": "meta", "type": "session.resume_hint", "session_id": "s1"}}))
''')
    env = {**os.environ, "HOME": str(tmp_path), "PATH": str(bindir) + os.pathsep + os.environ["PATH"],
           "PLAN_RUNNER": "kimi", "PLAN_QUIET": "1"}
    result = subprocess.run([sys.executable, str(ROOT / "src/agent_harness/workgraph/plan.py"),
                             "run", "g", "--workers", "1", "--max-rounds", "1"],
                            cwd=repo, env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "- [x] 1." in (repo / "plan/g.md").read_text()
    assert json.loads(argv.read_text())[-1] != ""
    assert effort.read_text() == "low"


def test_kimi_review_uses_review_tier_and_parses_stream_json(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    install_tier(home, "review")
    repo = tmp_path / "repo"
    git_repo(repo)
    (repo / "a.py").write_text("value = 2\n")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    argv = tmp_path / "argv.json"
    effort = tmp_path / "effort.txt"
    fake_kimi(bindir / "kimi", f'''import json, os, pathlib, sys
pathlib.Path({str(argv)!r}).write_text(json.dumps(sys.argv))
pathlib.Path({str(effort)!r}).write_text(os.environ.get("KIMI_MODEL_THINKING_EFFORT", ""))
print(json.dumps({{"role": "assistant", "content": "{{\\"findings\\": []}}"}}))
print(json.dumps({{"role": "meta", "type": "session.resume_hint", "session_id": "s1"}}))
''')
    out = tmp_path / "findings.json"
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("PLAN_RUNNER", "kimi")
        mp.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
        rc, message = review.run(None, str(out), home, root=repo)
    assert rc == 0, message
    assert json.loads(out.read_text())["findings"] == []
    args = json.loads(argv.read_text())
    assert args[args.index("--agent-file") + 1].endswith("/harness-review.md")
    assert args[args.index("--model") + 1] == "kimi-code/k3.1-pro"
    assert effort.read_text() == "high"


def test_kimi_adapter_adds_hooks_and_tiers_without_replacing_user_config(tmp_path):
    home = tmp_path / "home"
    root = kimi_home(home, CONFIG + '''
[thinking]
enabled = true

[[hooks]]
event = "Notification"
command = "my-notification"
''')
    original = (root / "config.toml").read_text()
    changes = KimiAdapter().plan(context(home))
    config = next(c for c in changes if c.path == root / "config.toml")
    assert config.kind == "merge-toml"
    hooks = config.content["+"]["hooks"]
    assert {(h["event"], h.get("matcher")) for h in hooks} >= {
        ("PreToolUse", "Bash"), ("PreToolUse", "Edit|Write"),
        ("SessionStart", "startup|resume"), ("UserPromptSubmit", None), ("PreCompact", None)}
    assert any(c.path == root / "agents/harness-deep.md" for c in changes)
    state = I.apply(home / ".agent-harness", [("kimi", changes)], {}, [home])
    parsed = I.load_toml((root / "config.toml").read_text())
    assert parsed["default_model"] == "kimi-code/k3.1-pro"
    assert parsed["thinking"] == {"enabled": True}
    assert {"command": "my-notification", "event": "Notification"} in parsed["hooks"]
    assert len(parsed["hooks"]) == 1 + len(hooks)
    state = I.apply(home / ".agent-harness", [("kimi", changes)], state, [home])
    assert len(I.load_toml((root / "config.toml").read_text())["hooks"]) == 1 + len(hooks)
    I.save_state(home / ".agent-harness", state)
    I.uninstall(home / ".agent-harness", lambda _line: None)
    assert (root / "config.toml").read_text() == original


def test_kimi_guard_hook_rejects_a_dangerous_bash_payload(tmp_path):
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": str(tmp_path),
               "tool_input": {"command": "rm -rf ~"}}
    result = subprocess.run([sys.executable, str(ROOT / "content/hooks/guard.py")],
                            input=json.dumps(payload), text=True, capture_output=True, timeout=5)
    assert result.returncode == 2


def test_kimi_plugin_discovery_uses_marketplace_pins_and_holds_install(monkeypatch, tmp_path):
    monkeypatch.setattr(discover.sys, "platform", "darwin")
    sha = "b" * 64
    kimi_home(tmp_path)
    monkeypatch.setattr(discover, "_get", lambda url: {"plugins": [
        {"id": "kimi-cu", "displayName": "Kimi Computer Use", "version": "0.5.12",
         "description": "macOS desktop automation", "source": "https://example.invalid/kimi-cu.zip",
         "sha256sum": sha, "clients": ["cli"], "platforms": ["macos"],
         "distribution": {"category": "official"}},
        {"id": "kimi-cu-win", "displayName": "Windows Computer Use", "version": "1.0.0",
         "source": "https://example.invalid/win.zip", "sha256sum": "c" * 64,
         "clients": ["cli"], "platforms": ["windows"]},
    ]})
    records = discover.kimi_plugins(tmp_path)
    assert [r["id"] for r in records] == ["kimi-cu"]
    assert records[0]["ref"] == sha and records[0]["tier"] == "official"
    assert records[0]["install"] == []
    assert discover.vet(records[0])[0] == "block"
    assert "no install command" in discover.vet(records[0])[1]
    monkeypatch.setattr(discover.sys, "platform", "linux")
    assert discover.kimi_plugins(tmp_path) == []
    monkeypatch.setattr(discover.sys, "platform", "win32")
    assert [r["id"] for r in discover.kimi_plugins(tmp_path)] == ["kimi-cu-win"]


def test_kimi_matrix_marks_only_implemented_capabilities():
    row = matrix(["kimi"])["kimi"]
    assert all(row[name] == "yes" for name in ("guard", "plan", "memory", "review", "run", "discover"))
    assert row["capture"] == "yes"


def test_kimi_routing_rejects_a_missing_or_mismatched_model(tmp_path):
    kimi_home(tmp_path)
    pair = routing.resolve(ROOT / "content", tmp_path)["quick"]["kimi"]
    assert routing.kimi_pair_supported(dict(pair, model="kimi-code/missing"), tmp_path) is False
    (tmp_path / ".kimi-code/config.toml").write_text('default_model = "kimi-code/missing"\n')
    assert routing.kimi_pair_supported(pair, tmp_path) is False


def test_kimi_plugin_discovery_filters_non_cli_and_current_platform(monkeypatch, tmp_path):
    kimi_home(tmp_path)
    monkeypatch.setattr(discover.sys, "platform", "darwin")
    monkeypatch.setattr(discover, "_get", lambda url: {"plugins": [
        {"id": "desktop-only", "clients": ["desktop"], "platforms": ["macos"]},
        {"id": "windows-only", "clients": ["cli"], "platforms": ["windows"]},
        {"id": "mac-cli", "clients": ["cli"], "platforms": ["macos"], "sha256sum": "d" * 64},
    ]})
    assert [r["id"] for r in discover.kimi_plugins(tmp_path)] == ["mac-cli"]


def test_kimi_plugin_checksum_changes_the_approval_digest():
    record = {"install": [], "ref": "b" * 64}
    assert discover.approval(record) != discover.approval(dict(record, ref="c" * 64))


def test_commandless_kimi_plugin_override_never_executes(tmp_path, monkeypatch):
    record = {"kind": "plugin", "tool": "kimi", "id": "kimi-cu", "description": "desktop",
              "ref": "b" * 64, "components": ["skill"], "install": []}
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps([record]))
    monkeypatch.setattr(discover.subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(
        AssertionError("command-less install was executed")))
    rc, message = discover.install("kimi-cu", discover.approval(record), True,
                                   tmp_path / "hh", str(catalog))
    assert rc != 0 and "no deterministic install command" in message


def test_commandless_kimi_plugin_render_has_no_install_instruction():
    record = {"id": "kimi-cu", "description": "desktop", "verdict": "block", "reasons": [],
              "install": []}
    assert "harness discover --install" not in discover.render([record])


def test_kimi_agent_extends_the_native_base_prompt(tmp_path):
    install_tier(tmp_path, "review")
    text = (tmp_path / ".kimi-code/agents/harness-review.md").read_text()
    assert "${base_prompt}" in text


def test_kimi_worker_uses_sandbox_and_explicit_validated_agent_file(tmp_path, monkeypatch):
    install_tier(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("KIMI_CODE_HOME", str(tmp_path / ".kimi-code"))
    monkeypatch.setattr(plan, "_sandbox_prefix", lambda: ["sandbox"])
    captured = {}

    class Process:
        returncode = 0
        def __init__(self, cmd, **kwargs):
            captured["cmd"] = cmd
            captured["env"] = kwargs["env"]
        def communicate(self, timeout):
            return ('{"role":"assistant","content":"done"}\n'
                    '{"role":"meta","type":"session.resume_hint","session_id":"s1"}\n', "")

    monkeypatch.setattr(plan.subprocess, "Popen", Process)
    result = plan._dispatch_kimi(1, "P", "quick", 5)
    assert result["ok"] and captured["cmd"][0] == "sandbox"
    args = captured["cmd"]
    assert args[args.index("--agent-file") + 1].endswith("/.kimi-code/agents/harness-quick.md")
    assert "--agent" not in args


def test_inline_hook_array_preserves_user_entries_added_later():
    original_hook = {"event": "Notification", "command": "original"}
    harness_hook = {"event": "PreToolUse", "matcher": "Bash", "command": "harness"}
    later_hook = {"event": "Notification", "command": "added-later"}
    original = 'hooks = [{ event = "Notification", command = "original" }]\n'
    patch = {"+": {"hooks": [harness_hook]}}
    installed = I.toml_merge(original, patch)
    changed = I.toml_merge(installed, {"+": {"hooks": [later_hook]}})
    restored = I.load_toml(I.toml_unmerge(changed, patch, original))
    assert restored["hooks"] == [original_hook, later_hook]


def test_multiline_inline_hook_array_can_be_merged_and_unmerged():
    original = 'hooks = [\n  { event = "Notification", command = "original" },\n]\n'
    harness_hook = {"event": "PreToolUse", "matcher": "Bash", "command": "harness"}
    patch = {"+": {"hooks": [harness_hook]}}
    merged = I.toml_merge(original, patch)
    assert [h["command"] for h in I.load_toml(merged)["hooks"]] == ["original", "harness"]
    assert I.load_toml(I.toml_unmerge(merged, patch, original))["hooks"] == [
        {"event": "Notification", "command": "original"}]


def test_custom_kimi_home_is_authorized_by_the_normal_installer(tmp_path, monkeypatch):
    from agent_harness import cli
    home = tmp_path / "home"
    custom = tmp_path / "custom-kimi"
    home.mkdir()
    custom.mkdir()
    monkeypatch.setenv("KIMI_CODE_HOME", str(custom))
    monkeypatch.setenv("HOME", str(home))
    rc = cli.main(["--home", str(home), "install", "--tools", "kimi", "--yes"])
    assert rc == 0 and (custom / "AGENTS.md").is_file() and (custom / "config.toml").is_file()


def test_review_defaults_to_kimi_and_keeps_agent_without_a_pinned_model(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    install_tier(home, "review")
    agent = home / ".kimi-code/agents/harness-review.md"
    agent.write_text("\n".join(line for line in agent.read_text().splitlines()
                               if not line.startswith("x-harness-model:")) + "\n")
    repo = tmp_path / "repo"
    git_repo(repo)
    (repo / "a.py").write_text("value = 2\n")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    argv = tmp_path / "argv.json"
    fake_kimi(bindir / "kimi", f'''import json, pathlib, sys
pathlib.Path({str(argv)!r}).write_text(json.dumps(sys.argv))
print(json.dumps({{"role": "assistant", "content": "{{\\"findings\\": []}}"}}))
print(json.dumps({{"role": "meta", "type": "session.resume_hint", "session_id": "s1"}}))
''')
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("PLAN_RUNNER", "")
        mp.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
        mp.setattr(review.shutil, "which", lambda name: str(bindir / "kimi") if name == "kimi" else None)
        rc, message = review.run(None, str(tmp_path / "findings.json"), home, root=repo)
    assert rc == 0, message
    args = json.loads(argv.read_text())
    assert args[args.index("--agent-file") + 1] == str(agent)
    assert "--model" not in args


def test_kimi_routing_never_exceeds_the_ceiling_when_only_max_is_offered(tmp_path):
    kimi_home(tmp_path, CONFIG.replace('["low", "high", "max"]', '["max"]'))
    resolved = routing.resolve(ROOT / "content", tmp_path)
    assert resolved["quick"]["kimi"]["effort"] == "low"
    assert routing.kimi_pair_supported(resolved["quick"]["kimi"], tmp_path) is False


def test_kimi_stop_and_precompact_hooks_use_native_session_state(tmp_path, monkeypatch, capsys):
    from agent_harness import cli
    from agent_harness.mcp.state import State
    import io
    home = tmp_path / "home"
    kimi = home / ".kimi-code"
    session_dir = tmp_path / "session"
    (session_dir / "agents/main").mkdir(parents=True)
    kimi.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HARNESS_HOME", str(home / ".agent-harness"))
    monkeypatch.delenv("KIMI_CODE_HOME", raising=False)
    session = "session-native"
    (kimi / "session_index.jsonl").write_text(json.dumps({
        "sessionId": session, "sessionDir": str(session_dir)}) + "\n")
    events = [
        {"type": "turn.prompt", "turnId": 7},
        {"type": "context.append_loop_event", "event": {"type": "tool.call", "turnId": "7",
         "name": "Edit", "args": {"path": str(tmp_path / "project/file.py")}}},
    ]
    (session_dir / "agents/main/wire.jsonl").write_text(
        "\n".join(json.dumps(event) for event in events) + "\n")
    payload = {"session_id": session, "cwd": str(tmp_path / "project")}
    assert cli.kimi_stop_hook(io.StringIO(json.dumps(payload))) == 2
    assert "run this project's checks" in capsys.readouterr().err
    assert cli.kimi_stop_hook(io.StringIO(json.dumps(payload))) == 0
    State().state_save("## Goal\nkeep existing state\n", project=str(tmp_path / "project"))
    assert cli.kimi_precompact_hook(io.StringIO(json.dumps(payload))) == 0
    saved = State().state_load(str(tmp_path / "project"))
    assert "keep existing state" in saved and session in saved


def test_kimi_marketplace_honors_base_override_and_skips_malformed_entries(monkeypatch, tmp_path):
    kimi_home(tmp_path)
    seen = []
    monkeypatch.setenv("KIMI_CODE_BASE_URL", "https://configured.example/v2")
    monkeypatch.setattr(discover, "_get", lambda url: seen.append(url) or {"plugins": [
        {"id": "bad-distribution", "distribution": "official"},
        {"id": "bad-description", "description": 123},
        {"id": "valid", "displayName": "Valid", "description": "working", "sha256sum": "e" * 64},
    ]})
    records = discover.kimi_plugins(tmp_path)
    assert seen == ["https://configured.example/v2/plugins/marketplace"]
    assert [r["id"] for r in records] == ["valid"]


def test_kimi_review_records_and_excuses_artifacts_in_the_reviewed_repo(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    install_tier(home, "review")
    repo = tmp_path / "repo"
    git_repo(repo)
    (repo / "a.py").write_text("value = 2\n")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake_kimi(bindir / "kimi", '''import json, pathlib
pathlib.Path("coverage-artifact.py").write_text("# reviewer artifact\\n")
print(json.dumps({"role": "assistant", "content": "{\\"findings\\": []}"}))
print(json.dumps({"role": "meta", "type": "session.resume_hint", "session_id": "s1"}))
''')
    out = tmp_path / "findings.json"
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(repo)
        mp.setenv("PLAN_RUNNER", "kimi")
        mp.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
        rc, message = review.run(None, str(out), home, root=repo)
    assert rc == 0, message
    assert "coverage-artifact.py" in json.loads(out.read_text())["reviewed"]["artefacts"]
    assert review.gate(str(out), repo)[0] == 0
