"""Permission recovery must retain the goal without re-executing a denied action.

Workers are local stubs; gates use harmless disposable files. No native login,
permission configuration, live hook or model call is involved.
"""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "src/agent_harness/workgraph/plan.py"


def engine():
    spec = importlib.util.spec_from_file_location("permission_recovery_fixture", ENGINE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "plan").mkdir()
    (tmp_path / "home").mkdir()
    (tmp_path / "stub").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("HARNESS_HOME", str(tmp_path / "home/.agent-harness"))
    monkeypatch.setenv("PLAN_RUNNER", "claude")
    monkeypatch.setenv("PLAN_QUIET", "1")
    monkeypatch.delenv("PLAN_DIR", raising=False)
    worker = tmp_path / "stub/claude"
    worker.write_text(f"#!{sys.executable}\n" + '''import json, re, sys
from pathlib import Path
prompt = sys.argv[sys.argv.index('-p') + 1]
node = re.search(r'^NODE (\\d+):', prompt, re.M).group(1)
with Path('calls').open('a') as out:
    out.write(node + '\\n')
if node != '1' or Path('finish-one').exists():
    Path('done-' + node).touch()
failed = node == '1' and Path('worker-error').exists()
print(json.dumps({'type': 'result', 'subtype': 'error_during_execution' if failed else 'success',
                  'is_error': failed,
                  'result': 'local fixture finished',
                  'permission_denials': [{'tool_name': 'Bash'}] if node == '1' else []}))
''')
    worker.chmod(0o700)
    monkeypatch.setenv("PATH", str(worker.parent) + os.pathsep + os.environ["PATH"])
    return tmp_path


def graph(root, lines):
    (root / "plan/g.md").write_text("## goal: preserve the authorized goal\n" + lines)


def run(root, *args):
    return subprocess.run([sys.executable, "-B", str(ENGINE), *args],
                          cwd=root, capture_output=True, text=True, timeout=40)


def test_denied_unfinished_node_is_held_once_while_independent_chain_finishes(project):
    graph(project, "- [ ] 1. blocked work | gate: test -f done-1\n"
          "- [ ] 2. independent work | gate: test -f done-2\n"
          "- [ ] 3. blocked child | needs: 1 | gate: test -f done-3\n"
          "- [ ] 4. independent child | needs: 2 | gate: test -f done-4\n")
    result = run(project, "run", "g", "--workers", "1", "--max-rounds", "6")
    assert result.returncode == 1, result.stdout + result.stderr
    assert (project / "calls").read_text().splitlines() == ["1", "2", "4"]
    text = (project / "plan/g.md").read_text()
    assert "hold: permission" in text
    assert "- [x] 2." in text and "- [x] 4." in text
    assert "- [ ] 1." in text and "- [ ] 3." in text
    assert "ALL DONE" not in result.stdout and "HELD 1." in result.stdout
    # A cold runner must not turn the hold into another paid/quota-consuming try.
    again = run(project, "run", "g", "--workers", "2", "--max-rounds", "3")
    assert again.returncode == 1
    assert (project / "calls").read_text().splitlines() == ["1", "2", "4"]
    status = run(project, "status", "g")
    assert "permission" in status.stdout.lower()
    assert "irreversible" not in status.stdout.lower()
    packet = run(project, "context", "g", "1")
    assert "HELD:" in packet.stdout and "permission" in packet.stdout
    resume = run(project, "resume")
    assert "permission" in resume.stdout.lower()
    claim = run(project, "claim", "g", "--id", "1")
    assert claim.returncode != 0
    assert "held" in claim.stderr.lower()


def test_incidental_worker_denial_does_not_invalidate_a_real_passing_gate(project):
    graph(project, "- [ ] 1. completed safely | gate: test -f done-1\n")
    (project / "finish-one").touch()
    result = run(project, "run", "g", "--workers", "1", "--max-rounds", "3")
    assert result.returncode == 0, result.stdout + result.stderr
    text = (project / "plan/g.md").read_text()
    assert "- [x] 1." in text and "hold:" not in text
    assert "permission denial" in text
    assert (project / "calls").read_text().splitlines() == ["1"]


def test_guard_refusal_is_not_a_test_failure_and_blocks_direct_retry(project, monkeypatch):
    graph(project, "- [ ] 1. harmless canary | gate: touch gate-ran\n")
    module = engine()
    monkeypatch.setattr(module, "guard_refusal", lambda *_: "fixture: requires native approval")
    args = SimpleNamespace(slug="g", id=1, attended=False, owner=None, force=False)
    assert module.cmd_gate(args) != 0
    assert not (project / "gate-ran").exists()
    text = (project / "plan/g.md").read_text()
    assert "hold: permission" in text and "NOT_RUN" in text
    _, _, nodes, _, _ = module.load("g")
    assert module.attempts(nodes[1]) == []
    # Neither --attended nor --force authorizes a denied effect or clears its hold.
    with pytest.raises(SystemExit):
        module.cmd_gate(SimpleNamespace(slug="g", id=1, attended=True, force=True, owner=None))
    assert not (project / "gate-ran").exists()


def test_existing_permission_hold_is_visible_and_keeps_independent_work_ready(project):
    graph(project, "- [ ] 1. held | hold: permission | gate: touch gate-ran\n"
          "- [ ] 2. independent | gate: test -f done-2\n")
    result = run(project, "run", "g", "--workers", "1", "--max-rounds", "3")
    assert result.returncode == 1, result.stdout + result.stderr
    assert (project / "calls").read_text().splitlines() == ["2"]
    assert not (project / "gate-ran").exists()
    ready = run(project, "ready", "g")
    assert "permission" in ready.stdout.lower()
    assert "irreversible" not in ready.stdout.lower()


def test_a_hold_field_buried_in_the_gate_is_a_malformed_contract(project):
    graph(project, "- [ ] 1. wrong field order | gate: touch gate-ran | hold: permission\n")
    result = run(project, "run", "g", "--workers", "1")
    assert result.returncode == 2, result.stdout + result.stderr
    assert "buried" in result.stdout
    assert not (project / "gate-ran").exists() and not (project / "calls").exists()


def test_dispatch_denial_is_held_without_fabricated_gate_evidence(project):
    graph(project, "- [ ] 1. worker cannot proceed | gate: touch gate-ran\n"
          "- [ ] 2. independent work | gate: test -f done-2\n")
    (project / "worker-error").touch()
    result = run(project, "run", "g", "--workers", "1", "--max-rounds", "4")
    assert result.returncode == 1, result.stdout + result.stderr
    assert (project / "calls").read_text().splitlines() == ["1", "2"]
    assert not (project / "gate-ran").exists()
    _, _, nodes, _, _ = engine().load("g")
    assert nodes[1]["fields"].get("hold") == "permission"
    assert engine().attempts(nodes[1]) == []


def test_a_gate_crash_does_not_hide_the_permission_hold(project, monkeypatch):
    graph(project, "- [ ] 1. blocked work | gate: touch gate-ran\n"
          "- [ ] 2. independent work | gate: test -f done-2\n")
    module = engine()
    original = module.cmd_gate

    def crashed_gate(args):
        if args.id == 1:
            raise OSError("fixture judge unavailable")
        return original(args)

    monkeypatch.setattr(module, "cmd_gate", crashed_gate)
    args = SimpleNamespace(slug="g", workers=1, max_rounds=4, timeout=20, model=None,
                           dry_run=False, accept_risks=True)
    assert module.cmd_run(args) == 1
    assert (project / "calls").read_text().splitlines() == ["1", "2"]
    text = (project / "plan/g.md").read_text()
    assert "fixture judge unavailable" in text and "hold: permission" in text
    _, _, nodes, _, _ = module.load("g")
    assert module.attempts(nodes[1]) == []


@pytest.mark.parametrize("versioned", [False, True])
def test_gate_guard_hold_survives_reconciliation_and_is_not_auto_cleared(project, monkeypatch, versioned):
    marker = "## versions: v1\n" if versioned else ""
    graph(project, marker + "- [ ] 1. harmless held gate | gate: touch gate-ran\n"
          "- [ ] 2. independent work | gate: test -f done-2\n")
    module = engine()
    monkeypatch.setattr(module, "guard_refusal",
                        lambda command, root: "fixture native refusal" if "gate-ran" in command else None)
    args = SimpleNamespace(slug="g", workers=1, max_rounds=4, timeout=20, model=None,
                           dry_run=False, accept_risks=True)
    assert module.cmd_run(args) == 1
    assert (project / "calls").read_text().splitlines() == ["1", "2"]
    assert not (project / "gate-ran").exists()
    _, _, nodes, _, _ = module.load("g")
    assert nodes[1]["fields"].get("hold") == "permission"
    assert module.attempts(nodes[1]) == []
    # Even if a later preflight would allow the command, resuming alone is not
    # proof that the original authority problem has been resolved.
    monkeypatch.setattr(module, "guard_refusal", lambda *_: None)
    assert module.cmd_run(args) == 1
    assert (project / "calls").read_text().splitlines() == ["1", "2"]
    assert not (project / "gate-ran").exists()
