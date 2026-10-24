"""Native lifecycle receipts stay distinct from task evaluation."""
import json
from pathlib import Path
import sys
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent_harness import launch  # noqa: E402


@pytest.mark.parametrize("terminal_failure", [None, "turn.failed", "error"])
def test_terminal_failure_overrides_completion(tmp_path, terminal_failure):
    events = [
        {"type": "thread.started", "thread_id": "fixture-thread"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "Finished."}},
        {"type": "turn.completed", "usage": {
            "input_tokens": 10, "cached_input_tokens": 2, "output_tokens": 3}},
    ]
    if terminal_failure:
        events.append({"type": terminal_failure, "error": {"message": "fixture failure"}})
    raw = b"".join(json.dumps(event).encode() + b"\n" for event in events)
    prepared = {"schema": launch.SCHEMA, "request_sha256": "request-digest",
                "context_sha256": "context-digest", "memory_receipts": [],
                "method_policy": "existing", "prompt": "Fixture task"}

    def native_process(*args, **kwargs):
        kwargs["stdout"].write(raw)
        return mock.Mock(pid=12345, returncode=0, poll=mock.Mock(return_value=0))

    with mock.patch.object(launch, "prepare", return_value=prepared), \
            mock.patch.object(launch.shutil, "which", return_value="/fixture/codex"), \
            mock.patch.object(launch.subprocess, "Popen", side_effect=native_process):
        result = launch.execute(tmp_path, "request.json", "receipt.json")

    saved = json.loads((tmp_path / "receipt.json").read_text())
    assert saved == result
    assert saved["exit_code"] == 0
    assert saved["native_completion"] == ("FAILED" if terminal_failure else "COMPLETED_UNGRADED")
    assert saved["answer"] == (None if terminal_failure else "Finished.")
    assert saved["task_evaluation"] == "NOT_RUN"
    assert saved["event_counts"] == {event["type"]: 1 for event in events}
    assert saved["last_event_type"] == (terminal_failure or "turn.completed")
    assert saved["usage_status"] == ("PARTIAL_OR_UNKNOWN" if terminal_failure
                                     else "PROVIDER_REPORTED")


def test_multiple_usage_reports_do_not_silently_take_the_last_one(tmp_path):
    events = [
        {"type": "item.completed", "item": {"type": "agent_message", "text": "Finished."}},
        {"type": "turn.completed", "usage": {"input_tokens": 100,
                                               "cached_input_tokens": 50, "output_tokens": 10}},
        {"type": "turn.completed", "usage": {"input_tokens": 150,
                                               "cached_input_tokens": 75, "output_tokens": 20}},
    ]
    raw = b"".join(json.dumps(event).encode() + b"\n" for event in events)
    prepared = {"schema": launch.SCHEMA, "request_sha256": "request-digest",
                "context_sha256": "context-digest", "memory_receipts": [],
                "method_policy": "existing", "prompt": "Fixture task"}

    def native_process(*args, **kwargs):
        kwargs["stdout"].write(raw)
        return mock.Mock(pid=12345, returncode=0, poll=mock.Mock(return_value=0))

    with mock.patch.object(launch, "prepare", return_value=prepared), \
            mock.patch.object(launch.shutil, "which", return_value="/fixture/codex"), \
            mock.patch.object(launch.subprocess, "Popen", side_effect=native_process):
        result = launch.execute(tmp_path, "request.json", "receipt.json")

    assert result["native_completion"] == "COMPLETED_UNGRADED"
    assert result["usage"] is None
    assert result["usage_status"] == "AMBIGUOUS"
    assert result["usage_report_count"] == 2


def test_eval_profile_can_deny_the_original_frozen_pack_outside_a_task_projection(tmp_path):
    task = tmp_path / "heldout-projection-fixture" / "memory-log-code"
    task.mkdir(parents=True)
    pack = tmp_path / "heldout-prereg-fixture"
    (pack / "oracle").mkdir(parents=True)
    (pack / "freeze.json").write_text("{}")
    (pack / "rubric.json").write_text("{}")
    prepared = {"schema": launch.SCHEMA, "request_sha256": "request-digest",
                "context_sha256": "context-digest", "memory_receipts": [],
                "method_policy": "existing", "prompt": "Fixture task"}
    events = [
        {"type": "item.completed", "item": {"type": "agent_message", "text": "ok"}},
        {"type": "turn.completed", "usage": {"input_tokens": 2,
                                               "cached_input_tokens": 0, "output_tokens": 1}},
    ]
    raw = b"".join(json.dumps(event).encode() + b"\n" for event in events)
    seen = []

    def native_process(argv, **kwargs):
        seen.extend(argv)
        kwargs["stdout"].write(raw)
        return mock.Mock(pid=12345, returncode=0, poll=mock.Mock(return_value=0))

    with mock.patch.object(launch, "prepare", return_value=prepared), \
            mock.patch.object(launch.shutil, "which", return_value="/fixture/codex"), \
            mock.patch.object(launch.subprocess, "Popen", side_effect=native_process):
        result = launch.execute(task, "request.json", "receipt.json", eval_deny_root=pack)

    assert result["native_completion"] == "COMPLETED_UNGRADED"
    assert "-s" not in seen
    assert any(str(pack) in arg and arg.startswith("permissions.harness_eval_") for arg in seen)


def test_eval_profile_rejects_a_pack_without_the_frozen_answer_shape(tmp_path):
    task = tmp_path / "heldout-projection-fixture" / "memory-log-code"
    task.mkdir(parents=True)
    pack = tmp_path / "heldout-prereg-fixture"
    pack.mkdir()
    with pytest.raises(ValueError, match="eval|oracle|frozen"):
        launch.execute(task, "request.json", "receipt.json", eval_deny_root=pack)
