"""Portable kit validation and non-destructive knowledge publication."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import zipfile

import pytest


def module():
    path = Path(__file__).resolve().parents[1] / "scripts/install-laptop.py"
    spec = importlib.util.spec_from_file_location("laptop_bootstrap", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def kit(tmp_path, name="docs/guide.md", content=b"Source evidence stays pending.\n", symbolic=False):
    tmp_path.mkdir(exist_ok=True)
    wheel = tmp_path / "agent_harness-2.0.0.dev3-py3-none-any.whl"
    wheel.write_bytes(b"Validation fixture only, never installed")
    archive = tmp_path / "knowledge-snapshot.zip"
    with zipfile.ZipFile(archive, "w") as z:
        entry = zipfile.ZipInfo(name)
        if symbolic:
            entry.create_system = 3
            entry.external_attr = 0o120777 << 16
        z.writestr(entry, content)
    sha = lambda b: hashlib.sha256(b).hexdigest()
    manifest = {"version": "2.0.0.dev3", "wheel": {"file": wheel.name, "sha256": sha(wheel.read_bytes())},
                "knowledge": {"file": archive.name, "sha256": sha(archive.read_bytes()),
                              "files": [{"path": name, "bytes": len(content), "sha256": sha(content)}]}}
    (tmp_path / "MANIFEST.json").write_text(json.dumps(manifest))
    return manifest


def test_validate_before_writing_and_preserve_pending_content(tmp_path):
    manifest = kit(tmp_path / "kit")
    m = module()
    assert m.validate(tmp_path / "kit") == manifest
    target = tmp_path / "hh/profile/knowledge/versioned"
    m.publish_knowledge(tmp_path / "kit", manifest, target)
    assert (target / "docs/guide.md").read_bytes() == b"Source evidence stays pending.\n"
    m.publish_knowledge(tmp_path / "kit", manifest, target)
    assert len(list(target.rglob("*.md"))) == 1


@pytest.mark.parametrize("name", ["../escape.md", "/absolute.md", "C:/escape.md", "docs\\escape.md"])
def test_unsafe_archive_paths_fail_without_writing(tmp_path, name):
    kit(tmp_path / "kit", name)
    with pytest.raises(ValueError):
        module().validate(tmp_path / "kit")
    assert not (tmp_path / "escape.md").exists()


def test_symlink_archive_member_is_refused(tmp_path):
    kit(tmp_path / "kit", symbolic=True)
    with pytest.raises(ValueError):
        module().validate(tmp_path / "kit")


def test_changed_artifact_fails_before_any_install(tmp_path):
    kit(tmp_path / "kit")
    (tmp_path / "kit/knowledge-snapshot.zip").write_bytes(b"broken")
    with pytest.raises(ValueError):
        module().validate(tmp_path / "kit")


def test_modified_existing_knowledge_is_never_overwritten(tmp_path):
    manifest = kit(tmp_path / "kit")
    m = module()
    target = tmp_path / "knowledge"
    m.publish_knowledge(tmp_path / "kit", manifest, target)
    source = target / "docs/guide.md"
    source.write_text("My edit must survive.\n")
    with pytest.raises(ValueError):
        m.publish_knowledge(tmp_path / "kit", manifest, target)
    assert source.read_text() == "My edit must survive.\n"


def test_restore_command_keeps_exact_target_and_quotes_paths():
    m = module()
    python = "/some runtime/bin/python"
    home = "/laptops/Oscar's home"
    store = "/some separate harness store"
    parts = shlex.split(m.restore_command(python, home, store, windows=False))
    assert parts == ["HARNESS_HOME=" + store, python, "-I", "-m", "agent_harness.cli",
                     "--home", home, "uninstall"]
