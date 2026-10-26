"""Explicit launch contract; no model, hooks, trust or live configuration."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize


@pytest.fixture
def launch_request(tmp_path):
    pid = initialize(tmp_path)
    source = tmp_path / "decision.md"
    source.write_text("Current qualification: NOT_DEPLOYED; limit 3.\n")
    item = {"id": "status", "project_id": pid, "layer": "project_facts", "kind": "fact",
            "scope": "qualification", "text": source.read_text(), "provenance": [
                {"source": SourceVault(tmp_path, pid).capture("decision.md"), "start_line": 1, "end_line": 1}],
            "confidence": "verified", "sensitivity": "internal", "access_boundary": "local_user",
            "owner": "fixture", "freshness": "current"}
    ref = ProjectMemory(tmp_path, pid).append(item, expected=None)
    data = {"schema": "harness.launch/v1", "project_id": pid,
            "task": "Return the qualification and limit from the current record as JSON.",
            "references": [ref], "scope": {"allowed_sensitivities": ["internal"],
                "allowed_scopes": ["qualification"], "layers": ["project_facts"]},
            "max_context_bytes": 8192}
    (tmp_path / "request.json").write_text(json.dumps(data))
    return tmp_path, data, item


def prepare(root):
    from agent_harness.launch import prepare
    return prepare(root, "request.json")


def test_prepare_resolves_correction_without_copying_history(launch_request):
    root, data, item = launch_request
    item["text"] = "Current qualification: NOT_DEPLOYED; limit 5."
    (root / "decision.md").write_text(item["text"] + "\n")
    item["provenance"][0]["source"] = SourceVault(root, data["project_id"]).capture("decision.md")
    current = ProjectMemory(root, data["project_id"]).append(item, expected=data["references"][0])
    packet = prepare(root)
    assert packet["memory_receipts"] == [current]
    assert "limit 5" in packet["prompt"] and "limit 3" not in packet["prompt"]
    assert "not authorization" in packet["prompt"]
    assert packet["native_completion"] == "NOT_RUN"


def test_prepared_handoff_has_a_runnable_relative_request_and_no_invented_plan(launch_request):
    root, _, _ = launch_request
    packet = prepare(root)
    assert "harness launch --project-root . --request request.json" in packet["prompt"]
    assert "PLAN_NODE: absent" in packet["prompt"]
    assert "WHEN VERIFIED: plan gate" not in packet["prompt"]
    assert str(root) not in packet["prompt"]
    cli = Path(__file__).resolve().parents[1] / "bin/harness"
    run = subprocess.run([sys.executable, str(cli), "launch", "--project-root", ".",
                          "--request", "request.json"], cwd=root, capture_output=True, text=True, timeout=10)
    assert run.returncode == 0, run.stderr


def test_request_handle_quotes_spaces_and_rejects_control_characters(launch_request):
    import shlex
    from agent_harness.launch import prepare as prepare_request
    root, _, _ = launch_request
    (root / "requests").mkdir()
    (root / "requests/my task.json").write_bytes((root / "request.json").read_bytes())
    prompt = prepare_request(root, "requests/my task.json")["prompt"]
    command = next(line.removeprefix("PREPARE: ") for line in prompt.splitlines()
                   if line.startswith("PREPARE: "))
    assert shlex.split(command) == ["harness", "launch", "--project-root", ".",
                                    "--request", "requests/my task.json"]
    (root / "-task.json").write_bytes((root / "request.json").read_bytes())
    dash_prompt = prepare_request(root, "-task.json")["prompt"]
    dash_command = next(line.removeprefix("PREPARE: ") for line in dash_prompt.splitlines()
                        if line.startswith("PREPARE: "))
    assert shlex.split(dash_command)[-1] == "./-task.json"
    with pytest.raises(ValueError, match="request path"):
        prepare_request(root, "requests/my\ntask.json")


def test_prepared_handoff_names_only_a_verified_plan_node(launch_request):
    root, data, _ = launch_request
    (root / "plan").mkdir()
    (root / "plan/work.md").write_text("## goal: fixture\n\n- [ ] 1. Check artifact | gate: true\n")
    data["plan_node"] = {"slug": "work", "id": 1}
    (root / "request.json").write_text(json.dumps(data))
    prompt = prepare(root)["prompt"]
    assert "PLAN_NODE: work 1" in prompt
    assert "plan context work 1" in prompt
    assert "plan gate work 1" in prompt
    assert str(root) not in prompt
    for invalid in ({"slug": "work", "id": 2}, {"slug": "../work", "id": 1},
                    {"slug": "work", "id": True}):
        data["plan_node"] = invalid
        (root / "request.json").write_text(json.dumps(data))
        with pytest.raises(ValueError, match="plan node"):
            prepare(root)


def test_malformed_or_linked_plan_cannot_supply_an_operator_handle(launch_request):
    root, data, _ = launch_request
    (root / "plan").mkdir()
    plan = root / "plan/work.md"
    data["plan_node"] = {"slug": "work", "id": 1}
    (root / "request.json").write_text(json.dumps(data))
    plan.write_text("## goal: fixture\n\n- [ ] 1. Missing check\n")
    with pytest.raises(ValueError, match="plan node"):
        prepare(root)
    plan.unlink()
    plan.symlink_to(root / "request.json")
    with pytest.raises(ValueError, match="plan node"):
        prepare(root)


def test_handoff_does_not_suggest_gating_a_held_or_completed_node(launch_request):
    root, data, _ = launch_request
    (root / "plan").mkdir()
    plan = root / "plan/work.md"
    data["plan_node"] = {"slug": "work", "id": 1}
    (root / "request.json").write_text(json.dumps(data))
    for line in ("- [ ] 1. Deploy | risk: irreversible | gate: true",
                 "- [x] 1. Already done | gate: true",
                 "- [>] 1. Claimed | owner: other | gate: true"):
        plan.write_text("## goal: fixture\n\n" + line + "\n")
        prompt = prepare(root)["prompt"]
        assert "PLAN_NODE: work 1" in prompt
        assert "WHEN VERIFIED: plan gate" not in prompt


def test_plan_gate_change_invalidates_prepared_context(launch_request):
    root, data, _ = launch_request
    (root / "plan").mkdir()
    plan = root / "plan/work.md"
    plan.write_text("## goal: fixture\n\n- [ ] 1. Check | gate: true\n")
    data["plan_node"] = {"slug": "work", "id": 1}
    (root / "request.json").write_text(json.dumps(data))
    first = prepare(root)
    plan.write_text("## goal: fixture\n\n- [ ] 1. Check | gate: false\n")
    second = prepare(root)
    assert first["request_sha256"] == second["request_sha256"]
    assert first["context_sha256"] != second["context_sha256"]


def test_handoff_context_does_not_bypass_withdrawn_memory(launch_request):
    root, data, item = launch_request
    data["plan_node"] = {"slug": "work", "id": 1}
    (root / "request.json").write_text(json.dumps(data))
    ProjectMemory(root, data["project_id"]).append({**item, "freshness": "withdrawn"},
                                                    expected=data["references"][0])
    with pytest.raises(ValueError, match="not current"):
        prepare(root)


def test_execute_refuses_withdrawn_memory_before_spawning(launch_request, monkeypatch):
    from agent_harness.launch import execute
    root, data, item = launch_request
    marker = root / "spawned"
    stub(root, f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")
    monkeypatch.setenv("PATH", str(root))
    ProjectMemory(root, data["project_id"]).append({**item, "freshness": "withdrawn"},
                                                    expected=data["references"][0])
    with pytest.raises(ValueError, match="not current"):
        execute(root, "request.json", "receipt.json", timeout=2)
    assert not marker.exists() and not (root / "receipt.json").exists()


def test_named_resume_accepts_a_large_launcher_receipt(launch_request, monkeypatch):
    from agent_harness.launch import execute, prepare as prepare_request
    root, _, _ = launch_request
    prior = {**prepare_request(root, "request.json"), "sandbox": "read-only",
             "native_completion": "TIMEOUT", "thread_id": "01a16828-6ebc-7e82-9fd6-99f867c645fc"}
    prior["runtime_events"] = {"items": [{"event_type": "item.completed",
                                          "route": "other_shell", "padding": "x" * 250}
                                         for _ in range(257)]}
    (root / "prior.json").write_text(json.dumps(prior))
    assert (root / "prior.json").stat().st_size > 32768
    stub(root, "import json\n"
         "print(json.dumps({'type':'thread.started','thread_id':'01a16828-6ebc-7e82-9fd6-99f867c645fc'}))\n"
         "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'ready'}}))\n"
         "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':3,'cached_input_tokens':0,'output_tokens':2}}))\n")
    monkeypatch.setenv("PATH", str(root))
    result = execute(root, "request.json", "next.json", timeout=2, resume_receipt="prior.json")
    assert result["native_completion"] == "COMPLETED_UNGRADED"
    assert result["task_evaluation"] == "NOT_RUN"


@pytest.mark.parametrize("defect", ["withdrawn", "unknown", "expired", "scope", "stale", "budget", "duplicate"])
def test_bad_dependency_refuses_before_execution(launch_request, defect):
    root, data, item = launch_request
    if defect in ("withdrawn", "unknown", "expired"):
        ProjectMemory(root, data["project_id"]).append({**item, "freshness": defect}, expected=data["references"][0])
    elif defect == "scope":
        data["scope"]["allowed_scopes"] = ["another"]
    elif defect == "stale":
        (root / "decision.md").write_text("Changed outside the store")
    elif defect == "budget":
        data["max_context_bytes"] = 100
    else:
        data["references"] *= 2
    (root / "request.json").write_text(json.dumps(data))
    with pytest.raises((ValueError, PermissionError)):
        prepare(root)


def stub(root, text):
    path = root / "codex"
    path.write_text(f"#!{sys.executable}\n" + text)
    path.chmod(0o700)
    return path


def test_invoke_pins_prompt_and_native_completion_is_ungraded(launch_request, monkeypatch):
    from agent_harness.launch import execute
    root, _, _ = launch_request
    native = stub(root, "import json,sys\np=sys.stdin.read()\n"
                  "assert sys.argv[1:]==['exec','--json','-s','read-only','-C',str(__import__('pathlib').Path.cwd()),'-']\n"
                  "assert __import__('os').environ['PATH'].split(__import__('os').pathsep)[0].endswith('agent_harness/workgraph/bin')\n"
                  "assert 'NOT_DEPLOYED' in p\n"
                  "print(json.dumps({'type':'thread.started','thread_id':'fixture'}))\n"
                  "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'NOT_DEPLOYED; limit 3'}}))\n"
                  "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':10,'cached_input_tokens':4,'output_tokens':2}}))\n")
    monkeypatch.setenv("PATH", str(root))
    result = execute(root, "request.json", "receipt.json", timeout=2)
    assert result["native_completion"] == "COMPLETED_UNGRADED"
    assert result["task_evaluation"] == "NOT_RUN"
    assert result["usage"]["input_tokens"] == 10
    assert result["event_counts"] == {"thread.started": 1, "item.completed": 1, "turn.completed": 1}
    assert result["last_event_type"] == "turn.completed"
    assert result["native_path"] == str(native)
    assert json.loads((root / "receipt.json").read_text()) == result
    with pytest.raises(ValueError, match="exist"):
        execute(root, "request.json", "receipt.json", timeout=2)


@pytest.mark.parametrize("body,status", [
    ("print('{}')", "FAILED"),
    ("raise SystemExit(3)", "FAILED"),
    ("import time; time.sleep(30)", "TIMEOUT"),
])
def test_incomplete_or_timed_out_native_never_passes(launch_request, monkeypatch, body, status):
    from agent_harness.launch import execute
    root, _, _ = launch_request
    stub(root, body)
    monkeypatch.setenv("PATH", str(root))
    result = execute(root, "request.json", "receipt.json", timeout=0.15 if status == "TIMEOUT" else 2)
    assert result["native_completion"] == status
    assert result["task_evaluation"] == "NOT_RUN"
    assert result["usage_status"] == "UNKNOWN" and result["usage"] is None
    with pytest.raises(ProcessLookupError):
        os.killpg(result["process_group"], 0)


def test_paths_and_request_schema_are_not_implicit_authority(launch_request):
    from agent_harness.launch import prepare
    root, data, _ = launch_request
    for path in ("../request.json", str(root / "request.json"), ".harness/records/00000001.json"):
        with pytest.raises(ValueError):
            prepare(root, path)
    data["permission"] = "all"
    (root / "request.json").write_text(json.dumps(data))
    with pytest.raises(ValueError, match="schema"):
        prepare(root, "request.json")


def test_native_output_budget_refuses_a_large_stream(launch_request, monkeypatch):
    from agent_harness.launch import execute, MAX_NATIVE_OUTPUT
    root, _, _ = launch_request
    stub(root, "import sys;sys.stdout.write('x'*" + str(MAX_NATIVE_OUTPUT + 10) + ")")
    monkeypatch.setenv("PATH", str(root))
    result = execute(root, "request.json", "receipt.json", timeout=5)
    assert result["native_completion"] == "OUTPUT_LIMIT"
    assert result["task_evaluation"] == "NOT_RUN"


def test_native_turn_bound_is_explicit_and_capped(launch_request, monkeypatch):
    from agent_harness.launch import execute
    root, _, _ = launch_request
    stub(root, "import json\n"
         "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'ok'}}))\n"
         "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':1,'cached_input_tokens':0,'output_tokens':1}}))\n")
    monkeypatch.setenv("PATH", str(root))
    assert execute(root, "request.json", "receipt.json", timeout=300)["native_completion"] == "COMPLETED_UNGRADED"
    with pytest.raises(ValueError, match="timeout"):
        execute(root, "request.json", "another-receipt.json", timeout=301)


def test_adaptive_method_is_opt_in_and_cannot_change_scope_or_grading(launch_request):
    from agent_harness.launch import prepare
    root, _, _ = launch_request
    fixed = prepare(root, "request.json")
    adaptive = prepare(root, "request.json", method_policy="adaptive")
    assert fixed["method_policy"] == "existing"
    assert adaptive["method_policy"] == "adaptive"
    assert adaptive["memory_receipts"] == fixed["memory_receipts"]
    assert adaptive["context_sha256"] == fixed["context_sha256"]
    assert adaptive["task_evaluation"] == fixed["task_evaluation"] == "NOT_RUN"
    assert "single deliverable" in adaptive["prompt"]
    assert "change method" in adaptive["prompt"]
    assert "single deliverable" not in fixed["prompt"]
    assert "counterexample" in adaptive["prompt"]
    assert "counterexample" not in fixed["prompt"]
    assert len(adaptive["prompt"].encode()) - len(fixed["prompt"].encode()) < 700
    with pytest.raises(ValueError, match="method"):
        prepare(root, "request.json", method_policy="unknown")


def test_resume_rechecks_same_context_and_reuses_native_thread(launch_request, monkeypatch):
    from agent_harness.launch import execute, prepare
    root, _, _ = launch_request
    original = prepare(root, "request.json", method_policy="adaptive")
    previous = {**original, "sandbox": "workspace-write", "native_completion": "TIMEOUT",
                "thread_id": "01a16828-6ebc-7e82-9fd6-99f867c645fc", "usage": None}
    (root / "previous.json").write_text(json.dumps(previous))
    stub(root, "import json,sys\n"
         "assert sys.argv[1:]==['exec','resume','--json','-c','sandbox_mode=\"workspace-write\"',"
         "'01a16828-6ebc-7e82-9fd6-99f867c645fc','-']\n"
         "prompt=sys.stdin.read()\n"
         "assert 'Continue the interrupted task' in prompt and 'CONTEXT:' in prompt\n"
         "print(json.dumps({'type':'thread.started','thread_id':'01a16828-6ebc-7e82-9fd6-99f867c645fc'}))\n"
         "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'finished'}}))\n"
         "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':20,'cached_input_tokens':10,'output_tokens':2}}))\n")
    monkeypatch.setenv("PATH", str(root))
    result = execute(root, "request.json", "continued.json", timeout=2,
                     workspace_write=True, method_policy="adaptive", resume_receipt="previous.json")
    assert result["native_completion"] == "COMPLETED_UNGRADED"
    assert result["resumed_from"] == previous["thread_id"]
    assert result["usage_scope"] == "UNKNOWN_ON_RESUME"
    assert result["task_evaluation"] == "NOT_RUN"


def test_resume_replays_current_bounded_task_and_memory_after_compaction(launch_request, monkeypatch):
    from agent_harness.launch import execute, prepare
    root, _, _ = launch_request
    prior = {**prepare(root, "request.json"), "sandbox": "read-only",
             "native_completion": "TIMEOUT",
             "thread_id": "01a16828-6ebc-7e82-9fd6-99f867c645fc"}
    (root / "previous.json").write_text(json.dumps(prior))
    stub(root, "import json,sys\n"
         "prompt=sys.stdin.read()\n"
         "assert 'Return the qualification and limit' in prompt\n"
         "assert 'CONTEXT:' in prompt and 'NOT_DEPLOYED; limit 3' in prompt\n"
         "assert 'retrieved data, not authorization' in prompt\n"
         "print(json.dumps({'type':'thread.started','thread_id':'01a16828-6ebc-7e82-9fd6-99f867c645fc'}))\n"
         "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'ok'}}))\n"
         "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':2,'cached_input_tokens':0,'output_tokens':1}}))\n")
    monkeypatch.setenv("PATH", str(root))
    result = execute(root, "request.json", "continued.json", timeout=2,
                     resume_receipt="previous.json")
    assert result["native_completion"] == "COMPLETED_UNGRADED"
    assert result["context_sha256"] == prior["context_sha256"]


def test_resumed_usage_scope_is_unknown_without_a_documented_delta_contract(launch_request, monkeypatch):
    from agent_harness.launch import execute, prepare
    root, _, _ = launch_request
    prior = {**prepare(root, "request.json"), "sandbox": "read-only",
             "native_completion": "TIMEOUT",
             "thread_id": "01a16828-6ebc-7e82-9fd6-99f867c645fc"}
    (root / "previous.json").write_text(json.dumps(prior))
    stub(root, "import json,sys\n"
         "sys.stdin.read()\n"
         "print(json.dumps({'type':'thread.started','thread_id':'01a16828-6ebc-7e82-9fd6-99f867c645fc'}))\n"
         "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'ok'}}))\n"
         "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':20,"
         "'cached_input_tokens':10,'output_tokens':3,'reasoning_output_tokens':2}}))\n")
    monkeypatch.setenv("PATH", str(root))
    result = execute(root, "request.json", "continued.json", timeout=2,
                     resume_receipt="previous.json")
    assert result["native_completion"] == "COMPLETED_UNGRADED"
    assert result["usage_scope"] == "UNKNOWN_ON_RESUME"
    assert result["usage"] == {"input_tokens": 20, "cached_input_tokens": 10,
                               "output_tokens": 3, "reasoning_output_tokens": 2}
    assert result["usage_status"] == "PROVIDER_REPORTED"


def test_resume_refuses_stale_memory_before_native_spawn(launch_request, monkeypatch):
    from agent_harness.launch import execute, prepare
    from agent_harness.project_memory import ProjectMemory
    root, data, item = launch_request
    previous = {**prepare(root, "request.json"), "sandbox": "read-only",
                "native_completion": "TIMEOUT", "thread_id": "01a16828-6ebc-7e82-9fd6-99f867c645fc"}
    (root / "previous.json").write_text(json.dumps(previous))
    item["text"] = "Corrected project fact."
    (root / "decision.md").write_text(item["text"] + "\n")
    item["provenance"][0]["source"] = SourceVault(root, data["project_id"]).capture("decision.md")
    ProjectMemory(root, data["project_id"]).append(item, expected=data["references"][0])
    stub(root, "raise SystemExit('must not run on stale context')")
    monkeypatch.setenv("PATH", str(root))
    with pytest.raises(ValueError, match="context"):
        execute(root, "request.json", "continued.json", timeout=2,
                resume_receipt="previous.json")
    assert not (root / "continued.json").exists()


def test_native_receipt_reports_timing_and_route_without_command_contents(launch_request, monkeypatch):
    from hashlib import sha256
    from agent_harness.launch import execute
    root, _, _ = launch_request
    stub(root, "import json,sys,time\nsys.stdin.read()\n"
         "print(json.dumps({'type':'item.started','item':{'id':'item_1','type':'command_execution',"
         "'command':'plan new task SECRET-SHOULD-NOT-LEAK'}}),flush=True)\n"
         "time.sleep(.09)\n"
         "print(json.dumps({'type':'item.completed','item':{'id':'item_1','type':'command_execution',"
         "'command':'plan new task SECRET-SHOULD-NOT-LEAK',"
         "'aggregated_output':'ORACLE_DENIED\\nTASK_READ_OK\\n'}}),flush=True)\n"
         "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'ok'}}),flush=True)\n"
         "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':3,'cached_input_tokens':0,'output_tokens':1}}),flush=True)\n")
    monkeypatch.setenv("PATH", str(root))
    result = execute(root, "request.json", "receipt.json", timeout=2)
    timing = result["runtime_events"]
    assert timing["items"][0]["route"] == "shell_plan_other"
    assert timing["items"][0]["command_sha256"] == sha256(
        b"plan new task SECRET-SHOULD-NOT-LEAK").hexdigest()
    assert timing["items"][1]["output_sha256"] == sha256(
        b"ORACLE_DENIED\nTASK_READ_OK\n").hexdigest()
    assert timing["timing_basis"] == "observer_poll_gap_not_tool_duration"
    assert "duration_seconds" not in timing["items"][1]
    gap = timing["items"][1]["observation_gap_seconds"]
    assert gap is None or gap >= 0
    assert timing["last_event_seconds"] >= timing["items"][1]["elapsed_seconds"]
    assert timing["omitted_items"] == 0
    assert "SECRET-SHOULD-NOT-LEAK" not in json.dumps(result)
    assert "ORACLE_DENIED" not in json.dumps(result)


def test_resume_consumes_bound_independent_failure_without_changing_grader(launch_request, monkeypatch):
    from hashlib import sha256
    from agent_harness.launch import execute, prepare
    root, _, _ = launch_request
    prepared = prepare(root, "request.json", method_policy="adaptive")
    prior = {**prepared, "sandbox": "workspace-write", "native_completion": "TIMEOUT",
             "thread_id": "01a16828-6ebc-7e82-9fd6-99f867c645fc"}
    (root / "previous.json").write_text(json.dumps(prior))
    (root / "draft.md").write_text("A draft needing source review")
    gate = {"schema": "harness.gate-result/v1", "artifact_sha256": sha256((root / "draft.md").read_bytes()).hexdigest(),
            "status": "FAIL", "check_id": "source-review", "failure_codes": ["missing-sync-event-limit"]}
    (root / "gate.json").write_text(json.dumps(gate))
    stub(root, "import json,sys\n"
         "prompt=sys.stdin.read()\n"
         "assert 'REVISE_ARTIFACT' in prompt and 'missing-sync-event-limit' in prompt\n"
         "assert 'Critical checks: current_source, counterexample, uncertainty' in prompt\n"
         "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'revised'}}))\n"
         "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':2,'cached_input_tokens':0,'output_tokens':1}}))\n")
    monkeypatch.setenv("PATH", str(root))
    result = execute(root, "request.json", "continued.json", timeout=2, workspace_write=True,
                     method_policy="adaptive", resume_receipt="previous.json",
                     artifact_path="draft.md", gate_receipt_path="gate.json")
    assert result["native_completion"] == "COMPLETED_UNGRADED"
    assert result["task_evaluation"] == "NOT_RUN"
    assert result["feedback_decision"]["action"] == "REVISE_ARTIFACT"


def test_completed_turn_can_revise_only_after_a_bound_failed_gate(launch_request, monkeypatch):
    from hashlib import sha256
    from agent_harness.launch import execute, prepare
    root, _, _ = launch_request
    prior_id = "01a16828-6ebc-7e82-9fd6-99f867c645fc"
    prior = {**prepare(root, "request.json", method_policy="adaptive"),
             "sandbox": "workspace-write", "native_completion": "COMPLETED_UNGRADED",
             "thread_id": prior_id}
    (root / "previous.json").write_text(json.dumps(prior))
    (root / "draft.md").write_text("A completed draft rejected by its independent check")
    gate = {"schema": "harness.gate-result/v1",
            "artifact_sha256": sha256((root / "draft.md").read_bytes()).hexdigest(),
            "status": "FAIL", "check_id": "artifact-check",
            "failure_codes": ["missing-required-source"]}
    (root / "gate.json").write_text(json.dumps(gate))
    stub(root, "import json,sys\n"
         "assert sys.argv[1:]==['exec','resume','--json','-c','sandbox_mode=\"workspace-write\"',"
         "'01a16828-6ebc-7e82-9fd6-99f867c645fc','-']\n"
         "prompt=sys.stdin.read()\n"
         "assert 'REVISE_ARTIFACT' in prompt and 'missing-required-source' in prompt\n"
         "print(json.dumps({'type':'thread.started','thread_id':'01a16828-6ebc-7e82-9fd6-99f867c645fc'}))\n"
         "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'revised'}}))\n"
         "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':3,'cached_input_tokens':0,'output_tokens':1}}))\n")
    monkeypatch.setenv("PATH", str(root))
    with pytest.raises(ValueError, match="completed|failed"):
        execute(root, "request.json", "unapproved.json", timeout=2, workspace_write=True,
                method_policy="adaptive", resume_receipt="previous.json")
    assert not (root / "unapproved.json").exists()
    result = execute(root, "request.json", "revised.json", timeout=2, workspace_write=True,
                     method_policy="adaptive", resume_receipt="previous.json",
                     artifact_path="draft.md", gate_receipt_path="gate.json")
    assert result["native_completion"] == "COMPLETED_UNGRADED"
    assert result["feedback_decision"]["action"] == "REVISE_ARTIFACT"
    assert result["resumed_from"] == prior_id


def test_paired_eval_pins_requested_model_and_effort_without_claiming_effective_identity(
        launch_request, monkeypatch):
    from agent_harness.launch import execute
    root, _, _ = launch_request
    stub(root, "import json,sys\n"
         "assert sys.argv[1:]==['exec','--json','-m','gpt-6.1-sol','-c',"
         "'model_reasoning_effort=\"xhigh\"','-s','read-only','-C',"
         "str(__import__('pathlib').Path.cwd()),'-']\n"
         "sys.stdin.read()\n"
         "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'ok'}}))\n"
         "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':2,'cached_input_tokens':0,'output_tokens':1}}))\n")
    monkeypatch.setenv("PATH", str(root))
    result = execute(root, "request.json", "receipt.json", timeout=2,
                     native_model="gpt-6.1-sol", native_effort="xhigh")
    assert result["native_completion"] == "COMPLETED_UNGRADED"
    assert result["requested_model"] == "gpt-6.1-sol"
    assert result["requested_effort"] == "xhigh"
    assert result["effective_model_evidence"] == "UNKNOWN"


def test_eval_only_profile_denies_a_sibling_oracle_without_changing_default_sandbox(
        launch_request, monkeypatch):
    root, _, _ = launch_request
    oracle = root.with_name(root.name + "-oracle")
    oracle.mkdir()
    (oracle / "canary.txt").write_text("HIDDEN-GRADER-CANARY\n")
    stub(root, "import json,sys\n"
         "args=sys.argv[1:]\n"
         "assert args[:2]==['exec','--json'] and '-s' not in args\n"
         "profile=json.loads(next(x.split('=',1)[1] for x in args "
         "if x.startswith('default_permissions=')))\n"
         "assert profile.startswith('harness_eval_')\n"
         "assert 'permissions.'+profile+'.extends=\":read-only\"' in args\n"
         "assert any(x.startswith('permissions.'+profile+'.filesystem=') "
         "and 'canary' not in x and 'oracle' in x for x in args)\n"
         "sys.stdin.read()\n"
         "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'ok'}}))\n"
         "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':2,'cached_input_tokens':0,'output_tokens':1}}))\n")
    monkeypatch.setenv("PATH", str(root))
    command = [sys.executable, str(Path(__file__).resolve().parents[1] / "bin/harness"),
               "launch", "--project-root", str(root), "--request", "request.json",
               "--execute", "--receipt-out", "eval-receipt.json", "--timeout", "2",
               "--eval-deny-root", str(oracle)]
    run = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result["native_completion"] == "COMPLETED_UNGRADED"
    assert result["permission_boundary"] == "requested_eval_profile_unverified"
    assert result["eval_deny_root_sha256"] is not None


def test_eval_profile_refuses_inside_project_or_missing_root_before_native_spawn(
        launch_request, monkeypatch):
    from agent_harness.launch import execute
    root, _, _ = launch_request
    stub(root, "raise SystemExit('must not start')")
    monkeypatch.setenv("PATH", str(root))
    config_sibling = root.parent / "config"
    config_sibling.mkdir()
    for invalid in (root, root / "nested", root.parent / "missing-oracle", config_sibling):
        with pytest.raises(ValueError, match="eval|oracle|sibling"):
            execute(root, "request.json", "bad-receipt.json", timeout=2,
                    eval_deny_root=invalid)
    assert not (root / "bad-receipt.json").exists()


def test_eval_profile_resume_rejects_an_oracle_boundary_change(launch_request, monkeypatch):
    from hashlib import sha256
    from agent_harness.launch import execute, prepare
    root, _, _ = launch_request
    first = root.with_name(root.name + "-oracle")
    second = root.with_name(root.name + "-other-oracle")
    first.mkdir()
    second.mkdir()
    prior = {**prepare(root, "request.json"), "sandbox": "workspace-write",
             "native_completion": "TIMEOUT",
             "thread_id": "01a16828-6ebc-7e82-9fd6-99f867c645fc",
             "eval_deny_root_sha256": sha256(str(first.resolve()).encode()).hexdigest(),
             "permission_boundary": "requested_eval_profile_unverified"}
    (root / "previous.json").write_text(json.dumps(prior))
    stub(root, "import json,sys\n"
         "args=sys.argv[1:]\n"
         "assert args[:3]==['exec','resume','--json'] and '-s' not in args\n"
         "assert any(x.endswith('.extends=\":workspace\"') for x in args)\n"
         "sys.stdin.read()\n"
         "print(json.dumps({'type':'thread.started','thread_id':'01a16828-6ebc-7e82-9fd6-99f867c645fc'}))\n"
         "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'ok'}}))\n"
         "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':2,'cached_input_tokens':0,'output_tokens':1}}))\n")
    monkeypatch.setenv("PATH", str(root))
    with pytest.raises(ValueError, match="resume context"):
        execute(root, "request.json", "wrong-oracle.json", timeout=2,
                workspace_write=True, resume_receipt="previous.json", eval_deny_root=second)
    assert not (root / "wrong-oracle.json").exists()
    result = execute(root, "request.json", "continued.json", timeout=2,
                     workspace_write=True, resume_receipt="previous.json", eval_deny_root=first)
    assert result["native_completion"] == "COMPLETED_UNGRADED"
    assert result["permission_boundary"] == "requested_eval_profile_unverified"


def test_paired_eval_rejects_partial_or_unsafe_native_pins_before_spawn(launch_request, monkeypatch):
    from agent_harness.launch import execute
    root, _, _ = launch_request
    native = stub(root, "raise SystemExit('must not spawn')")
    monkeypatch.setenv("PATH", str(root))
    for model, effort in (("gpt-6.1-sol", None), (None, "xhigh"),
                          ("gpt-6.1-sol;other", "xhigh"), ("gpt-6.1-sol", "impossible")):
        with pytest.raises(ValueError, match="model|effort"):
            execute(root, "request.json", "receipt.json", timeout=2,
                    native_model=model, native_effort=effort)
    assert native.exists() and not (root / "receipt.json").exists()


def test_paired_eval_resume_keeps_the_same_requested_model_and_effort(launch_request, monkeypatch):
    from agent_harness.launch import execute, prepare
    root, _, _ = launch_request
    prior_id = "01a16828-6ebc-7e82-9fd6-99f867c645fc"
    prior = {**prepare(root, "request.json"), "sandbox": "read-only",
             "native_completion": "TIMEOUT", "thread_id": prior_id,
             "requested_model": "gpt-6.1-sol", "requested_effort": "xhigh"}
    (root / "prior.json").write_text(json.dumps(prior))
    stub(root, "import json,sys\n"
         "assert sys.argv[1:]==['exec','resume','--json','-m','gpt-6.1-sol','-c',"
         "'model_reasoning_effort=\"xhigh\"','-c','sandbox_mode=\"read-only\"',"
         "'01a16828-6ebc-7e82-9fd6-99f867c645fc','-']\n"
         "sys.stdin.read()\n"
         "print(json.dumps({'type':'thread.started','thread_id':'01a16828-6ebc-7e82-9fd6-99f867c645fc'}))\n"
         "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'ok'}}))\n"
         "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':2,'cached_input_tokens':0,'output_tokens':1}}))\n")
    monkeypatch.setenv("PATH", str(root))
    with pytest.raises(ValueError, match="resume context"):
        execute(root, "request.json", "wrong.json", timeout=2, resume_receipt="prior.json",
                native_model="gpt-6.1-sol", native_effort="high")
    assert not (root / "wrong.json").exists()
    result = execute(root, "request.json", "continued.json", timeout=2,
                     resume_receipt="prior.json", native_model="gpt-6.1-sol", native_effort="xhigh")
    assert result["native_completion"] == "COMPLETED_UNGRADED"
    assert result["requested_effort"] == "xhigh"


def test_cli_prepares_without_native_process_and_execution_is_explicit(launch_request, monkeypatch):
    root, _, _ = launch_request
    native = stub(root, "raise SystemExit('must not run on prepare')")
    monkeypatch.setenv("PATH", str(root))
    command = [sys.executable, str(Path(__file__).resolve().parents[1] / "bin/harness"),
               "launch", "--project-root", str(root), "--request", "request.json"]
    read = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert read.returncode == 0, read.stderr
    data = json.loads(read.stdout)
    assert data["native_completion"] == "NOT_RUN" and "NOT_DEPLOYED" in data["prompt"]
    assert not (root / "receipt.json").exists() and native.exists()
    missing = subprocess.run(command + ["--execute"], capture_output=True, text=True, timeout=10)
    assert missing.returncode != 0
    assert "receipt-out" in missing.stderr


def test_explicit_workspace_write_uses_native_sandbox_and_creates_an_artifact(launch_request, monkeypatch):
    root, _, _ = launch_request
    stub(root, "import json,sys\n"
         "assert sys.argv[1:]==['exec','--json','-s','workspace-write','-C',str(__import__('pathlib').Path.cwd()),'-']\n"
         "__import__('pathlib').Path('artifact.txt').write_text('real fixture artifact')\n"
         "print(json.dumps({'type':'thread.started','thread_id':'write-test'}))\n"
         "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'created'}}))\n"
         "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':2,'cached_input_tokens':0,'output_tokens':1}}))\n")
    monkeypatch.setenv("PATH", str(root))
    command = [sys.executable, str(Path(__file__).resolve().parents[1] / "bin/harness"),
               "launch", "--project-root", str(root), "--request", "request.json", "--execute",
               "--workspace-write", "--receipt-out", "receipt.json", "--timeout", "2"]
    run = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert run.returncode == 0, run.stderr
    assert (root / "artifact.txt").read_text() == "real fixture artifact"
    assert json.loads(run.stdout)["task_evaluation"] == "NOT_RUN"


@pytest.mark.parametrize("descendant_survives", [False, True])
def test_cleanup_reaps_leader_but_still_checks_descendants(monkeypatch, descendant_survives):
    from agent_harness import launch

    class Child:
        pid = 12345
        reaped = False

        def poll(self):
            self.reaped = True
            return -15

    child = Child()
    signals = []

    def killpg(pid, signum):
        assert pid == child.pid
        signals.append(signum)
        if signum == 0 and child.reaped and not descendant_survives:
            raise ProcessLookupError

    monkeypatch.setattr(launch.os, "killpg", killpg)
    monkeypatch.setattr(launch.time, "sleep", lambda _: None)
    if descendant_survives:
        with pytest.raises(RuntimeError, match="cleanup could not be verified"):
            launch._end_group(child)
        assert launch.signal.SIGKILL in signals
    else:
        launch._end_group(child)
        assert launch.signal.SIGKILL not in signals
    assert child.reaped
