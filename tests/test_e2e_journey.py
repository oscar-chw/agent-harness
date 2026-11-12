"""tests for the e2e journey assembly (scripts/e2e_journey.py) — plan node 12.

Hermetic: journeys are SYNTHESISED step lists pushed through the real
receipt/verify path; the real journeys run once, hash-bound, via the node-12
gate (check_e2e.py). Unmarked: part of the fast unit tier.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import e2e_journey as ej


def fake_journeys(all_ok=True):
    out = []
    for name in ej.EXPECTED_JOURNEYS:
        ok = all_ok or name != "kb_honesty"
        out.append({"journey": name, "ok": ok,
                    "steps": [{"step": "s1", "ok": True, "detail": ""},
                              {"step": "s2", "ok": ok, "detail": ""}]})
    return out


def test_expected_surface_is_pinned():
    assert ej.EXPECTED_JOURNEYS == ("fact_memory", "page_memory", "kb_honesty", "plan_lifecycle")
    assert set(ej.EXPECTED_NOT_RUN) == {"session_search", "skill_promotion"}
    assert all(ej.EXPECTED_NOT_RUN.values())  # every NOT_RUN carries a reason


def test_honest_pass_receipt_verifies():
    receipt = ej.make_receipt(fake_journeys(), kind="self-test")
    ok, errors = ej.verify_receipt(receipt)
    assert receipt["verdict"] == "PASS" and ok and not errors
    assert receipt["schema"] == "harness.e2e-journey/v1"


def test_failed_step_fails_the_verdict():
    receipt = ej.make_receipt(fake_journeys(all_ok=False), kind="self-test")
    assert receipt["verdict"] == "FAIL"
    ok, errors = ej.verify_receipt(receipt)  # an honest FAIL is faithful evidence
    assert ok and not errors


def test_missing_journey_fails_closed():
    journeys = fake_journeys()[:3]  # plan_lifecycle silently dropped
    receipt = ej.make_receipt(journeys, kind="self-test")
    assert receipt["verdict"] == "FAIL"  # make_receipt requires the full set
    ok, errors = ej.verify_receipt(receipt)
    assert not ok and any("journey set" in e for e in errors)


def test_crude_tamper_is_refused_by_self_hash():
    receipt = ej.make_receipt(fake_journeys(), kind="self-test")
    receipt["journeys"][0]["steps"][0]["ok"] = False
    ok, errors = ej.verify_receipt(receipt)
    assert not ok and any("self-hash" in e for e in errors)


def test_rehashed_lying_verdict_is_refused():
    receipt = ej.make_receipt(fake_journeys(all_ok=False), kind="self-test")
    forged = ej._rehashed(receipt, verdict="PASS")  # valid hash over a lie
    ok, errors = ej.verify_receipt(forged)
    assert not ok and any("verdict" in e for e in errors)


def test_rehashed_dropped_journey_is_refused():
    receipt = ej.make_receipt(fake_journeys(), kind="self-test")
    forged = ej._rehashed(receipt, journeys=receipt["journeys"][:3])
    ok, errors = ej.verify_receipt(forged)
    assert not ok and any("journey set" in e for e in errors)


def test_reasonless_not_run_is_refused():
    receipt = ej.make_receipt(fake_journeys(), kind="self-test")
    naughty = [dict(n, reason="") for n in receipt["not_run"]]
    forged = ej._rehashed(receipt, not_run=naughty)
    ok, errors = ej.verify_receipt(forged)
    assert not ok and any("reason" in e for e in errors)


def test_journey_wrapper_turns_exceptions_into_failures(tmp_path):
    def boom(_tmp):
        raise RuntimeError("synthetic explosion")
    j = ej._journey("fact_memory", boom, tmp_path)
    assert j["ok"] is False
    assert j["steps"][0]["step"] == "unhandled-exception"
    assert "synthetic explosion" in j["steps"][0]["detail"]


def test_step_helper_coerces_truthiness():
    s = ej._step("x", 1, "d")
    assert s == {"step": "x", "ok": True, "detail": "d"}
