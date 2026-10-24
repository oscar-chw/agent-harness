"""The work graph changes tiers only after its own independent gate fails."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor


PLAN = Path(__file__).resolve().parents[1] / "src/agent_harness/workgraph/plan.py"
spec = importlib.util.spec_from_file_location("candidate_plan_routing", PLAN)
plan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plan)


def node(tier="quick", failures=0):
    return {"fields": {"tier": tier},
            "notes": [f"2026-10-24T00:00:0{i}Z exit 1 in 1s [deadbeef] — failed check"
                      for i in range(failures)]}


def test_explicit_minimum_steps_up_only_after_proven_gate_failure():
    first = node(failures=0)
    before = list(first["notes"])
    assert plan.route_for(first) == {"tier": "quick", "reason": "declared_minimum",
                                     "route_version": "workgraph-tier-v1", "attempt": 1}
    assert first["notes"] == before
    assert plan.route_for(node(failures=1))["tier"] == "standard"
    assert plan.route_for(node(failures=2))["tier"] == "deep"


def test_direct_high_start_does_not_deescalate_or_invent_success():
    high = plan.route_for(node(tier="deep", failures=0))
    assert (high["tier"], high["reason"], high["attempt"]) == (
        "deep", "declared_minimum", 1)
    repeated = plan.route_for(node(tier="deep", failures=2))
    assert repeated["tier"] == "deep"
    assert repeated["attempt"] == 3
    ordinary = plan.route_for(node(tier="", failures=0))
    assert ordinary["tier"] == "standard"


def test_guard_refusal_or_not_run_never_escalates_as_gate_failure():
    for code, tail in (("126", "refused by the guard before it ran: blocked"),
                       ("8", "NOT_RUN: version check refused: stale"),
                       ("124", "timed out after 1800s")):
        n = {"fields": {"tier": "quick"},
             "notes": [f"2026-10-24T00:00:00Z exit {code} in 0s [deadbeef] — {tail}"]}
        route = plan.route_for(n)
        assert route["tier"] is None and route["reason"] == "gate_not_run"


def test_route_reason_and_observed_counters_survive_in_the_node_record(tmp_path, monkeypatch):
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan/t.md").write_text("## goal: fixture\n\n- [ ] 1. Work | tier: quick | gate: true\n")
    monkeypatch.chdir(tmp_path)
    usage = plan.worker_usage("codex", {"input_tokens": 14, "cached_input_tokens": 4,
                                        "output_tokens": 3})
    route = {"tier": "quick", "reason": "declared_minimum",
             "route_version": "workgraph-tier-v1", "attempt": 1,
             "dispatch_seconds": 2, "tool_calls": None,
             "requested_model": "m-small", "requested_effort": "low"}
    plan.record_worker_usage("t", 1, usage, route=route)
    records = list((tmp_path / "plan/t").glob("*.md"))
    assert len(records) == 1
    body = records[0].read_text()
    assert '"route_version": "workgraph-tier-v1"' in body
    assert '"reason": "declared_minimum"' in body
    assert '"input_tokens": 14' in body
    assert '"tool_calls": null' in body
    assert '"requested_model": "m-small"' in body


def test_codex_tool_count_is_observed_only_from_completed_tool_events():
    events = [
        {"type": "item.completed", "item": {"type": "command_execution"}},
        {"type": "item.completed", "item": {"type": "mcp_tool_call"}},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "done"}},
        {"type": "turn.completed", "usage": {"input_tokens": 10,
                                             "cached_input_tokens": 2, "output_tokens": 3}},
    ]
    output = "\n".join(json.dumps(event) for event in events)
    complete = plan.codex_info(0, output, "")
    assert complete["observed_tool_calls"] == 2
    assert complete["tool_calls_status"] == "COMPLETE_EVENT_STREAM"
    partial = plan.codex_info(1, "\n".join(json.dumps(e) for e in events[:2]), "failed")
    assert partial["observed_tool_calls"] == 2
    assert partial["tool_calls_status"] == "PARTIAL_EVENT_STREAM"


def test_explicit_missing_tier_refuses_before_worker_dispatch(tmp_path, monkeypatch):
    n = {"fields": {"tier": "not-installed"}, "notes": []}
    monkeypatch.setattr(plan, "load", lambda slug: (None, None, {1: n}, [1], []))
    monkeypatch.setattr(plan, "build_context", lambda slug, nid: "NODE 1: fixture\n")
    monkeypatch.setattr(plan, "runner", lambda: "codex")
    monkeypatch.setattr(plan, "_dispatch_codex", lambda *a, **kw: (_ for _ in ()).throw(
        AssertionError("unavailable tier was dispatched")))
    monkeypatch.setenv("HOME", str(tmp_path))
    result = plan._dispatch("t", 1, 1)
    assert result["dispatch_failed"] is True
    assert "not-installed" in result["why"]


def test_declared_codex_tier_needs_a_supported_model_effort_pair(tmp_path, monkeypatch):
    n = {"fields": {"tier": "quick"}, "notes": []}
    monkeypatch.setattr(plan, "load", lambda slug: (None, None, {1: n}, [1], []))
    monkeypatch.setattr(plan, "build_context", lambda slug, nid: "NODE 1: fixture\n")
    monkeypatch.setattr(plan, "runner", lambda: "codex")
    monkeypatch.setattr(plan, "_dispatch_codex", lambda *a, **kw: (_ for _ in ()).throw(
        AssertionError("unsupported pair was dispatched")))
    monkeypatch.setenv("HOME", str(tmp_path))
    agents = tmp_path / ".codex/agents"
    agents.mkdir(parents=True)
    tier_file = agents / "harness-quick.toml"
    tier_file.write_text('name = "harness-quick"\nmodel_reasoning_effort = "low"\n')
    absent = plan._dispatch("t", 1, 1)
    assert absent["route_hold"] is True
    tier_file.write_text('model = "m-small"\nmodel_reasoning_effort = "max"\n')
    cache = {"models": [{"slug": "m-small", "visibility": "list", "priority": 1,
                         "supported_reasoning_levels": [{"effort": "low"}]}]}
    (tmp_path / ".codex/models_cache.json").write_text(json.dumps(cache))
    unsupported = plan._dispatch("t", 1, 1)
    assert unsupported["route_hold"] is True
    assert "unsupported" in unsupported["why"]
    tier_file.write_text('model = "m-small"\nmodel_reasoning_effort = "low"\n')
    monkeypatch.setattr(plan, "_dispatch_codex", lambda nid, prompt, tier, timeout, model:
                        {"id": nid, "tier": tier, "prompt": prompt})
    supported = plan._dispatch("t", 1, 1)
    assert supported["tier"] == "quick" and "NODE 1" in supported["prompt"]


def test_a_non_run_route_never_spawns_a_worker(tmp_path, monkeypatch):
    n = {"fields": {"tier": "quick"}, "notes": []}
    monkeypatch.setattr(plan, "load", lambda slug: (None, None, {1: n}, [1], []))
    monkeypatch.setattr(plan, "build_context", lambda slug, nid: "NODE 1: fixture\n")
    monkeypatch.setattr(plan, "runner", lambda: "codex")
    monkeypatch.setattr(plan, "_dispatch_codex", lambda *a, **kw: (_ for _ in ()).throw(
        AssertionError("held route was dispatched")))
    held = {"tier": None, "reason": "gate_not_run", "route_version": "workgraph-tier-v1", "attempt": 2}
    result = plan._dispatch("t", 1, 1, route=held)
    assert result["route_hold"] is True and result["dispatch_failed"] is True


def test_worker_cannot_rewrite_its_own_route_tier(tmp_path):
    (tmp_path / "plan").mkdir()
    graph = tmp_path / "plan/t.md"
    graph.write_text("## goal: fixture\n\n- [ ] 1. Work | gate: true\n")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    worker = bindir / "claude"
    worker.write_text("#!/bin/sh\n"
                      "sed 's/ | gate:/ | tier: deep | gate:/' plan/t.md > plan/next.md\n"
                      "mv plan/next.md plan/t.md\n"
                      "printf '%s\\n' '{\"type\":\"result\",\"subtype\":\"success\",\"is_error\":false,\"result\":\"done\"}'\n")
    worker.chmod(0o700)
    env = {**os.environ, "HOME": str(tmp_path), "PATH": str(bindir) + os.pathsep + os.environ["PATH"],
           "PLAN_RUNNER": "claude", "PLAN_QUIET": "1"}
    run = subprocess.run([sys.executable, str(PLAN), "run", "t", "--workers", "1",
                          "--max-rounds", "1"], cwd=tmp_path, env=env,
                         capture_output=True, text=True, timeout=15)
    assert run.returncode != 0
    assert "TAMPERED" in run.stdout
    assert "tier: deep" not in graph.read_text()


def test_concurrent_guard_checks_wait_for_the_guard_to_finish_loading(tmp_path, monkeypatch):
    guard = tmp_path / "guard.py"
    guard.write_text("import time\ntime.sleep(0.15)\nREADY = True\n")
    monkeypatch.setenv("PLAN_GUARD", str(guard))
    monkeypatch.setattr(plan, "_GUARD", [None, False])
    start = threading.Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(lambda: (start.wait(), plan._guard())[1]) for _ in range(2)]
        results = [future.result(timeout=3) for future in futures]
    assert all(getattr(module, "READY", False) for module in results)


def test_route_hold_does_not_claim_a_worker_was_dispatched(tmp_path):
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan/t.md").write_text(
        "## goal: fixture\n\n- [ ] 1. Work | tier: quick | gate: true\n")
    env = {**os.environ, "HOME": str(tmp_path), "PLAN_RUNNER": "codex", "PLAN_QUIET": "1"}
    run = subprocess.run([sys.executable, str(PLAN), "run", "t", "--workers", "1",
                          "--max-rounds", "1"], cwd=tmp_path, env=env,
                         capture_output=True, text=True, timeout=15)
    assert run.returncode != 0
    assert "DISPATCH FAILED" in run.stdout
    assert "dispatched 0" in run.stdout
