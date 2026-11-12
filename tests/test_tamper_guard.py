"""tests for scripts/tamper_guard.py — plan v3-eval-pipeline node 17.

Hermetic: every test builds a tiny git repo in tmp_path (two files of tests/),
drives tamper_guard.main() in process, and reads the verdict JSON. Both
directions for every control: silent weakening MUST trip, attested diffs pass,
tampered attestations fail, and a TRIP never rewrites the baseline.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import tamper_guard

TEST_CMD = "pytest -q tests eval"


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def make_repo(tmp_path, files=None):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "fixture@example.invalid")
    git(repo, "config", "user.name", "Fixture")
    (repo / "pytest.ini").write_text("[pytest]\n")
    body = {
        "tests/test_alpha.py": "def test_a1():\n    assert True\n    assert True\n\n\ndef test_a2():\n    assert True\n",
        "tests/test_beta.py": "def test_b1():\n    assert True\n",
    }
    for rel, text in (files or body).items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "init")
    return repo


def run_guard(repo, *extra):
    out = repo / "verdict.json"
    argv = ["--repo", str(repo), "--test-command", TEST_CMD, "--json-out", str(out)] + list(extra)
    code = tamper_guard.main(argv)
    return code, json.loads(out.read_text())


def sha_of(repo, rel):
    import hashlib
    return hashlib.sha256((repo / rel).read_bytes()).hexdigest()


def attest(repo, entries):
    path = repo / ".harness-work" / "tamper-attestations.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": "harness.tamper-attestations/v1",
                                "attestations": entries}, indent=2) + "\n")
    return path


def baseline_path(repo):
    return repo / ".harness-work" / "tamper-baseline.json"


def test_bootstrap_anchors_head_and_flags_dirty_diff(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "tests/test_new.py").write_text("def test_n1():\n    assert True\n")
    code, v = run_guard(repo)
    assert code == 1 and v["verdict"] == "TRIP"
    assert v["baseline_anchor"]["kind"] == "head"  # committed tree, never the dirty one
    assert [f["type"] for f in v["findings_unexcused"]] == ["new_file"]
    assert v["findings_unexcused"][0]["path"] == "tests/test_new.py"
    assert not baseline_path(repo).exists()  # TRIP never creates/refreshes the baseline


def test_clean_tree_passes_and_writes_baseline(tmp_path):
    repo = make_repo(tmp_path)
    code, v = run_guard(repo)
    assert code == 0 and v["verdict"] == "PASS"
    assert v["baseline_anchor"]["kind"] == "head"
    assert baseline_path(repo).exists()
    code, v = run_guard(repo)  # second run: surface == baseline
    assert code == 0 and not v["findings"]
    assert v["baseline_anchor"]["kind"] == "surface"


def test_silent_weakening_trips_and_preserves_baseline(tmp_path):
    repo = make_repo(tmp_path)
    assert run_guard(repo)[0] == 0
    before = baseline_path(repo).read_bytes()
    weakened = "def test_a1():\n    assert True\n"  # test_a2 silently gone
    (repo / "tests/test_alpha.py").write_text(weakened)
    code, v = run_guard(repo)
    assert code == 1 and v["verdict"] == "TRIP"
    f = v["findings_unexcused"][0]
    assert f["type"] == "modified_file" and f["path"] == "tests/test_alpha.py"
    assert f["signals"][0]["type"] == "function_drop"
    assert f["signals"][0]["baseline"] == 2 and f["signals"][0]["current"] == 1
    assert baseline_path(repo).read_bytes() == before  # a weakened tree never becomes baseline


def test_attested_diff_passes_and_refreshes_then_entry_is_stale(tmp_path):
    repo = make_repo(tmp_path)
    assert run_guard(repo)[0] == 0
    (repo / "tests/test_alpha.py").write_text("def test_a1():\n    assert True\n")
    attest(repo, [{"path": "tests/test_alpha.py", "sha256": sha_of(repo, "tests/test_alpha.py"),
                   "reason": "test_a2 merged into test_a1 (fixture acceptance criterion x)",
                   "noted": "2026-11-11"}])
    code, v = run_guard(repo)
    assert code == 0 and v["verdict"] == "PASS" and v["attested"] is True
    applied = v["applied_attestations"][0]
    assert applied["finding"] == "modified_file" and "function_drop" in applied["signals"]
    assert applied["reason"].startswith("test_a2 merged")
    code, v = run_guard(repo)  # baseline now carries the change: clean PASS, entry goes stale
    assert code == 0 and not v["findings"]
    assert [s["path"] for s in v["stale_attestations"]] == ["tests/test_alpha.py"]


def test_tampered_attestation_fails(tmp_path):
    repo = make_repo(tmp_path)
    assert run_guard(repo)[0] == 0
    (repo / "tests/test_alpha.py").write_text("def test_a1():\n    assert True\n")
    good = sha_of(repo, "tests/test_alpha.py")
    bad = "0" * 64 if good != "0" * 64 else "1" * 64
    attest(repo, [{"path": "tests/test_alpha.py", "sha256": bad,
                   "reason": "hash points at different bytes", "noted": "2026-11-11"}])
    code, v = run_guard(repo)
    assert code == 1 and v["verdict"] == "TRIP"  # tampered hash does not excuse
    assert v["stale_attestations"][0]["sha256"] == bad


def test_attestation_without_reason_or_malformed_file_is_error(tmp_path):
    repo = make_repo(tmp_path)
    assert run_guard(repo)[0] == 0
    (repo / "tests/test_alpha.py").write_text("def test_a1():\n    assert True\n")
    attest(repo, [{"path": "tests/test_alpha.py", "sha256": sha_of(repo, "tests/test_alpha.py"),
                   "reason": "   ", "noted": "2026-11-11"}])
    code, v = run_guard(repo)
    assert code == 2 and v["verdict"] == "ERROR" and "structurally invalid" in v["reason"]
    (repo / ".harness-work/tamper-attestations.json").write_text("{not json")
    code, v = run_guard(repo)
    assert code == 2 and v["verdict"] == "ERROR"


def test_deleted_file_both_directions(tmp_path):
    repo = make_repo(tmp_path)
    assert run_guard(repo)[0] == 0
    baseline_sha = sha_of(repo, "tests/test_beta.py")
    (repo / "tests/test_beta.py").unlink()
    code, v = run_guard(repo)
    assert code == 1 and v["findings_unexcused"][0]["type"] == "deleted_file"
    attest(repo, [{"path": "tests/test_beta.py", "sha256": baseline_sha,
                   "reason": "suite retired with feature x (acceptance criterion y)",
                   "noted": "2026-11-11"}])
    code, v = run_guard(repo)
    assert code == 0 and v["applied_attestations"][0]["finding"] == "deleted_file"


def test_per_file_function_drop_not_masked_by_growth(tmp_path):
    repo = make_repo(tmp_path)
    assert run_guard(repo)[0] == 0
    (repo / "tests/test_alpha.py").write_text("def test_a1():\n    assert True\n")  # -1
    (repo / "tests/test_gamma.py").write_text("def test_g1():\n    assert True\n")  # +1 (net zero)
    code, v = run_guard(repo)
    assert code == 1
    modified = next(f for f in v["findings_unexcused"] if f["type"] == "modified_file")
    assert modified["signals"][0]["type"] == "function_drop"  # per-file, net-masking impossible


def test_new_skip_xfail_flagged_with_unchanged_counts(tmp_path):
    repo = make_repo(tmp_path)
    assert run_guard(repo)[0] == 0
    (repo / "tests/test_beta.py").write_text(
        "import pytest\n\n\n@pytest.mark.skip(reason='fixture')\ndef test_b1():\n    assert True\n")
    code, v = run_guard(repo)
    assert code == 1
    assert v["findings_unexcused"][0]["signals"][0]["type"] == "new_skip_xfail"


def test_assertion_density_drop_flagged(tmp_path):
    repo = make_repo(tmp_path)
    assert run_guard(repo)[0] == 0
    (repo / "tests/test_alpha.py").write_text(
        "def test_a1():\n    pass\n\n\ndef test_a2():\n    pass\n")  # 3 asserts -> 0, same functions
    code, v = run_guard(repo)
    assert code == 1
    types = [s["type"] for s in v["findings_unexcused"][0]["signals"]]
    assert "assertion_density_drop" in types


def test_non_ascii_filename_roundtrip(tmp_path):
    repo = make_repo(tmp_path)
    assert run_guard(repo)[0] == 0
    (repo / "tests/test_界面.py").write_text("def test_u1():\n    assert True\n")
    code, v = run_guard(repo)
    assert code == 1 and v["findings_unexcused"][0]["path"] == "tests/test_界面.py"
    attest(repo, [{"path": "tests/test_界面.py", "sha256": sha_of(repo, "tests/test_界面.py"),
                   "reason": "non-ASCII name regression fixture", "noted": "2026-11-11"}])
    code, v = run_guard(repo)
    assert code == 0


def test_empty_surface_and_missing_command_are_not_run(tmp_path):
    repo = tmp_path / "empty"
    repo.mkdir()
    git(repo, "init", "-q")
    code, v = run_guard(repo)
    assert code == 2 and v["verdict"] == "NOT_RUN" and "empty test surface" in v["reason"]
    repo2 = tmp_path / "nocommand"
    repo2.mkdir()
    git(repo2, "init", "-q")
    (repo2 / "tests").mkdir()
    (repo2 / "tests/test_x.py").write_text("def test_x():\n    assert True\n")
    out = repo2 / "verdict.json"
    code = tamper_guard.main(["--repo", str(repo2), "--json-out", str(out)])  # no --test-command, no pytest config
    v = json.loads(out.read_text())
    assert code == 2 and v["verdict"] == "NOT_RUN" and "no test command" in v["reason"]
    assert not (repo2 / ".harness-work/tamper-baseline.json").exists()


def test_absent_attestation_file_means_zero_attestations(tmp_path):
    repo = make_repo(tmp_path)
    assert run_guard(repo)[0] == 0
    (repo / "tests/test_new.py").write_text("def test_n1():\n    assert True\n")
    code, v = run_guard(repo)
    assert code == 1 and v["attestation_present"] is False


def test_no_refresh_flag_keeps_control_runs_read_only(tmp_path):
    repo = make_repo(tmp_path)
    assert run_guard(repo)[0] == 0
    before = baseline_path(repo).read_bytes()
    (repo / "tests/test_new.py").write_text("def test_n1():\n    assert True\n")
    attest(repo, [{"path": "tests/test_new.py", "sha256": sha_of(repo, "tests/test_new.py"),
                   "reason": "control run", "noted": "2026-11-11"}])
    code, v = run_guard(repo, "--no-refresh")
    assert code == 0 and v["baseline_refreshed"] is False
    assert baseline_path(repo).read_bytes() == before


def test_internal_error_is_fail_closed(tmp_path):
    code = tamper_guard.main(["--repo", str(tmp_path), "--json-out",
                              str(tmp_path / "v.json")])
    v = json.loads((tmp_path / "v.json").read_text())
    assert code == 2 and v["verdict"] == "ERROR" and "not a git work tree" in v["reason"]
