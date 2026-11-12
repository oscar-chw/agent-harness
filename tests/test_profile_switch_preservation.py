"""Replacing a selected profile must preserve, not merge, the prior user data."""
from pathlib import Path

import pytest

from agent_harness import installer, storage
from agent_harness.mcp.kb import KB, profile_folder_roots


def layout(tmp_path):
    hh = tmp_path / "hh"
    old = hh / "profile"
    (old / "knowledge").mkdir(parents=True)
    (old / "knowledge/private.md").write_text("# Old\nquartzoldtenant\n")
    (old / "rules.md").write_text("My original profile rules.\n")
    new = tmp_path / "new"
    new.mkdir()
    (new / "MACHINE.md").write_text("# New\nzirconnewtenant\n")
    source = tmp_path / "source"
    (source / "content").mkdir(parents=True)
    (source / "content/AGENTS.md").write_text("# Package rules\n")
    return hh, old, new, source


def test_old_profile_survives_switch_and_retention_but_is_not_in_new_scope(tmp_path):
    hh, old, new, source = layout(tmp_path)
    retained = installer.copy_harness(hh, source, new)
    assert retained is not None
    assert Path(retained).is_relative_to(hh / "backup")
    assert (retained / "knowledge/private.md").read_text() == "# Old\nquartzoldtenant\n"
    assert (retained / "rules.md").read_text() == "My original profile rules.\n"
    assert not (old / "knowledge/private.md").exists()
    reader = KB(home=hh, paths=profile_folder_roots(old), fts=False)
    try:
        assert reader.search("zirconnewtenant")
        assert reader.search("quartzoldtenant") == []
    finally:
        reader.close()
    junk = [hh / "backup" / ("zzzz-%d" % n) for n in range(7)]
    for path in junk:
        path.mkdir()
    # Without readable install state pruning deliberately preserves all backups.
    (hh / "installed.json").write_text("{}")
    storage.prune(hh)
    assert sum(path.exists() for path in junk) == storage.CAPS["backups"]
    assert (retained / "knowledge/private.md").is_file()


def test_unreadable_install_state_does_not_prune_backups(tmp_path):
    hh, _, new, source = layout(tmp_path)
    retained = installer.copy_harness(hh, source, new)
    junk = [hh / "backup" / ("zzzz-%d" % n) for n in range(7)]
    for path in junk:
        path.mkdir()
    (hh / "installed.json").write_text("{")
    storage.prune(hh)
    assert all(path.is_dir() for path in junk)
    assert (retained / "knowledge/private.md").is_file()


def test_failed_source_copy_leaves_current_profile_untouched(tmp_path, monkeypatch):
    hh, old, new, source = layout(tmp_path)
    original = installer.shutil.copytree

    def fail(src, dest, *args, **kwargs):
        if Path(src) == new:
            raise OSError("source copy failed")
        return original(src, dest, *args, **kwargs)

    monkeypatch.setattr(installer.shutil, "copytree", fail)
    with pytest.raises(OSError, match="source copy failed"):
        installer.copy_harness(hh, source, new)
    assert (old / "knowledge/private.md").read_text() == "# Old\nquartzoldtenant\n"


@pytest.mark.parametrize("error", [OSError, KeyboardInterrupt])
def test_failed_publication_restores_original_profile(tmp_path, monkeypatch, error):
    hh, old, new, source = layout(tmp_path)
    original = Path.rename

    def fail(path, target):
        if Path(target) == old and not path.is_relative_to(hh / "backup"):
            raise error("publication failed")
        return original(path, target)

    monkeypatch.setattr(Path, "rename", fail)
    with pytest.raises(error, match="publication failed"):
        installer.copy_harness(hh, source, new)
    assert (old / "rules.md").read_text() == "My original profile rules.\n"
    assert (old / "knowledge/private.md").read_text() == "# Old\nquartzoldtenant\n"


def test_same_profile_does_not_create_archives(tmp_path):
    hh, old, _, source = layout(tmp_path)
    assert installer.copy_harness(hh, source, old) is None
    assert (old / "knowledge/private.md").is_file()
    assert not (hh / "backup").exists()


def test_selected_profile_inside_current_profile_can_be_published(tmp_path):
    hh, old, _, source = layout(tmp_path)
    selected = old / "presets/new"
    selected.mkdir(parents=True)
    (selected / "MACHINE.md").write_text("# New\nzirconnewtenant\n")
    retained = installer.copy_harness(hh, source, selected)
    assert (old / "MACHINE.md").read_text() == "# New\nzirconnewtenant\n"
    assert (retained / "knowledge/private.md").is_file()


def test_selected_source_package_is_copied_instead_of_the_running_package(tmp_path):
    hh, _, _, source = layout(tmp_path)
    package = source / "src/agent_harness"
    package.mkdir(parents=True)
    (package / "selected_source.py").write_text("SELECTED = True\n")
    installer.copy_harness(hh, source, None)
    assert (hh / "lib/agent_harness/selected_source.py").read_text() == "SELECTED = True\n"
