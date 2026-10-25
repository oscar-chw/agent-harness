"""A citation proves where words came from; it does not prove an arbitrary claim."""

import pytest

from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize


@pytest.fixture
def record(tmp_path):
    project_id = initialize(tmp_path)
    store = ProjectMemory(tmp_path, project_id)

    def save(source_text, claim, *, identity="claim"):
        (tmp_path / "source.txt").write_text(source_text)
        source = SourceVault(tmp_path, project_id).capture("source.txt")
        item = {
            "id": identity, "project_id": project_id, "layer": "project_facts", "kind": "fact",
            "scope": "project", "text": claim,
            "provenance": [{"source": source, "start_line": 1, "end_line": 1}],
            "confidence": "verified", "sensitivity": "internal", "access_boundary": "local_user",
            "owner": "fixture", "freshness": "current",
        }
        receipt = store.append(item, expected=None)
        reviewed = store.read_scoped(receipt, allowed_sensitivities=["internal"],
                                     allowed_scopes=["project"], layers=["project_facts"])
        return item, reviewed["item"]

    return save


@pytest.mark.parametrize("source_text,claim", [
    ("Port: 8081\n", "Port: 9999"),
    ('{"chosen": 8081, "alternatives": [8081, 9999]}\n', "Port: 9999"),
    ("Do not use Port: 9999.\n", "Port: 9999"),
    ("Deletion is disabled.\n", "Deletion is enabled."),
])
def test_contradiction_or_quoted_words_cannot_be_verified(record, source_text, claim):
    proposed, stored = record(source_text, claim)
    assert proposed["confidence"] == "verified"
    assert stored["text"] == claim
    assert stored["confidence"] == "pending"


def test_exact_cited_assertion_can_keep_verified_label(record):
    _, stored = record("Port: 8081\n", "Port: 8081")
    assert stored["confidence"] == "verified"


@pytest.mark.parametrize("source_text,claim", [
    ("The service listens on port 8081.\n", "Service port: 8081"),
    ("The service listens on port 8081.\n", "Service port: 8082"),
    ("The service is in review.\n", "The service is deployed."),
])
def test_paraphrase_and_unknown_relation_need_semantic_review(record, source_text, claim):
    _, stored = record(source_text, claim)
    assert stored["text"] == claim
    assert stored["confidence"] == "pending"


def test_pending_claim_is_not_a_normal_search_or_recovery_hit(tmp_path):
    project_id = initialize(tmp_path)
    (tmp_path / "source.txt").write_text("Port: 8081\n")
    source = SourceVault(tmp_path, project_id).capture("source.txt")
    store = ProjectMemory(tmp_path, project_id)
    item = {"id": "service-port", "project_id": project_id, "layer": "project_facts", "kind": "fact",
            "scope": "project", "text": "Port: 9999", "provenance": [
                {"source": source, "start_line": 1, "end_line": 1}], "confidence": "verified",
            "sensitivity": "internal", "access_boundary": "local_user", "owner": "fixture",
            "freshness": "current"}
    receipt = store.append(item, expected=None)
    policy = {"allowed_sensitivities": ["internal"], "allowed_scopes": ["project"],
              "layers": ["project_facts"]}
    results = store.search("service-port", **policy)
    assert not results["hits"]
    assert {entry["reason"] for entry in results["omitted"]} == {"pending"}
    recovered = store.recover(receipt, phase="resume", depends_on_memory=True,
                              verified_receipt=receipt, **policy)
    assert recovered["decision"] == "HOLD" and recovered["reason"] == "pending"
    assert "record" not in recovered
    exact = store.read_scoped(receipt, **policy)
    assert exact["kind"] == "pending-memory-data"
    assert exact["usable_for_current_decisions"] is False
    page = store.search_page("service-port", **policy)
    assert page["hits"] == []
    assert {entry["reason"] for entry in page["omitted"]} == {"pending"}
    with pytest.raises(ValueError, match="pending memory"):
        store.read(receipt, allowed_sensitivities=["internal"])
    with pytest.raises(ValueError, match="pending memory"):
        store.latest("service-port", allowed_sensitivities=["internal"])


def test_historical_superseded_fact_is_explicitly_unusable_for_current_decisions(tmp_path):
    project_id = initialize(tmp_path)
    store = ProjectMemory(tmp_path, project_id)
    policy = {"allowed_sensitivities": ["internal"], "allowed_scopes": ["project"],
              "layers": ["project_facts"]}

    def item(text):
        (tmp_path / "source.txt").write_text(text + "\n")
        source = SourceVault(tmp_path, project_id).capture("source.txt")
        return {"id": "service-port", "project_id": project_id, "layer": "project_facts",
                "kind": "fact", "scope": "project", "text": text,
                "provenance": [{"source": source, "start_line": 1, "end_line": 1}],
                "confidence": "verified", "sensitivity": "internal",
                "access_boundary": "local_user", "owner": "fixture", "freshness": "current"}

    old = store.append(item("Port: 8081"), expected=None)
    new = store.append(item("Port: 8082"), expected=old)
    historical = store.read_scoped(old, historical=True, **policy)
    assert historical["historical"] is True
    assert historical["item"]["text"] == "Port: 8081"
    assert historical["usable_for_current_decisions"] is False
    current = store.read_scoped(new, **policy)
    assert current["item"]["text"] == "Port: 8082"
    assert current.get("usable_for_current_decisions", True) is True
