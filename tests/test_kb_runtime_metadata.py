"""A connected reader must report its actual selection, without exposing sources."""
import json

import pytest

from agent_harness.mcp.server import Server


def call(server, name, arguments):
    return server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                          "params": {"name": name, "arguments": arguments}})["result"]


@pytest.mark.parametrize("selection", ["default", "paths", "environment"])
def test_selected_scope_is_reported_and_captured_at_creation(tmp_path, monkeypatch, selection):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("HARNESS_KB_PATHS", raising=False)
    home = tmp_path / "hh"
    profile = home / "profile"
    profile.mkdir(parents=True)
    own = tmp_path / "own"
    own.mkdir()
    if selection == "environment":
        monkeypatch.setenv("HARNESS_KB_PATHS", str(own))
    server = Server(home=home, kb_paths=[own] if selection == "paths" else None, fts=False)
    try:
        first = call(server, "kb_get", {"id": "NEW.md#notice"})
        assert first["isError"] is True
        initial = first["_meta"]["agent-harness/kb"]
        assert initial["selection"] == selection
        assert initial["live_profile"] is (selection == "default")
        assert initial["initialized"] is True
        assert len(initial["loaded_code_sha256"]) == 64
        assert len(initial["home_identity"]) == 64
        monkeypatch.setenv("HARNESS_KB_PATHS", str(tmp_path / "other"))
        (profile / "NEW.md").write_text("# Notice\nquartznotice newly published\n")
        after = call(server, "kb_get", {"id": "NEW.md#notice"})
        status = after["_meta"]["agent-harness/kb"]
        assert status["selection"] == initial["selection"]
        assert status["loaded_code_sha256"] == initial["loaded_code_sha256"]
        assert status["home_identity"] == initial["home_identity"]
        assert after["isError"] is (selection != "default")
        if selection == "default":
            assert "quartznotice" in after["content"][0]["text"]
        assert str(tmp_path) not in json.dumps(status)
        assert "quartznotice" not in json.dumps(status)
    finally:
        if server._kb is not None:
            server._kb.close()


@pytest.mark.parametrize("name,arguments", [("kb_search", {"query": "unknown"}),
                                           ("kb_toc", {})])
def test_empty_reads_are_diagnostic_without_inventing_a_hit(tmp_path, monkeypatch, name, arguments):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("HARNESS_KB_PATHS", raising=False)
    server = Server(home=tmp_path / "hh", kb_paths=[], fts=False)
    try:
        result = call(server, name, arguments)
        assert json.loads(result["content"][0]["text"]) == []
        meta = result["_meta"]["agent-harness/kb"]
        assert meta["selection"] == "paths"
        assert meta["root_count"] == 0
        assert meta["live_profile"] is False
    finally:
        if server._kb is not None:
            server._kb.close()


def test_bad_arguments_do_not_initialize_or_scan_the_kb(tmp_path):
    server = Server(home=tmp_path / "hh", kb_paths=[], fts=False)
    result = call(server, "kb_get", {})
    assert result["isError"] is True
    assert result["_meta"]["agent-harness/kb"]["initialized"] is False
    assert server._kb is None
    assert not (tmp_path / "hh/index.sqlite").exists()
