"""The section text budget also covers appended navigation and notices."""

import pytest

from agent_harness.mcp.kb import KB


@pytest.mark.parametrize("fts", [False, True])
@pytest.mark.parametrize("page_only", [False, True])
def test_large_contents_cannot_escape_a_small_read_budget(tmp_path, fts, page_only):
    source = tmp_path / "guide.md"
    source.write_text(
        "# Overview\nKEEP_CURRENT_QUALIFICATION\n"
        + "".join(
            f"## Topic {i} architecture rollback validation\nDetail {i}.\n"
            for i in range(180)
        )
    )
    reader = KB(home=tmp_path / "cache", paths=[source], fts=fts)
    try:
        identity = "guide.md" if page_only else "guide.md#overview"
        result = reader.get(identity, max_bytes=400)
        assert len(result["text"].encode()) <= 400
        assert result["truncated"] is True
        assert "truncated" in result["text"].lower()
        assert "kb_search" in result["text"] or "max_bytes" in result["text"]
        if not page_only:
            assert "KEEP_CURRENT_QUALIFICATION" in result["text"]
        # An omitted heading is still independently retrievable; no source or
        # index record was dropped to make a short response.
        last = reader.get("guide.md#topic-179-architecture-rollback-validation")
        assert "Detail 179." in last["text"] and last["truncated"] is False
        assert "Topic 179" in source.read_text()
    finally:
        reader.close()


def test_small_contents_and_body_remain_complete_when_they_fit(tmp_path):
    source = tmp_path / "guide.md"
    source.write_text("# Overview\nKeep the condition.\n## Deploy\nRun the check.\n")
    reader = KB(home=tmp_path / "cache", paths=[source], fts=False)
    try:
        section = reader.get("guide.md#overview", max_bytes=1000)
        assert not section["truncated"]
        assert section["text"].startswith("# Overview\nKeep the condition.")
        assert "guide.md#deploy" in section["text"]
        page = reader.get("guide.md", max_bytes=1000)
        assert not page["truncated"]
        assert "guide.md#overview" in page["text"] and "guide.md#deploy" in page["text"]
    finally:
        reader.close()


@pytest.mark.parametrize("limit", [200, 333, 2000])
def test_utf8_body_and_notice_share_the_same_budget(tmp_path, limit):
    source = tmp_path / "guide.md"
    source.write_text("# Overview\n導覽\n## Evidence\n" + ("必須得到批准。\n" * 400))
    reader = KB(home=tmp_path / "cache", paths=[source], fts=False)
    try:
        small = reader.get("guide.md#evidence", max_bytes=limit)
        assert len(small["text"].encode()) <= limit
        assert small["truncated"] is True
        assert small["text"].encode().decode() == small["text"]
        assert "next_part" in small
        complete = reader.get("guide.md#evidence", max_bytes=8192)
        assert complete["truncated"] is False and "必須得到批准。" in complete["text"]
    finally:
        reader.close()
