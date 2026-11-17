"""An archive update remains usable after its downloaded source is removed."""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from agent_harness import installer


ROOT = Path(__file__).resolve().parents[1]


def invoke(home, launcher, *args):
    env = dict(os.environ, HOME=str(home), HARNESS_HOME=str(home / ".agent-harness"))
    env.pop("PYTHONPATH", None)
    return subprocess.run([str(launcher), "--home", str(home), *args],
                          env=env, capture_output=True, text=True, timeout=30)


def test_update_survives_deleted_archive_source_and_keeps_installed_package(tmp_path):
    home = tmp_path / "user"
    home.mkdir()
    hh = home / ".agent-harness"
    with tempfile.TemporaryDirectory(dir=tmp_path) as folder:
        source = Path(folder)
        shutil.copytree(ROOT / "content", source / "content", ignore=installer.IGNORE)
        shutil.copytree(ROOT / "src/agent_harness", source / "src/agent_harness", ignore=installer.IGNORE)
        installer.copy_harness(hh, source, None)
        result = invoke(home, hh / "bin/harness", "install", "--yes", "--tools", "copilot-vscode",
                        "--source", str(source), "--permission-profile", "preserve")
        assert result.returncode == 0, result.stdout + result.stderr
        # Distinguish the retained payload from whichever checkout runs the command.
        (hh / "lib/agent_harness/retained_fixture.py").write_text("VALUE = 'retained'\n")
        preserved = {"memory/fact.json": b'{"fact": "keep"}\n',
                     "vault/method.md": b"# Retained knowledge\n",
                     "research/preferences.json": b'{"preference": "short"}\n',
                     "state/project/STATE.md": b"# Next\nVerify retained work.\n"}
        for name, data in preserved.items():
            path = hh / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    launcher = hh / "bin/harness"
    for _ in range(2):
        result = invoke(home, launcher, "update")
        assert result.returncode == 0, result.stdout + result.stderr
        assert Path(json.loads((hh / "installed.json").read_text())["source"]).is_dir()
        assert (hh / "lib/agent_harness/retained_fixture.py").read_text() == "VALUE = 'retained'\n"
        for name, data in preserved.items():
            assert (hh / name).read_bytes() == data


def test_explicit_missing_source_is_refused_without_falling_back(tmp_path):
    home = tmp_path / "user"
    home.mkdir()
    hh = home / ".agent-harness"
    installer.copy_harness(hh, ROOT, None)
    installer.save_state(hh, {"source": str(ROOT), "tools": [], "entries": []})
    before = (hh / "installed.json").read_bytes()
    result = invoke(home, hh / "bin/harness", "update", "--source", str(tmp_path / "missing"))
    assert result.returncode == 1
    assert "No harness source" in result.stdout
    assert (hh / "installed.json").read_bytes() == before


def test_missing_source_and_incomplete_payload_are_refused(tmp_path):
    home = tmp_path / "user"
    home.mkdir()
    hh = home / ".agent-harness"
    installer.copy_harness(hh, ROOT, None)
    installer.save_state(hh, {"source": str(tmp_path / "missing"), "tools": [], "entries": []})
    (hh / "lib/agent_harness/__init__.py").unlink()
    before = (hh / "installed.json").read_bytes()
    result = invoke(home, hh / "bin/harness", "update")
    assert result.returncode == 1
    assert "No harness source" in result.stdout
    assert (hh / "installed.json").read_bytes() == before


def test_installed_layout_uses_its_package_when_called_from_another_checkout(tmp_path):
    source = tmp_path / "installed"
    (source / "content").mkdir(parents=True)
    package = source / "lib/agent_harness"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('__version__ = "fixture"\n')
    installer.copy_harness(tmp_path / "target", source, None)
    assert (tmp_path / "target/lib/agent_harness/__init__.py").read_text() == '__version__ = "fixture"\n'
