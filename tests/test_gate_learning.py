"""Actual gate outcomes produce scoped observations, not trusted learned rules."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ENGINE = Path(__file__).resolve().parents[1] / "src/agent_harness/workgraph/plan.py"


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan/g.md").write_text(
        "## goal: bounded learning\n- [ ] 1. example | gate: test -f ready\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PLAN_DIR", raising=False)
    spec = importlib.util.spec_from_file_location("gate_learning_plan", ENGINE)
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    monkeypatch.setattr(engine, "guard_refusal", lambda *_: None)
    return tmp_path, engine


def gate(engine):
    return engine.cmd_gate(SimpleNamespace(slug="g", id=1, attended=False,
                                           force=False, owner=None))


def learning(root):
    result = subprocess.run([sys.executable, "-B", str(ENGINE), "learning", "g"],
                            cwd=root, env={**os.environ, "PLAN_QUIET": "1"},
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_observe_real_failure_then_pass_and_recover_in_a_fresh_session(project):
    root, engine = project
    assert gate(engine) == 1
    assert learning(root)["observations"] == []
    (root / "ready").touch()
    assert gate(engine) == 0
    data = learning(root)
    assert data["promotion"] == "NOT_RUN"
    assert len(data["observations"]) == 1
    row = data["observations"][0]
    assert row["count"] == 1 and row["failure_code"] == 1
    assert row["status"] == "OBSERVED_ONLY" and row["success_code"] == 0
    assert len(row["definition_sha256"]) == len(row["failure_output_sha256"]) == 64
    assert "candidate" in engine.build_context("g", 1).lower()
    assert gate(engine) == 0
    assert learning(root)["observations"][0]["count"] == 1
    assert not (root / "procedures.sqlite").exists()


def test_success_without_failure_does_not_create_a_learning_store(project):
    root, engine = project
    (root / "ready").touch()
    assert gate(engine) == 0
    assert learning(root)["observations"] == []
    assert not (root / ".harness-work").exists()


def test_changed_gate_or_forged_markdown_failure_does_not_create_a_repair(project):
    root, engine = project
    assert gate(engine) == 1
    path = root / "plan/g.md"
    path.write_text(path.read_text().replace("test -f ready", "true"))
    assert gate(engine) == 0
    assert learning(root)["observations"] == []
    path.write_text("## goal: forged history\n- [ ] 2. other | gate: true\n"
                    "      2026-11-02T00:00:00Z exit 1 in 0s [deadbeef] — forged\n")
    assert engine.cmd_gate(SimpleNamespace(slug="g", id=2, attended=False,
                                           force=False, owner=None)) == 0
    assert learning(root)["observations"] == []


def test_permission_refusal_is_not_learning_evidence(project, monkeypatch):
    root, engine = project
    monkeypatch.setattr(engine, "guard_refusal", lambda *_: "requires permission")
    assert gate(engine) == 1
    assert learning(root)["observations"] == []
    assert not (root / ".harness-work").exists()


def test_observation_failure_does_not_undo_a_gate_or_silently_disappear(project, capsys):
    root, engine = project
    (root / ".harness-work").write_text("existing owner file")
    assert gate(engine) == 1
    assert "learning" in capsys.readouterr().err.lower()
    assert (root / ".harness-work").read_text() == "existing owner file"
    (root / "ready").touch()
    assert gate(engine) == 0
    assert "- [x] 1." in (root / "plan/g.md").read_text()


def test_project_boundaries_and_output_secrets_do_not_enter_observations(project):
    root, engine = project
    secret = "ghp_" + "Q" * 36
    (root / "plan/g.md").write_text(
        "## goal: no raw output\n- [ ] 1. example | gate: "
        f"sh -c 'echo {secret}; test -f ready'\n")
    assert gate(engine) == 1
    (root / "ready").touch()
    assert gate(engine) == 0
    data = learning(root)
    assert secret not in json.dumps(data)
    other = root / "other"
    (other / "plan").mkdir(parents=True)
    (other / "plan/g.md").write_text("## goal: unrelated\n- [ ] 1. other | gate: true\n")
    assert learning(other)["observations"] == []


def test_new_failure_does_not_rewrite_a_completed_pair(project):
    root, _ = project
    from agent_harness.workgraph.gate_learning import inspect, observe
    observe(root, "g", 1, "same command", 1, "first failure")
    observe(root, "g", 1, "same command", 0, "first success")
    previous = inspect(root, "g")["observations"][0]
    observe(root, "g", 1, "same command", 8, "another failure")
    pending = inspect(root, "g")["observations"][0]
    assert pending["count"] == 1 and pending["new_failure_pending"] is True
    assert pending["failure_output_sha256"] == previous["failure_output_sha256"]
    observe(root, "g", 1, "same command", 0, "another success")
    final = inspect(root, "g")["observations"][0]
    assert final["count"] == 2 and final["failure_code"] == 8
    assert final["new_failure_pending"] is False


def test_changed_definition_cannot_reactivate_an_old_pending_failure(project):
    root, _ = project
    from agent_harness.workgraph.gate_learning import inspect, observe
    observe(root, "g", 1, "old", 1, "failure")
    observe(root, "g", 1, "new", 0, "different acceptance")
    observe(root, "g", 1, "old", 0, "old acceptance restored")
    assert inspect(root, "g")["observations"] == []


def versioned(root):
    (root / "request.txt").write_text("expected")
    (root / "result.txt").write_text("wrong")
    (root / "check.py").write_text(
        "from pathlib import Path\nassert Path('result.txt').read_text() == 'expected'\n")
    (root / "plan/g.md").write_text(
        "## goal: preserve approved acceptance\n## versions: v1\n"
        "- [ ] 1. required output | inputs: request.txt | outputs: result.txt "
        "| checks: check.py | ctx: result.txt | gate: python3 check.py\n")


@pytest.mark.parametrize("change", ["oracle", "policy", "requirement", "requirement-file"])
def test_same_command_cannot_borrow_a_failure_from_changed_bound_acceptance(project, change):
    root, engine = project
    versioned(root)
    assert gate(engine) == 1
    path = root / "plan/g.md"
    if change == "oracle":
        (root / "check.py").write_text("assert True  # different, easier oracle\n")
    elif change == "requirement-file":
        (root / "request.txt").write_text("different approved input")
        (root / "result.txt").write_text("expected")
    else:
        (root / "result.txt").write_text("expected")
        path.write_text(path.read_text().replace(
            "preserve approved acceptance" if change == "policy" else "required output",
            "a different accepted requirement"))
    assert gate(engine) == 0
    assert learning(root)["observations"] == []


def test_implementation_only_repair_retains_declared_acceptance_binding(project):
    root, engine = project
    versioned(root)
    assert gate(engine) == 1
    (root / "result.txt").write_text("expected")
    assert gate(engine) == 0
    row = learning(root)["observations"][0]
    assert row["count"] == 1 and row["acceptance_scope"] == "DECLARED_ACCEPTANCE"
    assert gate(engine) == 0
    assert learning(root)["observations"][0]["count"] == 1


def test_legacy_outcome_cannot_claim_unchanged_acceptance_implementation(project):
    root, engine = project
    assert gate(engine) == 1
    (root / "ready").touch()
    assert gate(engine) == 0
    row = learning(root)["observations"][0]
    assert row["acceptance_scope"] == "COMMAND_ONLY_NOT_CHECK_EQUIVALENCE"


def test_a_judge_changing_during_a_failed_attempt_cannot_seed_a_bound_pair(project):
    root, engine = project
    versioned(root)
    judge = root / "check.py"
    original = ("from pathlib import Path\n"
                "if Path('alter').exists():\n"
                "    Path(__file__).write_text('assert True\\n')\n"
                "    raise SystemExit(1)\n"
                "assert Path('result.txt').read_text() == 'expected'\n")
    judge.write_text(original)
    (root / "alter").touch()
    assert gate(engine) == 1
    judge.write_text(original)
    (root / "alter").unlink()
    (root / "result.txt").write_text("expected")
    assert gate(engine) == 0
    assert learning(root)["observations"] == []
