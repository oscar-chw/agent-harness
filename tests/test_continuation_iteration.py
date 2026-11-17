"""Controller fixtures cannot qualify native continuation efficacy."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def instrument():
    spec = importlib.util.spec_from_file_location("continuation_iteration", ROOT / "eval/continuation_iteration.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def observed(expected, tokens=10):
    text = json.dumps(expected)
    return {"exit_code": 0, "events": [
        {"type": "thread.started", "thread_id": "fixture-thread"},
        {"type": "turn.started"},
        {"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "harness",
            "tool": "op_state", "arguments": {"action": "status"}, "status": "completed",
            "error": None, "result": {"content": [{"type": "text", "text": json.dumps({"tasks": [{"value": expected}]})}]}}},
        {"type": "item.completed", "item": {"type": "agent_message", "text": text}},
        {"type": "turn.completed", "usage": {"input_tokens": tokens - 1, "cached_input_tokens": 0,
            "output_tokens": 1, "reasoning_output_tokens": 0, "cache_write_input_tokens": 0}}]}


EXPECTED = {"goal": "Resume retained checks.", "next": "Inspect the bound evidence.", "done": False}


def test_correct_source_bound_answer_counts_subsets_once(instrument):
    record = observed(EXPECTED)
    record["events"][-1]["usage"]["cached_input_tokens"] = 8
    result = instrument.assess(record, EXPECTED)
    assert result["correct"] and result["tokens"] == 10 and result["mcp_reads"] == 1


@pytest.mark.parametrize("field,value", [("goal", "different"), ("next", "wrong"), ("done", True), ("done", 0)])
def test_wrong_answer_or_false_completion_fails(instrument, field, value):
    record = observed(EXPECTED)
    answer = dict(EXPECTED, **{field: value})
    record["events"][-2]["item"]["text"] = json.dumps(answer)
    assert not instrument.assess(record, EXPECTED)["correct"]


@pytest.mark.parametrize("item", [
    {"type": "command_execution", "command": "cat STATE.md"},
    {"type": "file_change", "changes": []},
    {"type": "web_search", "query": "task"},
    {"type": "mcp_tool_call", "server": "other", "tool": "state_load", "arguments": {}},
    {"type": "mcp_tool_call", "server": "harness", "tool": "op_state", "arguments": {"action": "put"}},
])
def test_extra_actions_invalidate_the_trial(instrument, item):
    record = observed(EXPECTED)
    record["events"].insert(2, {"type": "item.completed", "item": item})
    with pytest.raises(ValueError, match="action"):
        instrument.assess(record, EXPECTED)


def test_answer_without_matching_mcp_evidence_is_incorrect(instrument):
    record = observed(EXPECTED)
    record["events"][2]["item"]["result"]["content"][0]["text"] = "no saved task"
    assert not instrument.assess(record, EXPECTED)["correct"]


@pytest.mark.parametrize("change", ["missing", "duplicate", "negative", "subset", "bool"])
def test_unknown_or_invalid_usage_stops(instrument, change):
    record = observed(EXPECTED)
    usage = record["events"][-1]["usage"]
    if change == "missing":
        usage.pop("input_tokens")
    elif change == "duplicate":
        record["events"].append(copy.deepcopy(record["events"][-1]))
    elif change == "negative":
        usage["output_tokens"] = -1
    elif change == "subset":
        usage["cached_input_tokens"] = 100
    else:
        usage["input_tokens"] = True
    with pytest.raises(ValueError, match="usage"):
        instrument.assess(record, EXPECTED)


def test_budget_stops_before_another_call_and_consumed_run_cannot_retry(instrument, tmp_path):
    out = tmp_path / "study"
    prepared = instrument.prepare(out, mode="simulation", max_tokens=10)
    calls = []

    def invoke(actor, prompt, frozen, expected):
        calls.append(actor)
        return observed(expected, tokens=10)

    result = instrument.execute(out, authorized_execute=prepared["freeze_sha256"], invoke=invoke)
    assert len(calls) == 1 and result["status"] == "CEILING_REACHED" and result["tokens_observed"] == 10
    with pytest.raises(ValueError, match="consumed"):
        instrument.execute(out, authorized_execute=prepared["freeze_sha256"], invoke=invoke)


def test_simulation_stays_unqualified_even_when_the_candidate_saves(instrument, tmp_path):
    out = tmp_path / "study"
    prepared = instrument.prepare(out, mode="simulation")

    def invoke(actor, prompt, frozen, expected):
        return observed(expected, tokens=8 if actor.name == "cand" else 10)

    result = instrument.execute(out, authorized_execute=prepared["freeze_sha256"], invoke=invoke)
    assert result["paired_quality_equal"] and result["tokens"] == {"base": 20, "cand": 16}
    assert result["status"] == "SIMULATION_ONLY" and result["promotion"] == "NOT_GRANTED"


def test_changed_frozen_case_refuses_execution(instrument, tmp_path):
    out = tmp_path / "study"
    prepared = instrument.prepare(out, mode="simulation")
    path = out / "oracle/freeze.json"
    data = json.loads(path.read_text())
    data["cases"][0]["goal"] = "replaced"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="copy changed"):
        instrument.execute(out, authorized_execute=prepared["freeze_sha256"], invoke=lambda *a: None)


def test_invalid_action_still_charges_known_consumed_tokens(instrument, tmp_path):
    out = tmp_path / "study"
    prepared = instrument.prepare(out, mode="simulation")

    def invoke(actor, prompt, frozen, expected):
        record = observed(expected, tokens=19)
        record["events"].insert(2, {"type": "item.completed", "item": {"type": "command_execution"}})
        return record

    result = instrument.execute(out, authorized_execute=prepared["freeze_sha256"], invoke=invoke)
    assert result["calls"] == 1 and result["tokens_observed"] == 19
    assert result["status"] == "INVALID_OBSERVATION" and result["unknown_usage_calls"] == 0


@pytest.mark.parametrize("kind", ["item.started", "item.updated"])
def test_uncompleted_forbidden_action_is_rejected(instrument, kind):
    record = observed(EXPECTED)
    record["events"].insert(2, {"type": kind, "item": {"id": "extra", "type": "command_execution"}})
    with pytest.raises(ValueError, match="action"):
        instrument.assess(record, EXPECTED)


def test_error_result_cannot_supply_task_evidence(instrument):
    record = observed(EXPECTED)
    record["events"][2]["item"]["result"]["isError"] = True
    with pytest.raises(ValueError, match="action"):
        instrument.assess(record, EXPECTED)


def test_diagnostic_text_containing_answers_is_not_a_task_packet(instrument):
    record = observed(EXPECTED)
    record['events'][2]['item']['result']['content'][0]['text'] = json.dumps({'error': EXPECTED})
    assert not instrument.assess(record, EXPECTED)['correct']


def test_unfinished_allowed_read_is_rejected(instrument):
    record = observed(EXPECTED)
    started = copy.deepcopy(record['events'][2])
    started['type'] = 'item.started'
    started['item']['id'] = 'unfinished'
    record['events'].insert(2, started)
    with pytest.raises(ValueError, match='lifecycle'):
        instrument.assess(record, EXPECTED)


def test_prelaunch_refusal_records_zero_model_calls(instrument, tmp_path):
    out = tmp_path / "study"
    prepared = instrument.prepare(out, mode="simulation")

    def refuse(*args):
        raise instrument.PrelaunchRefused("cold context mismatch")

    result = instrument.execute(out, authorized_execute=prepared["freeze_sha256"], invoke=refuse)
    assert result["status"] == "PRELAUNCH_REFUSED" and result["calls"] == 0
    assert result["prelaunch_failures"] == 1 and result["unknown_usage_calls"] == 0


def test_native_settings_bind_command_store_and_read_tools(instrument, tmp_path):
    settings = instrument._settings(tmp_path, ["harness", "other-server"])
    assert settings['mcp_servers.harness.command'] == instrument.sys.executable
    assert settings['mcp_servers.harness.args'][-2:] == ["--home", str(tmp_path / "store")]
    assert settings['mcp_servers.harness.enabled_tools'] == ["state_load", "op_state"]
    assert settings['mcp_servers."other-server"'] == {
        'enabled': False, 'command': instrument.sys.executable, 'args': ['-c', 'pass']}
    assert settings['model_provider'] == 'openai' and settings['service_tier'] == 'default'


@pytest.mark.parametrize("bad", ["apikey", "paid", "unknown-credits", "exhausted", "pagination", "malformed-server"])
def test_included_quota_and_surface_rejections(instrument, tmp_path, bad):
    account = {"account": {"type": "chatgpt"}}
    limits = {"credits": {"hasCredits": False}, "primary": {"usedPercent": 20}}
    inventory = {"data": [{"name": "harness"}], "nextCursor": None}
    good = instrument._admit_context(tmp_path, account, limits, inventory)
    assert good['auth_mode'] == 'chatgpt' and good['paid_credits_available'] is False and good['included_window_open']
    if bad == 'apikey':
        account['account']['type'] = 'apiKey'
    elif bad == 'paid':
        limits['credits']['hasCredits'] = True
        limits['primary']['usedPercent'] = 100
    elif bad == 'unknown-credits':
        limits['credits'] = None
    elif bad == 'exhausted':
        limits['primary']['usedPercent'] = 100
    elif bad == 'pagination':
        inventory['nextCursor'] = 'more'
    else:
        inventory['data'][0]['name'] = 123
    with pytest.raises(instrument.PrelaunchRefused):
        instrument._admit_context(tmp_path, account, limits, inventory)


def test_existing_credits_do_not_reject_an_open_included_window(instrument, tmp_path):
    result = instrument._admit_context(tmp_path, {"account": {"type": "chatgpt"}},
        {"credits": {"hasCredits": True}, "secondary": {"usedPercent": 20}},
        {"data": [{"name": "harness"}], "nextCursor": None})
    assert result['paid_credits_available'] is True and result['included_window_open'] is True


def test_invalid_native_configuration_never_spawns_a_model(instrument, tmp_path, monkeypatch):
    monkeypatch.setattr(instrument, '_preflight', lambda *args: None)
    monkeypatch.setattr(instrument, '_native_context', lambda *args: {'settings': {}})
    monkeypatch.setattr(instrument.subprocess, 'check_output', lambda *args, **kwargs: 'fixture')
    monkeypatch.setattr(instrument.subprocess, 'run', lambda *args, **kwargs:
                        instrument.subprocess.CompletedProcess([], 1, b'', b''))

    def forbidden_spawn(*args, **kwargs):
        raise AssertionError('model must not start after a rejected configuration')

    monkeypatch.setattr(instrument.subprocess, 'Popen', forbidden_spawn)
    with pytest.raises(instrument.PrelaunchRefused, match='configuration validation'):
        instrument._invoke(tmp_path, 'task', {'executable': 'fixture', 'native_version': 'fixture',
                                           'model': 'fixture'}, EXPECTED)
