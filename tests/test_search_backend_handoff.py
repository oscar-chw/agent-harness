"""One shared index must retain results across FTS and fallback clients."""
from contextlib import closing, nullcontext
import json
import sqlite3

import pytest

from agent_harness.mcp.kb import KB, fts5_available
from agent_harness.mcp.sessions import Sessions


@pytest.mark.parametrize("existing_fts", [False, True])
def test_notes_indexed_by_fallback_are_visible_to_fts(tmp_path, existing_fts):
    assert fts5_available()
    vault = tmp_path / "docs"
    vault.mkdir()
    page = vault / "page.md"
    page.write_text("# State\n\nvelvetquartz is approved.\n")
    home = tmp_path / "store"
    with closing(KB(home, [vault], fts=True)) if existing_fts else nullcontext() as active:
        if active:
            assert active.search("velvetquartz")
        with closing(KB(home, [vault], fts=False)) as other:
            page.write_text("# State\n\nrippleazurite is approved.\n")
            assert other.search("rippleazurite")
            with closing(KB(home, [vault], fts=True)) as cold:
                for consumer in (active, cold):
                    if consumer is None:
                        continue
                    assert [hit["id"] for hit in consumer.search("rippleazurite")] == ["docs/page.md#state"]
                    assert not consumer.search("velvetquartz")
                page.unlink()
                other.refresh()
                assert cold.con.execute("SELECT COUNT(*) FROM kb_sections").fetchone()[0] == 0
                assert cold.search("rippleazurite") == []
                assert cold.con.execute("SELECT rowid FROM kb_fts WHERE kb_fts MATCH 'rippleazurite'").fetchall() == []


@pytest.mark.parametrize("existing_fts", [False, True])
def test_transcript_indexed_by_fallback_is_visible_to_fts(tmp_path, existing_fts):
    assert fts5_available()
    home, user = tmp_path / "store", tmp_path / "user"
    folder = user / ".claude/projects/fixture"
    folder.mkdir(parents=True)
    log = folder / "source.jsonl"

    def line(value):
        return json.dumps({"type": "user", "cwd": "/bounded/fixture", "timestamp": "2026-11-01T10:00:00Z",
                           "message": {"role": "user", "content": value}}) + "\n"

    log.write_text(line("velvetquartz"))
    with closing(Sessions(home, user, fts=True)) if existing_fts else nullcontext() as active:
        if active:
            assert active.search("velvetquartz")["results"]
        with closing(Sessions(home, user, fts=False)) as other:
            with log.open("a") as stream:
                stream.write(line("rippleazurite"))
            assert other.search("rippleazurite")["results"]
            with closing(Sessions(home, user, fts=True)) as cold:
                for consumer in (active, cold):
                    if consumer is None:
                        continue
                    assert [hit["text"] for hit in consumer.search("rippleazurite")["results"]] == ["rippleazurite"]
                log.unlink()
                other.sync()
                assert cold.search("rippleazurite")["results"] == []
                assert cold.con.execute("SELECT rowid FROM sess_fts WHERE sess_fts MATCH 'rippleazurite'").fetchall() == []



def test_legacy_warm_cache_repairs_reused_row_and_stale_posting(tmp_path):
    assert fts5_available()
    doc = tmp_path / "reference.md"
    doc.write_text("# Current\n\nvelvetquartz approval note.\n")
    home = tmp_path / "store"
    with closing(KB(home, [doc], fts=True)) as original:
        assert original.search("velvetquartz")
        row = original.con.execute("SELECT rowid FROM kb_sections").fetchone()[0]
        original.con.execute("INSERT INTO kb_fts(rowid,title,body) VALUES(999,'old','strayalmandine')")
        for suffix in ("INSERT", "DELETE", "UPDATE"):
            original.con.execute(f"DROP TRIGGER kb_fts_pending_{suffix}")
        original.con.execute("DROP TABLE kb_fts_pending")
        # A legacy fallback client reused the section row while leaving the
        # old term postings and file fingerprints in place.
        original.con.execute("UPDATE kb_sections SET body=REPLACE(body,'velvetquartz','rippleazurite')")
        original.con.commit()
    with closing(KB(home, [doc], fts=True)) as upgraded:
        hit = upgraded.search("rippleazurite")
        assert [result["id"] for result in hit] == ["reference.md#current"]
        assert upgraded.con.execute("SELECT rowid FROM kb_sections").fetchone()[0] == row
        for old in ("velvetquartz", "strayalmandine"):
            assert not upgraded.search(old)
            assert upgraded.con.execute("SELECT rowid FROM kb_fts WHERE kb_fts MATCH ?", (old,)).fetchall() == []
        assert upgraded.con.execute("SELECT COUNT(*) FROM kb_fts_pending").fetchone()[0] == 0


def test_connected_search_syncs_fallback_commit_after_refresh(tmp_path, monkeypatch):
    assert fts5_available()
    doc = tmp_path / "reference.md"
    doc.write_text("# Current\n\nvelvetquartz approval note.\n")
    home = tmp_path / "store"
    with closing(KB(home, [doc], fts=True)) as active, closing(KB(home, [doc], fts=False)) as other:
        assert active.search("velvetquartz")
        refresh = active.refresh

        def with_peer_commit():
            result = refresh()
            doc.write_text("# Current\n\nrippleazurite approval note.\n")
            other.refresh()
            return result

        monkeypatch.setattr(active, "refresh", with_peer_commit)
        assert [hit["id"] for hit in active.search("rippleazurite")] == ["reference.md#current"]
        assert not active.search("velvetquartz")


def test_large_fallback_journal_collapses_without_losing_searchable_rows(tmp_path, monkeypatch):
    from agent_harness.mcp import kb

    assert fts5_available()
    monkeypatch.setattr(kb, "FTS_JOURNAL_ROWS", 2)
    vault = tmp_path / "docs"
    vault.mkdir()
    home = tmp_path / "store"
    with closing(KB(home, [vault], fts=True)) as active, closing(KB(home, [vault], fts=False)) as fallback:
        assert not active.search("rippleazurite")
        for i in range(6):
            (vault / f"page-{i}.md").write_text("# Current\n\nrippleazurite approval note.\n")
        assert fallback.refresh()["changed"] == 6
        assert [row[0] for row in fallback.con.execute("SELECT id FROM kb_fts_pending")] == [0]
        assert len(active.search("rippleazurite", k=10)) == 6
        assert active.con.execute("SELECT count(*) FROM kb_fts_pending").fetchone()[0] == 0



def test_failed_mirror_apply_retains_pending_rows_for_retry(tmp_path):
    assert fts5_available()
    doc = tmp_path / "reference.md"
    doc.write_text("# Current\n\nvelvetquartz approval note.\n")
    home = tmp_path / "store"
    with closing(KB(home, [doc], fts=True)) as active, closing(KB(home, [doc], fts=False)) as fallback:
        assert active.search("velvetquartz")
        doc.write_text("# Current\n\nrippleazurite approval note.\n")
        assert fallback.search("rippleazurite")
        active.con.execute("CREATE TRIGGER fixture_failure BEFORE DELETE ON kb_fts_pending "
                           "BEGIN SELECT RAISE(ABORT, 'fixture write failure'); END")
        with pytest.raises(sqlite3.IntegrityError, match="fixture write failure"):
            active.search("rippleazurite")
        assert not active.con.in_transaction
        assert active.con.execute("SELECT id FROM kb_fts_pending LIMIT 1").fetchone()
        assert active.con.execute("SELECT rowid FROM kb_fts WHERE kb_fts MATCH 'velvetquartz'").fetchone()
        active.con.execute("DROP TRIGGER fixture_failure")
        assert active.search("rippleazurite")
        assert not active.search("velvetquartz")
