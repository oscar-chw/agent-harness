"""Generated Codex hook configuration and direct event delivery in a temporary home.

These checks do not assert that native Codex trusted or invoked these hooks.
"""
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_harness import installer as I
from agent_harness.adapters.codex import CodexAdapter
from agent_harness.mcp.memory import Memory
from agent_harness.mcp.state import State

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def stage(tmp_path):
    home, hh = tmp_path / "home", tmp_path / "home/.agent-harness"
    home.mkdir()
    projects = [tmp_path / name for name in ("alpha", "bravo")]
    for project in projects:
        project.mkdir()
        (project / ".git").mkdir()
    I.copy_harness(hh, ROOT, None)
    ctx = I.make_ctx(home, hh, ROOT / "content", None)
    env = {k: v for k, v in os.environ.items() if not k.startswith("HARNESS_")}
    env.update(HOME=str(home), HARNESS_HOME=str(hh), PYTHONNOUSERSITE="1")
    path = tmp_path / "bin"
    path.mkdir()
    (path / "python3").symlink_to(sys.executable)
    env["PATH"] = str(path)
    return home, hh, ctx, projects, env


def install(stage):
    home, hh, ctx, _, _ = stage
    changes = CodexAdapter().plan(ctx)
    I.save_state(hh, I.apply(hh, [("codex", changes)], {}, [home]))
    path = home / ".codex/hooks.json"
    assert path.is_file(), "Codex adapter did not wire native recall hooks"
    return json.loads(path.read_text())["hooks"]


def event(stage, hooks, name, **values):
    _, _, _, projects, env = stage
    handlers = [handler for group in hooks[name] for handler in group["hooks"]
                if "agent_harness.cli" in handler.get("command", "")]
    assert len(handlers) == 1
    assert "bypass" not in handlers[0]["command"]
    payload = {"hook_event_name": name, "cwd": str(projects[0]), "session_id": "native-fixture", **values}
    return subprocess.run(["/bin/sh", "-c", handlers[0]["command"]],
                          input=json.dumps(payload), text=True, capture_output=True,
                          cwd=projects[1], env=env, timeout=10)


def seed(stage, project, fact):
    m = Memory(home=stage[1], project=project)
    try:
        return m.mem_add(fact, scope="project")["id"]
    finally:
        m.close()


def test_generated_prompt_hook_uses_event_scope_and_remains_reversible(stage):
    home, hh, _, projects, _ = stage
    codex = home / ".codex"
    codex.mkdir()
    original = {"hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "protect"}]}]}}
    (codex / "hooks.json").write_text(json.dumps(original))
    config = '[hooks]\nStop = [{ hooks = [{ type = "command", command = "keep-me" }] }]\n'
    (codex / "config.toml").write_text(config)
    hooks = install(stage)
    assert hooks["UserPromptSubmit"][0] == original["hooks"]["UserPromptSubmit"][0]
    assert I.load_toml((codex / "config.toml").read_text())["hooks"]["Stop"][0]["hooks"][0]["command"] == "keep-me"
    seed(stage, projects[0], "Archive recovery marker is jade.")
    seed(stage, projects[1], "Archive recovery marker is foreign-canary.")
    result = event(stage, hooks, "UserPromptSubmit", prompt="archive recovery marker")
    assert result.returncode == 0 and "jade" in result.stdout
    assert "foreign-canary" not in result.stdout
    assert event(stage, hooks, "UserPromptSubmit", prompt="oceanography").stdout == ""
    I.uninstall(hh, log=lambda _: None)
    assert json.loads((codex / "hooks.json").read_text()) == original
    assert (codex / "config.toml").read_text() == config


def test_compact_replays_full_current_context_and_releases_recall_suppression(stage):
    _, hh, _, projects, _ = stage
    hooks = install(stage)
    fact = "Archive recovery: " + "preserve originals; " * 16 + "Never erase raw inputs."
    identity = seed(stage, projects[0], fact)
    assert fact in event(stage, hooks, "UserPromptSubmit", prompt="archive recovery").stdout
    assert event(stage, hooks, "UserPromptSubmit", prompt="archive recovery").stdout == ""
    State(home=hh, project=projects[0]).state_save("Task still open. Re-run the acceptance check.")
    State(home=hh, project=projects[1]).state_save("foreign-state-canary")
    result = event(stage, hooks, "SessionStart", source="compact")
    assert result.returncode == 0 and fact in result.stdout and identity in result.stdout
    assert "Re-run the acceptance check" in result.stdout and "foreign-state-canary" not in result.stdout
    assert len(result.stdout.encode()) <= 6000
    assert fact in event(stage, hooks, "UserPromptSubmit", prompt="archive recovery").stdout


def test_resume_names_missing_recalled_source_instead_of_replaying_old_fact(stage):
    _, hh, _, projects, _ = stage
    hooks = install(stage)
    identity = seed(stage, projects[0], "Archive recovery marker is jade.")
    event(stage, hooks, "UserPromptSubmit", prompt="archive recovery marker")
    m = Memory(home=hh, project=projects[0])
    try:
        assert m.mem_forget(identity)["ok"]
    finally:
        m.close()
    result = event(stage, hooks, "SessionStart", source="resume")
    assert result.returncode == 0 and "unavailable" in result.stdout and identity in result.stdout
    assert "jade" not in result.stdout


def test_hook_scope_errors_fail_without_leaking_or_blocking_prompt(stage):
    hooks = install(stage)
    for name in ("UserPromptSubmit", "SessionStart"):
        result = event(stage, hooks, name, cwd="relative", prompt="archive recovery", source="compact")
        assert result.returncode == 0 and result.stdout == "" and result.stderr


def test_empty_start_is_quiet_and_oversized_record_is_explicit(stage):
    hooks = install(stage)
    assert event(stage, hooks, "SessionStart", source="startup").stdout == ""
    identity = seed(stage, stage[3][0], "Archive recovery " + "retain " * 250)
    event(stage, hooks, "UserPromptSubmit", prompt="archive recovery")
    # Oversized matches were not supplied; a pinned record must still name its omission.
    m = Memory(home=stage[1], project=stage[3][0])
    try:
        m.mem_add("Archive recovery " + "retain " * 250, scope="project", pin=True)
    finally:
        m.close()
    out = event(stage, hooks, "SessionStart", source="compact").stdout
    assert "omitted" in out and identity in out and len(out.encode()) <= 6000


def test_active_procedure_survives_compaction_with_its_exclusion(stage):
    from agent_harness import procedures
    from .test_v1_learning_loop import receipt
    home, hh, _, projects, _ = stage
    candidate = {"schema": 1, "title": "Archive recovery", "trigger": "archive recovery only for offline staging",
                 "steps": ["Verify the checksum before restoring."],
                 "exceptions": ["Never restore over a live database."], "episodes": []}
    for n in (1, 2):
        source = projects[0] / ("episode%d.json" % n)
        source.write_text(json.dumps({"task": n, "before": 1, "after": 0}))
        task = projects[0] / ("task%d.json" % n)
        task.write_text(json.dumps({"prompt": "archive recovery", "input": n}))
        candidate["episodes"].append({"task_id": str(n), "path": source.name,
                                     "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                                     "task_path": task.name, "task_sha256": hashlib.sha256(task.read_bytes()).hexdigest()})
    proposal = procedures.draft(hh, str(projects[0]), candidate)
    procedures.change(hh, str(projects[0]), proposal["id"], receipt(proposal))
    hooks = install(stage)
    assert proposal["id"] in event(stage, hooks, "UserPromptSubmit", prompt="archive recovery").stdout
    out = event(stage, hooks, "SessionStart", source="compact").stdout
    assert "Verify the checksum" in out and "Never restore over a live database" in out
    assert "only for offline staging" in out
    # Recovery must reset suppression without erasing delivery provenance.
    again = event(stage, hooks, "SessionStart", source="compact").stdout
    assert "Verify the checksum" in again
    procedures.change(hh, str(projects[0]), proposal["id"], rollback=True)
    withdrawn = event(stage, hooks, "UserPromptSubmit", prompt="write a short poem").stdout
    assert proposal["id"] in withdrawn and "withdrawn" in withdrawn


def test_inline_startup_only_does_not_suppress_resume_and_compact(stage):
    home, _, ctx, _, _ = stage
    first = next(c for c in CodexAdapter().plan(ctx) if c.path.name == "hooks.json")
    original = first.content['hooks']
    original['SessionStart'][0]['matcher'] = 'startup'
    native = home / '.codex'
    native.mkdir()
    before = I.toml_table('hooks', original)
    (native / 'config.toml').write_text(before)
    additions = next(c for c in CodexAdapter().plan(ctx) if c.path.name == 'hooks.json')
    assert additions.content['hooks']['SessionStart'][0]['matcher'] == 'resume|compact'
    assert 'UserPromptSubmit' not in additions.content['hooks']
    assert (native / 'config.toml').read_text() == before


def test_inline_equivalent_is_not_duplicated_in_json(stage):
    home, _, ctx, _, _ = stage
    first = next(c for c in CodexAdapter().plan(ctx) if c.path.name == "hooks.json")
    native = home / ".codex"
    native.mkdir()
    (native / "config.toml").write_text(I.toml_table("hooks", first.content["hooks"]))
    second = [c for c in CodexAdapter().plan(ctx) if c.path.name == "hooks.json"]
    assert not second, "equivalent inline definitions would execute the same hooks twice"


def test_new_session_gets_a_state_handle_not_an_unrelated_task_body(stage):
    hooks = install(stage)
    State(home=stage[1], project=stage[3][0]).state_save("Previous task body: confidential-fixture.")
    result = event(stage, hooks, "SessionStart", source="startup")
    assert result.returncode == 0 and "state_load" in result.stdout
    assert "confidential-fixture" not in result.stdout


@pytest.mark.parametrize("changes", [{"source": "unknown"}, {"hook_event_name": "PostToolUse"}])
def test_wrong_context_event_cannot_emit_saved_state(stage, changes):
    hooks = install(stage)
    State(home=stage[1], project=stage[3][0]).state_save("private-state-canary")
    result = event(stage, hooks, "SessionStart", **{"source": "resume", **changes})
    assert result.returncode == 0 and result.stdout == ""
    assert result.stderr and "private-state-canary" not in result.stderr
