"""Connected KB readers must apply honesty filtering to the current source revision."""

import os

import pytest

from agent_harness.mcp.kb import KB


@pytest.mark.integration
@pytest.mark.parametrize("fts", [False, True])
@pytest.mark.parametrize("refresh_owner", ["reader", "peer"])
@pytest.mark.parametrize(
    "before,after,initially_found,finally_found",
    [
        ("quarterly backup checklist required", "backup approval required quarterly", False, True),
        ("backup approval required quarterly", "quarterly backup checklist required", True, False),
    ],
    ids=["new-evidence-is-found", "removed-evidence-is-suppressed"],
)
def test_connected_honesty_reader_uses_current_evidence_after_refresh(
        tmp_path, monkeypatch, fts, refresh_owner, before, after,
        initially_found, finally_found):
    monkeypatch.setenv("HARNESS_KB_HONESTY", "1")
    source = tmp_path / "guide.md"
    source.write_text("# Procedure\n" + before + "\n")
    home = tmp_path / "cache"
    reader = KB(home=home, paths=[source], fts=fts)
    peer = KB(home=home, paths=[source], fts=fts)
    readers = {"reader": reader, "peer": peer}
    try:
        assert reader.fts is fts
        query = "backup approval required quarterly"
        assert bool(reader.search(query)) is initially_found

        old = source.stat()
        source.write_text("# Procedure\n" + after + "\n")
        os.utime(source, ns=(old.st_atime_ns, old.st_mtime_ns + 1_000_000_000))
        readers[refresh_owner].refresh()

        current = reader.get("guide.md#procedure")
        assert current["text"] == "# Procedure\n" + after + "\n"
        assert bool(reader.search(query)) is finally_found
    finally:
        reader.close()
        peer.close()
