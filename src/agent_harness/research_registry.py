"""Source-bound capability research and saved preference review.

These records are advisory. A confirmation digest detects changed preferences.
The invoking client owns evidence that the user actually confirmed an upgrade.
"""
import hashlib
import json
import re
from pathlib import Path

from .installer import REPO_ROOT
from .permission_profiles import _write as _atomic_write
from .mcp.memory import _store_lock
from .presets import _read
from .vault_sources import _source_path, _unique_object

DEFAULT_CONTENT = REPO_ROOT / "content"
LIMIT = 65536
ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
FIELDS = {"id", "summary", "sources", "related", "reviewed_at", "quality_evaluation"}


def _id(value):
    if not isinstance(value, str) or len(value) > 80 or not ID.fullmatch(value):
        raise ValueError("invalid capability identifier")
    return value


def _encoded(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    if len(raw) > LIMIT:
        raise ValueError("research record exceeds its byte limit")
    return raw


def _digest(value):
    return hashlib.sha256(_encoded(value)).hexdigest()


def _load(path):
    return json.loads(_read(path, LIMIT), object_pairs_hook=_unique_object)


def _record_schema(entry):
    if not isinstance(entry, dict) or not FIELDS <= set(entry) or set(entry) - FIELDS - {"lifecycle", "source_root"}:
        raise ValueError("research record needs its complete declared schema")
    if entry.get("source_root", "package") not in ("package", "vault"):
        raise ValueError("invalid research source root")
    _id(entry["id"])
    if "lifecycle" in entry:
        lifecycle = entry["lifecycle"]
        if (not isinstance(lifecycle, dict)
                or set(lifecycle) != {"state", "reason", "source", "previous_sha256"}
                or lifecycle["state"] not in ("withdrawn", "requalified")
                or not isinstance(lifecycle["previous_sha256"], str)
                or not re.fullmatch(r"[a-f0-9]{64}", lifecycle["previous_sha256"])):
            raise ValueError("invalid research lifecycle")
        _provenance(lifecycle["reason"], lifecycle["source"])
    for key in ("summary", "reviewed_at", "quality_evaluation"):
        if not isinstance(entry[key], str) or not entry[key].strip() or len(entry[key]) > 4096:
            raise ValueError("invalid research metadata")
    if not isinstance(entry["related"], list) or len(entry["related"]) > 32:
        raise ValueError("invalid related capability list")
    related = [_id(value) for value in entry["related"]]
    if len(set(related)) != len(related) or entry["id"] in related:
        raise ValueError("invalid related capability identity")
    sources = entry["sources"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= 16:
        raise ValueError("research needs bounded source references")
    paths = []
    for source in sources:
        if (not isinstance(source, dict) or set(source) != {"path", "sha256"}
                or not isinstance(source["path"], str)
                or Path(source["path"]).suffix not in {".md", ".json", ".txt", ".rst"}
                or not isinstance(source["sha256"], str)
                or not re.fullmatch(r"[a-f0-9]{64}", source["sha256"])):
            raise ValueError("invalid research source reference")
        paths.append(source["path"])
    if len(paths) != len(set(paths)):
        raise ValueError("duplicate research source")
    _encoded(entry)


def _sources_current(entry, content, home=None):
    if entry.get("source_root", "package") == "vault":
        if home is None:
            raise ValueError("vault research requires its owning harness store")
        content = Path(home) / "vault"
        if content.is_symlink():
            return False
    for source in entry["sources"]:
        try:
            path = _source_path(Path(content).resolve(), source["path"])
            if hashlib.sha256(_read(path, LIMIT)).hexdigest() != source["sha256"]:
                return False
        except (OSError, ValueError):
            return False
    return True


def _store(home):
    path = Path(home) / "research"
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise ValueError("research store is redirected")
    return path


def _entry(home, capability, content):
    local = _store(home) / (capability + ".json")
    if local.exists():
        entry = _load(local)
        _record_schema(entry)
        if entry["id"] != capability:
            raise ValueError("research identity changed")
        return entry
    catalogue = Path(content) / "knowledge/capability-research.json"
    if not catalogue.exists():
        return None
    value = _load(catalogue)
    if (not isinstance(value, dict) or set(value) != {"schema", "capabilities"}
            or type(value["schema"]) is not int or value["schema"] != 1
            or not isinstance(value["capabilities"], list) or len(value["capabilities"]) > 200):
        raise ValueError("invalid research catalogue")
    rows = {}
    for row in value["capabilities"]:
        _record_schema(row)
        if row["id"] in rows:
            raise ValueError("duplicate capability identity")
        rows[row["id"]] = row
    return rows.get(capability)


def _preferences(home, capability):
    path = _store(home) / (capability + ".preferences.json")
    if not path.exists():
        return []
    value = _load(path)
    if not isinstance(value, list) or len(value) > 64:
        raise ValueError("invalid saved preferences")
    for row in value:
        if (not isinstance(row, dict) or set(row) != {"text", "source"}
                or any(not isinstance(v, str) or not v.strip() or len(v) > 4096 for v in row.values())):
            raise ValueError("invalid saved preference provenance")
    return value


def check(home, capability, *, content=DEFAULT_CONTENT, update_requested=False):
    _id(capability)
    if type(update_requested) is not bool:
        raise ValueError("update intent must be explicit")
    entry = _entry(home, capability, content)
    preferences = _preferences(home, capability)
    status = "RESEARCH_REQUIRED"
    if entry is not None:
        status = "REUSE_EXISTING" if _sources_current(entry, content, home) else "SOURCE_REVIEW_REQUIRED"
        if update_requested:
            status = "CONFIRM_SAVED_PREFERENCES" if preferences else "UPDATE_REQUESTED"
    if entry is not None and entry.get("lifecycle", {}).get("state") == "withdrawn":
        status = "WITHDRAWN"
    missing = ({"next_action": "INSPECT_EXISTING_KNOWLEDGE", "local_coverage": "UNASSESSED"}
               if entry is None else {})
    return {"schema": "harness.capability-research/v1", "capability": capability,
            "status": status, "record": entry,
            "record_sha256": _digest(entry) if entry is not None else None,
            "preferences": preferences, "preferences_sha256": _digest(preferences),
            "execution_authorized": False, **missing}


def save_preference(home, capability, text, source):
    _id(capability)
    if any(not isinstance(v, str) or not v.strip() or len(v) > 4096 for v in (text, source)):
        raise ValueError("preference needs user text and source")
    with _store_lock(Path(home)):
        path = _store(home)
        path.mkdir(exist_ok=True)
        rows = _preferences(home, capability)
        row = {"text": text, "source": source}
        if row not in rows:
            rows.append(row)
        if len(rows) > 64:
            raise ValueError("preference storage limit reached")
        target = path / (capability + ".preferences.json")
        if not target.exists() and len(list(path.glob("*.json"))) >= 200:
            raise ValueError("research store limit reached")
        _atomic_write(target, _encoded(rows))
    return row


def _provenance(reason, source):
    if any(not isinstance(value, str) or not value.strip() or len(value) > 4096
           for value in (reason, source)):
        raise ValueError("lifecycle provenance needs a bounded reason and source")
    return {"reason": reason, "source": source}


def _save_record(home, entry, state):
    """Preserve the previous record by digest before replacement under the store lock."""
    _record_schema(entry)
    path = _store(home)
    path.mkdir(exist_ok=True)
    target = path / (entry["id"] + ".json")
    if not target.exists() and len(list(path.glob("*.json"))) >= 200:
        raise ValueError("research store limit reached")
    if state["record"] is not None and state["record"] != entry:
        history = path / "history"
        if history.is_symlink() or (history.exists() and not history.is_dir()):
            raise ValueError("research history is redirected")
        history.mkdir(exist_ok=True)
        previous = history / (entry["id"] + "-" + state["record_sha256"] + ".json")
        if previous.exists():
            if _load(previous) != state["record"]:
                raise ValueError("research history changed")
        else:
            if len(list(history.glob("*.json"))) >= 1000:
                raise ValueError("research history limit reached; preserve it before updating")
            _atomic_write(previous, _encoded(state["record"]))
    _atomic_write(target, _encoded(entry))


def withdraw(home, capability, *, reason, source, expected, content=DEFAULT_CONTENT):
    provenance = _provenance(reason, source)
    with _store_lock(Path(home)):
        state = check(home, capability, content=content)
        if state["record_sha256"] != expected:
            raise ValueError("research record changed; reread before withdrawing")
        if state["record"] is None:
            raise ValueError("no research record to withdraw")
        if state["status"] == "WITHDRAWN":
            raise ValueError("research is already withdrawn")
        entry = {**state["record"], "lifecycle": {
            "state": "withdrawn", **provenance, "previous_sha256": state["record_sha256"]}}
        _save_record(home, entry, state)
        return check(home, capability, content=content)


def record(home, entry, *, content=DEFAULT_CONTENT, expected=None, confirmed_preferences=None,
           requalify=False, reason=None, source=None):
    _record_schema(entry)
    if not _sources_current(entry, content, home):
        raise ValueError("research source unavailable or changed")
    if type(requalify) is not bool:
        raise ValueError("requalification intent must be explicit")
    if not requalify and (reason is not None or source is not None):
        raise ValueError("lifecycle provenance requires explicit requalification")
    with _store_lock(Path(home)):
        state = check(home, entry["id"], content=content, update_requested=True)
        if state["record_sha256"] != expected:
            raise ValueError("research record changed; reread before updating")
        lifecycle = (state["record"] or {}).get("lifecycle")
        if "lifecycle" in entry and entry["lifecycle"] != lifecycle:
            raise ValueError("research lifecycle must use withdraw or explicit requalification")
        if state["status"] == "WITHDRAWN" and not requalify:
            raise ValueError("withdrawn research requires explicit requalification")
        if requalify:
            if state["status"] != "WITHDRAWN":
                raise ValueError("only withdrawn research can be requalified")
            lifecycle = {"state": "requalified", **_provenance(reason, source),
                         "previous_sha256": state["record_sha256"]}
        if state["preferences"] and confirmed_preferences != state["preferences_sha256"]:
            raise ValueError("confirm the current saved preferences before upgrading")
        if lifecycle is not None:
            entry = {**entry, "lifecycle": lifecycle}
        if not _sources_current(entry, content, home):
            raise ValueError("research source unavailable or changed")
        _save_record(home, entry, state)
        return check(home, entry["id"], content=content)


def add_parser(subparsers):
    parser = subparsers.add_parser("research", help="reuse source-bound capability research and review saved preferences")
    commands = parser.add_subparsers(dest="research_action", required=True)
    for action in ("check", "record", "preference", "withdraw"):
        command = commands.add_parser(action)
        command.add_argument("capability")
        command.add_argument("--content-root", default=str(DEFAULT_CONTENT))
        if action == "check":
            command.add_argument("--update", action="store_true")
        elif action == "record":
            command.add_argument("--input", required=True)
            command.add_argument("--expected")
            command.add_argument("--confirmed-preferences")
            command.add_argument("--requalify", action="store_true")
            command.add_argument("--reason")
            command.add_argument("--source")
        elif action == "withdraw":
            command.add_argument("--expected", required=True)
            command.add_argument("--reason", required=True)
            command.add_argument("--source", required=True)
        else:
            command.add_argument("--text", required=True)
            command.add_argument("--source", required=True)


def command(args, home):
    try:
        if args.research_action == "check":
            result = check(home, args.capability, content=args.content_root, update_requested=args.update)
        elif args.research_action == "withdraw":
            result = withdraw(home, args.capability, content=args.content_root, expected=args.expected,
                              reason=args.reason, source=args.source)
        elif args.research_action == "preference":
            result = save_preference(home, args.capability, args.text, args.source)
        else:
            entry = _load(Path(args.input))
            _record_schema(entry)
            if entry.get("id") != args.capability:
                raise ValueError("input capability differs from the selected capability")
            result = record(home, entry, content=args.content_root, expected=args.expected,
                            confirmed_preferences=args.confirmed_preferences, requalify=args.requalify,
                            reason=args.reason, source=args.source)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, TypeError) as error:
        print(json.dumps({"status": "ERROR", "error": str(error)}))
        return 2
