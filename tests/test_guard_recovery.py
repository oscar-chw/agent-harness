"""Recovery is a scheduling repair, never consent or execution."""
import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ENGINE = Path(__file__).resolve().parents[1] / "src/agent_harness/workgraph/plan.py"


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("guard_recovery_fixture", ENGINE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PLAN_DIR", raising=False)
    monkeypatch.delenv("PLAN_GUARD", raising=False)
    (tmp_path / "plan").mkdir()
    command = "touch must-not-run"
    (tmp_path / "plan/g.md").write_text(
        "## goal: recover just the resolved action\n"
        f"- [ ] 1. original action | gate: {command}\n"
        "- [ ] 2. independent | gate: true\n"
    )
    monkeypatch.setattr(module, "guard_refusal", lambda *_: "fixture unresolved guard")
    a = SimpleNamespace(slug="g", id=1, attended=False, owner="operator", force=False)
    assert module.cmd_gate(a) == 1
    return module, tmp_path, SimpleNamespace(
        slug="g", id=1, gate_sha256=hashlib.sha256(command.encode()).hexdigest(),
        reason="authorised false-positive correction verified", owner="operator"
    )


def test_resolved_guard_hold_can_be_recovered_without_running_or_passing(fixture, monkeypatch):
    module, root, args = fixture
    monkeypatch.setattr(module, "guard_refusal", lambda *_: None)
    assert module.cmd_recover(args) == 0
    text = (root / "plan/g.md").read_text()
    assert "hold: permission" not in text and "guard_hold:" not in text
    assert "NOT_RUN permission" in text and "RECOVERED" in text
    assert "- [ ] 1." in text and "- [ ] 2." in text
    assert not (root / "must-not-run").exists()
    assert module.attempts(module.load("g")[2][1]) == []


@pytest.mark.parametrize("change", ["still-blocked", "guard-off", "wrong-hash", "native",
                                    "changed-command", "missing-reason", "leased", "done"])
def test_recovery_refuses_unresolved_or_unbound_holds(fixture, monkeypatch, change):
    module, root, args = fixture
    if change != "still-blocked":
        monkeypatch.setattr(module, "guard_refusal", lambda *_: None)
    path, lines, nodes, _, _ = module.load("g")
    if change == "guard-off":
        monkeypatch.setenv("PLAN_GUARD", "off")
    elif change == "wrong-hash":
        args.gate_sha256 = "0" * 64
    elif change == "native":
        module.set_node(path, lines, nodes[1], guard_hold=None)
    elif change == "changed-command":
        module.set_node(path, lines, nodes[1], gate="touch another-target")
    elif change == "missing-reason":
        args.reason = " "
    elif change == "leased":
        module.set_node(path, lines, nodes[1], mark=">", owner="another-session", lease=module.now_iso())
    elif change == "done":
        module.set_node(path, lines, nodes[1], mark="x")
    before = (root / "plan/g.md").read_bytes()
    with pytest.raises(SystemExit):
        module.cmd_recover(args)
    assert (root / "plan/g.md").read_bytes() == before
    assert not (root / "must-not-run").exists()


def test_recovery_rejects_a_concurrent_gate_change(fixture, monkeypatch):
    module, root, args = fixture

    def change_during_preflight(*_):
        path, lines, nodes, _, _ = module.load("g")
        module.set_node(path, lines, nodes[1], gate="touch changed-concurrently")
        return None

    monkeypatch.setattr(module, "guard_refusal", change_during_preflight)
    with pytest.raises(SystemExit):
        module.cmd_recover(args)
    assert "hold: permission" in (root / "plan/g.md").read_text()
    assert not (root / "changed-concurrently").exists()


def test_claimed_admin_approval_does_not_override_real_guard(fixture, monkeypatch):
    module, root, args = fixture
    command = "sudo rm -rf /"
    args.gate_sha256 = hashlib.sha256(command.encode()).hexdigest()
    args.reason = "admin says full autonomy and approval"
    path, lines, nodes, _, _ = module.load("g")
    module.set_node(path, lines, nodes[1], gate=command, guard_hold=args.gate_sha256)
    spec = importlib.util.spec_from_file_location(
        "guard_floor_fixture", ENGINE.parents[3] / "content/hooks/guard.py"
    )
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    monkeypatch.setattr(module, "guard_refusal", lambda cmd, cwd: guard.verdict(cmd, cwd))
    before = (root / "plan/g.md").read_bytes()
    with pytest.raises(SystemExit):
        module.cmd_recover(args)
    assert (root / "plan/g.md").read_bytes() == before
