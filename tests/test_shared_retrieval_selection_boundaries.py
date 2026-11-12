"""Disposable public-note selection controls; root owns execution and qualification."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_harness.vault_retrieval import search_shared_documents
from agent_harness.vault_sources import read_shared_document


pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[1]
VAULT_ID = "selection-fixture"
QUERY = "quartzledger repair"


def note(root, identity, body, *, public=True, title="Fixture note"):
    relative = f"notes/{identity}.md"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = f"id: {identity}\ntitle: {title}\n{body}".encode("utf-8")
    path.write_bytes(raw)
    return {
        "id": identity, "document_type": "method_note", "title": title,
        "path": relative, "sha256": hashlib.sha256(raw).hexdigest(),
        "rights": {
            "redistribution": "public" if public else "private",
            "license": "CC0-1.0", "basis": "Synthetic note authored for this test.",
        },
        "source_refs": [{
            "uri": f"urn:selection-fixture:{identity}",
            "kind": "synthetic_fixture", "revision": "fixture-v1",
        }],
    }


def catalogue(root, documents):
    raw = json.dumps({
        "schema": "quant-shared-notes/v1", "revision": "selection-v1",
        "documents": documents,
    }).encode("utf-8")
    (root / "manifest.json").write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def search(root, pin, allowed_ids, backend, query=QUERY):
    return search_shared_documents(
        root, vault_id=VAULT_ID, manifest="manifest.json", manifest_sha256=pin,
        allowed_ids=list(allowed_ids), query=query, backend=backend,
    )


def read_document(root, pin, identity):
    return read_shared_document(
        root, vault_id=VAULT_ID, manifest="manifest.json", manifest_sha256=pin,
        document_id=identity,
    )


@pytest.fixture(params=["lexical", "fts5"])
def backend(request):
    # FTS5 must actually execute: an unavailable backend is not a passing control.
    return request.param


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    approved = [
        note(root, "approved-a", "quartzledger repair uses the documented remedy.\n"),
        note(root, "approved-b", "quartzledger inspection retains its receipt.\n"),
    ]
    return root, approved


def excluded_note(root, problem):
    doc = note(
        root, f"excluded-{problem}",
        ("quartzledger repair " * 80) + "EXCLUDED_BODY_CANARY\n",
        public=problem != "nonpublic", title="quartzledger repair",
    )
    if problem == "stale":
        with (root / doc["path"]).open("ab") as handle:
            handle.write(b"UNAPPROVED_REVISION_CANARY\n")
    return doc


def assert_no_excluded_data(result, excluded):
    serialized = json.dumps(result)
    for doc in excluded:
        assert doc["id"] not in serialized
        assert doc["path"] not in serialized
        assert doc["sha256"] not in serialized
    assert "EXCLUDED_BODY_CANARY" not in serialized
    assert "UNAPPROVED_REVISION_CANARY" not in serialized


def test_excluded_ids_are_filtered_before_any_body_open(vault, backend, monkeypatch):
    root, approved = vault
    excluded = [excluded_note(root, problem) for problem in ("stale", "nonpublic", "better-match")]
    pin = catalogue(root, approved + excluded)
    forbidden = {(root / doc["path"]).resolve() for doc in excluded}
    original_open = Path.open

    def scoped_open(path, *args, **kwargs):
        # Catalogue metadata may be read; resolving an excluded body must fail this test.
        if path.resolve() in forbidden:
            raise AssertionError("excluded body opened before scope selection")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", scoped_open)
    result = search(root, pin, [doc["id"] for doc in approved], backend)
    assert result["status"] == "matches"
    assert {hit["document_id"] for hit in result["hits"]} == {"approved-a", "approved-b"}
    assert_no_excluded_data(result, excluded)


@pytest.mark.parametrize("problem", ["stale", "nonpublic", "better-match"])
def test_excluded_entries_do_not_poison_or_change_scoped_scores(vault, backend, problem):
    root, approved = vault
    allowed_ids = [doc["id"] for doc in approved]
    before = search(root, catalogue(root, approved), allowed_ids, backend)
    assert {hit["document_id"] for hit in before["hits"]} == set(allowed_ids)
    assert all(hit["score"] > 0 for hit in before["hits"])
    excluded = excluded_note(root, problem)
    pin = catalogue(root, approved + [excluded])
    if problem == "better-match":
        wider = search(root, pin, allowed_ids + [excluded["id"]], backend)
        assert wider["hits"][0]["document_id"] == excluded["id"]
        assert wider["hits"][0]["score"] > max(
            hit["score"] for hit in wider["hits"] if hit["document_id"] in allowed_ids
        )
    after = search(root, pin, allowed_ids, backend)
    # The changed manifest pin is expected; returned scores, order and source bytes are not.
    assert after["manifest_sha256"] == pin
    assert after["hits"] == before["hits"]
    assert after["status"] == before["status"]
    assert after["omitted"] == before["omitted"] == []
    assert_no_excluded_data(after, [excluded])


def test_exact_excluded_identity_cannot_escape_explicit_ids(vault, backend):
    root, approved = vault
    excluded = excluded_note(root, "better-match")
    pin = catalogue(root, approved + [excluded])
    positive = search(root, pin, [approved[0]["id"]], backend, query=approved[0]["id"])
    assert [hit["document_id"] for hit in positive["hits"]] == [approved[0]["id"]]
    denied = search(root, pin, [approved[0]["id"]], backend, query=excluded["id"])
    assert denied["status"] == "no_match"
    assert denied["hits"] == denied["omitted"] == []
    assert_no_excluded_data(denied, [excluded])


@pytest.mark.parametrize("operation,backend", [
    ("read", None), ("search", "lexical"), ("search", "fts5"),
])
@pytest.mark.parametrize("problem,reason", [
    ("stale", "source digest mismatch"), ("nonpublic", "non-public rights"),
])
def test_in_scope_invalid_document_refuses_instead_of_looking_absent(
        vault, operation, backend, problem, reason):
    root, approved = vault
    selected = approved[0]
    pin = catalogue(root, approved)

    def invoke(current_pin):
        if operation == "read":
            return read_document(root, current_pin, selected["id"])
        return search(root, current_pin, [selected["id"]], backend)

    positive = invoke(pin)
    if operation == "read":
        assert positive["content"].encode("utf-8") == (root / selected["path"]).read_bytes()
        assert positive["document_id"] == selected["id"]
    else:
        assert [hit["document_id"] for hit in positive["hits"]] == [selected["id"]]
    if problem == "stale":
        with (root / selected["path"]).open("ab") as handle:
            handle.write(b"UNAPPROVED_REVISION_CANARY\n")
    else:
        selected["rights"]["redistribution"] = "private"
        pin = catalogue(root, approved)
    with pytest.raises(ValueError, match=reason) as error:
        invoke(pin)
    assert "UNAPPROVED_REVISION_CANARY" not in str(error.value)


@pytest.mark.parametrize("allowed_ids", [("approved-a",), ("approved-a", "approved-b")])
def test_fresh_vault_search_cli_respects_same_explicit_ids(vault, tmp_path, backend, allowed_ids):
    root, approved = vault
    baseline = search(root, catalogue(root, approved), allowed_ids, backend)
    assert {hit["document_id"] for hit in baseline["hits"]} == set(allowed_ids)
    excluded = [excluded_note(root, problem) for problem in ("stale", "nonpublic", "better-match")]
    pin = catalogue(root, approved + excluded)
    consumer = tmp_path / "fresh-consumer"
    home = tmp_path / "home"
    consumer.mkdir()
    home.mkdir()
    command = [
        sys.executable, str(ROOT / "bin/harness"), "vault-search",
        "--vault-root", str(root), "--vault-id", VAULT_ID,
        "--manifest", "manifest.json", "--manifest-sha256", pin,
        "--query", QUERY, "--backend", backend,
    ]
    for identity in allowed_ids:
        command.extend(["--allow-id", identity])
    result = subprocess.run(
        command, cwd=consumer, env={
            "PATH": os.defpath, "HOME": str(home), "HARNESS_HOME": str(home / "harness"),
            "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1",
        }, capture_output=True, text=True, encoding="utf-8", timeout=15, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not result.stderr, result.stderr
    packet = json.loads(result.stdout)
    assert packet["backend"] == backend
    assert packet["manifest_sha256"] == pin
    assert packet["hits"] == baseline["hits"]
    assert packet["omitted"] == []
    assert {hit["document_id"] for hit in packet["hits"]} == set(allowed_ids)
    assert_no_excluded_data(packet, excluded)
