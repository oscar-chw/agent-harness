"""Read-only review of completed Codex text, not a question detector or model gate.

Labels come from a separate task-aware reviewer. Byte hashes do not authenticate
that reviewer or prove native execution. Tool/UI prompts and worker text outside
this captured stream require separate observation; absence here cannot cover them.
"""
import hashlib
import json

TRACE_LIMIT = 4 * 1024 * 1024
EVENTS = {"thread.started", "turn.started", "turn.completed", "turn.failed", "error",
          "item.started", "item.updated", "item.completed"}
ITEMS = {"agent_message", "reasoning", "command_execution", "file_change", "mcp_tool_call",
         "web_search", "todo_list", "error"}


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate trace field")
        result[key] = value
    return result


def _constant(value):
    raise ValueError("non-finite JSON constant: " + value)


def _trace(raw):
    if not isinstance(raw, bytes) or len(raw) > TRACE_LIMIT:
        raise ValueError("trace must be bytes within the 4 MiB cap")
    try:
        events = [(number, json.loads(line, object_pairs_hook=_object, parse_constant=_constant))
                  for number, line in enumerate(raw.decode("utf-8").splitlines(), 1) if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("trace is not UTF-8 JSONL") from error
    if any(not isinstance(e, dict) or not isinstance(e.get("type"), str) or e["type"] not in EVENTS
           for _, e in events):
        raise ValueError("unknown or malformed event; capture coverage is unqualified")
    terminal = [e["type"] for _, e in events if e["type"] in ("turn.completed", "turn.failed")]
    if len(terminal) != 1 or not events or events[-1][1]["type"] != terminal[0]:
        raise ValueError("one terminal event must end the complete single-turn trace")
    if any(sum(e["type"] == kind for _, e in events) != 1 for kind in ("thread.started", "turn.started")):
        raise ValueError("single-turn capture requires one thread and turn start")
    messages, identities = [], set()
    for number, event in events:
        if not event["type"].startswith("item."):
            continue
        item = event.get("item")
        if not isinstance(item, dict) or not isinstance(item.get("type"), str) or item["type"] not in ITEMS:
            raise ValueError("unknown item type; text coverage is unqualified")
        if event["type"] == "item.completed" and item["type"] == "agent_message":
            identity = item.get("id")
            if not isinstance(identity, str) or not identity or identity in identities:
                raise ValueError("completed message identity is missing or repeated")
            identities.add(identity)
            text = item.get("text")
            if not isinstance(text, str):
                raise ValueError("completed agent-message text is missing")
            messages.append({"id": f"line-{number}", "text": text,
                             "text_sha256": hashlib.sha256(text.encode()).hexdigest()})
    return messages, terminal[0]


def codex_messages(raw):
    """Extract all completed message text in a bounded single-turn Codex JSONL capture."""
    return _trace(raw)[0]


def audit_questions(raw, review):
    """Require one hash-bound label per message; uncertain review never becomes zero."""
    messages, terminal = _trace(raw)
    digest = hashlib.sha256(raw).hexdigest()
    if not isinstance(review, dict) or set(review) != {"trace_sha256", "messages"}:
        raise ValueError("review needs a trace digest and message coverage")
    if review["trace_sha256"] != digest:
        raise ValueError("trace digest changed since review")
    labels = review["messages"]
    if (not isinstance(labels, list) or len(labels) != len(messages)
            or any(not isinstance(label, dict) or set(label) != {"id", "text_sha256", "questions"}
                   or not isinstance(label["id"], str) for label in labels)):
        raise ValueError("message review coverage is incomplete")
    by_id = {label["id"]: label for label in labels}
    if len(by_id) != len(labels) or set(by_id) != {m["id"] for m in messages}:
        raise ValueError("message review coverage is duplicate, missing or foreign")
    counts = {"necessary": 0, "unnecessary": 0, "uncertain": 0}
    for message in messages:
        label = by_id[message["id"]]
        if label["text_sha256"] != message["text_sha256"]:
            raise ValueError("message digest changed since review")
        if not isinstance(label["questions"], list):
            raise ValueError("question spans must be an explicit list, including when empty")
        previous_end = 0
        for question in label["questions"]:
            if (not isinstance(question, dict)
                    or set(question) != {"start", "end", "classification", "rationale"}):
                raise ValueError("question annotation is incomplete")
            start, end = question["start"], question["end"]
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(message["text"]):
                raise ValueError("invalid question character span")
            if start < previous_end:
                raise ValueError("question spans overlap or are out of order")
            previous_end = end
            category = question["classification"]
            if not isinstance(category, str) or category not in counts:
                raise ValueError("unknown question classification")
            if not isinstance(question["rationale"], str) or not question["rationale"].strip():
                raise ValueError("question classification needs a task-bound rationale")
            counts[category] += 1
    observed = counts["uncertain"] == 0
    return {"status": "OBSERVED" if observed else "NOT_OBSERVABLE",
            "trace_sha256": digest, "terminal": terminal, "messages_reviewed": len(messages),
            "scope": "completed Codex agent-message text only", "uncertain": counts["uncertain"],
            "necessary": counts["necessary"] if observed else None,
            "unnecessary": counts["unnecessary"] if observed else None}
