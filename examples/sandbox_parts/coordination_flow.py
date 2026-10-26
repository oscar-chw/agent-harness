"""Bounded CPU-only demonstration of SQLite ownership and cold recovery."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

from agent_harness.operational_state import Conflict, OperationalState


def run(root: Path) -> dict:
    """Race two independent ledgers, recover the fence, and read it cold via CLI."""
    root = Path(root).resolve(strict=True)
    (root / ".git").mkdir(exist_ok=True)
    home = root / "harness-home"
    checkpoint = root / "checkpoint.md"
    checkpoint.write_text("checkpoint: resume coordination demo\n", encoding="utf-8")
    now = [1000.0]
    clock = lambda: now[0]
    first = OperationalState(home, root, clock=clock)
    second = OperationalState(home, root, clock=clock)
    value = {"goal": "demonstrate fenced ownership", "checkpoint": "checkpoint.md",
             "next": "recover after lease expiry"}
    first.put("coordination", value, expected=0, request_id="seed")

    barrier = threading.Barrier(2)
    outcomes = []

    def attempt(store, request_id):
        barrier.wait(timeout=5)
        try:
            outcomes.append(("won", store.claim("coordination", expected=1,
                                                  request_id=request_id, ttl=10)))
        except Conflict as error:
            outcomes.append(("lost", str(error)))

    workers = [threading.Thread(target=attempt, args=(first, "owner-a")),
               threading.Thread(target=attempt, args=(second, "owner-b"))]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=10)
    if any(worker.is_alive() for worker in workers):
        raise RuntimeError("concurrent claim did not finish")
    winners = [item[1] for item in outcomes if item[0] == "won"]
    if len(winners) != 1 or len(outcomes) != 2:
        raise AssertionError("SQLite claim race did not produce exactly one owner")
    old = winners[0]
    checks = [{"name": "single_concurrent_claim", "status": "PASS",
               "evidence": f"winner=fence {old['fence']}; owners={sum(x[0] == 'won' for x in outcomes)}"}]

    live = second.snapshot()["tasks"][0]
    if live["activity"] != "leased_unverified":
        raise AssertionError("live lease was not reported as unverified")
    checks.append({"name": "live_lease_unverified", "status": "PASS",
                   "evidence": f"activity={live['activity']}; until={live['until']}"})

    now[0] = old["until"] + 1
    replacement = second.claim("coordination", expected=2, request_id="owner-recovery", ttl=10)
    if replacement["fence"] != old["fence"] + 1:
        raise AssertionError("expired lease did not advance the fencing token")
    checks.append({"name": "expired_lease_reclaimed", "status": "PASS",
                   "evidence": f"fence={replacement['fence']}; prior={old['fence']}"})

    try:
        first.release("coordination", expected=3, request_id="stale-release",
                      token=old["token"], fence=old["fence"])
    except Conflict as error:
        stale = str(error)
    else:
        raise AssertionError("stale owner token was accepted")
    checks.append({"name": "stale_fence_refused", "status": "PASS",
                   "evidence": f"refused={stale}"})
    second.release("coordination", expected=3, request_id="release-recovery",
                   token=replacement["token"], fence=replacement["fence"])
    final_value = {**value, "blocked_on": "awaiting human review of recovered checkpoint"}
    first.put("coordination", final_value, expected=4, request_id="record-blocker")

    cold = OperationalState(home, root, clock=clock).snapshot()["tasks"][0]
    durable = cold["value"]
    if (durable.get("goal") != value["goal"] or durable.get("checkpoint") != "checkpoint.md"
            or durable.get("blocked_on") != final_value["blocked_on"]
            or cold["checkpoint_status"] != "present"):
        raise AssertionError("cold snapshot lost the goal, checkpoint, or block reason")
    checks.append({"name": "cold_snapshot_recovers_blocked_checkpoint", "status": "PASS",
                   "evidence": f"goal={durable['goal']}; checkpoint={durable['checkpoint']}"
                               f"({cold['checkpoint_status']}); blocked_on={durable['blocked_on']}"})

    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"),
               HARNESS_HOME=str(home), HOME=str(home))

    def cli(action, request=None):
        process = subprocess.run([sys.executable, "-m", "agent_harness.cli", "op", action],
                                 cwd=root, env=env,
                                 input=json.dumps(request) if request is not None else None,
                                 text=True, capture_output=True, timeout=10, check=False)
        return process

    seeded = cli("put", {"task": "cli-probe", "value": {"goal": "verify CLI process boundary",
                                                         "checkpoint": "checkpoint.md", "next": "snapshot"},
                         "expected": 0, "request_id": "cli-seed"})
    if seeded.returncode != 0:
        raise RuntimeError(f"CLI put failed ({seeded.returncode}): {seeded.stderr.strip()}")
    claimed = cli("claim", {"task": "cli-probe", "expected": 1, "request_id": "cli-owner", "ttl": 60})
    if claimed.returncode != 0:
        raise RuntimeError(f"CLI claim failed ({claimed.returncode}): {claimed.stderr.strip()}")
    refused = cli("claim", {"task": "cli-probe", "expected": 2, "request_id": "cli-contender", "ttl": 60})
    if refused.returncode != 2 or "lease" not in refused.stderr:
        raise AssertionError("fresh CLI process did not refuse a live claim")
    checks.append({"name": "fresh_cli_process_refuses_live_claim", "status": "PASS",
                   "evidence": f"command=python -m agent_harness.cli op claim; exit={refused.returncode}; "
                               f"reason={refused.stderr.strip()}"})

    snapshot = cli("snapshot")
    if snapshot.returncode != 0:
        raise RuntimeError(f"CLI cold snapshot failed ({snapshot.returncode}): {snapshot.stderr.strip()}")
    rows = json.loads(snapshot.stdout)["tasks"]
    recovered_cli = next((row for row in rows if row["task"] == "coordination"), None)
    if recovered_cli is None or recovered_cli["value"] != final_value:
        raise AssertionError("fresh CLI snapshot did not recover durable coordination state")
    checks.append({"name": "fresh_cli_snapshot_reads_durable_state", "status": "PASS",
                   "evidence": f"command=python -m agent_harness.cli op snapshot; "
                               f"task={recovered_cli['task']}; cursor={json.loads(snapshot.stdout)['cursor']}"})
    return {"section": "coordination", "checks": checks,
            "status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL"}
