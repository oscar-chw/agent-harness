"""Fresh source CLI expectations; optional evidence never promotes derived advice."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize


pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[1]
DERIVED = "Checks passed, so deployment is ready."
SOURCE_LINES = [
    b"# Deployment ticket\n",
    b"Ticket Q47 requires passing automated checks.\n",
    b"Deployment also requires the ticket owner's explicit approval.\r\n",
    b"Approval is ticket-scoped; a green check grants no permission.\n",
    b"UNCITED_APPENDIX_CANARY belongs to an unrelated topic.\n",
]
EVIDENCE = b"".join(SOURCE_LINES[1:4])


@pytest.fixture
def lab(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    project_id = initialize(root)
    path = root / "ticket.md"
    path.write_bytes(b"".join(SOURCE_LINES))
    source = SourceVault(root, project_id).capture("ticket.md")
    item = {
        "id": "ticket-deployment-review", "project_id": project_id,
        "layer": "project_facts", "kind": "fact", "scope": "task",
        "text": DERIVED, "provenance": [{
            "source": source, "start_line": 2, "end_line": 4,
        }],
        "confidence": "verified", "sensitivity": "internal",
        "access_boundary": "local_user", "owner": "fixture-owner", "freshness": "current",
    }
    store = ProjectMemory(root, project_id)
    receipt = store.append(item, expected=None)
    baseline = store.read_scoped(
        receipt, allowed_sensitivities=["internal"], allowed_scopes=["task"],
        layers=["project_facts"],
    )
    assert baseline["item"]["confidence"] == "pending"
    consumer = tmp_path / "fresh-consumer"
    home = tmp_path / "home"
    consumer.mkdir()
    home.mkdir()
    return {
        "root": root, "project_id": project_id, "source": source,
        "item": item, "store": store, "receipt": receipt,
        "consumer": consumer, "home": home,
    }


def cli(lab, *extra, receipt=None, sensitivity="internal", scope="task", layer="project_facts"):
    return subprocess.run([
        sys.executable, str(ROOT / "bin/harness"), "memory-read",
        "--project-root", str(lab["root"]), "--project-id", lab["project_id"],
        "--receipt", json.dumps(lab["receipt"] if receipt is None else receipt),
        "--allow-sensitivity", sensitivity, "--allow-scope", scope, "--layer", layer,
        *extra,
    ], cwd=lab["consumer"], env={
        "PATH": os.defpath, "HOME": str(lab["home"]),
        "HARNESS_HOME": str(lab["home"] / "harness"),
        "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1",
    }, capture_output=True, timeout=15, check=False)


def packet(result):
    assert result.returncode == 0, result.stderr.decode("utf-8")
    assert result.stderr == b""
    return json.loads(result.stdout)


def assert_source_span(value, source, expected=EVIDENCE, historical=False):
    assert value["source_spans"] == [{
        "kind": "source-data", "text": expected.decode("utf-8"), "historical": historical,
        "citation": {**source, "start_line": 2, "end_line": 4},
    }]
    assert "UNCITED_APPENDIX_CANARY" not in json.dumps(value)


def assert_pending(value):
    assert value["kind"] == "pending-memory-data"
    assert value["item"]["confidence"] == "pending"
    assert value["usable_for_current_decisions"] is False


def test_sources_recovers_stored_owner_approval_without_verifying_derived_note(lab):
    default_before = cli(lab)
    ordinary = packet(default_before)
    assert_pending(ordinary)
    assert ordinary["item"]["text"] == DERIVED
    assert "ticket owner's explicit approval" not in json.dumps(ordinary)
    assert "source_spans" not in ordinary
    assert set(ordinary) == {
        "schema", "kind", "project_id", "historical", "item", "receipt",
        "usable_for_current_decisions",
    }

    reviewed = packet(cli(lab, "--sources"))
    assert_source_span(reviewed, lab["source"])
    assert_pending(reviewed)
    assert reviewed["item"] == ordinary["item"]
    assert reviewed["receipt"] == ordinary["receipt"] == lab["receipt"]
    assert reviewed["historical"] is False
    assert {key: value for key, value in reviewed.items() if key != "source_spans"} == ordinary

    default_after = cli(lab)
    packet(default_after)
    assert default_after.stdout == default_before.stdout


def test_current_source_edit_refuses_and_explicit_history_returns_saved_bytes(lab):
    current = packet(cli(lab, "--sources"))
    assert_source_span(current, lab["source"])
    (lab["root"] / "ticket.md").write_text("Replacement has no ticket approval terms.\n")

    refused = cli(lab, "--sources")
    assert refused.returncode != 0
    assert refused.stdout == b""
    assert b"stale source" in refused.stderr

    historical = packet(cli(lab, "--sources", "--historical"))
    assert historical["historical"] is True
    assert_source_span(historical, lab["source"], historical=True)
    assert_pending(historical)
    assert historical["item"]["text"] == DERIVED


def test_superseded_receipt_needs_history_and_keeps_its_actual_original(lab):
    old_receipt = lab["receipt"]
    newer_lines = SOURCE_LINES.copy()
    newer_lines[2] = b"Ticket Q47 now also requires security-owner signoff.\n"
    (lab["root"] / "ticket.md").write_bytes(b"".join(newer_lines))
    new_source = SourceVault(lab["root"], lab["project_id"]).capture("ticket.md")
    item = copy.deepcopy(lab["item"])
    item["text"] = "The updated checklist is ready."
    item["provenance"][0]["source"] = new_source
    new_receipt = lab["store"].append(item, expected=old_receipt)

    refused = cli(lab, "--sources", receipt=old_receipt)
    assert refused.returncode != 0
    assert refused.stdout == b""
    assert b"superseded" in refused.stderr
    old = packet(cli(lab, "--sources", "--historical", receipt=old_receipt))
    assert old["current_status"] == "superseded"
    assert_pending(old)
    assert_source_span(old, lab["source"], historical=True)
    current = packet(cli(lab, "--sources", receipt=new_receipt))
    assert_source_span(current, new_source, expected=b"".join(newer_lines[1:4]))
    assert current["receipt"] == new_receipt
    assert_pending(current)


def test_withdrawn_record_history_is_data_and_not_current_advice(lab):
    item = copy.deepcopy(lab["item"])
    item["freshness"] = "withdrawn"
    receipt = lab["store"].append(item, expected=lab["receipt"])
    refused = cli(lab, "--sources", receipt=receipt)
    assert refused.returncode != 0
    assert refused.stdout == b""
    assert b"withdrawn" in refused.stderr
    historical = packet(cli(lab, "--sources", "--historical", receipt=receipt))
    assert historical["current_status"] == "withdrawn"
    assert historical["item"]["freshness"] == "withdrawn"
    assert_pending(historical)
    assert_source_span(historical, lab["source"], historical=True)


@pytest.mark.parametrize("denied", [
    {"sensitivity": "public"}, {"scope": "another-task"}, {"layer": "knowledge"},
])
@pytest.mark.parametrize("historical", [False, True])
def test_explicit_scope_refuses_before_missing_source_is_resolved(lab, denied, historical):
    assert_source_span(packet(cli(lab, "--sources")), lab["source"])
    (lab["root"] / "ticket.md").unlink()
    snapshot = lab["root"] / ".harness/sources" / (lab["source"]["source_id"] + ".json")
    snapshot.unlink()
    flags = ("--sources", "--historical") if historical else ("--sources",)
    refused = cli(lab, *flags, **denied)
    assert refused.returncode != 0
    assert refused.stdout == b""
    assert b"declared scope" in refused.stderr
    assert b"No such file" not in refused.stderr
    assert EVIDENCE not in refused.stderr


def test_budget_includes_source_packets_and_never_truncates_them(lab):
    default = cli(lab)
    packet(default)
    full = cli(lab, "--sources")
    assert_source_span(packet(full), lab["source"])
    budget = len(default.stdout)
    assert len(full.stdout) > budget
    fits = cli(lab, "--max-bytes", str(budget))
    packet(fits)
    assert len(fits.stdout) <= budget
    refused = cli(lab, "--sources", "--max-bytes", str(budget))
    assert refused.returncode != 0
    assert refused.stdout == b""
    assert b"budget" in refused.stderr


@pytest.mark.parametrize("phase", ["resume", "compact"])
def test_sources_cannot_bypass_pending_recovery_hold(lab, phase):
    assert_source_span(packet(cli(lab, "--sources")), lab["source"])
    flags = ("--recover", phase, "--verified-receipt", json.dumps(lab["receipt"]))
    ordinary = packet(cli(lab, *flags))
    assert ordinary["decision"] == "HOLD"
    assert ordinary["reason"] == "pending"
    assert "source_spans" not in ordinary
    refused = cli(lab, "--sources", *flags)
    assert refused.returncode != 0
    assert refused.stdout == b""
    assert b"sources" in refused.stderr and b"recover" in refused.stderr


def test_default_and_explicit_source_cli_reads_do_not_publish_or_rewrite_files(lab):
    def snapshot():
        return {
            (name, str(path.relative_to(lab[name]))): path.read_bytes()
            for name in ("root", "home", "consumer")
            for path in lab[name].rglob("*") if path.is_file()
        }

    before = snapshot()
    packet(cli(lab))
    assert_source_span(packet(cli(lab, "--sources")), lab["source"])
    packet(cli(lab))
    assert snapshot() == before
