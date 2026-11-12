"""Advisory hook observations and bounded, session-scoped board delivery."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from agent_harness import cli
from agent_harness.operational_state import OperationalState


@pytest.fixture
def board(tmp_path, monkeypatch):
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HARNESS_HOME", str(home / ".agent-harness"))
    monkeypatch.delenv("HARNESS_DISABLE", raising=False)
    monkeypatch.delenv("HARNESS_PROJECT", raising=False)
    return root, OperationalState(home / ".agent-harness", root)


def payload(board, **values):
    return {"cwd": str(board[0]), "session_id": "actual-session", **values}


def task_id(session="actual-session"):
    return "hook-session-" + hashlib.sha256(session.encode()).hexdigest()


def observe(board, event="prompt", *, deliver=True, **values):
    from agent_harness.board_hooks import participate
    return participate(payload(board, **values), event, deliver=deliver)


def peer(board, task="peer", stage="inspect", expected=0):
    return board[1].put(task, {"stage": stage}, expected=expected,
                        request_id=f"{task}-{expected}")


@pytest.mark.integration
def test_startup_registers_actual_session_with_only_observed_advisory_state(board, capsys):
    event = payload(board, hook_event_name="SessionStart", source="startup")
    assert cli.op_context_hook(io.StringIO(json.dumps(event))) == 0
    rows = board[1].snapshot()["tasks"]
    assert len(rows) == 1
    assert rows[0]["task"] == task_id()
    assert rows[0]["value"]["stage"] == "observed_startup"
    assert rows[0]["status"] == "open"
    assert set(rows[0]["value"]) == {"stage", "summary"}
    assert capsys.readouterr().out == ""


@pytest.mark.integration
def test_prompt_registers_even_without_prompt_text_and_never_stores_it(board, capsys):
    event = payload(board, hook_event_name="UserPromptSubmit", prompt="")
    assert cli.prompt_hook(io.StringIO(json.dumps(event))) == 0
    rows = board[1].snapshot()["tasks"]
    assert len(rows) == 1
    assert rows[0]["task"] == task_id()
    assert rows[0]["value"]["stage"] == "observed_prompt"
    assert capsys.readouterr().out == ""


@pytest.mark.integration
@pytest.mark.parametrize("event", ["startup", "resume", "compact", "prompt", "stop", "precompact"])
def test_observations_share_one_row_without_intent_or_completion(board, event):
    observe(board, "startup")
    observe(board, event, prompt="PRIVATE-PROMPT", transcript_path="/private/transcript")
    rows = board[1].snapshot()["tasks"]
    assert len(rows) == 1 and rows[0]["task"] == task_id()
    assert rows[0]["value"]["stage"] == "observed_" + event
    assert rows[0]["status"] == "open" and rows[0]["activity"] == "idle_unprepared"
    assert "PRIVATE-PROMPT" not in json.dumps(rows)
    assert "/private/transcript" not in json.dumps(rows)


@pytest.mark.integration
def test_unchanged_delivery_is_suppressed_across_lifecycle_transitions(board):
    peer(board)
    assert "inspect" in observe(board, "startup")
    for event in ("prompt", "stop", "precompact", "prompt"):
        assert observe(board, event) == ""
    assert board[1].snapshot()["cursor"] == 6  # peer plus five observed transitions


@pytest.mark.integration
def test_startup_and_resume_recover_fresh_context_even_after_prior_delivery(board):
    peer(board)
    assert "inspect" in observe(board, "startup")
    assert "inspect" in observe(board, "startup")
    assert "inspect" in observe(board, "resume")
    assert observe(board) == ""


@pytest.mark.integration
def test_delta_delivers_only_changed_peer_and_is_consumed_once(board):
    peer(board, "alpha")
    peer(board, "beta")
    observe(board, "startup")
    peer(board, "alpha", "verify", expected=1)
    output = observe(board)
    assert '"mode":"delta"' in output and "verify" in output
    assert "beta" not in output
    assert observe(board) == ""


@pytest.mark.integration
def test_stop_publication_does_not_consume_context_that_cannot_be_delivered(board):
    peer(board)
    observe(board, "startup")
    peer(board, stage="verify", expected=1)
    assert observe(board, "stop", deliver=False) == ""
    assert "verify" in observe(board)
    assert observe(board) == ""


@pytest.mark.integration
def test_changed_checkpoint_freshness_is_delivered_without_an_operational_event(board):
    checkpoint = board[0] / "handoff.md"
    checkpoint.write_text("advisory")
    board[1].put("peer", {"goal": "inspect", "checkpoint": "handoff.md", "next": "check"},
                 expected=0, request_id="checkpoint")
    observe(board, "startup")
    checkpoint.unlink()
    assert "checkpoint_missing" in observe(board)
    assert observe(board) == ""


@pytest.mark.integration
def test_summary_and_tracking_are_bounded_and_overflow_is_explicit(board):
    from agent_harness.board_hooks import MAX_CONTEXT_BYTES, MAX_TRACKING_BYTES
    for number in range(40):
        peer(board, f"peer-{number}", "x" * 1000)
    output = observe(board, "startup")
    packet = json.loads(output.split(": ", 1)[1])
    assert len(output.encode()) <= MAX_CONTEXT_BYTES
    assert packet["omitted"] > 0 and packet["read_more"] == "harness task status --json"
    for path in board[1].path.parent.rglob("*.json"):
        assert path.stat().st_size <= MAX_TRACKING_BYTES


@pytest.mark.integration
def test_event_overflow_falls_back_to_current_bounded_summary(board):
    peer(board)
    observe(board, "startup")
    for version in range(1, 40):
        peer(board, stage=f"stage-{version}", expected=version)
    output = observe(board)
    assert '"mode":"snapshot"' in output and "stage-39" in output
    assert observe(board) == ""


@pytest.mark.integration
def test_payload_cwd_controls_scope_even_when_launcher_and_environment_disagree(board, tmp_path, monkeypatch):
    other = tmp_path / "other"
    (other / ".git").mkdir(parents=True)
    monkeypatch.chdir(other)
    monkeypatch.setenv("HARNESS_PROJECT", str(other))
    observe(board)
    assert board[1].snapshot()["tasks"][0]["task"] == task_id()
    foreign = OperationalState(board[1].path.parent.parent, other)
    assert foreign.snapshot()["tasks"] == []


@pytest.mark.case
@pytest.mark.parametrize("changes", [
    {"cwd": "relative"}, {"cwd": "/absent-board-project"}, {"cwd": 7},
    {"session_id": ""}, {"session_id": None}, {"session_id": "x" * 4097},
    {"hook_event_name": "Unrelated"},
])
def test_invalid_supported_payload_is_reported_without_publishing(board, capsys, changes):
    assert observe(board, **changes) == ""
    assert board[1].snapshot()["tasks"] == []
    assert "unavailable" in capsys.readouterr().err


@pytest.mark.case
def test_missing_host_identity_is_quiet_without_inventing_a_session(board, capsys):
    from agent_harness.board_hooks import participate
    assert participate({"cwd": str(board[0])}, "stop") == ""
    assert participate({"session_id": "real"}, "prompt") == ""
    assert board[1].snapshot()["tasks"] == []
    assert capsys.readouterr().err == ""


@pytest.mark.integration
def test_explicit_disable_opts_out_before_opening_board_or_tracking(board, monkeypatch, capsys):
    monkeypatch.setenv("HARNESS_DISABLE", "run_checks, op_state")
    assert observe(board, "startup") == ""
    assert not board[1].path.parent.exists()
    assert capsys.readouterr().err == ""


@pytest.mark.integration
def test_distinct_real_session_ids_have_distinct_rows_and_delivery_cursors(board):
    peer(board)
    assert "inspect" in observe(board, session_id="../actual-session")
    assert "inspect" in observe(board, session_id=".._actual-session")
    rows = board[1].snapshot()["tasks"]
    assert {row["task"] for row in rows} >= {
        task_id("../actual-session"), task_id(".._actual-session")}
    assert observe(board, session_id=".._actual-session") == ""


@pytest.mark.integration
def test_concurrent_processes_share_atomic_cursor_and_registration(board):
    peer(board)
    script = """
import json,sys
from agent_harness.board_hooks import participate
print(participate(json.loads(sys.argv[1]), 'prompt'), end='')
"""
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    command = [sys.executable, "-c", script, json.dumps(payload(board))]

    def invoke(_):
        return subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(invoke, range(5)))
    assert all(result.returncode == 0 and not result.stderr for result in results)
    assert sum(bool(result.stdout) for result in results) == 1
    assert board[1].snapshot()["cursor"] == 2
    assert observe(board) == ""


@pytest.mark.integration
def test_corrupt_tracking_is_explicit_and_does_not_replay_context(board, capsys):
    peer(board)
    observe(board)
    paths = list(board[1].path.parent.rglob("*.json"))
    assert len(paths) == 1
    paths[0].write_text("PRIVATE-CORRUPTION")
    assert observe(board) == ""
    error = capsys.readouterr().err
    assert "unavailable" in error and "PRIVATE-CORRUPTION" not in error


@pytest.mark.integration
def test_tracking_symlink_cannot_read_or_replace_another_file(board, tmp_path, capsys):
    observe(board)
    tracking = next(board[1].path.parent.rglob("*.json"))
    retained = tmp_path / "retained"
    retained.write_text("PRIVATE-RETAINED")
    tracking.unlink()
    tracking.symlink_to(retained)
    assert observe(board) == ""
    assert retained.read_text() == "PRIVATE-RETAINED" and tracking.is_symlink()
    assert "unavailable" in capsys.readouterr().err


@pytest.mark.integration
def test_redirected_operational_directory_cannot_create_tracking_outside_store(board, tmp_path, capsys):
    retained = tmp_path / "retained"
    retained.mkdir()
    board[1].path.parent.parent.mkdir(parents=True)
    board[1].path.parent.symlink_to(retained, target_is_directory=True)
    assert observe(board) == ""
    assert list(retained.iterdir()) == []
    assert "unavailable" in capsys.readouterr().err


@pytest.mark.integration
def test_atomic_tracking_failure_retains_the_previous_delivery_cursor(board, monkeypatch, capsys):
    from agent_harness import board_hooks
    peer(board)
    observe(board, "startup")
    tracking = next(board[1].path.parent.rglob("*.json"))
    original = tracking.read_bytes()
    peer(board, stage="verify", expected=1)
    replace = board_hooks.os.replace

    def failed_replace(*_args, **_kwargs):
        raise OSError("PRIVATE-STORAGE-ERROR")
    monkeypatch.setattr(board_hooks.os, "replace", failed_replace)
    assert observe(board) == ""
    assert tracking.read_bytes() == original
    assert not list(tracking.parent.glob(".hook-*"))
    error = capsys.readouterr().err
    assert "unavailable" in error and "PRIVATE-STORAGE-ERROR" not in error
    monkeypatch.setattr(board_hooks.os, "replace", replace)
    assert "verify" in observe(board)
    assert observe(board) == ""


@pytest.mark.integration
def test_busy_tracking_lock_is_bounded_and_preserves_duplicate_suppression(board, monkeypatch, capsys):
    import fcntl
    from agent_harness import board_hooks
    peer(board)
    observe(board)
    lock = next(board[1].path.parent.rglob("*.lock"))
    with lock.open("rb") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        times = iter([0, 1])
        with monkeypatch.context() as patch:
            patch.setattr(board_hooks.time, "monotonic", lambda: next(times))
            assert observe(board) == ""
    assert "TimeoutError" in capsys.readouterr().err
    assert observe(board) == ""


@pytest.mark.integration
def test_observations_never_read_transcripts_call_models_or_change_graph_marks(board, monkeypatch, capsys):
    graph = board[0] / "plan.md"
    original = "- [ ] 1. Verify independently | gate: false\n"
    graph.write_text(original)
    transcript = board[0] / "private-transcript"
    transcript.write_text("PRIVATE-TRANSCRIPT")
    path_open = Path.open

    def no_transcript(path, *args, **kwargs):
        assert path != transcript, "board read a transcript"
        return path_open(path, *args, **kwargs)

    def no_process(*_args, **_kwargs):
        raise AssertionError("board invoked a process")
    monkeypatch.setattr(Path, "open", no_transcript)
    monkeypatch.setattr(subprocess, "run", no_process)
    monkeypatch.setattr(subprocess, "Popen", no_process)
    for event in ("startup", "prompt", "stop", "precompact", "resume"):
        observe(board, event, transcript_path=str(transcript))
    assert graph.read_text() == original
    assert len(board[1].snapshot()["tasks"]) == 1
    assert capsys.readouterr().err == ""


@pytest.mark.case
def test_board_errors_are_explicit_redacted_and_do_not_swallow_interrupts(board, monkeypatch, capsys):
    def fail(*_args, **_kwargs):
        raise RuntimeError("PRIVATE-ERROR")
    monkeypatch.setattr(OperationalState, "snapshot", fail)
    assert observe(board) == ""
    error = capsys.readouterr().err
    assert "unavailable" in error and "RuntimeError" in error and "PRIVATE-ERROR" not in error

    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt
    monkeypatch.setattr(OperationalState, "snapshot", interrupt)
    with pytest.raises(KeyboardInterrupt):
        observe(board)


@pytest.mark.integration
@pytest.mark.parametrize("handler,event", [
    (cli.stop_hook, "stop"), (cli.capture_hook, "stop"), (cli.kimi_stop_hook, "stop"),
    (cli.kimi_precompact_hook, "precompact"),
])
def test_available_stop_handlers_publish_before_existing_optional_processing(board, handler, event, capsys):
    # No transcript is provided. Existing capture/guard behavior still owns its own input handling.
    assert handler(io.StringIO(json.dumps(payload(board)))) == 0
    rows = board[1].snapshot()["tasks"]
    assert len(rows) == 1 and rows[0]["value"]["stage"] == "observed_" + event
    assert capsys.readouterr().out == ""


@pytest.mark.integration
def test_context_registration_and_delivery_survive_memory_recovery_failure(board, monkeypatch, capsys):
    from agent_harness.mcp.memory import Memory
    peer(board)

    def unavailable(*_args, **_kwargs):
        raise ValueError("memory unavailable")
    monkeypatch.setattr(Memory, "resume_context", unavailable)
    event = payload(board, hook_event_name="SessionStart", source="resume")
    assert cli.context_hook(io.StringIO(json.dumps(event))) == 0
    output = capsys.readouterr()
    assert "inspect" in output.out and "unavailable" in output.err
    assert any(row["task"] == task_id() for row in board[1].snapshot()["tasks"])


@pytest.mark.integration
def test_prompt_delivery_survives_recall_failure_and_keeps_total_context_bounded(board, monkeypatch, capsys):
    peer(board)

    def recalled(*_args, **_kwargs):
        return subprocess.CompletedProcess([], 0, "x" * 1200, "")
    monkeypatch.setattr(cli.subprocess, "run", recalled)
    event = payload(board, prompt="PRIVATE-PROMPT")
    assert cli.prompt_hook(io.StringIO(json.dumps(event))) == 0
    output = capsys.readouterr().out
    assert "inspect" in output and "omitted" in output
    assert "PRIVATE-PROMPT" not in output and len(output.encode()) <= 1200

    peer(board, stage="verify", expected=1)

    def failed(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("recall", 2)
    monkeypatch.setattr(cli.subprocess, "run", failed)
    assert cli.prompt_hook(io.StringIO(json.dumps(event))) == 0
    output = capsys.readouterr()
    assert "verify" in output.out and "unavailable" in output.err


@pytest.mark.integration
@pytest.mark.parametrize("field,limit", [("goal", 100), ("stage", 80), ("summary", 160),
                                       ("checkpoint", 120), ("next", 120), ("blocked_on", 120)])
def test_display_redacts_the_full_field_before_truncating(board, field, limit):
    value = "x" * (limit - 10) + " sk-" + "A" * 60
    board[1].put("peer", {field: value}, expected=0, request_id="secret-span")
    output = observe(board)
    assert "sk-" not in output and "AAAA" not in output
    assert "REDACT" in output


@pytest.mark.integration
def test_omitted_rows_remain_pending_and_delivered_rows_do_not_repeat(board):
    for number in range(8):
        peer(board, f"peer-{number}", f"inspect-{number}")
    first = observe(board)
    packet = json.loads(first.split(": ", 1)[1])
    assert packet["omitted"] > 0
    tracking = next(board[1].path.parent.rglob("*.json"))
    assert json.loads(tracking.read_text())["cursor"] < board[1].snapshot()["cursor"]
    seen = [row["task"] for row in packet["tasks"]]
    for _ in range(10):
        output = observe(board)
        if output:
            seen += [row["task"] for row in json.loads(output.split(": ", 1)[1])["tasks"]]
    assert sorted(seen) == [f"peer-{number}" for number in range(8)]
    assert observe(board) == ""
    assert json.loads(tracking.read_text())["cursor"] == board[1].snapshot()["cursor"]


@pytest.mark.integration
def test_multibyte_oversized_first_row_cannot_starve_following_rows(board):
    from agent_harness.board_hooks import MAX_CONTEXT_BYTES
    board[1].put("a-wide", {field: "界" * 120 for field in
                           ("goal", "stage", "summary", "next", "blocked_on")},
                 expected=0, request_id="wide")
    peer(board, "b-small", "readable")
    seen = []
    for _ in range(4):
        output = observe(board)
        assert len(output.encode()) <= MAX_CONTEXT_BYTES
        if output:
            seen += [row["task"] for row in json.loads(output.split(": ", 1)[1])["tasks"]]
    assert sorted(seen) == ["a-wide", "b-small"]
    assert observe(board) == ""


@pytest.mark.integration
def test_unchanged_leased_peer_does_not_repeat_or_expose_lease_token(board):
    peer(board)
    claim = board[1].claim("peer", expected=1, request_id="lease", ttl=300)
    first = observe(board)
    assert "leased_unverified" in first and claim["token"] not in first
    assert observe(board) == ""


@pytest.mark.integration
def test_display_and_acknowledgement_use_the_exact_same_snapshot(board, monkeypatch):
    peer(board)
    observe(board)
    peer(board, stage="before-race", expected=1)
    snapshot = OperationalState.snapshot
    observed = []

    def racing_snapshot(store):
        state = snapshot(store)
        observed.append(state)
        if len(observed) == 1:
            peer(board, stage="after-race", expected=2)
        return state
    with monkeypatch.context() as patch:
        patch.setattr(OperationalState, "snapshot", racing_snapshot)
        output = observe(board)
    assert len(observed) == 1
    assert "before-race" in output and "after-race" not in output
    assert "after-race" in observe(board)


@pytest.mark.integration
def test_lifecycle_only_peers_stay_diagnostic_and_never_create_context_noise(board):
    board[1].put("other-session", {"stage": "observed_prompt", "summary": "advisory observation"},
                 expected=0, request_id="other-prompt")
    assert observe(board, "startup") == ""
    assert observe(board) == ""
    board[1].put("other-session", {"stage": "observed_stop", "summary": "advisory observation"},
                 expected=1, request_id="other-stop")
    assert observe(board) == ""
    rows = board[1].snapshot()["tasks"]
    assert {row["task"] for row in rows} == {"other-session", task_id()}
    assert next(row for row in rows if row["task"] == "other-session")["value"]["stage"] == "observed_stop"


@pytest.mark.integration
@pytest.mark.parametrize("field", ["goal", "checkpoint", "next", "evidence"])
def test_lifecycle_rows_with_actual_task_handles_are_still_delivered(board, field):
    value = {"stage": "observed_prompt", field: "task handle"}
    if field in {"checkpoint", "evidence"}:
        (board[0] / "handoff.md").write_text("advisory evidence")
        value[field] = "handoff.md"
    if field == "evidence":
        value["evidence_sha256"] = board[1].bind_evidence("handoff.md")
    board[1].put("task-bearing-session", value, expected=0, request_id="task-bearing")
    output = observe(board)
    assert "task-bearing-session" in output and field in output
    assert observe(board) == ""
