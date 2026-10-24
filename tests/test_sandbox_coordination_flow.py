from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from examples.sandbox_parts.coordination_flow import run


def test_coordination_flow_uses_real_operational_state_and_recovers(tmp_path):
    result = run(tmp_path)

    assert result["section"] == "coordination"
    assert result["status"] == "PASS"
    checks = {check["name"]: check for check in result["checks"]}
    assert {check["status"] for check in checks.values()} == {"PASS"}
    assert {
        "single_concurrent_claim",
        "live_lease_unverified",
        "expired_lease_reclaimed",
        "stale_fence_refused",
        "cold_snapshot_recovers_blocked_checkpoint",
        "fresh_cli_process_refuses_live_claim",
        "fresh_cli_snapshot_reads_durable_state",
    } <= checks.keys()
    assert "winner=" in checks["single_concurrent_claim"]["evidence"]
    assert "leased_unverified" in checks["live_lease_unverified"]["evidence"]
    assert "fence=2" in checks["expired_lease_reclaimed"]["evidence"]
    assert "refused" in checks["stale_fence_refused"]["evidence"]
    recovered = checks["cold_snapshot_recovers_blocked_checkpoint"]["evidence"]
    assert all(value in recovered for value in ("goal=", "checkpoint=", "blocked_on="))
    assert "exit=2" in checks["fresh_cli_process_refuses_live_claim"]["evidence"]
    assert "coordination" in checks["fresh_cli_snapshot_reads_durable_state"]["evidence"]
