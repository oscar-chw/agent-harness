"""tests for the local pipeline runner (scripts/pipeline.py) — plan v3-eval-pipeline node 7.

Hermetic: every test injects a STUB registry of interpreter one-liners, so the gate
runs in seconds, spends nothing, and never touches the real tiers. The real registry
is exercised once, read-only, by the plan's node-9 smoke run.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import pipeline


def ok_cmd():
    return {"argv": [sys.executable, "-c", "pass"], "timeout_s": 30}


def bad_cmd():
    return {"argv": [sys.executable, "-c", "raise SystemExit(1)"], "timeout_s": 30}


def full_registry(cmd=None):
    return {t: [cmd() if callable(cmd) else ok_cmd()] for t in pipeline.TIER_ORDER}


def test_tier_order_fixed():
    assert pipeline.TIER_ORDER == ("push", "unit", "integration", "e2e", "perf", "ship")


def test_real_registry_shape_without_running():
    reg = pipeline.default_registry()
    assert set(reg) == set(pipeline.TIER_ORDER)
    assert reg["ship"] == []  # empty by design: promotion stays human
    perf = reg["perf"]
    assert len(perf) == 1 and perf[0]["argv"][1:] == ["scripts/perf_probe.py"]  # node 11 wiring
    assert any("ruff" in " ".join(c["argv"]) for c in reg["push"])
    assert reg["unit"][0]["timeout_s"] >= 1800  # suite measured >300 s wall


def test_fast_registry_swaps_only_the_unit_tier():
    slow = pipeline.default_registry()
    fast = pipeline.default_registry(fast=True)
    assert slow["unit"][0]["argv"][-2:] == ["tests", "eval"]
    argv = fast["unit"][0]["argv"]
    assert argv[1:4] == ["-m", "pytest", "-q"]
    assert argv[4:] == pipeline.FAST_UNIT_PATHS
    assert fast["unit"][0]["timeout_s"] < slow["unit"][0]["timeout_s"]
    assert "tests/test_plan_component.py" not in pipeline.FAST_UNIT_PATHS  # 63 s vendored suites
    for p in pipeline.FAST_UNIT_PATHS:
        assert (ROOT / p).is_file(), p  # fail-closed on list rot
    for t in pipeline.TIER_ORDER:
        if t != "unit":
            assert fast[t] == slow[t]


def test_staging_python_probe_both_directions(tmp_path, monkeypatch):
    # green: a fake "capable" interpreter on PATH is accepted
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "python3-fake"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(bindir))
    monkeypatch.setenv("HARNESS_STAGING_PYTHON", "python3-fake")
    assert pipeline._staging_python() == str(fake)
    # red: a bogus preset qualifies nothing and leaves the env untouched
    monkeypatch.setenv("HARNESS_STAGING_PYTHON", "definitely-not-a-python-xyz")
    assert pipeline._staging_python() is None


def test_verify_allow_not_run_policy_both_directions(tmp_path):
    # red: a scoped run leaves five tiers NOT_RUN — allowing only ship must refuse
    receipt, code = pipeline.run(selected=["push"], registry=full_registry(),
                                 root=tmp_path, receipt_dir=tmp_path / "runs")
    assert code == 2
    ok, errors = pipeline.verify(receipt, root=tmp_path, allow_not_run=["ship"])
    assert not ok and any("NOT_RUN outside" in e for e in errors)
    # green: ship the only NOT_RUN tier -> the adapter policy accepts
    reg = full_registry()
    reg["ship"] = []
    receipt, code = pipeline.run(registry=reg, root=tmp_path, receipt_dir=tmp_path / "runs")
    assert code == 2 and receipt["verdict"] == "INCOMPLETE"
    ok, errors = pipeline.verify(receipt, root=tmp_path, allow_not_run=["ship"])
    assert ok and not errors


def test_verify_allow_not_run_never_excuses_a_fail(tmp_path):
    reg = full_registry()
    reg["unit"] = [bad_cmd()]
    reg["ship"] = []
    receipt, code = pipeline.run(registry=reg, root=tmp_path, receipt_dir=tmp_path / "runs")
    assert code == 1
    ok, errors = pipeline.verify(receipt, root=tmp_path, allow_not_run=["ship"])
    assert not ok and any("never excuses" in e for e in errors)


def test_all_pass_verdict_pass(tmp_path):
    receipt, code = pipeline.run(registry=full_registry(), root=tmp_path, receipt_dir=tmp_path / "runs")
    assert code == 0 and receipt["verdict"] == "PASS"
    assert all(t["status"] == "PASS" for t in receipt["tiers"])
    assert list(tmp_path.glob("runs/run-*.json"))  # receipt actually written


def test_fail_fast_halts_later_tiers(tmp_path):
    reg = full_registry()
    reg["unit"] = [bad_cmd()]
    receipt, code = pipeline.run(registry=reg, root=tmp_path, receipt_dir=tmp_path / "runs")
    assert code == 1 and receipt["verdict"] == "FAIL"
    status = {t["name"]: t["status"] for t in receipt["tiers"]}
    assert status["push"] == "PASS" and status["unit"] == "FAIL"
    for t in ("integration", "e2e", "perf", "ship"):
        assert status[t] == "NOT_RUN"


def test_within_tier_fail_fast(tmp_path):
    reg = full_registry()
    reg["push"] = [bad_cmd(), ok_cmd()]
    receipt, _ = pipeline.run(registry=reg, root=tmp_path, receipt_dir=tmp_path / "runs")
    push = next(t for t in receipt["tiers"] if t["name"] == "push")
    assert push["status"] == "FAIL" and len(push["commands"]) == 1  # second command never ran


def test_tier_scoping_leaves_rest_not_run(tmp_path):
    receipt, code = pipeline.run(selected=["push"], registry=full_registry(),
                                 root=tmp_path, receipt_dir=tmp_path / "runs")
    assert code == 2 and receipt["verdict"] == "INCOMPLETE"
    ran = [t["name"] for t in receipt["tiers"] if t["status"] == "PASS"]
    assert ran == ["push"]


def test_empty_tier_means_incomplete_never_green(tmp_path):
    reg = full_registry()
    reg["perf"] = []
    receipt, code = pipeline.run(registry=reg, root=tmp_path, receipt_dir=tmp_path / "runs")
    assert code == 2 and receipt["verdict"] == "INCOMPLETE"
    assert next(t for t in receipt["tiers"] if t["name"] == "perf")["status"] == "NOT_RUN"


def test_receipt_schema_and_self_verify(tmp_path):
    receipt, _ = pipeline.run(registry=full_registry(), root=tmp_path, receipt_dir=tmp_path / "runs")
    assert receipt["schema"] == "harness.pipeline-receipt/v1"
    ok, errors = pipeline.verify(receipt, root=tmp_path)
    assert ok, errors


def test_verify_rejects_tampered_status(tmp_path):
    receipt, _ = pipeline.run(registry=full_registry(), root=tmp_path, receipt_dir=tmp_path / "runs")
    receipt["tiers"][0]["status"] = "FAIL"
    ok, errors = pipeline.verify(receipt, root=tmp_path)
    assert not ok and any("self-hash" in e for e in errors)


def test_verify_rejects_tampered_argv(tmp_path):
    receipt, _ = pipeline.run(registry=full_registry(), root=tmp_path, receipt_dir=tmp_path / "runs")
    receipt["tiers"][0]["commands"][0]["argv"].append("--evil")
    ok, errors = pipeline.verify(receipt, root=tmp_path)
    assert not ok


def test_verify_rejects_deleted_artifact(tmp_path):
    script = tmp_path / "step.py"
    script.write_text("pass\n")
    reg = full_registry(lambda: {"argv": [sys.executable, "step.py"], "timeout_s": 30})
    receipt, code = pipeline.run(registry=reg, root=tmp_path, receipt_dir=tmp_path / "runs")
    assert code == 0
    assert receipt["tiers"][0]["commands"][0]["artifacts"]  # bound to the file's bytes
    script.unlink()
    ok, errors = pipeline.verify(receipt, root=tmp_path)
    assert not ok and any("artifact missing" in e for e in errors)


def test_timeout_is_fail_not_skip(tmp_path):
    slow = {"argv": [sys.executable, "-c", "import time; time.sleep(5)"], "timeout_s": 1}
    reg = full_registry()
    reg["push"] = [slow]
    receipt, code = pipeline.run(registry=reg, root=tmp_path, receipt_dir=tmp_path / "runs")
    push = next(t for t in receipt["tiers"] if t["name"] == "push")
    assert code == 1 and push["status"] == "FAIL"
    assert push["commands"][0]["timed_out"] is True


def test_unknown_tier_is_usage_error(tmp_path):
    with pytest.raises(ValueError):
        pipeline.run(selected=["deploy-the-world"], registry=full_registry(), root=tmp_path,
                     receipt_dir=tmp_path / "runs")
    assert pipeline.main(["--tier", "deploy-the-world", "--receipt-dir", str(tmp_path / "runs")]) == 64


def test_cli_list_and_verify_roundtrip(tmp_path, capsys):
    assert pipeline.main(["--list"]) == 0
    assert "push" in capsys.readouterr().out
    _, code = pipeline.run(registry=full_registry(), root=tmp_path, receipt_dir=tmp_path / "runs")
    path = next((tmp_path / "runs").glob("run-*.json"))
    assert pipeline.main(["verify", str(path)]) == 0


def test_receipt_records_repo_state(tmp_path):
    receipt, _ = pipeline.run(registry=full_registry(), root=ROOT, receipt_dir=tmp_path / "runs")
    assert receipt["repo"]["root"] == str(ROOT)
    assert len(receipt["repo"]["git_head"]) == 40
    assert receipt["repo"]["tree_dirty"] in (True, False)


def test_receipts_are_additive(tmp_path):
    pipeline.run(registry=full_registry(), root=tmp_path, receipt_dir=tmp_path / "runs")
    pipeline.run(registry=full_registry(), root=tmp_path, receipt_dir=tmp_path / "runs")
    assert len(list((tmp_path / "runs").glob("run-*.json"))) == 2  # same second, no overwrite


def test_receipt_is_parseable_json_with_verdict(tmp_path):
    _, code = pipeline.run(registry=full_registry(), root=tmp_path, receipt_dir=tmp_path / "runs")
    path = next((tmp_path / "runs").glob("run-*.json"))
    loaded = json.loads(path.read_text())
    assert loaded["verdict"] == "PASS" and code == 0


# --- plan node 17: tamper guard wiring + the evidence_file channel ------------

def test_push_tier_runs_tamper_guard_first():
    reg = pipeline.default_registry()
    push = reg["push"]
    assert push[0]["argv"][1:] == ["scripts/tamper_guard.py", "--repo", ".", "--test-command",
                                   "pytest -q tests eval", "--json-out", pipeline.TAMPER_VERDICT]
    assert push[0]["evidence_file"] == pipeline.TAMPER_VERDICT
    assert any("ruff" in " ".join(c["argv"]) for c in push[1:])  # ruff/scan unchanged, after the guard


def _evidence_writer(body):
    return {"argv": [sys.executable, "-c",
                     "import json, pathlib; pathlib.Path('verdict.json').write_text(%r)"
                     % json.dumps(body)],
            "timeout_s": 30, "evidence_file": "verdict.json"}


def test_evidence_embedded_and_volatile_file_not_pinned(tmp_path):
    att = {"path": "tests/x.py", "sha256": "a" * 64, "reason": "known diff", "noted": "2026-11-11"}
    reg = full_registry(lambda: _evidence_writer({"verdict": "PASS", "applied_attestations": [att]}))
    receipt, code = pipeline.run(registry=reg, root=tmp_path, receipt_dir=tmp_path / "runs")
    assert code == 0
    rec = receipt["tiers"][0]["commands"][0]
    assert rec["evidence"]["applied_attestations"][0]["sha256"] == "a" * 64  # attestation IN the receipt
    assert "verdict.json" not in rec["artifacts"]  # volatile file embedded, never hash-pinned
    ok, errors = pipeline.verify(receipt, root=tmp_path)
    assert ok, errors  # the evidence key is additive; the receipt still verifies


def test_evidence_missing_after_pass_fails_closed(tmp_path):
    silent = {"argv": ok_cmd()["argv"], "timeout_s": 30, "evidence_file": "verdict.json"}
    reg = full_registry(lambda: silent)
    receipt, code = pipeline.run(registry=reg, root=tmp_path, receipt_dir=tmp_path / "runs")
    assert code == 1 and receipt["verdict"] == "FAIL"
    rec = receipt["tiers"][0]["commands"][0]
    assert rec["exit"] == 1 and "evidence_error" in rec


def test_stale_evidence_from_prior_run_is_never_read(tmp_path):
    (tmp_path / "verdict.json").write_text(json.dumps({"verdict": "STALE"}))
    silent = {"argv": ok_cmd()["argv"], "timeout_s": 30, "evidence_file": "verdict.json"}
    reg = full_registry(lambda: silent)
    receipt, code = pipeline.run(registry=reg, root=tmp_path, receipt_dir=tmp_path / "runs")
    rec = receipt["tiers"][0]["commands"][0]
    assert code == 1 and "evidence_error" in rec  # pre-deleted; the leftover is not this run's evidence
    assert rec.get("evidence", {}).get("verdict") != "STALE"


# --- plan node 19: deterministic tool resolution + named tool errors ---------

def test_tool_resolution_preference_order(tmp_path):
    fake_system = tmp_path / "python3-sys"
    fake_system.write_text("x")  # existence is all the resolver checks
    fb = "/fallback/sys-executable"
    # (a) HARNESS_PIPELINE_PYTHON override wins over everything
    assert pipeline._resolve_tool_python(environ={pipeline.TOOL_ENV_VAR: "/env/override"},
                                         system_py=str(fake_system), fallback=fb) == \
        ("/env/override", "env:%s" % pipeline.TOOL_ENV_VAR)
    # (b) /usr/bin/python3 (present) beats the fallback
    assert pipeline._resolve_tool_python(environ={}, system_py=str(fake_system), fallback=fb) == \
        (str(fake_system), "system:%s" % fake_system)
    # (c) sys.executable is the last resort when neither exists
    assert pipeline._resolve_tool_python(environ={}, system_py=str(tmp_path / "absent-python3"),
                                         fallback=fb) == (fb, "fallback:sys.executable")


def test_registry_stamps_resolution_and_tool_metadata(monkeypatch):
    monkeypatch.setenv(pipeline.TOOL_ENV_VAR, "/override/python3")
    reg = pipeline.default_registry()
    ruff = next(c for c in reg["push"] if "ruff" in " ".join(c["argv"]))
    assert ruff["argv"][0] == "/override/python3"  # env override honored in the real registry
    assert ruff["tool_module"] == "ruff" and ruff["tool_pinned"] == pipeline.RUFF_PINNED_VERSION
    assert ruff["tool_resolution"] == "env:%s" % pipeline.TOOL_ENV_VAR
    for tier in ("unit", "integration"):
        cmd = reg[tier][0]
        assert cmd["argv"][0] == "/override/python3" and cmd["tool_module"] == "pytest"
        assert cmd["tool_pinned"] is None  # version recorded; drift policy not applicable
    # audit: repo scripts and shell commands stay OFF the tool resolver
    assert reg["push"][0]["argv"][0] == sys.executable  # tamper guard: repo script
    assert "tool_module" not in reg["push"][0]
    assert reg["push"][2]["argv"][0] == "bash"  # secret scan: no interpreter at all
    assert reg["perf"][0]["argv"][0] == sys.executable and "tool_module" not in reg["perf"][0]
    assert reg["e2e"][1]["argv"][0] == sys.executable  # e2e_journey.py: repo script


def test_missing_tool_fails_with_named_error(tmp_path):
    spec = {"argv": [sys.executable, "-m", "definitely_not_a_module_xyz", "check"],
            "timeout_s": 30, "tool_module": "definitely_not_a_module_xyz",
            "tool_version_argv": ["-m", "definitely_not_a_module_xyz", "--version"],
            "tool_resolution": "fallback:sys.executable"}
    reg = full_registry(lambda: dict(spec))
    receipt, code = pipeline.run(registry=reg, root=tmp_path, receipt_dir=tmp_path / "runs")
    assert code == 1 and receipt["verdict"] == "FAIL"
    rec = receipt["tiers"][0]["commands"][0]
    assert receipt["tiers"][0]["status"] == "FAIL"
    assert rec["not_executed"] is True and rec["exit"] == 1  # never executed, never bare
    assert rec["tool"]["available"] is False
    assert "tool definitely_not_a_module_xyz unavailable in" in rec["stderr_tail"]
    assert "No module named" in rec["stderr_tail"]  # the interpreter's own reason, verbatim
    assert all(t["status"] == "NOT_RUN" for t in receipt["tiers"][1:])  # fail-fast intact
    path = next((tmp_path / "runs").glob("run-*.json"))
    assert "tool definitely_not_a_module_xyz unavailable in" in path.read_text()  # receipt records it
    ok, errors = pipeline.verify(receipt, root=tmp_path)
    assert ok, errors  # a faithful named-FAIL receipt still verifies


def test_tool_probe_crash_is_named_fail_closed(tmp_path):
    spec = {"argv": ["/nonexistent/python3-xyz", "-m", "ruff"], "timeout_s": 30,
            "tool_module": "ruff", "tool_version_argv": ["-m", "ruff", "--version"]}
    reg = full_registry(lambda: dict(spec))
    receipt, code = pipeline.run(registry=reg, root=tmp_path, receipt_dir=tmp_path / "runs")
    rec = receipt["tiers"][0]["commands"][0]
    assert code == 1 and rec["not_executed"] is True
    assert "tool ruff unavailable in /nonexistent/python3-xyz" in rec["stderr_tail"]


def _stub_python(tmp_path, version):
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    stub = bindir / "python3-stub"
    stub.write_text("#!/bin/sh\ncase \"$*\" in\n *--version*) echo 'ruff %s';;\n esac\nexit 0\n"
                    % version)
    stub.chmod(0o755)
    return str(stub)


def test_version_drift_noted_but_run_green(tmp_path, monkeypatch):
    stub = _stub_python(tmp_path, "9.9.9")
    monkeypatch.setenv(pipeline.TOOL_ENV_VAR, stub)
    tpy, resolution = pipeline._resolve_tool_python()
    assert tpy == stub and resolution == "env:%s" % pipeline.TOOL_ENV_VAR
    spec = {"argv": [tpy, "-m", "ruff", "check", "."], "timeout_s": 30,
            "tool_resolution": resolution, **pipeline._tool("ruff", pinned=pipeline.RUFF_PINNED_VERSION)}
    reg = full_registry(lambda: dict(spec))
    receipt, code = pipeline.run(registry=reg, root=tmp_path, receipt_dir=tmp_path / "runs")
    assert code == 0 and receipt["verdict"] == "PASS"  # drift NEVER fails the run
    rec = receipt["tiers"][0]["commands"][0]
    assert rec["exit"] == 0
    tool = rec["tool"]
    assert tool["interpreter"] == stub and tool["resolution"] == "env:%s" % pipeline.TOOL_ENV_VAR
    assert tool["version"] == "9.9.9" and tool["pinned"] == pipeline.RUFF_PINNED_VERSION
    assert "9.9.9" in tool["version_drift"] and pipeline.RUFF_PINNED_VERSION in tool["version_drift"]


def test_ruff_pin_matches_design_doc():
    doc = (ROOT / "docs" / "v3" / "eval-pipeline-design-20261110.md").read_text(encoding="utf-8")
    assert pipeline.RUFF_PINNED_VERSION in doc  # hosted lint.yml pin, cited in the push-tier choice
    assert "lint.yml" in doc
