"""Integration expectations for optional evidence packets; execution belongs to root.

These source-bound fixtures test quote/citation integrity and existing record
labels, not semantic truth, permission grants or native model compliance.
"""
import hashlib
import json

import pytest

from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize


pytestmark = pytest.mark.integration


def policy(**changes):
    return {"allowed_sensitivities": ["public"], "allowed_scopes": ["project"],
            "layers": ["project_facts"], **changes}


def wire_bytes(value):
    return len(json.dumps(value, ensure_ascii=False).encode("utf-8"))


def tree_bytes(root):
    return {str(path.relative_to(root)): path.read_bytes() if path.is_file() else None
            for path in root.rglob("*")}


@pytest.fixture
def memory(tmp_path):
    project_id = initialize(tmp_path)
    store = ProjectMemory(tmp_path, project_id)
    vault = SourceVault(tmp_path, project_id)

    def source(relative, text):
        path = tmp_path / relative
        path.write_bytes(text.encode("utf-8"))
        return {"path": path, "ref": vault.capture(relative)}

    def save(identity, text, provenance, *, expected=None, **changes):
        item = {
            "id": identity, "project_id": project_id, "layer": "project_facts",
            "kind": "fact", "scope": "project", "text": text,
            "provenance": provenance, "confidence": "verified",
            "sensitivity": "public", "access_boundary": "local_user",
            "owner": "source-packet-fixture", "freshness": "current", **changes,
        }
        return item, store.append(item, expected=expected)

    return store, vault, source, save


def entry(source, start=1, end=1):
    return {"source": source["ref"], "start_line": start, "end_line": end}


def expected_source(source, text, start=1, end=1, *, historical=False):
    return {"kind": "source-data", "text": text, "historical": historical,
            "citation": {**source["ref"], "start_line": start, "end_line": end}}


def test_default_and_explicit_false_keep_the_existing_packet(memory):
    store, _, source, save = memory
    original = source("current.txt", "Ticket owner approval is required.\n")
    _, receipt = save("default-control", "Ticket owner approval is required.",
                      [entry(original)])
    default = store.read_scoped(receipt, **policy())
    explicit_false = store.read_scoped(receipt, include_sources=False, **policy())
    with_sources = store.read_scoped(receipt, include_sources=True, **policy())

    assert set(default) == {"schema", "kind", "project_id", "historical", "item", "receipt"}
    assert default["kind"] == "retrieved-memory-data"
    assert default["item"]["confidence"] == "verified"
    assert default["receipt"] == receipt
    assert "source_spans" not in default
    assert explicit_false == default
    assert with_sources["source_spans"] == [
        expected_source(original, "Ticket owner approval is required.\n")]
    assert {key: value for key, value in with_sources.items()
            if key != "source_spans"} == default


def test_evidence_preserves_actual_provenance_order_exact_bytes_and_citations(memory):
    store, _, source, save = memory
    first = source("first.txt",
                   "heading\r\nTicket owner approval is required.\r\n"
                   "UNSELECTED_LINE_32701\r\nRollback needs a recorded reason.")
    second = source("second.txt", "first\n原始核准条件\u2028仍是一行。\nlast\n")
    source("unlinked.txt", "UNLINKED_BODY_62983\n")
    provenance = [entry(second, 2, 2), entry(first, 2, 2),
                  entry(first, 4, 4), entry(first, 2, 2)]
    _, receipt = save("ordered-provenance", "A derived note omits conditions.", provenance)

    packet = store.read_scoped(receipt, include_sources=True, **policy())
    assert packet["source_spans"] == [
        expected_source(second, "原始核准条件\u2028仍是一行。\n", 2, 2),
        expected_source(first, "Ticket owner approval is required.\r\n", 2, 2),
        expected_source(first, "Rollback needs a recorded reason.", 4, 4),
        expected_source(first, "Ticket owner approval is required.\r\n", 2, 2),
    ]
    assert packet["item"]["provenance"] == provenance
    encoded = json.dumps(packet, ensure_ascii=False)
    assert "UNSELECTED_LINE_32701" not in encoded
    assert "UNLINKED_BODY_62983" not in encoded
    for span, selected in zip(packet["source_spans"], (second, first, first, first)):
        assert span["citation"]["sha256"] == hashlib.sha256(
            selected["path"].read_bytes()).hexdigest()
        assert span["citation"]["project_id"] == receipt["project_id"]


def test_each_distinct_provenance_entry_is_resolved_once_after_selection(memory, monkeypatch):
    store, _, source, save = memory
    first = source("once-a.txt", "First actual condition.\n")
    second = source("once-b.txt", "Second actual condition.\n")
    _, receipt = save("once-control", "A pending combined description.",
                      [entry(first), entry(second)])
    calls = []
    resolve = SourceVault.resolve

    def traced(vault, ref, **kwargs):
        calls.append((ref["source_id"], kwargs.get("start_line", 1),
                      kwargs.get("end_line"), kwargs.get("historical", False)))
        return resolve(vault, ref, **kwargs)

    # Delegate to the real public resolver; a second validation could observe new bytes.
    monkeypatch.setattr(SourceVault, "resolve", traced)
    packet = store.read_scoped(receipt, include_sources=True, **policy())
    assert packet["source_spans"] == [
        expected_source(first, "First actual condition.\n"),
        expected_source(second, "Second actual condition.\n"),
    ]
    assert calls == [(first["ref"]["source_id"], 1, 1, False),
                     (second["ref"]["source_id"], 1, 1, False)]


def test_source_review_does_not_promote_a_pending_derived_note(memory):
    store, _, source, save = memory
    original = source("approval.txt",
                      "Tests must pass.\nDeployment also requires ticket-owner approval.\n")
    _, receipt = save("pending-note", "Deployment only requires passing tests.",
                      [entry(original, 1, 2)])
    before = store.read_scoped(receipt, **policy())
    reviewed = store.read_scoped(receipt, include_sources=True, **policy())

    assert before["kind"] == reviewed["kind"] == "pending-memory-data"
    assert before["item"]["confidence"] == reviewed["item"]["confidence"] == "pending"
    assert reviewed["usable_for_current_decisions"] is False
    assert reviewed["item"]["text"] == "Deployment only requires passing tests."
    assert reviewed["source_spans"] == [expected_source(
        original, "Tests must pass.\nDeployment also requires ticket-owner approval.\n", 1, 2)]
    assert store.read_scoped(receipt, **policy()) == before
    recovered = store.recover(receipt, phase="resume", depends_on_memory=True,
                              verified_receipt=receipt, **policy())
    assert recovered["decision"] == "HOLD"
    assert recovered["reason"] == "pending"
    assert "record" not in recovered
    assert store.search("pending-note", **policy())["hits"] == []
    with pytest.raises(ValueError, match="pending"):
        store.read(receipt, allowed_sensitivities=["public"])


@pytest.mark.parametrize("include_sources", [False, True])
def test_superseded_record_requires_explicit_history_and_keeps_old_evidence(
        memory, include_sources):
    store, _, source, save = memory
    old = source("decision.txt", "The release is held.\n")
    _, old_receipt = save("release-state", "The release is held.", [entry(old)])
    current = source("decision.txt", "The release needs a new review.\n")
    _, new_receipt = save("release-state", "The release needs a new review.",
                          [entry(current)], expected=old_receipt)

    with pytest.raises(ValueError, match="superseded"):
        store.read_scoped(old_receipt, include_sources=include_sources, **policy())
    history = store.read_scoped(old_receipt, historical=True,
                                include_sources=include_sources, **policy())
    assert history["receipt"] == old_receipt
    assert history["historical"] is True
    assert history["current_status"] == "superseded"
    assert history["usable_for_current_decisions"] is False
    assert history["item"]["text"] == "The release is held."
    if include_sources:
        assert history["source_spans"] == [
            expected_source(old, "The release is held.\n", historical=True)]
    else:
        assert "source_spans" not in history
    latest = store.read_scoped(new_receipt, include_sources=True, **policy())
    assert latest["source_spans"] == [
        expected_source(current, "The release needs a new review.\n")]


@pytest.mark.parametrize("include_sources", [False, True])
def test_withdrawal_cannot_be_bypassed_by_requesting_sources(memory, include_sources):
    store, _, source, save = memory
    original = source("withdrawn.txt", "Use only an approved release.\n")
    _, old_receipt = save("withdrawn-advice", "Use only an approved release.",
                          [entry(original)])
    _, withdrawn = save("withdrawn-advice", "Use only an approved release.",
                        [entry(original)], expected=old_receipt, freshness="withdrawn")

    with pytest.raises(ValueError, match="withdrawn"):
        store.read_scoped(withdrawn, include_sources=include_sources, **policy())
    for receipt in (old_receipt, withdrawn):
        history = store.read_scoped(receipt, historical=True,
                                    include_sources=include_sources, **policy())
        assert history["historical"] is True
        assert history["current_status"] == "withdrawn"
        assert history["usable_for_current_decisions"] is False
        if include_sources:
            assert history["source_spans"] == [
                expected_source(original, "Use only an approved release.\n", historical=True)]
        else:
            assert "source_spans" not in history
    recovered = store.recover(old_receipt, phase="resume",
                              depends_on_memory=True, **policy())
    assert recovered["decision"] == "REFUSE_WITHDRAWN"
    assert "record" not in recovered


@pytest.mark.parametrize("metadata,admitted", [
    pytest.param({"sensitivity": "private"}, {"allowed_sensitivities": ["private"]},
                 id="sensitivity"),
    pytest.param({"scope": "other-task"}, {"allowed_scopes": ["other-task"]}, id="scope"),
    pytest.param({"layer": "knowledge", "kind": "knowledge"}, {"layers": ["knowledge"]},
                 id="layer"),
])
@pytest.mark.parametrize("historical", [False, True])
def test_scope_is_checked_before_resolving_corrupt_excluded_sources(
        memory, metadata, admitted, historical, tmp_path):
    store, vault, source, save = memory
    allowed = source("allowed.txt", "An in-scope source remains readable.\n")
    _, good = save("scope-control", "An in-scope source remains readable.", [entry(allowed)])
    excluded = source("excluded.txt", "EXCLUDED_BODY_86271\n")
    _, denied = save("denied-record", "EXCLUDED_BODY_86271", [entry(excluded)], **metadata)
    snapshot = tmp_path / ".harness" / "sources" / (excluded["ref"]["source_id"] + ".json")
    snapshot.write_bytes(b"{}")

    control = store.read_scoped(good, include_sources=True, **policy())
    assert control["source_spans"] == [
        expected_source(allowed, "An in-scope source remains readable.\n")]
    with pytest.raises(ValueError, match="integrity"):
        vault.resolve(excluded["ref"], historical=historical)
    with pytest.raises(PermissionError) as error:
        store.read_scoped(denied, historical=historical, include_sources=True, **policy())
    message = str(error.value)
    for marker in ("EXCLUDED_BODY_86271", excluded["ref"]["source_id"],
                   excluded["ref"]["sha256"], denied["sha256"]):
        assert marker not in message
    with pytest.raises(ValueError, match="integrity"):
        store.read_scoped(denied, historical=historical, include_sources=True,
                          **policy(**admitted))


@pytest.mark.parametrize("include_sources", [False, True])
def test_changed_current_source_refuses_but_explicit_history_returns_pinned_bytes(
        memory, include_sources):
    store, _, source, save = memory
    original = source("changed.txt", "Original approved condition.\n")
    _, receipt = save("changed-source", "Original approved condition.", [entry(original)])
    original["path"].write_bytes(b"Different current condition.\n")

    with pytest.raises(ValueError, match="stale source"):
        store.read_scoped(receipt, include_sources=include_sources, **policy())
    history = store.read_scoped(receipt, historical=True,
                                include_sources=include_sources, **policy())
    assert history["historical"] is True
    assert history["item"]["text"] == "Original approved condition."
    if include_sources:
        assert history["source_spans"] == [
            expected_source(original, "Original approved condition.\n", historical=True)]


@pytest.mark.parametrize("historical", [False, True])
def test_corrupt_snapshot_refuses_in_current_and_history_modes(memory, historical, tmp_path):
    store, _, source, save = memory
    original = source("corrupt.txt", "Pinned integrity control.\n")
    _, receipt = save("corrupt-source", "Pinned integrity control.", [entry(original)])
    control = store.read_scoped(receipt, include_sources=True, historical=historical, **policy())
    assert control["source_spans"] == [
        expected_source(original, "Pinned integrity control.\n", historical=historical)]
    snapshot = tmp_path / ".harness" / "sources" / (original["ref"]["source_id"] + ".json")
    snapshot.write_bytes(b"{}")
    before = tree_bytes(tmp_path)

    with pytest.raises(ValueError, match="integrity"):
        store.read_scoped(receipt, include_sources=True, historical=historical, **policy())
    assert tree_bytes(tmp_path) == before


@pytest.mark.parametrize("invalid", [
    pytest.param(None, id="none"), pytest.param(0, id="zero"), pytest.param(1, id="one"),
    pytest.param("true", id="string"), pytest.param([], id="list"), pytest.param({}, id="dict"),
])
def test_include_sources_requires_an_exact_bool(memory, invalid):
    store, _, source, save = memory
    original = source("bool.txt", "Boolean option control.\n")
    _, receipt = save("bool-control", "Boolean option control.", [entry(original)])
    assert "source_spans" not in store.read_scoped(receipt, include_sources=False, **policy())
    assert store.read_scoped(receipt, include_sources=True, **policy())["source_spans"]
    with pytest.raises(ValueError, match="include_sources|sources|boolean"):
        store.read_scoped(receipt, include_sources=invalid, **policy())


def test_budget_covers_the_whole_utf8_packet_without_truncation(memory):
    store, _, source, save = memory
    quote = "Ticket-owner approval condition: " + "核验" * 650 + "\n"
    first = source("budget-a.txt", "header\n" + quote + "footer\n")
    second = source("budget-b.txt", "Additional approval is still required.\n")
    _, receipt = save("budget-note", "A compact pending note.",
                      [entry(first, 2, 2), entry(second)])
    default = store.read_scoped(receipt, **policy())
    small_budget = wire_bytes(default)
    assert store.read_scoped(receipt, include_sources=False,
                             max_bytes=small_budget, **policy()) == default
    with pytest.raises(ValueError, match="budget"):
        store.read_scoped(receipt, include_sources=True, max_bytes=small_budget, **policy())

    full = store.read_scoped(receipt, include_sources=True, max_bytes=65536, **policy())
    assert full["source_spans"] == [
        expected_source(first, quote, 2, 2),
        expected_source(second, "Additional approval is still required.\n"),
    ]
    exact_budget = wire_bytes(full)
    assert exact_budget > len(json.dumps(full, ensure_ascii=False))
    assert store.read_scoped(receipt, include_sources=True,
                             max_bytes=exact_budget, **policy()) == full
    with pytest.raises(ValueError, match="budget"):
        store.read_scoped(receipt, include_sources=True, max_bytes=exact_budget - 1, **policy())


def test_source_review_success_and_budget_refusal_do_not_write_project_state(memory, tmp_path):
    store, _, source, save = memory
    original = source("readonly.txt", "Inspect this evidence without activation.\n")
    _, receipt = save("readonly-note", "A weaker derived note.", [entry(original)])
    before = tree_bytes(tmp_path)

    store.read_scoped(receipt, **policy())
    store.read_scoped(receipt, include_sources=False, **policy())
    store.read_scoped(receipt, include_sources=True, **policy())
    store.read_scoped(receipt, historical=True, include_sources=True, **policy())
    with pytest.raises(ValueError, match="budget"):
        store.read_scoped(receipt, include_sources=True, max_bytes=1, **policy())
    assert tree_bytes(tmp_path) == before
