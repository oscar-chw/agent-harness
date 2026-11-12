"""Replay helper projections, not native/model/domain-quality evaluation.

Run from the repository root with PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src.
Fixtures live temporarily inside this owned documentation directory. No models,
shell commands from the pack, installed state or native configuration are used.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import tempfile

from agent_harness.launch import prepare
from agent_harness.method_control import decide
from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DOMAINS = {"coding", "research", "debugging", "daily", "learning"}
DECISIONS = {"direct", "investigate", "plan", "implement", "diagnose", "replan"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(pack):
    require(pack.get("schema") == "harness.methodology-cases/v1", "unknown pack schema")
    require(pack.get("split") == "development", "visible cases cannot be held-out")
    require(pack.get("origin") == "authored_synthetic", "missing synthetic origin")
    cases = pack["cases"]
    require(isinstance(cases, list) and cases, "empty case pack")
    require({c["domain"] for c in cases} == DOMAINS, "missing or unknown domain")
    require(len({c["id"] for c in cases}) == len(cases), "duplicate case identity")
    require({c["expected"]["decision"] for c in cases} == DECISIONS,
            "missing or unknown next decision")
    for case in cases:
        identity = case["id"]
        require(isinstance(identity, str) and identity.strip(), "empty case identity")
        require(case["probe_kind"] in {"method", "contract_only"}, f"{identity}: probe kind")
        require(bool(case["input"]["task"].strip()), f"{identity}: missing task")
        expected, counter = case["expected"], case["counterexample"]
        require(bool(case["failure"].strip()) and bool(expected["observations"]),
                f"{identity}: missing failure or observations")
        require(counter["decision"] in DECISIONS and bool(counter["change"].strip())
                and bool(counter["reason"].strip()), f"{identity}: missing counterexample")
        if case["probe_kind"] == "method":
            require(("runtime_action" in expected) != ("error_contains" in expected),
                    f"{identity}: exactly one runtime verdict required")
        else:
            require("runtime_action" not in expected, f"{identity}: unsupported runtime claim")
        for reference in case["existing_checks"]:
            name, function = reference.split("::")
            require(name.startswith("tests/") and ".." not in Path(name).parts,
                    f"{identity}: reference leaves tests")
            tree = ast.parse((ROOT / name).read_text())
            require(any(isinstance(n, ast.FunctionDef) and n.name == function
                        for n in ast.walk(tree)), f"{identity}: missing existing check {reference}")
    return cases


def fixture(root, task):
    pid = initialize(root)
    policy = "Check the artifact against the current task.\n"
    (root / "policy.md").write_text(policy)
    source = SourceVault(root, pid).capture("policy.md")
    item = {"id": "policy", "project_id": pid, "layer": "project_facts", "kind": "fact",
            "scope": "task", "text": policy.strip(),
            "provenance": [{"source": source, "start_line": 1, "end_line": 1}],
            "confidence": "verified", "sensitivity": "internal", "access_boundary": "local_user",
            "owner": "synthetic-methodology-fixture", "freshness": "current"}
    receipt = ProjectMemory(root, pid).append(item, expected=None)
    request = {"schema": "harness.launch/v1", "project_id": pid, "task": task,
               "references": [receipt], "scope": {"allowed_sensitivities": ["internal"],
               "allowed_scopes": ["task"], "layers": ["project_facts"]},
               "max_context_bytes": 8192}
    (root / "request.json").write_text(json.dumps(request))
    return request


def replay(case, root):
    inputs, expected = case["input"], case["expected"]
    request = fixture(root, inputs["task"])
    kwargs = {"dependencies": inputs["dependencies"], "uncertainty": inputs["uncertainty"]}
    if "prior_status" in inputs:
        prior = prepare(root, "request.json")
        prior["native_completion"] = inputs["prior_status"]
        (root / "prior.json").write_text(json.dumps(prior))
        kwargs["receipt_path"] = "prior.json"
    if "mutate_request_after_receipt" in inputs:
        request["task"] = inputs["mutate_request_after_receipt"]
        (root / "request.json").write_text(json.dumps(request))
    if "artifact" in inputs:
        (root / "artifact.txt").write_text(inputs["artifact"])
        kwargs["artifact_path"] = "artifact.txt"
    if "gate" in inputs:
        gate = {"schema": "harness.gate-result/v1", **inputs["gate"],
                "artifact_sha256": hashlib.sha256((root / "artifact.txt").read_bytes()).hexdigest()}
        (root / "gate.json").write_text(json.dumps(gate))
        kwargs["gate_receipt_path"] = "gate.json"
    try:
        result = decide(root, "request.json", **kwargs)
    except ValueError as error:
        require("error_contains" in expected and expected["error_contains"] in str(error),
                f"{case['id']}: unexpected rejection: {error}")
        return
    require("error_contains" not in expected, f"{case['id']}: stale evidence accepted")
    require(result["action"] == expected["runtime_action"],
            f"{case['id']}: got {result['action']}, expected {expected['runtime_action']}")
    checks = result["diagnosis"]["checks"] if result["diagnosis"] else None
    require(checks == expected["diagnosis_checks"], f"{case['id']}: diagnosis differs")
    require(result["gate_unchanged"] is True and result["authority_unchanged"] is True,
            f"{case['id']}: advisory boundary changed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", nargs="?", type=Path, default=HERE / "cases.json")
    args = parser.parse_args()
    raw = args.pack.read_bytes()
    cases = validate(json.loads(raw))
    count = 0
    for case in cases:
        if case["probe_kind"] == "method":
            with tempfile.TemporaryDirectory(prefix=".methodology-replay-", dir=HERE) as temp:
                replay(case, Path(temp))
            count += 1
    print(json.dumps({"status": "PASS", "claim_class": "structural_and_helper_behavior_only",
                      "pack_sha256": hashlib.sha256(raw).hexdigest(),
                      "cases": len(cases), "helper_probes": count,
                      "contract_only_not_behaviorally_graded": len(cases) - count,
                      "not_proven": ["native_method_selection", "domain_quality", "transfer",
                                     "token_gain", "promotion"]}, sort_keys=True))


if __name__ == "__main__":
    main()
