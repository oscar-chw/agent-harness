"""Closed-world controls. All transports here are model-free fixtures."""

from pathlib import Path
import copy
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys

import pytest

from agent_harness import launch


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def instrument(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "reasoning_iteration", ROOT / "eval/reasoning_iteration.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "_native_client",
                        lambda: {"path": "/fixture/bin/codex", "version": "codex-cli 0.169.0"})
    return module


@pytest.fixture
def lab(tmp_path, instrument):
    out = tmp_path / "run"
    prepared = instrument.prepare(
        out, model="fixture-model", effort="high", timeout_seconds=5
    )
    return instrument, out, prepared


def test_source_hash_covers_file_tail(instrument, tmp_path, monkeypatch):
    root = tmp_path
    monkeypatch.setattr(instrument, "ROOT", root)
    cases = root / "cases.json"
    cases.write_text("{}")
    guide = root / "reasoning.md"
    guide.write_text("# Guide\n")
    monkeypatch.setattr(instrument, "FULL_GUIDE", guide)
    checker = root / "eval/check_reasoning_outcome.py"
    checker.parent.mkdir()
    checker.write_text("# Fixture\n")
    source = root / "src/agent_harness/workgraph/plan.py"
    source.parent.mkdir(parents=True)
    prefix = b"a" * (instrument.P.MAX_BYTES + 1)
    source.write_bytes(prefix + b"x")
    before = instrument._sources(cases)
    source.write_bytes(prefix + b"y")
    after = instrument._sources(cases)
    key = str(source.resolve())
    assert before[key] != after[key]
    assert {name: sha for name, sha in before.items() if name != key} == {
        name: sha for name, sha in after.items() if name != key
    }
    with source.open("r+b") as stream:
        stream.truncate(instrument.SOURCE_FILE_BYTES + 1)
    with pytest.raises(ValueError, match="file exceeds its byte budget"):
        instrument._sources(cases)


@pytest.mark.parametrize("changed", ["path", "version"])
@pytest.mark.parametrize("completed", [0, 1])
def test_native_client_drift_refuses_before_consuming_slot(instrument, tmp_path, monkeypatch, changed, completed):
    out = tmp_path / "run"
    client = {"path": "/fixture/bin/codex", "version": "codex-cli 0.169.0"}
    monkeypatch.setattr(instrument, "_native_client", lambda: client.copy())
    frozen = instrument.prepare(out, model="fixture", effort="high")
    if completed == 0:
        client[changed] += "-changed"
    invoked = []

    def invoke(*args):
        invoked.append(args)
        client[changed] += "-changed"
        return native_fixture(instrument, *args)

    monkeypatch.setattr(instrument.C, "_call", invoke)
    with pytest.raises(ValueError, match="frozen native Codex client changed"):
        instrument.execute(out, authorized_execute=frozen["freeze_sha256"])
    assert [item["kind"] for item in instrument.journal(out)] == (
        ["FROZEN"] + ["CONSUMED", "RECEIVED"] * completed
    )
    assert len(invoked) == completed


def native_fixture(r, actor, request, frozen):
    """Controller-side transport fixture, never a native execution claim."""
    batch = int(actor.name.split("-")[0]) - 1
    answers = r.read_json(
        Path(frozen["oracle"]) / frozen["batches"][batch]["answers"]["path"]
    )
    answer = json.dumps({"answers": answers, "source_ids": ["task-evidence"]})
    prepared = launch.prepare(actor, "request.json", method_policy="existing")
    count = 10 if actor.name.endswith("baseline") else 9
    identity = r.C._sha(str(actor).encode())
    return {
        **{
            k: prepared[k]
            for k in (
                "request_sha256",
                "context_sha256",
                "prompt_sha256",
                "memory_receipts",
            )
        },
        "native_completion": "COMPLETED_UNGRADED",
        "usage_scope": "fresh_thread_total",
        "usage_status": "PROVIDER_REPORTED",
        "usage_report_count": 1,
        "resumed_from": None,
        "usage": {
            "input_tokens": count - 1,
            "cached_input_tokens": 0,
            "output_tokens": 1,
        },
        "permission_boundary": "observed_parent_file_and_command_control",
        "eval_deny_root_sha256": r.C._sha(frozen["oracle"].encode()),
        "thread_id": identity,
        "evaluation_boundary": {
            "status": "OBSERVED_PARENT_FILE_AND_COMMAND_CONTROL",
            "mcp_surface": "OBSERVED_EMPTY",
            "usage_boundary": "native_upstream_completions_after_terminal_read_barrier",
            "resolved": {
                "model": frozen["model"],
                "reasoningEffort": frozen["effort"],
                "modelProvider": "openai",
                "approvalPolicy": "never",
            },
            "provider_usage": {
                "status": "OBSERVED_UPSTREAM_COMPLETIONS",
                "responses": 1,
                "response_id_sha256": [identity],
                "scope": "fresh native thread upstream completions; "
                "not whole-workflow cost",
                "input_tokens": count - 1,
                "cached_input_tokens": 0,
                "output_tokens": 1,
                "cache_write_input_tokens": 0,
                "reasoning_output_tokens": 0,
            },
        },
        "runtime_events": {
            "items": [{"item_type": "agent_message"}],
            "omitted_items": 0,
        },
        "answer": answer,
        "answer_sha256": r.C._sha(answer.encode()),
    }


def execute_fixture(lab, monkeypatch, change=None):
    r, out, prepared = lab

    def invoke(actor, request, frozen):
        events = r.journal(out)
        assert events[-1]["kind"] == "CONSUMED"
        receipt = native_fixture(r, actor, request, frozen)
        if change:
            change(receipt, actor)
        return receipt

    monkeypatch.setattr(r.C, "_call", invoke)
    return r.execute(out, authorized_execute=prepared["freeze_sha256"])


def test_requested_instrument_exists():
    assert (
        Path(__file__).resolve().parents[1] / "eval/reasoning_iteration.py"
    ).is_file()


def test_frozen_actors_satisfy_the_real_launch_oracle_boundary(lab, monkeypatch):
    r, out, _ = lab
    frozen = r.read_freeze(out)
    actor = out / "1-baseline"

    class PreflightReached(Exception):
        pass

    def before_model(*args, **kwargs):
        raise PreflightReached()

    monkeypatch.setattr(launch, "prepare", before_model)
    with pytest.raises(PreflightReached):
        r.C._call(actor, r.read_json(actor / "request.json"), frozen)


def test_closed_world_cases_and_balanced_order(lab):
    r, out, prepared = lab
    cases = r.load_cases()
    frozen = r.read_freeze(out)
    assert len(cases) == 24
    assert len(frozen["batches"]) == 6
    assert {len(b["ids"]) for b in frozen["batches"]} == {4}
    assert [b["order"][0] for b in frozen["batches"]] == ["baseline", "candidate"] * 3
    assert set(c["family"] for c in cases) == {
        "causal",
        "base_rate",
        "sql",
        "retry",
        "external_effect",
        "research",
        "intent",
    }
    assert len(r.CANDIDATE.split()) <= 60
    assert prepared["promotion"] == "NOT_GRANTED"


def test_compaction_uses_the_existing_guide_as_its_explicit_baseline(tmp_path, instrument):
    r = instrument
    out = tmp_path / "compaction"
    r.prepare(out, model="fixture-model", effort="high", comparison="existing-full-guide")
    frozen = r.read_freeze(out)
    baseline = (ROOT / "content/skills/work-loop/reasoning.md").read_text()
    assert frozen["comparison"] == "existing-full-guide"
    assert frozen["baseline"] == baseline
    request = r.read_json(out / "1-baseline/request.json")
    task = r._bound(frozen["oracle"], frozen["batches"][0]["task"])
    adapted, procedure = r._adapt_task(task, frozen["comparison"], "baseline", baseline)
    assert request["task"] == r.C._prompt(adapted, procedure)
    assert json.loads((out / "1-baseline/evidence.md").read_text())["selected_guidance"] == baseline
    assert json.loads((out / "1-candidate/evidence.md").read_text())["selected_guidance"] == r.CANDIDATE
    assert str((ROOT / "content/skills/work-loop/reasoning.md").resolve()) in frozen["sources"]


def test_check_accepts_the_same_run_by_absolute_and_relative_path(lab, monkeypatch):
    r, out, _ = lab
    execute_fixture(lab, monkeypatch)
    expected = r.replay(out)
    monkeypatch.chdir(out.parent)
    assert r.replay(Path(out.name)) == expected


def test_compaction_receipts_replay_against_both_real_contexts(tmp_path, instrument, monkeypatch):
    out = tmp_path / "comparison"
    frozen = instrument.prepare(out, model="fixture-model", effort="high",
                                max_tokens=350000, comparison="existing-full-guide")
    result = execute_fixture((instrument, out, frozen), monkeypatch)
    assert result["status"] == "PASS_BOUNDED"
    assert result["consumed_calls"] == 12
    assert result["promotion"] == "NOT_GRANTED"


def test_selected_compact_reference_matches_the_evaluated_candidate(instrument):
    reference = ROOT / "content/skills/work-loop/decision-check.md"
    assert reference.read_text().strip() == instrument.CANDIDATE


@pytest.mark.parametrize(
    "fault", ["empty", "duplicate", "unequal", "too_many", "missing_oracle"]
)
def test_invalid_case_sets_fail(instrument, fault):
    cases = instrument.load_cases()
    if fault == "empty":
        cases = []
    elif fault == "duplicate":
        cases[-1] = cases[0]
    elif fault == "unequal":
        cases.pop()
    elif fault == "too_many":
        cases *= 2
    else:
        cases[0].pop("expected")
    with pytest.raises(ValueError):
        instrument.validate_cases(cases)


def test_every_case_rejects_a_wrong_decision(instrument):
    for case in instrument.load_cases():
        expected = {case["id"]: case["expected"]}
        assert instrument.grade(
            expected, {"answers": expected, "source_ids": ["task-evidence"]}
        ) == {case["id"]: 1}
        wrong = copy.deepcopy(expected)
        field = next(iter(wrong[case["id"]]))
        wrong[case["id"]][field] = None
        assert instrument.grade(
            expected, {"answers": wrong, "source_ids": ["task-evidence"]}
        ) == {case["id"]: 0}


@pytest.mark.parametrize(
    "fault", ["empty", "unmatched", "missing", "citation", "extra", "boolean"]
)
def test_format_and_case_coverage_fail(instrument, fault):
    expected = {"one": {"result": 1}, "two": {"result": 2}}
    output = {"answers": copy.deepcopy(expected), "source_ids": ["task-evidence"]}
    if fault == "empty":
        expected, output["answers"] = {}, {}
    elif fault == "unmatched":
        output["answers"]["other"] = output["answers"].pop("one")
    elif fault == "missing":
        output["answers"].pop("one")
    elif fault == "citation":
        output["source_ids"] = []
    elif fault == "extra":
        output["grade"] = "PASS"
    else:
        output["answers"]["one"]["result"] = True
        assert instrument.grade(expected, output)["one"] == 0
        return
    with pytest.raises(ValueError):
        instrument.grade(expected, output)


def test_freeze_makes_no_calls_or_keys_in_actor_tasks(lab, monkeypatch):
    r, out, prepared = lab
    monkeypatch.setattr(
        r.C, "_call", lambda *a: pytest.fail("preparation cannot launch")
    )
    for batch in r.read_freeze(out)["batches"]:
        task = r.read_json(out / "oracle" / batch["task"]["path"])
        public = json.loads(task["evidence"])
        assert [c["id"] for c in public] == batch["ids"]
        assert all(set(c) == {"id", "facts", "output"} for c in public)
        injected = {**public[0], "expected": {"decision": "leaked"}}
        assert set(injected) != {"id", "facts", "output"}
    assert r.replay(out)["status"] == "HOLD"
    with pytest.raises(ValueError, match="authoriz"):
        r.execute(out, authorized_execute="unapproved")
    assert len(r.journal(out)) == 1


def test_bound_native_fixture_replays_and_reports_pairs(lab, monkeypatch):
    result = execute_fixture(lab, monkeypatch)
    assert result["status"] == "PASS_BOUNDED"
    assert result["promotion"] == "NOT_GRANTED"
    assert result["baseline_tokens"] == 60 and result["candidate_tokens"] == 54
    assert result["paired_token_differences"] == [-1] * 6
    assert result["paired_quality_differences"] == [0] * 6
    assert result["token_difference_se"] == 0
    assert result["usage_complete"] is True
    assert result == lab[0].replay(lab[1])


@pytest.mark.parametrize(
    "fault",
    [
        "wrong",
        "format",
        "missing_usage",
        "unknown_usage",
        "boundary",
        "model",
        "prompt",
        "context",
        "oracle",
        "tools",
        "duplicate_thread",
    ],
)
def test_native_controls_hold_and_keep_consumed_attempt(lab, monkeypatch, fault):
    identity = []

    def change(receipt, actor):
        if fault == "wrong":
            output = json.loads(receipt["answer"])
            key = next(iter(output["answers"]))
            output["answers"][key] = {"wrong": True}
            receipt["answer"] = json.dumps(output)
            receipt["answer_sha256"] = lab[0].C._sha(receipt["answer"].encode())
        elif fault == "format":
            receipt["answer"] = "{}"
            receipt["answer_sha256"] = lab[0].C._sha(b"{}")
        elif fault == "missing_usage":
            receipt["usage"].pop("output_tokens")
        elif fault == "unknown_usage":
            receipt["usage_status"] = "UNKNOWN"
        elif fault == "boundary":
            receipt["evaluation_boundary"]["status"] = "UNVERIFIED"
        elif fault == "model":
            receipt["evaluation_boundary"]["resolved"]["model"] = "other"
        elif fault in ("prompt", "context"):
            receipt[fault + "_sha256"] = "0" * 64
        elif fault == "oracle":
            receipt["eval_deny_root_sha256"] = "0" * 64
        elif fault == "tools":
            receipt["runtime_events"]["items"] = [{"item_type": "command_execution"}]
        elif identity:
            receipt["thread_id"] = identity[0]
        identity.append(receipt["thread_id"])

    result = execute_fixture(lab, monkeypatch, change)
    assert result["status"] == "HOLD" and result["promotion"] == "NOT_GRANTED"
    events = lab[0].journal(lab[1])
    assert any(e["kind"] == "CONSUMED" for e in events)
    assert any(e["kind"] == "RECEIVED" for e in events)
    assert list((lab[1] / "oracle/receipts").glob("*.json"))


def test_cost_increase_and_no_improvement_hold(lab, monkeypatch):
    def expensive(receipt, actor):
        receipt["usage"]["input_tokens"] = 10
        receipt["evaluation_boundary"]["provider_usage"]["input_tokens"] = 10

    result = execute_fixture(lab, monkeypatch, expensive)
    assert result["status"] == "HOLD"
    assert "no_strict_improvement" in result["holds"]
    # A fresh manifest is required for another comparison, consumed calls stay fixed.
    result = lab[0].replay(lab[1])
    assert result["baseline_tokens"] == result["candidate_tokens"] == 66


def test_aggregate_increase_holds(lab, monkeypatch):
    def expensive(receipt, actor):
        if actor.name.endswith("candidate"):
            receipt["usage"]["input_tokens"] = 20
            receipt["evaluation_boundary"]["provider_usage"]["input_tokens"] = 20

    result = execute_fixture(lab, monkeypatch, expensive)
    assert result["candidate_tokens"] > result["baseline_tokens"]
    assert result["status"] == "HOLD" and "candidate_cost_increase" in result["holds"]


def test_failure_unknown_usage_never_retries(lab, monkeypatch):
    r, out, prepared = lab
    calls = []

    def failure(*args):
        calls.append(1)
        raise RuntimeError("fixture protocol failure")

    monkeypatch.setattr(r.C, "_call", failure)
    first = r.execute(out, authorized_execute=prepared["freeze_sha256"])
    second = r.execute(out, authorized_execute=prepared["freeze_sha256"])
    assert first == second and len(calls) == 1
    assert first["status"] == "HOLD" and first["usage_complete"] is False
    assert first["unknown_attempts"] == [1]


def test_partial_failure_receipt_is_retained(lab, monkeypatch):
    r, out, prepared = lab

    def failure(actor, *args):
        (actor / "native.json.failure.json").write_text(
            json.dumps(
                {
                    "observed_usage_not_final": {"input_tokens": 7, "output_tokens": 2},
                    "usage_status": "PARTIAL_OR_UNKNOWN",
                }
            )
        )
        raise ValueError("fixture protocol refusal")

    monkeypatch.setattr(r.C, "_call", failure)
    result = r.execute(out, authorized_execute=prepared["freeze_sha256"])
    assert result["unknown_attempts"] == [1]
    assert result["partial_tokens_lower_bound"] == 9
    assert result["usage_complete"] is False


def test_resume_after_committed_receipt_does_not_repeat_a_call(lab, monkeypatch):
    r, out, prepared = lab
    append = r._append
    calls = []

    class ProcessLoss(BaseException):
        pass

    def crash(out, kind, data):
        event = append(out, kind, data)
        if kind == "RECEIVED":
            raise ProcessLoss()
        return event

    def invoke(*args):
        calls.append(args[0].name)
        return native_fixture(r, *args)

    monkeypatch.setattr(r.C, "_call", invoke)
    monkeypatch.setattr(r, "_append", crash)
    with pytest.raises(ProcessLoss):
        r.execute(out, authorized_execute=prepared["freeze_sha256"])
    monkeypatch.setattr(r, "_append", append)
    assert (
        r.execute(out, authorized_execute=prepared["freeze_sha256"])["status"]
        == "PASS_BOUNDED"
    )
    assert len(calls) == len(set(calls)) == 12


@pytest.mark.parametrize("artifact", ["freeze", "task", "answer", "receipt", "journal"])
def test_changed_artifacts_refuse_replay(lab, monkeypatch, artifact):
    execute_fixture(lab, monkeypatch)
    r, out, prepared = lab
    frozen = r.read_freeze(out)
    paths = {
        "freeze": out / "oracle/freeze.json",
        "task": out / "oracle" / frozen["batches"][0]["task"]["path"],
        "answer": out / "oracle" / frozen["batches"][0]["answers"]["path"],
        "receipt": next((out / "oracle/receipts").glob("*.json")),
        "journal": out / "oracle/journal/0002.json",
    }
    paths[artifact].write_text("{}")
    with pytest.raises(ValueError):
        r.replay(out)


def test_changed_runtime_refuses_before_launch(lab, monkeypatch):
    r, out, prepared = lab
    monkeypatch.setattr(r.C, "_runtime", lambda: {})
    monkeypatch.setattr(
        r.C, "_call", lambda *a: pytest.fail("changed runtime cannot launch")
    )
    with pytest.raises(ValueError, match="changed"):
        r.execute(out, authorized_execute=prepared["freeze_sha256"])


def test_ceiling_stops_further_launches(tmp_path, instrument, monkeypatch):
    out = tmp_path / "bounded"
    prepared = instrument.prepare(
        out, model="fixture-model", effort="high", timeout_seconds=5, max_tokens=10
    )
    calls = []

    def invoke(*args):
        calls.append(1)
        return native_fixture(instrument, *args)

    monkeypatch.setattr(instrument.C, "_call", invoke)
    result = instrument.execute(out, authorized_execute=prepared["freeze_sha256"])
    assert len(calls) == 1 and result["status"] == "HOLD"
    assert "token_ceiling_reached" in result["holds"]


def test_simulation_cannot_be_promoted_by_claim_or_result_file(
    tmp_path, instrument, monkeypatch
):
    out = tmp_path / "simulation"
    monkeypatch.setattr(
        instrument.C, "_call", lambda *a: pytest.fail("simulation cannot call native")
    )
    prepared = instrument.prepare(
        out, model="fixture-model", effort="high", mode="simulation"
    )
    result = instrument.execute(out, authorized_execute=prepared["freeze_sha256"])
    assert result["status"] == "HOLD" and result["evidence"] == "MODEL_FREE_SIMULATION"
    assert result["promotion"] == "NOT_GRANTED"
    (out / "result.json").write_text('{"promotion":"GRANTED","status":"PASS_BOUNDED"}')
    assert instrument.replay(out) == result
    command = [
        sys.executable,
        str(ROOT / "eval/check_reasoning_outcome.py"),
        str(out),
    ]
    checked = subprocess.run(command, capture_output=True, text=True, check=False)
    assert checked.returncode == 1
    assert json.loads(checked.stdout)["promotion"] == "NOT_GRANTED"


def test_prepare_and_execute_cli_are_separate(tmp_path):
    command = [sys.executable, str(ROOT / "eval/reasoning_iteration.py")]
    client = tmp_path / "codex"
    client.write_text("#!/bin/sh\n[ \"$1\" = --version ] || exit 42\nprintf '%s\\n' 'codex-cli 0.169.0'\n")
    client.chmod(0o700)
    prepared = subprocess.run(
        command
        + ["prepare", str(tmp_path / "cli"), "--model", "fixture", "--effort", "high"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ.get("PATH", "")},
    )
    assert prepared.returncode == 0
    assert json.loads(prepared.stdout)["status"] == "FROZEN_NOT_RUN"
    freeze = json.loads((tmp_path / "cli/oracle/freeze.json").read_bytes())
    assert freeze["native_cli"] == {"path": str(client.resolve()), "version": "codex-cli 0.169.0"}
    refused = subprocess.run(
        command + ["execute", str(tmp_path / "cli")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert refused.returncode != 0


def test_independent_sql_and_arithmetic_oracles(instrument):
    expected = {c["id"]: c["expected"] for c in instrument.load_cases()}
    con = sqlite3.connect(":memory:")
    con.executescript(
        "CREATE TABLE orders(id TEXT,total INTEGER);"
        'INSERT INTO orders VALUES ("A",100),("B",80);'
        'CREATE TABLE lines(order_id TEXT); INSERT INTO lines VALUES ("A"),("A"),("B");'
        "CREATE TABLE payments(order_id TEXT);"
        'INSERT INTO payments VALUES ("A"),("A"),("A"),("B"),("B");'
    )
    rows, total = con.execute(
        "SELECT COUNT(*),SUM(total) FROM orders "
        "JOIN lines ON lines.order_id=orders.id "
        "JOIN payments ON payments.order_id=orders.id"
    ).fetchone()
    once = con.execute("SELECT SUM(total) FROM orders").fetchone()[0]
    con.close()
    assert expected["join_fanout"] == {
        "joined_rows": rows,
        "joined_sum_total": total,
        "once_per_order_total": once,
    }
    assert expected["screen_rare"]["condition_given_positive"] == "8/" + str(8 + 99)
    assert expected["allocation"]["treated_recoveries"] == 9 + 18
    assert expected["allocation"]["untreated_recoveries"] == 72 + 1
    assert expected["retry_deadline"]["attempts_started"] == sum(
        4 * n + 2 * (n - 1) <= 15 for n in range(1, 4)
    )
    assert expected["multiple_tests"]["rejected_hypotheses"] == sum(
        p <= 0.05 / 20 for p in [0.01] * 20
    )
    assert expected["paired_research"]["paired_error_differences"] == [
        a - b for a, b in zip([3, 5, 7, 9], [4, 6, 8, 10])
    ]
    assert expected["teach_distribution"] == {
        "result": 6 * (2 + 5),
        "work": [6 * 2, 6 * 5, 6 * (2 + 5)],
    }


def test_quality_gain_at_equal_cost_passes(lab, monkeypatch):
    def change(receipt, actor):
        receipt["usage"]["input_tokens"] = 9
        receipt["evaluation_boundary"]["provider_usage"]["input_tokens"] = 9
        if actor.name.endswith("baseline"):
            output = json.loads(receipt["answer"])
            output["answers"][next(iter(output["answers"]))] = {"wrong": True}
            receipt["answer"] = json.dumps(output)
            receipt["answer_sha256"] = lab[0].C._sha(receipt["answer"].encode())

    result = execute_fixture(lab, monkeypatch, change)
    assert result["status"] == "PASS_BOUNDED"
    assert result["paired_token_differences"] == [0] * 6
    assert result["paired_quality_differences"] == [1] * 6


def test_corresponding_case_regression_cannot_hide_in_batch_average(lab, monkeypatch):
    def change(receipt, actor):
        output = json.loads(receipt["answer"])
        key = list(output["answers"])[0 if actor.name.endswith("baseline") else 1]
        output["answers"][key] = {"wrong": True}
        receipt.update(answer=json.dumps(output), promotion="GRANTED", score=1)
        receipt["answer_sha256"] = lab[0].C._sha(receipt["answer"].encode())

    result = execute_fixture(lab, monkeypatch, change)
    assert result["paired_quality_differences"] == [0]
    assert "case_quality_regression" in result["holds"]
    assert result["promotion"] == "NOT_GRANTED"


def test_incomplete_last_provider_observation_stays_incomplete(lab, monkeypatch):
    def change(receipt, actor):
        if actor.name == "6-baseline":
            receipt["evaluation_boundary"]["provider_usage"].pop("responses")

    result = execute_fixture(lab, monkeypatch, change)
    assert result["consumed_calls"] == 12
    assert result["status"] == "HOLD" and result["usage_complete"] is False
    assert result["known_consumed_tokens"] == 114


def test_receipt_persisted_before_event_keeps_usage_lower_bound(lab, monkeypatch):
    r, out, prepared = lab
    # Failure is injected after the immutable receipt exists, before its event commits.
    append = r._append

    class ProcessLoss(BaseException):
        pass

    def crash(out, kind, data):
        if kind == "RECEIVED":
            raise ProcessLoss()
        return append(out, kind, data)

    monkeypatch.setattr(r.C, "_call", lambda *a: native_fixture(r, *a))
    monkeypatch.setattr(r, "_append", crash)
    with pytest.raises(ProcessLoss):
        r.execute(out, authorized_execute=prepared["freeze_sha256"])
    monkeypatch.setattr(r, "_append", append)
    result = r.replay(out)
    assert result["status"] == "HOLD" and result["unknown_attempts"] == [1]
    assert result["partial_tokens_lower_bound"] == 10
    assert len(result["orphan_receipts"]) == 1
    monkeypatch.setattr(
        r.C, "_call", lambda *a: pytest.fail("consumed unknown cannot retry")
    )
    assert r.execute(out, authorized_execute=prepared["freeze_sha256"]) == result


def test_completed_native_file_survives_answer_read_failure(lab, monkeypatch):
    r, out, prepared = lab

    def failure(actor, *args):
        (actor / "native.json").write_text(
            json.dumps(
                {
                    "usage": {"input_tokens": 8, "output_tokens": 4},
                    "usage_status": "PARTIAL_OR_UNKNOWN",
                }
            )
        )
        raise ValueError("fixture answer retention failure")

    monkeypatch.setattr(r.C, "_call", failure)
    result = r.execute(out, authorized_execute=prepared["freeze_sha256"])
    assert (
        result["unknown_attempts"] == [1] and result["partial_tokens_lower_bound"] == 12
    )


def test_immutable_writes_reuse_identical_objects_and_refuse_updates(
    tmp_path, instrument
):
    path = tmp_path / "receipt.json"
    original = instrument._immutable(path, {"consumed": True})
    assert instrument._immutable(path, {"consumed": True}) == original
    with pytest.raises(ValueError, match="immutable"):
        instrument._immutable(path, {"consumed": False})
    assert instrument.read_json(path) == {"consumed": True}


def test_actual_actor_requests_and_contexts_are_bound_at_prepare(lab):
    r, out, prepared = lab
    frozen = r.read_freeze(out)
    for index, batch in enumerate(frozen["batches"], 1):
        for arm in ("baseline", "candidate"):
            actor = out / f"{index}-{arm}"
            actual = launch.prepare(actor, "request.json", method_policy="existing")
            assert batch["actors"][arm] == {key: actual[key] for key in r.BINDINGS}
            request = r.read_json(actor / "request.json")
            task = r.read_json(out / "oracle" / batch["task"]["path"])
            assert request["task"] == r.C._prompt(
                task, r.CANDIDATE if arm == "candidate" else None
            )


def test_changed_prepared_context_prevents_consumption(lab, monkeypatch):
    r, out, prepared = lab
    actor = out / "1-baseline"
    request = r.read_json(actor / "request.json")
    request["task"] += "\nChanged after freeze"
    (actor / "request.json").write_bytes(r.P.encoded(request))
    monkeypatch.setattr(
        r.C, "_call", lambda *a: pytest.fail("changed prompt cannot launch")
    )
    with pytest.raises(ValueError, match="changed"):
        r.execute(out, authorized_execute=prepared["freeze_sha256"])
    assert len(r.journal(out)) == 1


@pytest.mark.parametrize(
    "configuration",
    [
        {"max_tokens": 350001},
        {"max_tokens": True},
        {"timeout_seconds": 121},
        {"timeout_seconds": False},
        {"effort": "unbounded"},
        {"model": ""},
        {"mode": "claimed-native"},
    ],
)
def test_invalid_frozen_resource_settings_refuse(tmp_path, instrument, configuration):
    settings = {"model": "fixture-model", "effort": "high", **configuration}
    with pytest.raises(ValueError):
        instrument.prepare(tmp_path / "invalid", **settings)
    assert not (tmp_path / "invalid").exists()


def test_source_bindings_work_without_any_ignored_local_helpers(tmp_path, instrument, monkeypatch):
    import shutil
    root = tmp_path / "checkout"
    (root / "eval").mkdir(parents=True)
    (root / "src/agent_harness").mkdir(parents=True)
    checker = ROOT / "eval/check_reasoning_outcome.py"
    assert checker.is_file(), "the replay entrypoint must ship in a clean checkout"
    shutil.copyfile(checker, root / "eval/check_reasoning_outcome.py")
    monkeypatch.setattr(instrument, "ROOT", root)
    sources = instrument._sources(instrument.CASES)
    assert str((root / "eval/check_reasoning_outcome.py").resolve()) in sources
    assert not (root / ".harness-work").exists()
    (root / "eval/check_reasoning_outcome.py").unlink()
    with pytest.raises(FileNotFoundError):
        instrument._sources(instrument.CASES)
