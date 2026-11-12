"""A route advances only on current, independently checked evidence."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent_harness import routing


CONTENT = Path(__file__).resolve().parents[1] / "content"
CONTEXT = "a" * 64
ARTIFACT = "b" * 64


def configured(tmp_path):
    codex = tmp_path / ".codex"
    codex.mkdir()
    codex.joinpath("models_cache.json").write_text(json.dumps({"models": [
        {"slug": "m-small", "visibility": "list", "priority": 1,
         "description": "fast", "supported_reasoning_levels": [{"effort": "low"}]},
        {"slug": "m-strong", "visibility": "list", "priority": 2,
         "description": "capable", "supported_reasoning_levels":
         [{"effort": "high"}, {"effort": "max"}]},
    ]}))
    profile = {"routing": {"ceiling": "max", "tiers": {
        "quick": {"codex": "m-small", "effort": "low"},
        "standard": {"codex": "m-strong", "effort": "high"},
        "deep": {"codex": "m-strong", "effort": "max"}},
        "progression": {"enabled": True, "selector": "declared",
                        "codex_steps": ["quick", "standard", "deep"]}}}
    return profile


def state(**changes):
    base = {"schema": "harness.route-state/v1", "provider": "codex",
            "context_sha256": CONTEXT, "check_id": "independent-test",
            "start_tier": "quick", "start_reason": "small task with a known check",
            "route_version": None, "attempts": [],
            "limits": {"max_attempts": 3, "max_total_tokens": 100,
                       "max_wall_seconds": 30, "max_tools": 5}}
    return {**base, **changes}


def attempt(decision, status="FAIL", *, context=CONTEXT, tokens=20, tools=1, seconds=2):
    return {"tier": decision["tier"], "route_version": decision["route_version"],
            "context_sha256": context, "artifact_sha256": ARTIFACT,
            "usage": {"input_tokens": tokens - 2, "output_tokens": 2,
                      "tool_calls": tools, "wall_seconds": seconds},
            "gate": {"schema": "harness.gate-result/v1", "status": status,
                     "check_id": "independent-test", "artifact_sha256": ARTIFACT}}


def task_state(**changes):
    record = state()
    record.pop("start_tier")
    record.pop("start_reason")
    record["task"] = {"schema": "harness.task-profile/v1", "kind": "implementation",
                      "impact": "normal", "uncertainty": "low"}
    return {**record, **changes}


def test_task_selector_starts_at_a_tier_supported_by_the_task_evidence(tmp_path):
    profile = configured(tmp_path)
    profile["routing"]["progression"]["selector"] = "task"
    mechanical = task_state(task={"schema": "harness.task-profile/v1", "kind": "mechanical",
                                  "impact": "low", "uncertainty": "low"})
    quick = routing.next_decision(CONTENT, tmp_path, mechanical,
                                  current_context_sha256=CONTEXT, profile=profile)
    assert (quick["decision"], quick["tier"], quick["model"], quick["effort"]) == (
        "DISPATCH", "quick", "m-small", "low")

    ordinary = routing.next_decision(CONTENT, tmp_path, task_state(),
                                     current_context_sha256=CONTEXT, profile=profile)
    assert (ordinary["decision"], ordinary["tier"], ordinary["model"], ordinary["effort"]) == (
        "DISPATCH", "standard", "m-strong", "high")
    assert ordinary["reason"] == "task_selected_start"

    for kind, impact, uncertainty in (("design", "low", "low"),
                                      ("review", "low", "low"),
                                      ("mechanical", "high", "low"),
                                      ("implementation", "normal", "high")):
        record = task_state(task={"schema": "harness.task-profile/v1", "kind": kind,
                                  "impact": impact, "uncertainty": uncertainty})
        deep = routing.next_decision(CONTENT, tmp_path, record,
                                     current_context_sha256=CONTEXT, profile=profile)
        assert (deep["decision"], deep["tier"], deep["model"], deep["effort"]) == (
            "DISPATCH", "deep", "m-strong", "max")


def test_task_selector_refuses_unknown_or_underqualified_task(tmp_path):
    profile = configured(tmp_path)
    profile["routing"]["progression"]["selector"] = "task"
    for record in (state(), task_state(task={"schema": "harness.task-profile/v1",
                                        "kind": "unknown", "impact": "low", "uncertainty": "low"}),
                   task_state(task={"schema": "harness.task-profile/v1", "kind": "implementation",
                                    "impact": "normal", "uncertainty": "low", "extra": "surprise"})):
        result = routing.next_decision(CONTENT, tmp_path, record,
                                       current_context_sha256=CONTEXT, profile=profile)
        assert result["decision"] == "HOLD" and result["reason"] == "invalid_task"
    low = routing.next_decision(CONTENT, tmp_path,
                                task_state(start_tier="quick", start_reason="save tokens"),
                                current_context_sha256=CONTEXT, profile=profile)
    assert (low["decision"], low["reason"]) == ("HOLD", "tier_underqualified")
    high = routing.next_decision(CONTENT, tmp_path,
                                 task_state(start_tier="deep", start_reason="sensitive API change"),
                                 current_context_sha256=CONTEXT, profile=profile)
    assert (high["decision"], high["tier"]) == ("DISPATCH", "deep")
    ceiling = routing.next_decision(CONTENT, tmp_path,
                                    task_state(task={"schema": "harness.task-profile/v1", "kind": "design",
                                                     "impact": "normal", "uncertainty": "high"},
                                               max_tier="standard"),
                                    current_context_sha256=CONTEXT, profile=profile)
    assert (ceiling["decision"], ceiling["reason"]) == ("HOLD", "tier_ceiling")
    profile["routing"]["progression"]["codex_steps"] = ["deep", "quick", "standard"]
    reordered = routing.next_decision(CONTENT, tmp_path, task_state(),
                                      current_context_sha256=CONTEXT, profile=profile)
    assert (reordered["decision"], reordered["reason"]) == ("HOLD", "invalid_policy")


def test_task_profile_is_bound_to_route_history_and_gate_result(tmp_path):
    profile = configured(tmp_path)
    profile["routing"]["progression"]["selector"] = "task"
    first = routing.next_decision(CONTENT, tmp_path, task_state(),
                                  current_context_sha256=CONTEXT, profile=profile)
    assert first["tier"] == "standard"
    history = task_state(route_version=first["route_version"], attempts=[attempt(first)])
    changed = routing.next_decision(CONTENT, tmp_path,
                                    {**history, "task": {"schema": "harness.task-profile/v1",
                                                         "kind": "mechanical", "impact": "low",
                                                         "uncertainty": "low"}},
                                    current_context_sha256=CONTEXT, profile=profile)
    assert (changed["decision"], changed["reason"]) == ("HOLD", "stale_route")
    escalated = routing.next_decision(CONTENT, tmp_path, history,
                                      current_context_sha256=CONTEXT, profile=profile)
    assert (escalated["decision"], escalated["tier"], escalated["reason"]) == (
        "DISPATCH", "deep", "independent_gate_failed")
    passed = routing.next_decision(CONTENT, tmp_path,
                                   task_state(route_version=first["route_version"],
                                              attempts=[attempt(first, status="PASS")]),
                                   current_context_sha256=CONTEXT,
                                   current_artifact_sha256=ARTIFACT, profile=profile)
    assert (passed["decision"], passed["reason"]) == ("STOP", "independent_gate_passed")


def test_minimum_start_escalates_only_after_independent_gate_failure(tmp_path):
    profile = configured(tmp_path)
    first = routing.next_decision(CONTENT, tmp_path, state(),
                                  current_context_sha256=CONTEXT, profile=profile)
    assert (first["decision"], first["tier"], first["model"], first["effort"]) == (
        "DISPATCH", "quick", "m-small", "low")
    assert first["reason"] == "configured_minimum_start"
    assert first["counters"] == {"attempts": 0, "total_tokens": 0,
                                 "tool_calls": 0, "wall_seconds": 0}
    second_state = state(route_version=first["route_version"], attempts=[attempt(first)])
    second = routing.next_decision(CONTENT, tmp_path, second_state,
                                   current_context_sha256=CONTEXT, profile=profile)
    assert (second["decision"], second["tier"], second["reason"]) == (
        "DISPATCH", "standard", "independent_gate_failed")
    third_state = state(route_version=first["route_version"],
                        attempts=[attempt(first), attempt(second)])
    third = routing.next_decision(CONTENT, tmp_path, third_state,
                                  current_context_sha256=CONTEXT, profile=profile)
    assert (third["tier"], third["model"], third["effort"]) == (
        "deep", "m-strong", "max")
    passed = routing.next_decision(CONTENT, tmp_path,
                                   state(route_version=first["route_version"],
                                         attempts=[attempt(first, status="PASS")]),
                                   current_context_sha256=CONTEXT,
                                   current_artifact_sha256=ARTIFACT, profile=profile)
    assert passed["decision"] == "STOP" and passed["reason"] == "independent_gate_passed"
    assert passed["tier"] is None


def test_justified_direct_high_start_and_ceiling(tmp_path):
    profile = configured(tmp_path)
    high = routing.next_decision(CONTENT, tmp_path,
                                 state(start_tier="deep", start_reason="high-stakes interface change"),
                                 current_context_sha256=CONTEXT, profile=profile)
    assert (high["decision"], high["tier"], high["reason"]) == (
        "DISPATCH", "deep", "declared_direct_start")
    unjustified = routing.next_decision(CONTENT, tmp_path,
                                        state(start_tier="deep", start_reason=""),
                                        current_context_sha256=CONTEXT, profile=profile)
    assert unjustified["decision"] == "HOLD"
    limited = routing.next_decision(CONTENT, tmp_path,
                                    state(start_tier="deep", start_reason="high-stakes interface change",
                                          max_tier="standard"),
                                    current_context_sha256=CONTEXT, profile=profile)
    assert limited["decision"] == "HOLD" and limited["reason"] == "tier_ceiling"
    profile["routing"]["ceiling"] = "high"
    effort_limited = routing.next_decision(
        CONTENT, tmp_path, state(start_tier="deep", start_reason="high-stakes interface change"),
        current_context_sha256=CONTEXT, profile=profile)
    assert effort_limited["decision"] == "HOLD" and effort_limited["reason"] == "tier_ceiling"


def test_public_template_does_not_activate_strict_progression(tmp_path):
    configured(tmp_path)
    default = routing.next_decision(CONTENT, tmp_path, state(),
                                    current_context_sha256=CONTEXT)
    assert default["decision"] == "HOLD" and default["reason"] == "route_disabled"


def test_unavailable_or_unsupported_pair_never_falls_back(tmp_path):
    profile = configured(tmp_path)
    profile["routing"]["tiers"]["quick"]["codex"] = "not-in-cache"
    unknown = routing.next_decision(CONTENT, tmp_path, state(),
                                    current_context_sha256=CONTEXT, profile=profile)
    assert unknown["decision"] == "HOLD" and unknown["reason"] == "model_unavailable"
    profile["routing"]["tiers"]["quick"].update(codex="m-small", effort="max")
    unsupported = routing.next_decision(CONTENT, tmp_path, state(),
                                        current_context_sha256=CONTEXT, profile=profile)
    assert unsupported["decision"] == "HOLD" and unsupported["reason"] == "pair_unsupported"
    profile["routing"]["tiers"]["quick"].update(codex="fast", effort="low")
    cache = json.loads((tmp_path / ".codex/models_cache.json").read_text())
    for model in cache["models"]:
        model["description"] = "general purpose"
    (tmp_path / ".codex/models_cache.json").write_text(json.dumps(cache))
    (tmp_path / ".codex/config.toml").write_text('model = "m-strong"\n')
    fallback = routing.next_decision(CONTENT, tmp_path, state(),
                                     current_context_sha256=CONTEXT, profile=profile)
    assert fallback["decision"] == "HOLD" and fallback["reason"] == "model_unavailable"


def test_stale_unknown_and_exhausted_budget_hold_before_dispatch(tmp_path):
    profile = configured(tmp_path)
    first = routing.next_decision(CONTENT, tmp_path, state(),
                                  current_context_sha256=CONTEXT, profile=profile)
    stale = routing.next_decision(CONTENT, tmp_path, state(),
                                  current_context_sha256="c" * 64, profile=profile)
    assert stale["decision"] == "HOLD" and stale["reason"] == "stale_context"
    no_gate = attempt(first)
    no_gate.pop("gate")
    unknown = routing.next_decision(CONTENT, tmp_path,
                                    state(route_version=first["route_version"], attempts=[no_gate]),
                                    current_context_sha256=CONTEXT, profile=profile)
    assert unknown["decision"] == "HOLD" and unknown["reason"] == "unknown_outcome"
    over = routing.next_decision(CONTENT, tmp_path,
                                 state(route_version=first["route_version"],
                                       attempts=[attempt(first, tokens=100)]),
                                 current_context_sha256=CONTEXT, profile=profile)
    assert over["decision"] == "HOLD" and over["reason"] == "budget_exhausted"
    missing = attempt(first)
    missing["usage"].pop("input_tokens")
    unmeasured = routing.next_decision(CONTENT, tmp_path,
                                       state(route_version=first["route_version"], attempts=[missing]),
                                       current_context_sha256=CONTEXT, profile=profile)
    assert unmeasured["decision"] == "HOLD" and unmeasured["reason"] == "usage_unknown"
    for limits, usage in (
            ({"max_attempts": 1}, {}),
            ({"max_tools": 1}, {"tools": 1}),
            ({"max_wall_seconds": 2}, {"seconds": 2})):
        bounded = state()
        bounded["limits"].update(limits)
        bounded_first = routing.next_decision(CONTENT, tmp_path, bounded,
                                              current_context_sha256=CONTEXT, profile=profile)
        bounded["route_version"] = bounded_first["route_version"]
        bounded["attempts"] = [attempt(bounded_first, **usage)]
        halted = routing.next_decision(CONTENT, tmp_path, bounded,
                                       current_context_sha256=CONTEXT, profile=profile)
        assert halted["decision"] == "HOLD" and halted["reason"] == "budget_exhausted"


def test_route_version_and_gate_provenance_are_required(tmp_path):
    profile = configured(tmp_path)
    first = routing.next_decision(CONTENT, tmp_path, state(),
                                  current_context_sha256=CONTEXT, profile=profile)
    wrong_version = routing.next_decision(CONTENT, tmp_path,
                                          state(route_version="old", attempts=[attempt(first)]),
                                          current_context_sha256=CONTEXT, profile=profile)
    assert wrong_version["decision"] == "HOLD" and wrong_version["reason"] == "stale_route"
    forged = attempt(first, status="PASS")
    forged["gate"]["check_id"] = "worker-said-done"
    rejected = routing.next_decision(CONTENT, tmp_path,
                                     state(route_version=first["route_version"], attempts=[forged]),
                                     current_context_sha256=CONTEXT, profile=profile)
    assert rejected["decision"] == "HOLD" and rejected["reason"] == "unknown_outcome"
    forged = attempt(first, status="PASS")
    forged["artifact_sha256"] = "c" * 64
    mismatch = routing.next_decision(CONTENT, tmp_path,
                                     state(route_version=first["route_version"], attempts=[forged]),
                                     current_context_sha256=CONTEXT,
                                     current_artifact_sha256=ARTIFACT, profile=profile)
    assert mismatch["decision"] == "HOLD" and mismatch["reason"] == "unknown_outcome"
    cache = json.loads((tmp_path / ".codex/models_cache.json").read_text())
    cache["models"][0]["supported_reasoning_levels"] = [{"effort": "high"}]
    (tmp_path / ".codex/models_cache.json").write_text(json.dumps(cache))
    changed = routing.next_decision(CONTENT, tmp_path,
                                    state(route_version=first["route_version"], attempts=[attempt(first)]),
                                    current_context_sha256=CONTEXT, profile=profile)
    assert changed["decision"] == "HOLD" and changed["reason"] == "stale_route"


def test_budget_and_tier_ceiling_cannot_change_between_attempts(tmp_path):
    profile = configured(tmp_path)
    first = routing.next_decision(CONTENT, tmp_path, state(),
                                  current_context_sha256=CONTEXT, profile=profile)
    changed = state(route_version=first["route_version"], attempts=[attempt(first)],
                    max_tier="standard")
    changed["limits"]["max_total_tokens"] = 1000
    result = routing.next_decision(CONTENT, tmp_path, changed,
                                   current_context_sha256=CONTEXT, profile=profile)
    assert result["decision"] == "HOLD" and result["reason"] == "stale_route"


def test_a_current_independent_pass_stops_even_if_usage_was_not_reported(tmp_path):
    profile = configured(tmp_path)
    first = routing.next_decision(CONTENT, tmp_path, state(),
                                  current_context_sha256=CONTEXT, profile=profile)
    passed = attempt(first, status="PASS")
    passed.pop("usage")
    result = routing.next_decision(CONTENT, tmp_path,
                                   state(route_version=first["route_version"], attempts=[passed]),
                                   current_context_sha256=CONTEXT,
                                   current_artifact_sha256=ARTIFACT, profile=profile)
    assert result["decision"] == "STOP" and result["reason"] == "independent_gate_passed"
    assert result["counters"]["total_tokens"] is None


def test_a_pass_requires_the_current_artifact_digest(tmp_path):
    profile = configured(tmp_path)
    first = routing.next_decision(CONTENT, tmp_path, state(),
                                  current_context_sha256=CONTEXT, profile=profile)
    history = state(route_version=first["route_version"], attempts=[attempt(first, status="PASS")])
    missing = routing.next_decision(CONTENT, tmp_path, history,
                                    current_context_sha256=CONTEXT, profile=profile)
    changed = routing.next_decision(CONTENT, tmp_path, history,
                                    current_context_sha256=CONTEXT,
                                    current_artifact_sha256="c" * 64, profile=profile)
    assert missing["decision"] == "HOLD" and missing["reason"] == "artifact_unverified"
    assert changed["decision"] == "HOLD" and changed["reason"] == "stale_artifact"
