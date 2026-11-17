"""Ordinary memory entrypoints honor scoped tombstones without injected guards."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_harness import memory_forget as MF
from agent_harness.mcp.memory import Memory
from agent_harness.mcp.server import Server
from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize


TEXT = "# Retired advice\nUse `retired-quartz --unsafe-mode` on the build box.\n"
PARAPHRASE = "The build box should use retired-quartz --unsafe-mode."
UNRELATED = "Use the ordinary deployment checklist."


@pytest.fixture
def admission(tmp_path):
    corpus = tmp_path / "corpus"
    (corpus / "memory").mkdir(parents=True)
    (corpus / "memory/old.md").write_text(TEXT)
    (corpus / "memory/current.md").write_text("# Current\nUse the ordinary deployment checklist.\n")
    escrow = tmp_path / "escrow"
    MF.unlearn(corpus, "memory/old.md", authority="fixture-owner", reason="invalid advice",
               escrow_dir=escrow, apply=True)
    home = tmp_path / "hh"
    (home / "profile").mkdir(parents=True)
    config = {"schema": 1, "ledger_root": str(corpus.resolve()), "escrow_dir": str(escrow.resolve())}
    (home / "profile/memory-admission.json").write_text(json.dumps(config))
    return home, corpus, escrow, config


def test_ordinary_server_memory_refuses_unlearned_text_and_allows_unrelated(admission):
    home, _, _, _ = admission
    server = Server(home=home, fts=False)
    try:
        assert server.call_tool("mem_add", {"text": TEXT, "scope": "user"})["ok"] is False
        assert server.mem.mem_add(PARAPHRASE, scope="user")["ok"] is False
        assert "id" in server.mem.mem_add(UNRELATED, scope="user")
        assert server.mem.mem_search("retired-quartz") == []
    finally:
        server.mem.close()


def test_existing_script_hook_entrypoint_retains_runtime_admission(admission):
    home, _, _, _ = admission
    script = Path(__file__).resolve().parents[1] / "src/agent_harness/mcp/memory.py"
    env = dict(os.environ, HARNESS_HOME=str(home))
    result = subprocess.run([sys.executable, str(script), "digest"], env=env,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr


def test_broken_configuration_never_falls_back_to_an_unprotected_store(admission):
    home, _, _, _ = admission
    (home / "profile/memory-admission.json").write_text('{"schema":1}')
    memory = Memory(home=home, fts=False)
    try:
        with pytest.raises(ValueError, match="configuration"):
            memory.mem_add(TEXT)
        assert not (home / "memory/user").exists()
    finally:
        memory.close()


def test_live_relearn_reopens_normal_admission(admission):
    home, corpus, escrow, _ = admission
    memory = Memory(home=home, fts=False)
    try:
        assert memory.mem_add(TEXT, scope="user")["ok"] is False
        MF.relearn(corpus, "memory/old.md", authority="fixture-owner", reason="explicit restore",
                   escrow_dir=escrow, mode="restore", apply=True)
        assert "id" in memory.mem_add(TEXT, scope="user")
    finally:
        memory.close()


def test_corrupt_ledger_stops_admission_without_changing_it(admission):
    home, corpus, _, _ = admission
    ledger = corpus / MF.LEDGER_REL
    ledger.write_text("not valid JSON\n")
    before = ledger.read_bytes()
    memory = Memory(home=home, fts=False)
    try:
        assert memory.mem_add(UNRELATED, scope="user")["ok"] is False
        assert ledger.read_bytes() == before
    finally:
        memory.close()


def test_unconfigured_store_uses_its_own_ledger_without_changing_other_scopes(tmp_path, admission):
    home, corpus, _, _ = admission
    memory = Memory(home=tmp_path / "unrelated", fts=False)
    try:
        assert "id" in memory.mem_add(TEXT, scope="user")
        assert not (home / "memory/user").exists()
        assert MF.page_states(MF.load_ledger(corpus))["memory/old.md"] == "tombstoned"
    finally:
        memory.close()


def test_late_configuration_applies_to_an_existing_reader(tmp_path, admission):
    home, _, _, config = admission
    path = home / "profile/memory-admission.json"
    path.unlink()
    memory = Memory(home=home, fts=False)
    try:
        assert "id" in memory.mem_add(TEXT, scope="user")
        path.write_text(json.dumps(config))
        assert memory.mem_add(TEXT, scope="user")["ok"] is False
        assert memory.mem_search("retired-quartz") == []
    finally:
        memory.close()


def test_project_memory_append_uses_its_scoped_configuration(tmp_path, admission):
    _, _, _, config = admission
    root = tmp_path / "project"
    root.mkdir()
    project_id = initialize(root)
    (root / ".harness/memory-admission.json").write_text(json.dumps(config))
    (root / "evidence.md").write_text(TEXT)
    source = SourceVault(root, project_id).capture("evidence.md")
    item = {"id": "old-advice", "project_id": project_id, "layer": "project_facts", "kind": "fact",
            "scope": "test", "text": TEXT, "provenance": [{"source": source, "start_line": 1, "end_line": 2}],
            "confidence": "verified", "sensitivity": "internal", "access_boundary": "local_user",
            "owner": "fixture-owner", "freshness": "current"}
    with pytest.raises(ValueError, match="backflow"):
        ProjectMemory(root, project_id).append(item, expected=None)
    assert list((root / ".harness/records").glob("*.json")) == []
