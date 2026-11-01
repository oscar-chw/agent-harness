"""An observable method switch derived from receipts and project artifacts."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent_harness.launch import prepare
from agent_harness.method_control import decide
from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize


@pytest.fixture
def project(tmp_path):
    pid = initialize(tmp_path)
    (tmp_path / "policy.md").write_text("Verify the artifact from a current source.\n")
    ref = SourceVault(tmp_path, pid).capture("policy.md")
    item = {"id": "policy", "project_id": pid, "layer": "project_facts", "kind": "fact",
            "scope": "task", "text": "Verify the artifact from a current source.",
            "provenance": [{"source": ref, "start_line": 1, "end_line": 1}],
            "confidence": "verified", "sensitivity": "internal", "access_boundary": "local_user",
            "owner": "fixture", "freshness": "current"}
    receipt = ProjectMemory(tmp_path, pid).append(item, expected=None)
    request = {"schema": "harness.launch/v1", "project_id": pid, "task": "Create a reviewed document.",
               "references": [receipt], "scope": {"allowed_sensitivities": ["internal"],
               "allowed_scopes": ["task"], "layers": ["project_facts"]}, "max_context_bytes": 8192}
    (tmp_path / "request.json").write_text(json.dumps(request))
    return tmp_path


def prior(root, status="TIMEOUT"):
    data = prepare(root, "request.json")
    data.update(native_completion=status, thread_id="01a16828-6ebc-7e82-9fd6-99f867c645fc")
    (root / "prior.json").write_text(json.dumps(data))


def test_direct_simple_work_and_plan_only_for_real_dependencies(project):
    root = project
    direct = decide(root, "request.json", dependencies=0)
    assert direct["action"] == "DIRECT"
    assert direct["gate_unchanged"] is True and direct["authority_unchanged"] is True
    assert decide(root, "request.json", dependencies=3)["action"] == "PLAN"
    assert decide(root, "request.json", uncertainty="consequential")["action"] == "CLARIFY"


def test_critical_checks_are_selected_only_when_evidence_or_stakes_require_them(project):
    root = project
    direct = decide(root, "request.json")
    assert direct["critical_checks"] == []
    assert decide(root, "request.json", dependencies=3)["critical_checks"] == [
        "constraints", "alternative", "dependency_check"]
    clarify = decide(root, "request.json", uncertainty="consequential")
    assert clarify["critical_checks"] == [
        "assumption", "current_source", "counterexample", "uncertainty"]
    assert clarify["authority_unchanged"] is True


def test_failed_gate_requires_source_and_counterexample_but_cannot_replace_gate(project):
    from hashlib import sha256
    root = project
    (root / "out.md").write_text("Unsupported claim")
    gate = {"schema": "harness.gate-result/v1",
            "artifact_sha256": sha256((root / "out.md").read_bytes()).hexdigest(),
            "status": "FAIL", "check_id": "source-review",
            "failure_codes": ["missing-source-claim"]}
    (root / "gate.json").write_text(json.dumps(gate))
    decision = decide(root, "request.json", artifact_path="out.md", gate_receipt_path="gate.json")
    assert decision["critical_checks"] == ["current_source", "counterexample", "uncertainty"]
    assert decision["next_check"] == "rerun the same independent artifact gate"
    assert decision["gate_unchanged"] is True


def test_timeout_feedback_switches_based_on_actual_artifact(project):
    root = project
    prior(root)
    no_artifact = decide(root, "request.json", receipt_path="prior.json", artifact_path="out.md")
    assert no_artifact["action"] == "CHANGE_METHOD"
    assert no_artifact["evidence"]["native_completion"] == "TIMEOUT"
    (root / "out.md").write_text("An unfinished but concrete draft")
    with_artifact = decide(root, "request.json", receipt_path="prior.json", artifact_path="out.md")
    assert with_artifact["action"] == "VERIFY_ARTIFACT"
    assert with_artifact["evidence"]["artifact_sha256"] is not None
    assert with_artifact["next_check"] == "run the independent artifact gate"


def test_failure_and_stale_dependency_never_become_authority(project):
    root = project
    prior(root, "FAILED")
    result = decide(root, "request.json", receipt_path="prior.json")
    assert result["action"] == "DIAGNOSE" and result["gate_unchanged"] is True
    (root / "request.json").write_text((root / "request.json").read_text().replace("reviewed", "published"))
    with pytest.raises(ValueError, match="stale"):
        decide(root, "request.json", receipt_path="prior.json")


def test_method_feedback_accepts_a_large_valid_launcher_receipt(project):
    root = project
    prior(root)
    receipt = json.loads((root / "prior.json").read_text())
    receipt["runtime_events"] = {"items": [{"event_type": "item.completed", "route": "other_shell",
                                           "elapsed_seconds": 1.0, "padding": "x" * 250}
                                          for _ in range(257)]}
    (root / "prior.json").write_text(json.dumps(receipt))
    assert (root / "prior.json").stat().st_size > 32768
    assert decide(root, "request.json", receipt_path="prior.json")["action"] == "CHANGE_METHOD"


def test_cli_exposes_a_read_only_feedback_decision(project):
    root = project
    prior(root)
    (root / "out.md").write_text("Draft from the interrupted task")
    before = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
    cli = Path(__file__).resolve().parents[1] / "bin/harness"
    result = subprocess.run([sys.executable, str(cli), "method", "--project-root", str(root),
                             "--request", "request.json", "--receipt", "prior.json",
                             "--artifact", "out.md"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["action"] == "VERIFY_ARTIFACT"
    assert before == {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}


def test_independent_gate_feedback_revises_method_without_redefining_gate(project):
    from hashlib import sha256
    root = project
    prior(root)
    (root / "out.md").write_text("Draft with a missing citation")
    artifact_sha = sha256((root / "out.md").read_bytes()).hexdigest()
    gate = {"schema": "harness.gate-result/v1", "artifact_sha256": artifact_sha,
            "status": "FAIL", "check_id": "source-review",
            "failure_codes": ["missing-source-claim"]}
    (root / "gate.json").write_text(json.dumps(gate))
    result = decide(root, "request.json", receipt_path="prior.json", artifact_path="out.md",
                    gate_receipt_path="gate.json")
    assert result["action"] == "REVISE_ARTIFACT"
    assert result["evidence"]["gate_status"] == "FAIL"
    assert result["evidence"]["failure_codes"] == ["missing-source-claim"]
    assert result["next_check"] == "rerun the same independent artifact gate"
    (root / "out.md").write_text("Revised draft, now different")
    with pytest.raises(ValueError, match="gate receipt"):
        decide(root, "request.json", receipt_path="prior.json", artifact_path="out.md",
               gate_receipt_path="gate.json")


def test_gate_receipt_cannot_pass_an_absent_artifact(project):
    from hashlib import sha256
    root = project
    gate = {"schema": "harness.gate-result/v1", "artifact_sha256": None,
            "status": "PASS", "check_id": "missing-artifact"}
    (root / "gate.json").write_text(json.dumps(gate))
    with pytest.raises(ValueError, match="existing artifact"):
        decide(root, "request.json", artifact_path="out.md", gate_receipt_path="gate.json")
    (root / "out.md").write_text("Checked artifact")
    gate["artifact_sha256"] = sha256((root / "out.md").read_bytes()).hexdigest()
    (root / "gate.json").write_text(json.dumps(gate))
    result = decide(root, "request.json", artifact_path="out.md", gate_receipt_path="gate.json")
    assert result["action"] == "REPORT_GATE_RECEIPT"
