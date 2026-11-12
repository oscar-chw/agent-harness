"""Opt-in, pure context-packet candidate; not wired into any native client or hook.

The caller chooses scoped records and required IDs. Content is retained exactly or omitted
with a revisioned pointer. This neither authenticates authority nor counts model tokens.
"""
import hashlib
import json


def _render(packet):
    return json.dumps(packet, ensure_ascii=False, separators=(",", ":"))


def compile_packet(project_id, sections, *, required_ids, max_bytes):
    """Return a complete JSON packet within max_bytes, or refuse without partial output.

    Budget covers every emitted byte, including provenance and omission/duplicate receipts.
    Required records are never trimmed. Optional records retain caller order, with no inferred
    importance or silent conflict resolution. Sources must already be authorized by the caller.
    """
    if not isinstance(project_id, str) or not project_id:
        raise ValueError("project_id must be nonempty")
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer budget")
    if not isinstance(sections, list) or not isinstance(required_ids, list):
        raise TypeError("sections and required_ids must be lists")
    if any(not isinstance(x, str) or not x for x in required_ids):
        raise ValueError("required IDs must be nonempty strings")
    unique, duplicates = {}, {}
    fields = {"id", "project_id", "source", "revision", "text"}
    for entry in sections:
        if not isinstance(entry, dict) or set(entry) != fields:
            raise ValueError("section needs id/project_id/source/revision/text")
        if any(not isinstance(entry[k], str) or not entry[k] for k in fields - {"text"}):
            raise ValueError("section identity and provenance must be nonempty strings")
        if not isinstance(entry["text"], str):
            raise TypeError("section text must be a string")
        if entry["project_id"] != project_id:
            raise ValueError("section belongs to another project")
        if hashlib.sha256(entry["text"].encode("utf-8")).hexdigest() != entry["revision"]:
            raise ValueError("section text does not match its revision")
        sid = entry["id"]
        if sid in unique:
            if unique[sid] != entry:
                raise ValueError(f"conflicting section: {sid}")
            duplicates[sid] = duplicates.get(sid, 0) + 1
        else:
            unique[sid] = dict(entry)
    missing = set(required_ids) - set(unique)
    if missing:
        raise ValueError(f"required sections missing: {sorted(missing)}")
    selected = {sid for sid in unique if sid in required_ids}

    def render_selection():
        included = [entry for sid, entry in unique.items() if sid in selected and sid in required_ids]
        included += [entry for sid, entry in unique.items() if sid in selected and sid not in required_ids]
        omitted = [{k: entry[k] for k in ("id", "source", "revision")}
                   for sid, entry in unique.items() if sid not in selected]
        return _render({"kind": "retrieved-context-data", "project_id": project_id,
                        "included": included, "omitted": omitted,
                        "omission_reason": "budget", "duplicates": duplicates})

    text = render_selection()
    if len(text.encode("utf-8")) > max_bytes:
        raise ValueError("budget cannot fit required records and complete omission receipts")
    for sid in unique:
        if sid in selected:
            continue
        selected.add(sid)
        candidate = render_selection()
        if len(candidate.encode("utf-8")) <= max_bytes:
            text = candidate
        else:
            selected.remove(sid)
    return text
