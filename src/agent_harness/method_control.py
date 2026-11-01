"""Advisory method choice from current project state and observed run evidence.

This does not execute tools, grant authority, write a plan or grade an artifact.
The same independent gate decides done regardless of the recommended method.
"""
import hashlib
from pathlib import Path
import re

from .launch import MAX_RECEIPT, _json, prepare
from .vault_sources import _read, _source_path


def decide(root, request_path, *, receipt_path=None, artifact_path=None,
           gate_receipt_path=None, dependencies=0, uncertainty="none"):
    if type(dependencies) is not int or not 0 <= dependencies <= 32:
        raise ValueError("dependency count must be a bounded integer")
    if uncertainty not in ("none", "consequential"):
        raise ValueError("unknown uncertainty class")
    root = Path(root).resolve(strict=True)
    current = prepare(root, request_path)
    prior = None
    prior_sha = None
    if receipt_path is not None:
        raw = _read(_source_path(root, receipt_path), MAX_RECEIPT)
        prior = _json(raw)
        if (not isinstance(prior, dict) or prior.get("schema") != current["schema"]
                or prior.get("request_sha256") != current["request_sha256"]
                or prior.get("context_sha256") != current["context_sha256"]
                or prior.get("memory_receipts") != current["memory_receipts"]):
            raise ValueError("prior receipt is stale or belongs to another task")
        if prior.get("native_completion") not in ("TIMEOUT", "OUTPUT_LIMIT", "FAILED",
                                                   "COMPLETED_UNGRADED"):
            raise ValueError("prior native completion status is unsupported")
        prior_sha = hashlib.sha256(raw).hexdigest()
    artifact_sha = None
    if artifact_path is not None:
        path = _source_path(root, artifact_path)
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError("artifact boundary is not a regular file")
        if path.is_file():
            artifact_sha = hashlib.sha256(_read(path, 1024 * 1024)).hexdigest()
    gate_sha, gate_status, gate_check_id, failure_codes = None, None, None, []
    if gate_receipt_path is not None:
        if artifact_sha is None:
            raise ValueError("gate receipt requires an existing artifact")
        raw = _read(_source_path(root, gate_receipt_path), 8192)
        gate = _json(raw)
        base = {"schema", "artifact_sha256", "status", "check_id"}
        if (not isinstance(gate, dict) or not base <= set(gate)
                or not set(gate) <= base | {"failure_codes"}
                or gate["schema"] != "harness.gate-result/v1"
                or gate["artifact_sha256"] != artifact_sha
                or gate["status"] not in ("PASS", "FAIL")
                or not isinstance(gate["check_id"], str) or not gate["check_id"].strip()
                or len(gate["check_id"]) > 128):
            raise ValueError("gate receipt is invalid or belongs to another artifact")
        failure_codes = gate.get("failure_codes", [])
        if (not isinstance(failure_codes, list) or len(failure_codes) > 8
                or any(not isinstance(code, str) or not re.fullmatch(r"[a-z0-9._-]{1,64}", code)
                       for code in failure_codes)
                or len(failure_codes) != len(set(failure_codes))):
            raise ValueError("gate receipt has invalid failure categories")
        gate_sha = hashlib.sha256(raw).hexdigest()
        gate_status = gate["status"]
        gate_check_id = gate["check_id"]
    status = prior["native_completion"] if prior else None
    if uncertainty == "consequential":
        action, reason, check = "CLARIFY", "consequential_uncertainty", "resolve the consequential question"
    elif gate_status == "FAIL":
        action, reason, check = "REVISE_ARTIFACT", "independent_gate_failed", "rerun the same independent artifact gate"
    elif gate_status == "PASS":
        action, reason, check = "REPORT_GATE_RECEIPT", "independent_gate_passed", "verify gate provenance before completion"
    elif artifact_sha is not None:
        action, reason, check = "VERIFY_ARTIFACT", "artifact_present", "run the independent artifact gate"
    elif status in ("TIMEOUT", "OUTPUT_LIMIT"):
        action, reason, check = "CHANGE_METHOD", "bounded_run_without_artifact", "choose a different bounded approach"
    elif status == "FAILED":
        action, reason, check = "DIAGNOSE", "native_failure", "identify the failed layer before retrying"
    elif dependencies > 1:
        action, reason, check = "PLAN", "multiple_dependencies", "gate each dependent work node"
    else:
        action, reason, check = "DIRECT", "single_ready_outcome", "run the task-specific independent gate"
    critical_checks = {
        "DIRECT": [],
        "PLAN": ["constraints", "alternative", "dependency_check"],
        "CLARIFY": ["assumption", "current_source", "counterexample", "uncertainty"],
        "REVISE_ARTIFACT": ["current_source", "counterexample", "uncertainty"],
        "REPORT_GATE_RECEIPT": ["current_source"],
        "VERIFY_ARTIFACT": ["current_source", "counterexample"],
        "CHANGE_METHOD": ["failed_assumption", "alternative"],
        "DIAGNOSE": ["failure_layer", "counterexample"],
    }[action]
    return {"schema": "harness.method-decision/v1", "action": action, "reason_code": reason,
            "next_check": check, "gate_unchanged": True, "authority_unchanged": True,
            "critical_checks": critical_checks,
            "evidence": {"request_sha256": current["request_sha256"],
                         "context_sha256": current["context_sha256"],
                         "prior_receipt_sha256": prior_sha, "native_completion": status,
                         "artifact_sha256": artifact_sha,
                         "gate_receipt_sha256": gate_sha, "gate_status": gate_status,
                         "gate_check_id": gate_check_id,
                         "failure_codes": failure_codes},
            "scope": "advisory_method_only"}
