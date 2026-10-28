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
