"""Integration-tier selection controls; not OS authentication or native recall proof.

Same-project journal metadata may load. Excluded source bodies and excluded
ranking candidates must not affect the caller's explicitly selected records.
Run with the existing workgraph tier configuration to register integration.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize


pytestmark = pytest.mark.integration

SELECTIONS = [
    pytest.param({"sensitivity": "private"}, "allowed_sensitivities", ["private"],
                 id="sensitivity"),
    pytest.param({"scope": "another-task"}, "allowed_scopes", ["another-task"],
                 id="scope"),
    pytest.param({"layer": "knowledge"}, "layers", ["knowledge"], id="layer"),
]


def policy(**changes):
    selected = {"allowed_sensitivities": ["public"], "allowed_scopes": ["project"],
                "layers": ["project_facts"]}
    return {**selected, **changes}


@pytest.fixture
def memory(tmp_path):
    project_id = initialize(tmp_path)
    store = ProjectMemory(tmp_path, project_id)
    vault = SourceVault(tmp_path, project_id)

    def save(identity, text, *, sensitivity="public", scope="project",
             layer="project_facts"):
        relative = identity + ".txt"
        path = tmp_path / relative
        path.write_text(text + "\n", encoding="utf-8")
        source = vault.capture(relative)
        item = {
            "id": identity, "project_id": project_id, "layer": layer,
            "kind": {"project_facts": "fact", "knowledge": "knowledge"}[layer],
            "scope": scope, "text": text,
            "provenance": [{"source": source, "start_line": 1, "end_line": 1}],
            "confidence": "verified", "sensitivity": sensitivity,
            "access_boundary": "local_user", "owner": "selection-fixture",
            "freshness": "current",
        }
        receipt = store.append(item, expected=None)
        return {"path": path, "source": source, "item": item, "receipt": receipt}

    return store, save


def assert_not_disclosed(result, excluded):
    encoded = json.dumps(result, sort_keys=True)
    markers = (
        excluded["item"]["id"], excluded["item"]["text"],
        excluded["source"]["source"], excluded["source"]["source_id"],
        excluded["source"]["sha256"], excluded["receipt"]["sha256"],
    )
    for marker in markers:
        assert marker not in encoded


def assert_allowed_hit(result, allowed):
    assert result["status"] == "matches"
    assert [hit["receipt"] for hit in result["hits"]] == [allowed["receipt"]]
    assert result["hits"][0]["item"]["text"] == allowed["item"]["text"]
    assert result["hits"][0]["item"]["confidence"] == "verified"
    assert result["hits"][0]["score"] > 0
    assert result["omitted"] == []


def test_in_scope_control_reads_searches_and_recovers_real_source(memory):
    store, save = memory
    allowed = save("allowed-control", "Nebula handoff preserves the approved checkpoint.")
    for method in (store.search, store.search_page):
        assert_allowed_hit(method("nebula handoff", **policy()), allowed)
    read = store.read_scoped(allowed["receipt"], **policy())
    assert read["receipt"] == allowed["receipt"]
    assert read["item"]["text"] == allowed["item"]["text"]
    assert read["item"]["provenance"][0]["source"] == allowed["source"]
    recovered = store.recover(allowed["receipt"], phase="resume",
                              depends_on_memory=True, **policy())
    assert recovered["decision"] == "CANDIDATE"
    assert recovered["record"]["receipt"] == allowed["receipt"]
    assert recovered["record"]["item"]["text"] == allowed["item"]["text"]


@pytest.mark.parametrize("metadata,filter_name,admitted", SELECTIONS)
@pytest.mark.parametrize("method_name", ["search", "search_page"])
def test_excluded_matches_do_not_change_allowed_ranking(
        memory, metadata, filter_name, admitted, method_name):
    store, save = memory
    first = save("allowed-first", "Nebula handoff preserves the approved checkpoint.")
    second = save("allowed-second", "Nebula handoff needs a bounded review of pending work.")
    search = getattr(store, method_name)
    before = search("nebula handoff", **policy())
    assert {hit["receipt"]["id"] for hit in before["hits"]} == {
        first["item"]["id"], second["item"]["id"]}
    assert all(hit["score"] > 0 for hit in before["hits"])

    excluded = save("excluded-ranking-sentinel",
                    "Nebula handoff " * 20 + "EXCLUDED_RANKING_BODY", **metadata)
    after = search("nebula handoff", **policy())

    # Comparing scores catches filter-after-BM25 even when the final IDs look safe.
    assert after["hits"] == before["hits"]
    assert after["status"] == "matches"
    assert after["omitted"] == []
    assert_not_disclosed(after, excluded)
    if method_name == "search_page":
        assert after["total_matches"] == 2
        assert after["total_expired"] == 0
        assert after["remaining"] == 0
        assert after["next_cursor"] is None
    admitted_result = search("nebula handoff", **policy(**{filter_name: admitted}))
    assert [hit["receipt"] for hit in admitted_result["hits"]] == [excluded["receipt"]]


@pytest.mark.parametrize("metadata,filter_name,admitted", SELECTIONS)
@pytest.mark.parametrize("method_name", ["search", "search_page"])
def test_stale_excluded_source_cannot_poison_allowed_recall(
        memory, metadata, filter_name, admitted, method_name):
    store, save = memory
    allowed = save("allowed-current", "Nebula handoff uses current approved evidence.")
    excluded = save("excluded-stale-sentinel",
                    "Nebula handoff " * 20 + "EXCLUDED_STALE_BODY", **metadata)
    excluded["path"].write_text("Replacement bytes invalidate the captured source.\n",
                                encoding="utf-8")
    search = getattr(store, method_name)

    result = search("nebula handoff", **policy())
    assert_allowed_hit(result, allowed)
    assert_not_disclosed(result, excluded)

    # The same real source must refuse when it actually enters the selected scope.
    with pytest.raises(ValueError, match="stale source"):
        search("nebula handoff", **policy(**{filter_name: admitted}))


@pytest.mark.parametrize("metadata,filter_name,admitted", SELECTIONS)
@pytest.mark.parametrize("method_name", ["search", "search_page"])
def test_exact_identity_does_not_bypass_selection(
        memory, metadata, filter_name, admitted, method_name):
    store, save = memory
    allowed = save("allowed-exact", "Current approved exact lookup control.")
    excluded = save("unselectedquasar57291", "EXCLUDED_EXACT_BODY", **metadata)
    search = getattr(store, method_name)

    assert_allowed_hit(search(allowed["item"]["id"], **policy()), allowed)
    result = search(excluded["item"]["id"], **policy())
    assert result["status"] == "no_match"
    assert result["hits"] == []
    assert result["omitted"] == []
    assert_not_disclosed(result, excluded)
    if method_name == "search_page":
        assert result["total_matches"] == 0
        assert result["remaining"] == 0
        assert result["next_cursor"] is None
    admitted_result = search(excluded["item"]["id"],
                             **policy(**{filter_name: admitted}))
    assert [hit["receipt"] for hit in admitted_result["hits"]] == [excluded["receipt"]]


@pytest.mark.parametrize("metadata,filter_name,admitted", SELECTIONS)
@pytest.mark.parametrize("historical", [False, True])
def test_scoped_read_refuses_excluded_record_before_stale_source_resolution(
        memory, metadata, filter_name, admitted, historical):
    store, save = memory
    allowed = save("allowed-read", "An allowed read remains available.")
    excluded = save("excluded-read-sentinel", "EXCLUDED_READ_BODY", **metadata)
    excluded["path"].write_text("Changed original source.\n", encoding="utf-8")

    assert store.read_scoped(allowed["receipt"], **policy())["item"]["text"] == (
        allowed["item"]["text"])
    with pytest.raises(PermissionError) as error:
        store.read_scoped(excluded["receipt"], historical=historical, **policy())
    assert_not_disclosed(str(error.value), excluded)
    with pytest.raises(ValueError, match="stale source"):
        store.read_scoped(excluded["receipt"], **policy(**{filter_name: admitted}))


@pytest.mark.parametrize("metadata,filter_name,admitted", SELECTIONS)
@pytest.mark.parametrize("reuse_verified", [False, True])
def test_recovery_refuses_excluded_record_even_with_a_verified_receipt(
        memory, metadata, filter_name, admitted, reuse_verified):
    store, save = memory
    allowed = save("allowed-recovery", "Current allowed recovery evidence.")
    excluded = save("excluded-recovery-sentinel", "EXCLUDED_RECOVERY_BODY", **metadata)
    excluded["path"].write_text("Changed original source.\n", encoding="utf-8")
    verified = excluded["receipt"] if reuse_verified else None

    control = store.recover(allowed["receipt"], phase="resume",
                            depends_on_memory=True, verified_receipt=allowed["receipt"],
                            **policy())
    assert control["decision"] == "REUSE_VERIFIED"
    assert control["receipt"] == allowed["receipt"]
    with pytest.raises(PermissionError) as error:
        store.recover(excluded["receipt"], phase="resume", depends_on_memory=True,
                      verified_receipt=verified, **policy())
    assert_not_disclosed(str(error.value), excluded)
    with pytest.raises(ValueError, match="stale source"):
        store.recover(excluded["receipt"], phase="resume", depends_on_memory=True,
                      verified_receipt=verified, **policy(**{filter_name: admitted}))


@pytest.mark.parametrize("filter_name", [
    "allowed_sensitivities", "allowed_scopes", "layers",
])
@pytest.mark.parametrize("method_name", ["search", "search_page"])
def test_empty_selection_does_not_fall_back_to_all_records(
        memory, filter_name, method_name):
    store, save = memory
    excluded = save("empty-selection-sentinel", "Nebula handoff EMPTY_SELECTION_BODY")
    search = getattr(store, method_name)
    assert_allowed_hit(search("nebula handoff", **policy()), excluded)
    excluded["path"].write_text("Changed original source.\n", encoding="utf-8")

    result = search("nebula handoff", **policy(**{filter_name: []}))
    assert result["status"] == "no_match"
    assert result["hits"] == []
    assert result["omitted"] == []
    assert_not_disclosed(result, excluded)
    if method_name == "search_page":
        assert result["total_matches"] == 0
        assert result["remaining"] == 0
        assert result["next_cursor"] is None


@pytest.mark.parametrize("metadata,filter_name,admitted", SELECTIONS)
@pytest.mark.parametrize("method_name", ["search", "search_page"])
def test_excluded_id_query_can_still_match_eligible_words(
        memory, metadata, filter_name, admitted, method_name):
    store, save = memory
    allowed = save("allowed-exact", "Current approved exact lookup control.")
    search = getattr(store, method_name)
    query = "excluded-exact-sentinel"
    before = search(query, **policy())
    assert_allowed_hit(before, allowed)
    excluded = save(query, "EXCLUDED_OVERLAP_BODY", **metadata)
    after = search(query, **policy())
    assert after["hits"] == before["hits"]
    assert_not_disclosed(after, excluded)
    selected = search(query, **policy(**{filter_name: admitted}))
    assert [hit["receipt"] for hit in selected["hits"]] == [excluded["receipt"]]


@pytest.mark.parametrize("metadata,filter_name,admitted", SELECTIONS)
def test_fresh_memory_cli_uses_explicit_selection_before_source_resolution(
        memory, metadata, filter_name, admitted, tmp_path):
    store, save = memory
    allowed = save("cli-allowed", "Nebula handoff preserves approved current evidence.")
    excluded = save("cli-excluded", "Nebula handoff EXCLUDED_CLI_BODY", **metadata)
    excluded["path"].write_text("Stale original must not poison other selections.\n", encoding="utf-8")
    home = tmp_path / "child-home"; home.mkdir()
    cli = Path(__file__).resolve().parents[1] / "bin/harness"
    flags = ["--project-root", str(store.root), "--project-id", store.project_id,
             "--allow-sensitivity", "public", "--allow-scope", "project", "--layer", "project_facts"]
    env = {"PATH": os.defpath, "HOME": str(home), "HARNESS_HOME": str(home / "hh"),
           "PYTHONDONTWRITEBYTECODE": "1"}
    def invoke(command, *extra):
        return subprocess.run([sys.executable, str(cli), command, *flags, *extra],
            cwd=home, env=env, text=True, capture_output=True, timeout=15)
    page = invoke("memory-page", "--query", "nebula handoff")
    assert page.returncode == 0 and not page.stderr
    result = json.loads(page.stdout)
    assert_allowed_hit(result, allowed)
    assert_not_disclosed(result, excluded)
    for extra in [[], ["--recover", "resume", "--verified-receipt", json.dumps(excluded["receipt"])]]:
        denied = invoke("memory-read", "--receipt", json.dumps(excluded["receipt"]), *extra)
        assert denied.returncode == 2 and not denied.stdout
        assert "scope" in denied.stderr
        assert_not_disclosed(denied.stderr, excluded)
