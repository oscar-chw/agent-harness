"""Run three real, local harness flows without model calls or client changes.

Usage: python3 examples/sandbox_demo.py --output /tmp/harness-demo-receipt.json
An existing output file is never overwritten. Exit 0 requires every section to
pass; it never implies full v1 release qualification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

SECTION_NAMES = ("memory", "coordination", "acceptance")
EXPECTED_CHECKS = {
    "memory": {"source_capture", "memory_append_and_read", "correction_invalidates_old_receipt",
               "fresh_process_launch_prepare", "withdrawal_invalidates_current_use",
               "negative_control_stale_receipt"},
    "coordination": {"single_concurrent_claim", "live_lease_unverified",
                     "expired_lease_reclaimed", "stale_fence_refused",
                     "cold_snapshot_recovers_blocked_checkpoint",
                     "fresh_cli_process_refuses_live_claim", "fresh_cli_snapshot_reads_durable_state"},
    "acceptance": {"generated_artifact_passes_independent_structural_grader",
                   "mutated_artifact_fails_independent_structural_grader"},
}
UNKNOWN_ACCOUNTING = {"direct_input_tokens": "UNKNOWN", "direct_output_tokens": "UNKNOWN",
                      "cached_input_tokens": "UNKNOWN", "whole_cost": "UNKNOWN"}


def overall_status(rows):
    if [row.get("section") for row in rows] != list(SECTION_NAMES):
        return "FAIL"
    for row in rows:
        checks = row.get("checks")
        if row.get("status") != "PASS" or not isinstance(checks, list) or not checks:
            return "FAIL"
        if any(not isinstance(check, dict) or check.get("status") != "PASS"
               or not check.get("name") or not check.get("evidence") for check in checks):
            return "FAIL"
        names = [check["name"] for check in checks]
        if len(names) != len(EXPECTED_CHECKS[row["section"]]) or set(names) != EXPECTED_CHECKS[row["section"]]:
            return "FAIL"
    if rows[-1].get("accounting") != UNKNOWN_ACCOUNTING:
        return "FAIL"
    return "PASS"


def _source_hashes():
    names = ["examples/sandbox_demo.py"] + [
        f"examples/sandbox_parts/{section}_flow.py" for section in SECTION_NAMES]
    return {name: hashlib.sha256((REPO / name).read_bytes()).hexdigest() for name in names}


def run():
    from sandbox_parts import acceptance_flow, coordination_flow, memory_flow

    flows = (memory_flow, coordination_flow, acceptance_flow)
    rows = []
    with tempfile.TemporaryDirectory(prefix="harness-sandbox-demo-") as directory:
        base = Path(directory)
        for section, flow in zip(SECTION_NAMES, flows):
            root = base / section
            root.mkdir()
            if section == "memory":
                (root / "decision.md").write_text("Build cutoff: 10:00 UTC.\n", encoding="utf-8")
            elif section == "acceptance":
                (root / "README.md").write_text(
                    "# Sandbox source\nOne local input for an independent semantic check.\n",
                    encoding="utf-8")
            try:
                row = flow.run(root)
                if not isinstance(row, dict) or row.get("section") != section:
                    raise ValueError("section returned the wrong identity")
            except Exception as exc:  # a broken section must become an explicit failure
                row = {"section": section, "status": "FAIL", "checks": [
                    {"name": "section-execution", "status": "FAIL", "evidence": type(exc).__name__}]}
            rows.append(row)
    return {"schema": "harness.sandbox-demo/v1", "status": overall_status(rows),
            "qualification": "NOT_QUALIFIED", "model_calls": 0,
            "source_sha256": _source_hashes(), "sections": rows,
            "accounting": UNKNOWN_ACCOUNTING.copy(),
            "limits": ["local sandbox only", "no native model turn", "no live installation",
                       "no automatic resume of an idle chat", "no full-v1 or cost-superiority claim"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="new JSON receipt file; never overwrites")
    args = parser.parse_args(argv)
    if args.output and os.path.lexists(args.output):
        parser.error("receipt already exists; choose a new output path")
    result = run()
    payload = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(payload)
    sys.stdout.write(payload)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
