"""Behavioral acceptance for the isolated interviewer demonstration."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "examples" / "interview"


def checker():
    path = PACK / "check_pack.py"
    assert path.is_file(), "The interview pack needs an independent receipt checker"
    spec = importlib.util.spec_from_file_location("interview_checker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_receipt():
    return {
        "schema": "harness.interview-demo/v1", "status": "PASS", "model_calls": 0,
        "commands_sha256": "c" * 64,
        "runtime": {"version": "3.0.0rc2", "engine_sha256": "a" * 64},
        "readers": [
            {"pid": 123, "cold_pickup": True, "unchanged_board_bytes": 0},
            {"pid": 456, "cold_pickup": True, "unchanged_board_bytes": 0}],
        "delta": {"first_bytes": 100, "repeat_bytes": 0, "contains_next_step": True},
        "gate": {"before_exit": 1, "before_mark": "pending", "after_exit": 0,
                 "before_tests_run": 3, "before_failures": 2, "after_tests_run": 3,
                 "after_mark": "done", "tests_sha256_before": "b" * 64,
                 "tests_sha256_after": "b" * 64},
        "stale_write": {"exit": 1, "version_before": 2, "version_after": 2,
                        "version_conflict_observed": True,
                        "summary_preserved": True},
        "isolation": {"disposable_home": True, "disposable_project": True},
        "limits": ["No native model turn", "No universal compliance claim"],
    }


def test_contract_accepts_exact_observed_success_shape():
    checker().validate_receipt(valid_receipt())


@pytest.mark.parametrize("mutate", [
    lambda r: r["readers"][1].update(pid=123),
    lambda r: r["gate"].update(before_exit=0),
    lambda r: r["gate"].update(after_mark="pending"),
    lambda r: r["gate"].update(tests_sha256_after="c" * 64),
    lambda r: r["stale_write"].update(exit=0),
    lambda r: r["stale_write"].update(version_conflict_observed=False),
    lambda r: r["gate"].update(before_tests_run=0),
    lambda r: r["delta"].update(repeat_bytes=100),
    lambda r: r.update(model_calls=1),
    lambda r: r.update(readers=[]),
])
def test_contract_rejects_false_success(mutate):
    result = copy.deepcopy(valid_receipt())
    mutate(result)
    with pytest.raises(ValueError):
        checker().validate_receipt(result)


def test_demo_entrypoint_exists():
    assert (PACK / "demo.py").is_file(), "A runnable installed-runtime demo is required"


@pytest.fixture
def runtime_tree(tmp_path):
    runtime = tmp_path / "runtime"
    shutil.copytree(ROOT / "src/agent_harness", runtime / "lib/agent_harness",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "content", runtime / "content")
    return runtime


def test_real_runtime_processes_and_output_preservation(tmp_path, runtime_tree):
    demo = PACK / "demo.py"
    assert demo.is_file(), "A runnable installed-runtime demo is required"
    output = tmp_path / "run"
    command = [sys.executable, str(demo), "--output", str(output), "--runtime", str(runtime_tree)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = output / "demo-proof.json"
    original = receipt.read_bytes()
    checker().validate_receipt(json.loads(original))
    again = subprocess.run(command, capture_output=True, text=True, timeout=15)
    assert again.returncode != 0
    assert receipt.read_bytes() == original


def test_missing_runtime_fails_before_creating_output(tmp_path):
    output = tmp_path / "run"
    result = subprocess.run([sys.executable, str(PACK / "demo.py"), "--output", str(output),
                             "--runtime", str(tmp_path / "missing")],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 2
    assert "runtime missing" in result.stderr
    assert not output.exists()


def test_demo_rejects_a_runtime_that_drops_automatic_board_context(tmp_path, runtime_tree):
    board = runtime_tree / "lib/agent_harness/shared_board.py"
    source = board.read_text()
    original = "    def context(self):\n"
    assert source.count(original) == 1
    board.write_text(source.replace(original, original + "        return ''\n", 1))
    output = tmp_path / "broken-run"
    result = subprocess.run([sys.executable, str(PACK / "demo.py"), "--output", str(output),
                             "--runtime", str(runtime_tree)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 1
    assert "reader A" in result.stderr
    assert "PASS 1/5" not in result.stdout
    assert json.loads((output / "demo-proof.json").read_text())["status"] == "FAIL"


def test_guard_refusal_cannot_be_presented_as_reproduced_assertion_failure(tmp_path, runtime_tree):
    engine = runtime_tree / "lib/agent_harness/workgraph/plan.py"
    source = engine.read_text()
    original = "def guard_refusal(gate, root):\n"
    assert source.count(original) == 1
    engine.write_text(source.replace(original, original + "    return 'Fixture policy refuses execution'\n", 1))
    output = tmp_path / "refused-run"
    result = subprocess.run([sys.executable, str(PACK / "demo.py"), "--output", str(output),
                             "--runtime", str(runtime_tree)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 1
    assert "expected assertion failures were not observed" in result.stderr
    assert "PASS 2/5" not in result.stdout


@pytest.mark.parametrize("bad_receipt", [True, False])
def test_guide_refuses_failed_or_unbound_replay_before_writing(tmp_path, monkeypatch, bad_receipt):
    monkeypatch.syspath_prepend(str(PACK))
    spec = importlib.util.spec_from_file_location("interview_builder", PACK / "build_guide.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "HERE", tmp_path)
    (tmp_path / "demo.py").write_text("demo fixture")
    (tmp_path / "architecture.svg").write_text("preserve old diagram")
    receipt = valid_receipt()
    receipt["demo_sha256"] = hashlib.sha256((tmp_path / "demo.py").read_bytes()).hexdigest()
    if bad_receipt:
        receipt["status"] = "FAIL"
    (tmp_path / "recorded-demo-proof.json").write_text(json.dumps(receipt))
    (tmp_path / "recorded-commands.json").write_text("[]")
    with pytest.raises(ValueError, match="demo did not pass|different rehearsal"):
        module.main()
    assert (tmp_path / "architecture.svg").read_text() == "preserve old diagram"
    assert not (tmp_path / "guide.html").exists()
