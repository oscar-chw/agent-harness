import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from examples.sandbox_parts.memory_flow import run


def test_run_executes_sourced_memory_correction_and_withdrawal(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    marker = "PRIVATE-REVIEW-MARKER"
    original = f"Build cutoff: 10:00 UTC. {marker}"
    (project / "decision.md").write_text(original, encoding="utf-8")

    receipt = run(project)

    assert receipt["section"] == "memory"
    assert receipt["status"] == "PASS"
    assert receipt["checks"][0]["evidence"]["source_origin"] == "provided"
    encoded_receipt = json.dumps(receipt)
    assert marker not in encoded_receipt
    assert receipt["checks"][1]["evidence"]["source_match"] is True
    assert receipt["checks"][2]["evidence"]["current_matches_correction"] is True
    assert receipt["checks"][3]["evidence"]["corrected_context_present"] is True
    assert (project / "decision.md").read_text(encoding="utf-8") == original
    assert [check["name"] for check in receipt["checks"]] == [
        "source_capture", "memory_append_and_read", "correction_invalidates_old_receipt",
        "fresh_process_launch_prepare", "withdrawal_invalidates_current_use",
        "negative_control_stale_receipt",
    ]
    assert all(check["status"] == "PASS" for check in receipt["checks"])
    assert receipt["checks"][-1]["evidence"]["rejected"] is True
    assert receipt["checks"][-1]["evidence"]["refusal_type"] == "ValueError"
    json.dumps(receipt)


def test_wrong_memory_read_cannot_report_pass(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    (project / "decision.md").write_text("Build cutoff: 10:00 UTC.\n", encoding="utf-8")
    from agent_harness.project_memory import ProjectMemory

    original_read = ProjectMemory.read

    def wrong_read(self, receipt, **kwargs):
        result = original_read(self, receipt, **kwargs)
        result["item"]["text"] = "wrong memory text"
        return result

    monkeypatch.setattr(ProjectMemory, "read", wrong_read)
    receipt = run(project)

    assert receipt["status"] == "FAIL"
    assert receipt["checks"][1]["status"] == "FAIL"
    assert receipt["checks"][1]["evidence"]["source_match"] is False
    assert receipt["checks"][2]["status"] == "FAIL"
    assert receipt["checks"][2]["evidence"]["current_matches_correction"] is False
    assert "wrong memory text" not in json.dumps(receipt)
