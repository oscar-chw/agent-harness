"""Independent structural qualification-contract cases; no execution/efficacy claims.

Receipt metadata in these fixtures is synthetic. CONTRACT_VALID is deliberately
not proof that any command/model ran or that evidence semantically supports it.
"""
import copy
import hashlib
import subprocess

import pytest

from agent_harness.qualification import validate


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def contract(tmp_path):
    root = tmp_path / "repo"
    (root / "inputs").mkdir(parents=True)
    (root / "src").mkdir()
    source = root / "inputs/owner.txt"
    source.write_text("\n\n".join(
        f"{i}. SECTION {i}\nRequired observable outcome {i}." for i in range(1, 12)))
    subject = root / "src/fixture.py"
    subject.write_text("# Synthetic evidence bytes; not native execution.\n")
    evidence = {"path": "src/fixture.py", "sha256": sha(subject),
                "why": "Synthetic byte-binding fixture only"}
    sections = []
    for i in range(1, 12):
        identity = f"H05-{i:02}"
        sections.append({"id": identity, "source_section": i, "title": f"SECTION {i}",
                         "clauses": [{"id": identity + ".01",
                                      "requirement": f"Check observable outcome {i}.",
                                      "source_quote": f"Required observable outcome {i}.",
                                      "implementation": {"status": "partial", "evidence": [copy.deepcopy(evidence)]},
                                      "local_qualification": {"status": "not_run", "evidence": []},
                                      "native_qualification": {"status": "not_run", "evidence": []},
                                      "gap": "Independent task/native outcome evidence is absent.",
                                      "next_check": "Run the independently authorized original outcome check."}]})
    manifest = {"schema": "harness.requirements/v1",
                "source": {"path": "inputs/owner.txt", "sha256": sha(source)},
                "sections": sections}
    return root, manifest


def clauses(manifest):
    return [clause for section in manifest["sections"] for clause in section["clauses"]]


def complete_fixture(manifest):
    manifest = copy.deepcopy(manifest)
    for clause in clauses(manifest):
        clause["implementation"]["status"] = "present"
        for axis, level in (("local_qualification", "local"), ("native_qualification", "native")):
            entry = copy.deepcopy(clause["implementation"]["evidence"][0])
            entry["receipt"] = {"level": level, "exit_code": 0,
                                "command": "fixture-only: no command or native model was run",
                                "subjects": [{"path": entry["path"], "sha256": entry["sha256"]}]}
            clause[axis] = {"status": "qualified", "evidence": [entry]}
    return manifest


def test_honest_partial_coverage_is_valid_but_incomplete(contract):
    root, manifest = contract
    result = validate(manifest, root)
    assert result["status"] == "CONTRACT_VALID"
    assert result["requirements"] == 11
    assert result["complete"] is False


def test_complete_requires_present_and_both_qualified_axes_for_every_clause(contract):
    root, manifest = contract
    full = complete_fixture(manifest)
    assert validate(full, root)["complete"] is True
    for axis, status in (("implementation", "partial"), ("local_qualification", "partial"),
                         ("local_qualification", "not_run"), ("native_qualification", "unknown")):
        changed = copy.deepcopy(full)
        clauses(changed)[-1][axis]["status"] = status
        assert validate(changed, root)["complete"] is False


@pytest.mark.parametrize("fault", ["omitted-section", "duplicate-section", "wrong-section-number",
                                  "duplicate-clause", "wrong-clause-prefix", "no-clauses"])
def test_section_and_clause_identity_coverage_cannot_shrink_or_alias(contract, fault):
    root, manifest = contract
    if fault == "omitted-section":
        manifest["sections"].pop()
    elif fault == "duplicate-section":
        manifest["sections"][-1] = copy.deepcopy(manifest["sections"][0])
    elif fault == "wrong-section-number":
        manifest["sections"][0]["source_section"] = 2
    elif fault == "duplicate-clause":
        manifest["sections"][0]["clauses"] *= 2
    elif fault == "wrong-clause-prefix":
        clauses(manifest)[0]["id"] = "H05-02.99"
    else:
        manifest["sections"][0]["clauses"] = []
    with pytest.raises(ValueError):
        validate(manifest, root)


@pytest.mark.parametrize("quote", ["", "A fabricated owner requirement.", "Required observable outcome 2."])
def test_quote_must_be_nonempty_and_verbatim_in_its_own_section(contract, quote):
    root, manifest = contract
    clauses(manifest)[0]["source_quote"] = quote
    with pytest.raises(ValueError):
        validate(manifest, root)


@pytest.mark.parametrize("field", ["requirement", "implementation", "local_qualification",
                                  "native_qualification", "gap", "next_check"])
def test_missing_required_clause_fields_fail_closed(contract, field):
    root, manifest = contract
    del clauses(manifest)[0][field]
    with pytest.raises(ValueError):
        validate(manifest, root)


@pytest.mark.parametrize("axis,status", [("implementation", "done"), ("implementation", True),
                                        ("local_qualification", "PASS"),
                                        ("native_qualification", None)])
def test_malformed_axis_statuses_are_not_coerced_to_success(contract, axis, status):
    root, manifest = contract
    clauses(manifest)[0][axis]["status"] = status
    with pytest.raises(ValueError):
        validate(manifest, root)


@pytest.mark.parametrize("axis,status", [("implementation", "present"), ("implementation", "partial"),
                                        ("local_qualification", "partial"),
                                        ("native_qualification", "qualified")])
def test_positive_or_partial_axis_claims_require_evidence(contract, axis, status):
    root, manifest = contract
    clauses(manifest)[0][axis] = {"status": status, "evidence": []}
    with pytest.raises(ValueError):
        validate(manifest, root)


@pytest.mark.parametrize("axis", ["local_qualification", "native_qualification"])
def test_source_bytes_alone_cannot_claim_qualified_execution(contract, axis):
    root, manifest = contract
    clauses(manifest)[0][axis] = {"status": "qualified",
                                 "evidence": copy.deepcopy(clauses(manifest)[0]["implementation"]["evidence"])}
    with pytest.raises(ValueError):
        validate(manifest, root)


@pytest.mark.parametrize("fault", ["wrong-level", "nonzero-exit", "boolean-exit", "empty-command",
                                  "no-subjects", "stale-subject"])
def test_receipt_level_exit_command_and_current_subject_binding_are_required(contract, fault):
    root, manifest = contract
    full = complete_fixture(manifest)
    entry = clauses(full)[0]["native_qualification"]["evidence"][0]
    receipt = entry["receipt"]
    if fault == "wrong-level":
        receipt["level"] = "local"
    elif fault == "nonzero-exit":
        receipt["exit_code"] = 1
    elif fault == "boolean-exit":
        receipt["exit_code"] = False
    elif fault == "empty-command":
        receipt["command"] = ""
    elif fault == "no-subjects":
        receipt["subjects"] = []
    else:
        (root / "src/fixture.py").write_text("# Changed current subject.\n")
        current = sha(root / "src/fixture.py")
        # Update ordinary evidence bindings so only the stale executed-subject
        # receipt remains wrong; an unrelated hash failure must not mask it.
        for clause in clauses(full):
            for axis in ("implementation", "local_qualification", "native_qualification"):
                for evidence in clause[axis]["evidence"]:
                    evidence["sha256"] = current
    with pytest.raises(ValueError):
        validate(full, root)


@pytest.mark.parametrize("fault", ["absolute-inside", "traversal", "symlink-escape", "missing",
                                  "directory", "wrong-hash"])
def test_evidence_paths_and_hashes_are_bound_inside_the_root(contract, fault):
    root, manifest = contract
    entry = clauses(manifest)[0]["implementation"]["evidence"][0]
    outside = root.parent / "outside.txt"
    outside.write_text("Outside the authorized fixture root.\n")
    if fault == "absolute-inside":
        entry["path"] = str(root / "src/fixture.py")
    elif fault == "traversal":
        entry.update(path="../outside.txt", sha256=sha(outside))
    elif fault == "symlink-escape":
        (root / "escape.txt").symlink_to(outside)
        entry.update(path="escape.txt", sha256=sha(outside))
    elif fault == "missing":
        entry["path"] = "src/absent.py"
    elif fault == "directory":
        entry["path"] = "src"
    else:
        entry["sha256"] = "0" * 64
    with pytest.raises(ValueError):
        validate(manifest, root)


@pytest.mark.parametrize("fault", ["changed-hash", "invalid-utf8", "oversized"])
def test_owner_source_binding_utf8_and_byte_limit_are_not_optional(contract, fault):
    root, manifest = contract
    source = root / manifest["source"]["path"]
    if fault == "changed-hash":
        source.write_text(source.read_text() + "\nchanged after freeze\n")
    else:
        source.write_bytes(b"\xff" if fault == "invalid-utf8" else b"x" * (1024 * 1024 + 1))
        manifest["source"]["sha256"] = sha(source)
    with pytest.raises(ValueError):
        validate(manifest, root)


@pytest.mark.parametrize("manifest", [None, [], {}, {"schema": "harness.requirements/unsupported"}])
def test_bad_top_level_input_raises_valueerror_instead_of_defaulting_green(contract, manifest):
    root, _ = contract
    with pytest.raises(ValueError):
        validate(manifest, root)


def test_validation_does_not_repair_mutate_write_or_spawn(contract, monkeypatch):
    root, manifest = contract
    original = copy.deepcopy(manifest)
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    def no_process(*args, **kwargs):
        raise AssertionError("contract validation must not execute an evidence command")

    monkeypatch.setattr(subprocess, "Popen", no_process)
    result = validate(manifest, root)
    assert result["status"] == "CONTRACT_VALID" and result["complete"] is False
    assert manifest == original
    after = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert after == before
