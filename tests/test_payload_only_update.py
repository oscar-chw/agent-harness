from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/update-payload.py"
VERSION = "3.0.26"
OLD = {
    "src/agent_harness/__init__.py": b'__version__ = "3.0.0rc2"\n',
    "src/agent_harness/mcp/server.py": b"# previous server\n",
    "content/hooks/guard.py": b"# existing guard\n",
}
NEW = {**OLD, "src/agent_harness/__init__.py": b'__version__ = "3.0.26"\n',
       "src/agent_harness/mcp/server.py": b"# updated server\n",
       "src/agent_harness/lookup.py": b"# new module\n"}


def sha(data):
    return sha256(data).hexdigest()


def store(root, files):
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)


@pytest.fixture
def fixture(tmp_path):
    old, new, home = [tmp_path / name for name in ("old", "new", "home")]
    runtime = home / ".agent-harness"
    store(old, OLD)
    store(new, NEW)
    store(runtime, {name.replace("src/", "lib/", 1): body for name, body in OLD.items()})
    store(home, {".codex/config.toml": b'model = "unchanged"\n',
                 ".claude/settings.json": b'{"hooks":{}}\n',
                 ".agent-harness/vault/prior.md": b"owner source\n"})
    state = {"source": str(old), "tools": ["claude-code", "codex"],
             "permission_profile": "preserve", "entries": []}
    (runtime / "installed.json").write_text(json.dumps(state))
    return old, new, home, runtime


def args(fixture, tmp_path):
    old, new, _, runtime = fixture
    files = {p.relative_to(new).as_posix(): p.read_bytes() for p in new.rglob("*") if p.is_file()}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"version": VERSION, "build_commit": "1" * 40,
                                    "packaged_files": [{"source": p, "sha256": sha(d)}
                                                       for p, d in files.items()]}))
    return ["--baseline", str(old), "--source", str(new), "--manifest", str(manifest),
            "--manifest-sha256", sha(manifest.read_bytes()), "--harness-home", str(runtime),
            "--backup", str(tmp_path / "backup")]


def run(options, *extra):
    return subprocess.run([sys.executable, str(SCRIPT), *options, *extra],
                          capture_output=True, text=True, timeout=20)


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file() and not p.is_symlink()}


def test_preview_and_apply_preserve_configuration_and_user_data(fixture, tmp_path):
    _, _, home, runtime = fixture
    before = snapshot(home)
    options = args(fixture, tmp_path)
    preview = run(options)
    assert preview.returncode == 0, preview.stderr
    assert json.loads(preview.stdout)["status"] == "READY"
    assert snapshot(home) == before and not (tmp_path / "backup").exists()
    updated = run(options, "--apply")
    assert updated.returncode == 0, updated.stderr
    result = json.loads(updated.stdout)
    assert result["status"] == "INSTALLED" and result["package_files"] == len(NEW)
    expected = {k.replace("src/", "lib/", 1): v for k, v in NEW.items()}
    assert all((runtime / k).read_bytes() == body for k, body in expected.items())
    for key in (".codex/config.toml", ".claude/settings.json", ".agent-harness/vault/prior.md"):
        assert (home / key).read_bytes() == before[key]
    state = json.loads((runtime / "installed.json").read_bytes())
    assert state["source_commit"] == "1" * 40 and state["source"] == str(runtime)
    assert state["tools"] == ["claude-code", "codex"] and state["permission_profile"] == "preserve"
    assert (tmp_path / "backup/lib/agent_harness/mcp/server.py").read_bytes() == OLD[
        "src/agent_harness/mcp/server.py"]


@pytest.mark.parametrize(("changed", "error"), [
    ("local edit", "differs from the baseline"),
    ("guard", "protected package file"),
    ("linked target", "linked path"),
    ("missing baseline", "differs from the baseline"),
    ("linked config", "active application configuration"),
])
def test_refuses_unqualified_payload_before_write(fixture, tmp_path, changed, error):
    _, new, home, runtime = fixture
    server = runtime / "lib/agent_harness/mcp/server.py"
    if changed == "local edit":
        server.write_bytes(b"# local edit\n")
    elif changed == "guard":
        (new / "content/hooks/guard.py").write_bytes(b"# changed guard\n")
    elif changed == "linked target":
        server.unlink()
        server.symlink_to(home / ".claude/settings.json")
    elif changed == "linked config":
        settings = home / ".codex/config.toml"
        settings.unlink()
        settings.symlink_to(server)
    else:
        server.unlink()
    before = snapshot(home)
    refused = run(args(fixture, tmp_path), "--apply")
    assert refused.returncode == 1 and error in refused.stderr
    assert snapshot(home) == before and not (tmp_path / "backup").exists()


def test_apply_restores_prior_bytes_after_failure(fixture, tmp_path, monkeypatch):
    _, _, home, runtime = fixture
    before = snapshot(home)
    spec = importlib.util.spec_from_file_location("update_payload", SCRIPT)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    real = tool.replace
    failed = []

    def fail_after_writing_version(path, payload, **options):
        real(path, payload, **options)
        if path == runtime / tool.VERSION_FILE and not failed:
            failed.append(path)
            raise OSError("fixture write interrupted")

    monkeypatch.setattr(tool, "replace", fail_after_writing_version)
    assert tool.main([*args(fixture, tmp_path), "--apply"]) == 1
    assert failed and (tmp_path / "backup/transaction.json").is_file()
    snapshot_after = snapshot(home)
    snapshot_after.pop(".agent-harness/state/.self-update.lock")
    assert snapshot_after == before


def test_apply_respects_the_installed_updater_lock(fixture, tmp_path):
    _, _, home, runtime = fixture
    lock = runtime / "state/.self-update.lock"
    lock.parent.mkdir()
    with sqlite3.connect(lock) as other:
        other.execute("PRAGMA user_version = 1")
        # Closing the snapshot's descriptor can release this process's POSIX locks.
        before = snapshot(home)
        other.execute("BEGIN IMMEDIATE")
        result = run(args(fixture, tmp_path), "--apply")
        assert result.returncode == 1 and "locked" in result.stderr
    assert snapshot(home) == before and not (tmp_path / "backup").exists()


@pytest.fixture
def missing_prompt(fixture):
    old, new, _, runtime = fixture
    content = b"# Installed VS Code prompt\n"
    source = "content/prompts/plan.md"
    for root in (old, new, runtime):
        store(root, {source: content})
    generated = runtime / "content/copilot/prompts/plan.prompt.md"
    state_path = runtime / "installed.json"
    state = json.loads(state_path.read_bytes())
    state["entries"].append({"path": str(generated), "tools": ["copilot-vscode"],
                             "kind": "replace", "written": "f:" + sha(content)})
    state_path.write_text(json.dumps(state))
    return generated, content


def test_missing_managed_prompt_requires_explicit_hash_bound_repair(fixture, missing_prompt, tmp_path):
    _, _, home, _ = fixture
    generated, content = missing_prompt
    options = args(fixture, tmp_path)
    before = snapshot(home)
    held = run(options)
    assert held.returncode == 1 and generated.name in held.stderr
    assert snapshot(home) == before

    repair = "--restore-missing-vscode-prompts"
    preview = run(options, repair)
    assert preview.returncode == 0, preview.stderr
    assert json.loads(preview.stdout)["restored_vscode_prompts"] == 1
    assert snapshot(home) == before and not (tmp_path / "backup").exists()

    applied = run(options, repair, "--apply")
    assert applied.returncode == 0, applied.stderr
    result = json.loads(applied.stdout)
    assert result["updated_paths"] == 3 and result["restored_vscode_prompts"] == 1
    assert generated.read_bytes() == content
    tx = json.loads((tmp_path / "backup/transaction.json").read_bytes())
    assert tx["content/copilot/prompts/plan.prompt.md"]["before"] is None
    second = run(options, repair, "--apply")
    assert second.returncode == 0 and json.loads(second.stdout)["status"] == "CURRENT"

    generated.unlink()
    options[-1] = str(tmp_path / "repair-current")
    current = run(options, repair, "--apply")
    assert current.returncode == 0, current.stderr
    result = json.loads(current.stdout)
    assert result["updated_paths"] == 0 and result["restored_vscode_prompts"] == 1
    assert generated.read_bytes() == content


def test_repair_preserves_a_prompt_created_concurrently(fixture, missing_prompt, tmp_path, monkeypatch):
    _, _, _, runtime = fixture
    generated, _ = missing_prompt
    spec = importlib.util.spec_from_file_location("update_payload", SCRIPT)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    link = tool.os.link
    competing = b"# Prompt saved by another process\n"

    def concurrent_save(src, dst, *a, **kw):
        if dst == generated:
            generated.write_bytes(competing)
        return link(src, dst, *a, **kw)

    monkeypatch.setattr(tool.os, "link", concurrent_save)
    assert tool.main([*args(fixture, tmp_path), "--restore-missing-vscode-prompts", "--apply"]) == 1
    assert generated.read_bytes() == competing
    assert (runtime / tool.VERSION_FILE).read_bytes() == OLD["src/agent_harness/__init__.py"]


def test_prompt_repair_refuses_bytes_that_differ_from_the_owner_record(fixture, missing_prompt, tmp_path):
    old, new, home, runtime = fixture
    generated, _ = missing_prompt
    source = "content/prompts/plan.md"
    for root in (old, new, runtime):
        store(root, {source: b"# Different prompt\n"})
    before = snapshot(home)
    result = run(args(fixture, tmp_path), "--restore-missing-vscode-prompts", "--apply")
    assert result.returncode == 1 and generated.name in result.stderr
    assert snapshot(home) == before and not (tmp_path / "backup").exists()
