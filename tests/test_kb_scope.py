"""Other projects' cached documents cannot change this project's retrieval."""
import pytest

from agent_harness.mcp.kb import KB, fts5_available


@pytest.mark.parametrize("fts", [False, True])
def test_foreign_cache_cannot_change_scoped_scores_or_hide_an_answer(tmp_path, fts):
    if fts:
        assert fts5_available(), "this FTS-specific regression requires SQLite FTS5"
    own = tmp_path / "project-a"
    other = tmp_path / "project-b"
    own.mkdir()
    other.mkdir()
    (own / "guide.md").write_text(
        "# Backup\nRotate encryption key using rotate-tool.\n"
        "## Other\nDeployment service instructions.\n")
    for i in range(50):
        (other / f"{i}.md").write_text("# Backup\nencryption key encryption key encryption key.\n")
    first = KB(home=tmp_path / "hh", paths=[own], fts=fts)
    second = KB(home=tmp_path / "hh", paths=[other], fts=fts)
    try:
        before = first.search("rotate encryption key", min_score=0.45)
        assert len(before) == 1
        assert before[0]["id"] == "project-a/guide.md#backup"
        second.refresh()
        assert first.search("rotate encryption key", min_score=0.45) == before
        assert second.search("rotate-tool") == []
        # An actually missing term remains absent; fixing relevance cannot return all docs.
        assert first.search("quasar-neutrino") == []
    finally:
        first.close()
        second.close()


def test_foreign_cache_cannot_change_which_scoped_candidates_survive(tmp_path):
    assert fts5_available(), "this FTS-specific regression requires SQLite FTS5"
    own = tmp_path / "own"
    other = tmp_path / "other"
    own.mkdir()
    other.mkdir()
    for term in ("apricot", "blueberry"):
        for i in range(60):
            (own / f"{term}-{i:02}.md").write_text(f"# Guide\n{term} recipes.\n")
    for i in range(120):
        (other / f"extra-{i}.md").write_text("# Guide\napricot recipes.\n")
    first = KB(home=tmp_path / "hh", paths=[own], fts=True)
    second = KB(home=tmp_path / "hh", paths=[other], fts=True)
    try:
        before = first.search("apricot blueberry", k=50, min_score=0)
        assert len(before) == 50
        second.refresh()
        assert first.search("apricot blueberry", k=50, min_score=0) == before
        assert all(h["path"].startswith("own/") for h in before)
    finally:
        first.close()
        second.close()


@pytest.mark.parametrize("fts", [False, True])
def test_peer_refresh_cannot_leave_a_reader_using_old_terms(tmp_path, fts):
    import os
    root = tmp_path / "docs"
    root.mkdir()
    source = root / "guide.md"
    source.write_text("# Guide\nalpha remedy\n")
    first = KB(home=tmp_path / "hh", paths=[root], fts=fts)
    second = KB(home=tmp_path / "hh", paths=[root], fts=fts)
    try:
        assert first.search("alpha")
        old = source.stat()
        source.write_text("# Guide\nomega remedy\n")
        os.utime(source, (old.st_atime, old.st_mtime + 1))
        second.refresh()
        assert first.search("omega"), "peer already refreshed the source, so new terms must be visible"
        assert first.search("alpha") == []
    finally:
        first.close()
        second.close()


@pytest.mark.parametrize("fts", [False, True])
def test_connected_reader_discovers_new_profile_page_and_retracts_removed_link(
        tmp_path, monkeypatch, fts):
    monkeypatch.delenv("HARNESS_KB_PATHS", raising=False)
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "hh"
    profile = home / "profile"
    profile.mkdir(parents=True)
    (profile / "MACHINE.md").write_text("# Machine\nExisting descriptor.\n")
    reader = KB(home=home, fts=fts)
    source = tmp_path / "published.md"
    source.write_text("# Engineering\nquartzledger rollback receipt\n")
    try:
        with pytest.raises(KeyError):
            reader.get("NEW.md#engineering")
        connection = reader.con
        link = profile / "NEW.md"
        link.symlink_to(source)
        assert "quartzledger" in reader.get("NEW.md#engineering")["text"]
        assert reader.search("quartzledger")[0]["id"] == "NEW.md#engineering"
        assert reader.con is connection, "discovery must not require reconnecting"
        link.unlink()
        with pytest.raises(KeyError):
            reader.get("NEW.md#engineering")
        assert reader.search("quartzledger") == []
        assert source.is_file(), "removing discovery never deletes the source"
    finally:
        reader.close()


@pytest.mark.parametrize("override", ["paths", "environment"])
def test_live_profile_discovery_never_expands_explicit_roots(tmp_path, monkeypatch, override):
    own = tmp_path / "own"
    own.mkdir()
    home = tmp_path / "hh"
    (home / "profile").mkdir(parents=True)
    monkeypatch.delenv("HARNESS_KB_PATHS", raising=False)
    if override == "environment":
        monkeypatch.setenv("HARNESS_KB_PATHS", str(own))
    reader = KB(home=home, paths=[own] if override == "paths" else None, fts=False)
    try:
        reader.refresh()
        (home / "profile/PRIVATE.md").write_text("# Private\nquartzprivate token\n")
        assert reader.search("quartzprivate") == []
        with pytest.raises(KeyError):
            reader.get("PRIVATE.md#private")
    finally:
        reader.close()


def test_new_profile_page_does_not_switch_projects_or_reload_kb_path_policy(
        tmp_path, monkeypatch):
    monkeypatch.delenv("HARNESS_KB_PATHS", raising=False)
    own, foreign = tmp_path / "own", tmp_path / "foreign"
    for folder in (own, foreign):
        (folder / ".git").mkdir(parents=True)
        (folder / "docs").mkdir()
    (foreign / "docs/private.md").write_text("# Private\nquartzforeign record\n")
    home = tmp_path / "hh"
    profile = home / "profile"
    profile.mkdir(parents=True)
    monkeypatch.chdir(own)
    reader = KB(home=home, fts=False)
    try:
        reader.refresh()
        monkeypatch.chdir(foreign)
        (profile / "profile.toml").write_text('kb_paths = ["' + str(foreign) + '"]\n')
        (profile / "NEW.md").write_text("# New\nquartzpublic guidance\n")
        assert reader.search("quartzpublic")
        assert reader.search("quartzforeign") == []
    finally:
        reader.close()
