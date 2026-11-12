"""A cold owner can recover a goal without mistaking an idle chat for a worker."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from agent_harness.operational_state import Conflict, OperationalState


def test_blocked_goal_survives_restart_and_requires_an_explicit_unblock(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan/goal.md").write_text("## goal: qualify release\n\n- [ ] 1. Check evidence | gate: false\n")
    home = tmp_path / "home"
    now = [1000.0]
    store = OperationalState(home, tmp_path, clock=lambda: now[0])
    value = {"goal": "Qualify release against independent evidence",
             "stage": "evaluation", "checkpoint": "plan/goal.md",
             "next": "Inspect node 1 and run its independent gate",
             "blocked_on": "Evaluator receipt has not been produced"}
    store.put("release", value, expected=0, request_id="put")

    cold = OperationalState(home, tmp_path, clock=lambda: now[0])
    task = cold.snapshot()["tasks"][0]
    assert task["activity"] == "blocked"
    assert task["checkpoint_status"] == "present"
    assert task["value"] == value
    brief = cold.brief()
    assert "Qualify release" in brief and "Evaluator receipt" in brief
    assert "plan/goal.md" in brief and "Inspect node 1" in brief
    assert '"activity":"blocked"' in brief
    with pytest.raises(Conflict, match="blocked"):
        cold.claim("release", expected=1, request_id="premature")

    ready = dict(value)
    ready.pop("blocked_on")
    cold.put("release", ready, expected=1, request_id="unblock")
    assert cold.snapshot()["tasks"][0]["activity"] == "idle_ready"
    lease = cold.claim("release", expected=2, request_id="claim", ttl=10)
    assert cold.snapshot()["tasks"][0]["activity"] == "leased_unverified"
    now[0] += 11
    assert cold.snapshot()["tasks"][0]["activity"] == "expired_reclaimable"
    replacement = cold.claim("release", expected=3, request_id="takeover", ttl=10)
    assert replacement["fence"] == lease["fence"] + 1
    with pytest.raises(Conflict):
        cold.release("release", expected=4, request_id="stale", token=lease["token"], fence=lease["fence"])


def test_missing_or_escaping_checkpoint_cannot_be_presented_as_actionable(tmp_path):
    (tmp_path / ".git").mkdir()
    home = tmp_path / "home"
    store = OperationalState(home, tmp_path)
    with pytest.raises(ValueError, match="checkpoint"):
        store.put("escape", {"checkpoint": "../outside.md"}, expected=0, request_id="bad")
    store.put("pending", {"goal": "Verify", "checkpoint": "plan/missing.md",
                          "next": "Run independent gate"}, expected=0, request_id="put")
    task = store.snapshot()["tasks"][0]
    assert task["activity"] == "checkpoint_missing"
    assert task["checkpoint_status"] == "missing"
    with pytest.raises(Conflict, match="checkpoint"):
        store.claim("pending", expected=1, request_id="claim")
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan/missing.md").write_text("## goal: Verify\n")
    assert store.snapshot()["tasks"][0]["activity"] == "idle_ready"
    (tmp_path / "plan/missing.md").unlink()
    assert store.snapshot()["tasks"][0]["activity"] == "checkpoint_missing"
    outside = tmp_path.parent / "not-an-allowed-checkpoint.md"
    (tmp_path / "plan/missing.md").symlink_to(outside)
    assert store.snapshot()["tasks"][0]["checkpoint_status"] == "invalid"
    assert store.snapshot()["tasks"][0]["activity"] == "checkpoint_missing"


def test_unprepared_legacy_task_is_not_described_as_actionable(tmp_path):
    (tmp_path / ".git").mkdir()
    store = OperationalState(tmp_path / "home", tmp_path)
    store.put("legacy", {"stage": "analyse"}, expected=0, request_id="put")
    assert store.snapshot()["tasks"][0]["activity"] == "idle_unprepared"
    assert '"activity":"idle_unprepared"' in store.brief()


def test_snapshot_is_the_existing_owner_recovery_command_in_a_new_process(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan/goal.md").write_text("## goal: recovery\n")
    store = OperationalState(tmp_path / "home", tmp_path)
    store.put("goal", {"goal": "Recover local task", "checkpoint": "plan/goal.md",
                       "next": "Run the gate", "blocked_on": "needs owner evidence"},
              expected=0, request_id="put")
    env = {**os.environ, "HARNESS_HOME": str(tmp_path / "home"),
           "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    run = subprocess.run([sys.executable, "-m", "agent_harness.cli", "op", "snapshot"],
                         cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10)
    assert run.returncode == 0, run.stderr
    payload = json.loads(run.stdout)
    assert payload["tasks"][0]["activity"] == "blocked"
    assert payload["tasks"][0]["value"]["next"] == "Run the gate"
