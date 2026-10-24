"""The public sandbox entry point must run real local flows and report limits."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def valid_rows(demo):
    rows = [{"section": name, "status": "PASS", "checks": [
        {"name": check, "status": "PASS", "evidence": "independent check"}
        for check in sorted(demo.EXPECTED_CHECKS[name])]}
        for name in demo.SECTION_NAMES]
    rows[-1]["accounting"] = demo.UNKNOWN_ACCOUNTING.copy()
    return rows


def test_demo_entry_is_runnable_and_cannot_claim_v1_qualification(tmp_path):
    receipt = tmp_path / "receipt.json"
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    run = subprocess.run([sys.executable, str(ROOT / "examples/sandbox_demo.py"),
                          "--output", str(receipt)], cwd=ROOT, env=env,
                         capture_output=True, text=True, timeout=90)
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result == json.loads(receipt.read_text())
    assert result["status"] == "PASS"
    assert result["qualification"] == "NOT_QUALIFIED"
    assert {row["section"] for row in result["sections"]} == {
        "memory", "coordination", "acceptance"}
    assert all(row["status"] == "PASS" and row["checks"] for row in result["sections"])
    assert result["accounting"]["whole_cost"] == "UNKNOWN"
    assert result["model_calls"] == 0


def test_demo_refuses_to_call_a_section_pass_when_it_fails(monkeypatch):
    sys.path.insert(0, str(ROOT / "examples"))
    import sandbox_demo

    rows = valid_rows(sandbox_demo)
    rows[1]["status"] = "FAIL"
    rows[1]["checks"][0]["status"] = "FAIL"
    assert sandbox_demo.overall_status(rows) == "FAIL"


def test_demo_rejects_missing_evidence_even_if_section_self_reports_pass():
    sys.path.insert(0, str(ROOT / "examples"))
    import sandbox_demo

    rows = valid_rows(sandbox_demo)
    rows[0]["checks"][0]["evidence"] = ""
    assert sandbox_demo.overall_status(rows) == "FAIL"


def test_existing_receipt_refused_before_running_sections(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / "examples"))
    import sandbox_demo

    receipt = tmp_path / "receipt.json"
    receipt.write_text("precious")
    monkeypatch.setattr(sandbox_demo, "run", lambda: pytest.fail("sections ran before refusal"))
    with pytest.raises(SystemExit) as outcome:
        sandbox_demo.main(["--output", str(receipt)])
    assert outcome.value.code == 2
    assert receipt.read_text() == "precious"


def test_cpu_only_demo_rejects_numeric_usage_without_native_receipt():
    sys.path.insert(0, str(ROOT / "examples"))
    import sandbox_demo

    rows = valid_rows(sandbox_demo)
    rows[-1]["accounting"] = {**sandbox_demo.UNKNOWN_ACCOUNTING, "direct_input_tokens": 1}
    assert sandbox_demo.overall_status(rows) == "FAIL"


def test_aggregate_rejects_fabricated_check_names():
    sys.path.insert(0, str(ROOT / "examples"))
    import sandbox_demo

    rows = [{"section": name, "status": "PASS", "checks": [
        {"name": "invented", "status": "PASS", "evidence": "arbitrary"}]}
        for name in sandbox_demo.SECTION_NAMES]
    rows[-1]["accounting"] = sandbox_demo.UNKNOWN_ACCOUNTING.copy()
    assert sandbox_demo.overall_status(rows) == "FAIL"
