"""tests for the perf tier probe (scripts/perf_probe.py) — plan v3-eval-pipeline node 11.

Hermetic: every test feeds SYNTHETIC sample sets through the real evaluate /
receipt / verify path, so the gate runs in seconds and never launches the real
probes. The real probes run once, hash-bound, via the plan's node-11 gate
(check_perf.py). Left unmarked: this file is part of the fast unit tier.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import perf_probe


def green_probes():
    return {p: {"n": 50, "min_ms": 0.1, "p50_ms": limit / 4, "p95_ms": limit / 2,
                "max_ms": limit, "mean_ms": limit / 3}
            for p, limit in perf_probe.THRESHOLDS_P95_MS.items()}


def test_thresholds_cover_exactly_the_five_probes():
    assert set(perf_probe.THRESHOLDS_P95_MS) == {
        "kb_search", "guard_admission", "mcp_roundtrip",
        "runner_overhead_subprocess", "runner_overhead_inprocess"}
    assert all(isinstance(v, float) and v > 0 for v in perf_probe.THRESHOLDS_P95_MS.values())


def test_stats_percentiles_on_known_data():
    st = perf_probe.stats(list(range(1, 101)))  # 1..100 ms
    assert st["n"] == 100 and st["min_ms"] == 1 and st["max_ms"] == 100
    assert st["p50_ms"] == 50.5
    assert st["p95_ms"] == 95  # s[int(0.95*100)-1] == s[94]
    assert st["mean_ms"] == 50.5


def test_evaluate_green_when_all_under_threshold():
    assert perf_probe.evaluate(green_probes()) == []


def test_evaluate_names_the_exceeded_probe():
    red = green_probes()
    red["guard_admission"]["p95_ms"] = perf_probe.THRESHOLDS_P95_MS["guard_admission"] * 5
    violations = perf_probe.evaluate(red)
    assert [v["probe"] for v in violations] == ["guard_admission"]
    assert violations[0]["threshold_p95_ms"] == perf_probe.THRESHOLDS_P95_MS["guard_admission"]


def test_evaluate_is_fail_closed_on_missing_probe():
    incomplete = green_probes()
    del incomplete["mcp_roundtrip"]
    violations = perf_probe.evaluate(incomplete)
    assert any(v["probe"] == "mcp_roundtrip" and "missing" in v.get("error", "")
               for v in violations)


def test_evaluate_is_fail_closed_on_missing_p95():
    broken = green_probes()
    del broken["kb_search"]["p95_ms"]
    assert any(v["probe"] == "kb_search" for v in perf_probe.evaluate(broken))


def test_honest_pass_receipt_verifies():
    receipt = perf_probe.make_receipt(green_probes(), [], kind="self-test")
    ok, errors = perf_probe.verify_receipt(receipt)
    assert ok and not errors
    assert receipt["schema"] == "harness.perf-probe/v1"
    assert receipt["verdict"] == "PASS"


def test_honest_fail_receipt_verifies_as_faithful_evidence():
    red = green_probes()
    red["kb_search"]["p95_ms"] = perf_probe.THRESHOLDS_P95_MS["kb_search"] * 10
    violations = perf_probe.evaluate(red)
    receipt = perf_probe.make_receipt(red, violations, kind="self-test")
    ok, errors = perf_probe.verify_receipt(receipt)
    assert receipt["verdict"] == "FAIL"
    assert ok and not errors  # FAIL recorded honestly is faithful, not forgery


def test_crude_tamper_after_hashing_is_refused():
    receipt = perf_probe.make_receipt(green_probes(), [], kind="self-test")
    receipt["probes"]["mcp_roundtrip"]["p95_ms"] = 0.001
    ok, errors = perf_probe.verify_receipt(receipt)
    assert not ok and any("self-hash" in e for e in errors)


def test_rehashed_lying_verdict_is_refused():
    red = green_probes()
    red["kb_search"]["p95_ms"] = perf_probe.THRESHOLDS_P95_MS["kb_search"] * 10
    receipt = perf_probe.make_receipt(red, perf_probe.evaluate(red), kind="self-test")
    forged = perf_probe._rehashed(receipt, verdict="PASS")  # forgery with a VALID hash
    ok, errors = perf_probe.verify_receipt(forged)
    assert not ok and any("verdict" in e for e in errors)  # semantics, not the hash, catch it


def test_rehashed_relaxed_thresholds_are_refused():
    receipt = perf_probe.make_receipt(green_probes(), [], kind="self-test")
    relaxed = dict(perf_probe.THRESHOLDS_P95_MS, kb_search=1e9)
    forged = perf_probe._rehashed(receipt, thresholds_p95_ms=relaxed)
    ok, errors = perf_probe.verify_receipt(forged)
    assert not ok and any("threshold" in e for e in errors)


def test_verify_rejects_unreadable_and_wrong_schema(tmp_path):
    ok, _ = perf_probe.verify_receipt(tmp_path / "nope.json")
    assert not ok
    bad = perf_probe.make_receipt(green_probes(), [], kind="self-test")
    forged = perf_probe._rehashed(bad, schema="harness.perf-probe/v0")
    ok, errors = perf_probe.verify_receipt(forged)
    assert not ok and any("schema" in e for e in errors)


def test_self_test_function_demonstrates_both_directions(capsys):
    assert perf_probe.self_test() is True
    out = capsys.readouterr().out
    assert "green:" in out and "red:" in out and "FAILED" not in out
