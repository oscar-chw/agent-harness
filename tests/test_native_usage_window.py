"""Read actual bounded native counter frames, never accept a declared total."""

import importlib
import importlib.util
import json
import os

import pytest

THREAD = "owned-native-thread"


@pytest.fixture
def usage():
    assert importlib.util.find_spec("agent_harness.native_usage") is not None
    return importlib.import_module("agent_harness.native_usage")


def counts(inputs, outputs, *, cached=0, reasoning=0, residual=0):
    return {
        "input_tokens": inputs,
        "output_tokens": outputs,
        "cached_input_tokens": cached,
        "reasoning_output_tokens": reasoning,
        "total_tokens": inputs + outputs + residual,
    }


def event(total, last):
    return {
        "type": "event_msg",
        "timestamp": "2026-11-06T00:00:00Z",
        "payload": {
            "type": "token_count",
            "info": {"total_token_usage": total, "last_token_usage": last},
        },
    }


def fixture(tmp_path, rows):
    path = tmp_path / "native.jsonl"
    header = (
        json.dumps({"type": "session_meta", "payload": {"id": THREAD}}) + "\n"
    ).encode()
    raw = b"".join((json.dumps(x) + "\n").encode() for x in rows)
    path.write_bytes(header + raw)
    return path, len(header), len(header + raw)


def read(usage, tmp_path, rows, **options):
    path, start, end = fixture(tmp_path, rows)
    return usage.inspect_window(
        tmp_path, path, thread_id=THREAD, start_offset=start, end_offset=end, **options
    )


def test_native_file_counters_include_cached_input_without_double_counting(
    usage, tmp_path
):
    rows = [
        event(counts(100, 10, cached=80), counts(100, 10, cached=80)),
        {"type": "response_item", "payload": {"text": "PRIVATE_BODY_NOT_TO_COPY"}},
        event(
            counts(140, 18, cached=110, reasoning=3),
            counts(40, 8, cached=30, reasoning=3),
        ),
    ]
    result = read(usage, tmp_path, rows)
    assert result["delta"] == counts(40, 8, cached=30, reasoning=3)
    assert result["distinct_increments"] == 1
    assert result["status"] == "CONSISTENT_COUNTER_WINDOW"
    assert result["whole_workflow_usage_complete"] is False
    assert "PRIVATE_BODY_NOT_TO_COPY" not in json.dumps(result)
    assert result["first_anchor"]["sha256"] and result["last_anchor"]["sha256"]


def test_duplicate_notifications_do_not_add_usage_twice(usage, tmp_path):
    first = event(counts(10, 2), counts(10, 2))
    second = event(counts(15, 3), counts(5, 1))
    result = read(usage, tmp_path, [first, first, second, second])
    assert result["delta"]["total_tokens"] == 6
    assert result["duplicate_notifications"] == 2


def test_historical_total_offset_is_explicit_never_repaired_into_full_usage(
    usage, tmp_path
):
    result = read(
        usage,
        tmp_path,
        [
            event(counts(100, 10, residual=7), counts(100, 10)),
            event(counts(120, 13, residual=7), counts(20, 3)),
        ],
    )
    assert result["delta"]["total_tokens"] == 23
    assert result["cumulative_total_residual"] == 7
    assert result["status"] == "CONSISTENT_DELTA_WITH_HISTORICAL_OFFSET"
    assert result["whole_workflow_usage_complete"] is False


@pytest.mark.parametrize(
    "fault",
    [
        "reset",
        "missing-event",
        "changed-residual",
        "boolean",
        "cached-over-input",
        "bad-last-total",
    ],
)
def test_inconsistent_or_partial_counters_fail_instead_of_becoming_zero(
    usage, tmp_path, fault
):
    first = event(counts(100, 10, cached=80), counts(100, 10, cached=80))
    second = event(counts(120, 13, cached=90), counts(20, 3, cached=10))
    total = second["payload"]["info"]["total_token_usage"]
    last = second["payload"]["info"]["last_token_usage"]
    if fault == "reset":
        total.update(counts(20, 3))
    elif fault == "missing-event":
        last.update(counts(10, 1))
    elif fault == "changed-residual":
        total["total_tokens"] += 1
    elif fault == "boolean":
        last["input_tokens"] = True
    elif fault == "cached-over-input":
        last["cached_input_tokens"] = 21
    else:
        last["total_tokens"] += 1
    with pytest.raises(ValueError):
        read(usage, tmp_path, [first, second])


def test_missing_usage_or_foreign_header_cannot_be_claimed_complete(usage, tmp_path):
    with pytest.raises(ValueError, match="counter|anchor"):
        read(
            usage,
            tmp_path,
            [{"type": "event_msg", "payload": {"type": "task_complete"}}],
        )
    path, start, end = fixture(tmp_path, [event(counts(1, 1), counts(1, 1))])
    with pytest.raises(ValueError, match="thread"):
        usage.inspect_window(
            tmp_path, path, thread_id="foreign", start_offset=start, end_offset=end
        )


def test_scope_link_budget_and_partial_line_are_rejected(usage, tmp_path):
    rows = [event(counts(10, 2), counts(10, 2)), event(counts(15, 3), counts(5, 1))]
    path, start, end = fixture(tmp_path, rows)
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(ValueError):
        usage.inspect_window(
            other, path, thread_id=THREAD, start_offset=start, end_offset=end
        )
    with pytest.raises(ValueError):
        usage.inspect_window(
            tmp_path,
            path,
            thread_id=THREAD,
            start_offset=start,
            end_offset=end,
            max_bytes=10,
        )
    with pytest.raises(ValueError):
        usage.inspect_window(
            tmp_path, path, thread_id=THREAD, start_offset=start + 1, end_offset=end
        )
    link = tmp_path / "linked.jsonl"
    link.symlink_to(path)
    with pytest.raises(ValueError):
        usage.inspect_window(
            tmp_path, link, thread_id=THREAD, start_offset=start, end_offset=end
        )


def test_prior_counter_span_can_be_read_after_append_without_reading_new_body(
    usage, tmp_path
):
    rows = [event(counts(10, 2), counts(10, 2)), event(counts(15, 3), counts(5, 1))]
    path, start, end = fixture(tmp_path, rows)
    with path.open("ab") as output:
        output.write(
            b'{"type":"response_item","payload":{"text":"NEW_PRIVATE_BODY"}}\n'
        )
    before = path.stat()
    result = usage.inspect_window(
        tmp_path, path, thread_id=THREAD, start_offset=start, end_offset=end
    )
    assert result["delta"]["total_tokens"] == 6
    assert result["source_span"]["end_offset"] == end
    assert "NEW_PRIVATE_BODY" not in json.dumps(result)
    assert (before.st_ino, before.st_size) == (
        os.stat(path).st_ino,
        os.stat(path).st_size,
    )


def test_non_object_json_and_one_anchor_are_not_complete_usage(usage, tmp_path):
    first = event(counts(10, 2), counts(10, 2))
    second = event(counts(15, 3), counts(5, 1))
    with pytest.raises(ValueError, match="object"):
        read(usage, tmp_path, [first, [], second])
    with pytest.raises(ValueError, match="anchors"):
        read(usage, tmp_path, [first])


def test_explicitly_selected_root_alias_keeps_its_scope(usage, tmp_path):
    selected = tmp_path / "selected"
    actual = tmp_path / "actual"
    actual.mkdir()
    selected.symlink_to(actual, target_is_directory=True)
    rows = [event(counts(10, 2), counts(10, 2)), event(counts(15, 3), counts(5, 1))]
    _, start, end = fixture(actual, rows)
    result = usage.inspect_window(
        selected,
        selected / "native.jsonl",
        thread_id=THREAD,
        start_offset=start,
        end_offset=end,
    )
    assert result["delta"]["total_tokens"] == 6
    assert result["source"] == "native.jsonl"


def test_first_anchor_request_usage_is_validated_too(usage, tmp_path):
    first = event(counts(10, 2), counts(10, 2))
    first["payload"]["info"]["last_token_usage"]["total_tokens"] += 1
    with pytest.raises(ValueError, match="last-request"):
        read(usage, tmp_path, [first, event(counts(15, 3), counts(5, 1))])


@pytest.mark.parametrize("position", [0, 1, 2])
def test_null_usage_event_is_not_silently_treated_as_zero(usage, tmp_path, position):
    rows = [event(counts(10, 2), counts(10, 2)), event(counts(15, 3), counts(5, 1))]
    rows.insert(
        position,
        {"type": "event_msg", "payload": {"type": "token_count", "info": None}},
    )
    with pytest.raises(ValueError, match="missing|invalid"):
        read(usage, tmp_path, rows)
