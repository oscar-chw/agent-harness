"""Bounded CPU-only source and project-memory workflow for a temporary project."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize


def run(root: Path) -> dict:
    """Capture, store, correct, and withdraw one sourced project fact."""
    root = Path(root).resolve(strict=True)
    project_id = initialize(root)
    vault = SourceVault(root, project_id)
    memory = ProjectMemory(root, project_id)
    checks = []

    source_path = root / "decision.md"
    source_origin = "provided" if source_path.exists() else "synthetic"
    if source_origin == "synthetic":
        source_path.write_text("Synthetic demo decision: build cutoff is 10:00 UTC.\n", encoding="utf-8")

    source_ref = vault.capture("decision.md")
    resolved = vault.resolve(source_ref, start_line=1, end_line=1)
    text = resolved["text"]
    checks.append({"name": "source_capture", "status": "PASS",
                   "evidence": {"source": source_ref["source"], "source_origin": source_origin,
                                "source_id": source_ref["source_id"], "source_sha256": source_ref["sha256"],
                                "citation": resolved["citation"]}})

    item = {"id": "build-cutoff", "project_id": project_id, "layer": "project_facts",
            "kind": "fact", "scope": "project", "text": text,
            "provenance": [{"source": source_ref, "start_line": 1, "end_line": 1}],
            "confidence": "verified", "sensitivity": "private", "access_boundary": "local_user",
            "owner": "sandbox-memory-flow", "freshness": "current"}
    first = memory.append(item, expected=None)
    read = memory.read(first, allowed_sensitivities=["private"])
    source_match = read["item"]["text"] == text
    checks.append({"name": "memory_append_and_read", "status": "PASS" if source_match else "FAIL",
                   "evidence": {"receipt": first, "source_match": source_match,
                                "text_sha256": hashlib.sha256(read["item"]["text"].encode()).hexdigest()}})

    corrected_path = root / "corrected-decision.md"
    corrected_path.write_text("Build cutoff: 12:00 UTC.\n", encoding="utf-8")
    revised_source = vault.capture("corrected-decision.md")
    revised = {**item, "text": "Build cutoff: 12:00 UTC.\n",
               "provenance": [{"source": revised_source, "start_line": 1, "end_line": 1}]}
    second = memory.append(revised, expected=first)
    try:
        memory.read(first, allowed_sensitivities=["private"])
    except ValueError as error:
        stale_error = str(error)
    else:
        raise AssertionError("superseded receipt remained readable as current")
    current = memory.read(second, allowed_sensitivities=["private"])
    corrected_text = "Build cutoff: 12:00 UTC.\n"
    old_receipt_refused = bool(stale_error)
    current_matches_correction = current["item"]["text"] == corrected_text
    checks.append({"name": "correction_invalidates_old_receipt",
                   "status": "PASS" if old_receipt_refused and current_matches_correction else "FAIL",
                   "evidence": {"old_receipt": first, "current_receipt": second,
                                "old_receipt_refused": old_receipt_refused,
                                "current_matches_correction": current_matches_correction,
                                "current_text_sha256": hashlib.sha256(
                                    current["item"]["text"].encode()).hexdigest(),
                                "source": revised_source["source"], "source_id": revised_source["source_id"],
                                "source_sha256": revised_source["sha256"]}})

    request = {"schema": "harness.launch/v1", "project_id": project_id,
               "task": "Resume using the current build cutoff.", "references": [second],
               "scope": {"allowed_sensitivities": ["private"], "allowed_scopes": ["project"],
                         "layers": ["project_facts"]}, "max_context_bytes": 8192}
    (root / "request.json").write_text(json.dumps(request), encoding="utf-8")
    cli = Path(__file__).resolve().parents[2] / "bin" / "harness"
    process = subprocess.run([sys.executable, str(cli), "launch", "--project-root", str(root),
                              "--request", "request.json"], cwd=root, capture_output=True, text=True,
                             timeout=15, check=False)
    if process.returncode != 0 or process.stderr:
        raise RuntimeError(f"harness launch failed ({process.returncode}): {process.stderr.strip()}")
    packet = json.loads(process.stdout)
    corrected_context_present = (packet.get("memory_receipts") == [second]
                                 and corrected_text.strip() in packet.get("prompt", ""))
    checks.append({"name": "fresh_process_launch_prepare",
                   "status": "PASS" if corrected_context_present else "FAIL",
                   "evidence": {"command": "bin/harness launch --project-root <root> --request request.json",
                                "exit_code": process.returncode, "memory_receipts": packet["memory_receipts"],
                                "context_sha256": packet["context_sha256"],
                                "corrected_context_present": corrected_context_present,
                                "native_completion": packet["native_completion"]}})

    withdrawn = {**revised, "freshness": "withdrawn"}
    final = memory.append(withdrawn, expected=second)
    try:
        memory.read(final, allowed_sensitivities=["private"])
    except ValueError as error:
        withdrawal_error = str(error)
    else:
        raise AssertionError("withdrawn memory remained available for current use")
    withdrawal_refused = bool(withdrawal_error)
    checks.append({"name": "withdrawal_invalidates_current_use",
                   "status": "PASS" if withdrawal_refused else "FAIL",
                   "evidence": {"receipt": final, "withdrawal_refused": withdrawal_refused}})

    # Negative control: the original receipt must still be rejected after withdrawal.
    try:
        memory.read(first, allowed_sensitivities=["private"])
    except ValueError as error:
        negative = {"rejected": True, "refusal_type": type(error).__name__}
    else:
        negative = {"rejected": False}
    checks.append({"name": "negative_control_stale_receipt",
                   "status": "PASS" if negative["rejected"] else "FAIL", "evidence": negative})
    return {"section": "memory", "status": "PASS" if all(
        check["status"] == "PASS" for check in checks) else "FAIL", "checks": checks}
