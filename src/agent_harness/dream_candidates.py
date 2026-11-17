"""Candidate-only dream intake and graph-gated, reversible knowledge links.

Scores propose work. They grant neither semantic truth nor write authority.
The owner-controlled work graph supplies the independent check and its bound
output. This is a local cooperating-runner protocol, not hostile-host security.
"""
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import quote

from . import memory_dreaming_v1 as dreaming
from . import settlement
from .mcp.memory import _store_lock
from .permission_profiles import _write
from .presets import _read
from .vault_sources import _source_path, _unique_object

LIMIT = 65536
MAX_CANDIDATES = 200


def _encoded(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    if len(raw) > LIMIT:
        raise ValueError("dream record exceeds its byte bound")
    return raw


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _store(corpus):
    root = Path(corpus).resolve(strict=True)
    directory = root
    for name in (".harness", "dreaming"):
        directory = directory / name
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise ValueError("dream store is redirected")
    return root, directory


def _load(path):
    return json.loads(_read(path, LIMIT), object_pairs_hook=_unique_object)


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ValueError("invalid dream candidate identity")
    return value


def _candidate(root, source, target, origin):
    if (source == target or any(not isinstance(v, str) or not v or len(v) > 4096
                               or any(ord(c) < 32 for c in v) for v in (source, target, origin))):
        raise ValueError("invalid dream source or origin")
    hashes = {}
    for name in (source, target):
        if Path(name).suffix != ".md":
            raise ValueError("dream links require Markdown sources")
        hashes[name] = _sha(_read(_source_path(root, name), LIMIT))
    payload = {"schema": 1, "source": source, "target": target, "origin": origin, "sources": hashes}
    identity = _sha(_encoded(payload))
    return {**payload, "id": identity, "status": "proposed", "admitted": False}


def _candidate_folder(store):
    folder = store / "candidates"
    if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
        raise ValueError("dream candidate store is redirected or invalid")
    return folder


def propose(corpus, source, target, *, origin):
    root, store = _store(corpus)
    with _store_lock(store):
        value = _candidate(root, source, target, origin)
        identity = value["id"]
        folder = _candidate_folder(store)
        folder.mkdir(exist_ok=True)
        path = folder / (identity + ".json")
        if path.exists() or path.is_symlink():
            if _load(path) != value:
                raise ValueError("dream candidate changed")
        else:
            if len(list(folder.glob("*.json"))) >= MAX_CANDIDATES:
                raise ValueError("dream candidate storage limit reached")
            _write(path, _encoded(value))
        return read(root, identity)


def read(corpus, identity):
    _identifier(identity)
    _, store = _store(corpus)
    value = _load(_source_path(store, "candidates/" + identity + ".json"))
    fields = {"schema", "source", "target", "origin", "sources", "id", "status", "admitted"}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("invalid dream candidate")
    payload = {k: value[k] for k in ("schema", "source", "target", "origin", "sources")}
    if (value["id"] != identity or _sha(_encoded(payload)) != identity
            or value["status"] != "proposed" or value["admitted"] is not False):
        raise ValueError("dream candidate identity changed")
    withdrawn = store / (identity + ".withdrawn.json")
    if withdrawn.exists():
        record = _load(withdrawn)
        if (not isinstance(record, dict) or record.get("candidate") != identity
                or record.get("status") not in ("prepared", "withdrawn")):
            raise ValueError("dream withdrawal identity changed")
        return {**value, "status": "withdrawn" if record["status"] == "withdrawn" else "withdrawal_pending"}
    admitted = store / (identity + ".admitted.json")
    if admitted.exists():
        receipt = _receipt(store, value)
        return {**value, "status": "admitted" if receipt["status"] == "admitted" else "admission_pending",
                "admitted": receipt["status"] == "admitted"}
    return value


def _receipt(store, value):
    receipt = _load(store / (value["id"] + ".admitted.json"))
    fields = {"status", "candidate", "proof", "before_sha256", "after_sha256", "backup"}
    if (not isinstance(receipt, dict) or set(receipt) != fields
            or receipt["candidate"] != value["id"] or receipt["status"] not in ("prepared", "admitted")
            or receipt["before_sha256"] != value["sources"][value["source"]]
            or receipt["backup"] != str(store / (value["id"] + ".before.md"))
            or not isinstance(receipt["proof"], dict)
            or set(receipt["proof"]) != {"plan_sha256", "node", "record_sha256", "settlement"}):
        raise ValueError("invalid dream admission receipt")
    if _sha(_read(Path(receipt["backup"]), LIMIT)) != receipt["before_sha256"]:
        raise ValueError("dream rollback copy changed")
    return receipt


def _gate(plan, node, identity):
    plan = Path(plan).resolve(strict=True)
    _read(plan, LIMIT)
    if type(node) is not int or node < 0:
        raise ValueError("invalid independent gate node")
    records = list((plan.parent / plan.stem).glob(f"{node:02}-*.md"))
    if len(records) != 1 or records[0].is_symlink():
        raise ValueError("independent gate record missing or ambiguous")
    body = _read(records[0], LIMIT).decode("utf-8")
    selected = [r for r in settlement.scan_plan(str(plan)) if str(r["action"]["node"]) == str(node)]
    if len(selected) != 1 or selected[0]["status"] != "settled":
        raise ValueError("independent gate is not settled")
    attempts = [a for a in settlement._attempts(body) if not a["not_applied"]]
    if not attempts or identity not in attempts[-1]["body"]:
        raise ValueError("independent gate is not bound to this candidate")
    return {"plan_sha256": _sha(_read(plan, LIMIT)), "node": node,
            "record_sha256": _sha(body.encode()), "settlement": selected[0]["settled_by"]}


def admit(corpus, identity, plan, node):
    root, store = _store(corpus)
    with _store_lock(store):
        value = read(root, identity)
        if value["status"] in ("withdrawn", "withdrawal_pending"):
            raise ValueError("dream candidate was withdrawn or withdrawal is pending; a new review is required")
        proof = _gate(plan, node, identity)
        path = store / (identity + ".admitted.json")
        if path.exists():
            receipt = _receipt(store, value)
            if (receipt["proof"]["record_sha256"] != proof["record_sha256"]
                    or receipt["proof"]["node"] != node):
                raise ValueError("independent gate evidence changed")
            current = _read(_source_path(root, value["source"]), LIMIT)
            target = _read(_source_path(root, value["target"]), LIMIT)
            if _sha(target) != value["sources"][value["target"]]:
                raise ValueError("admitted dream target source changed")
            if _sha(current) == receipt["after_sha256"]:
                receipt["status"] = "admitted"
                _write(path, _encoded(receipt))
                return receipt
            if receipt["status"] != "prepared" or _sha(current) != receipt["before_sha256"]:
                raise ValueError("admitted dream source changed")
        for name, expected in value["sources"].items():
            if _sha(_read(_source_path(root, name), LIMIT)) != expected:
                raise ValueError("dream source changed; review a fresh candidate")
        target = _source_path(root, value["source"])
        original = _read(target, LIMIT)
        relative = os.path.relpath(root / value["target"], target.parent).replace(os.sep, "/")
        label = Path(value["target"]).stem.replace("[", "\\[").replace("]", "\\]")
        suffix = ("\nRelated (reviewed dream): [" + label + "](" + quote(relative, safe="/.") + ")\n").encode()
        if len(original) + len(suffix) > LIMIT:
            raise ValueError("dream link would exceed the source byte bound")
        backup = store / (identity + ".before.md")
        if backup.exists() and _read(backup, LIMIT) != original:
            raise ValueError("dream rollback copy changed")
        _write(backup, original)
        receipt = {"status": "prepared", "candidate": identity, "proof": proof,
                   "before_sha256": _sha(original), "after_sha256": _sha(original + suffix),
                   "backup": str(backup)}
        _write(path, _encoded(receipt))
        if _read(target, LIMIT) != original:
            raise ValueError("dream source changed before apply")
        _write(target, original + suffix, mode=target.stat().st_mode & 0o777)
        receipt["status"] = "admitted"
        _write(path, _encoded(receipt))
        return receipt


def withdraw(corpus, identity, *, reason):
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 1024:
        raise ValueError("dream withdrawal needs a reason")
    root, store = _store(corpus)
    with _store_lock(store):
        value = read(root, identity)
        receipt = _receipt(store, value)
        target = _source_path(root, value["source"])
        current = _read(target, LIMIT)
        record = store / (identity + ".withdrawn.json")
        if value["status"] == "withdrawn":
            if _sha(current) != receipt["before_sha256"]:
                raise ValueError("withdrawn source changed")
            return _load(record)
        if value["status"] == "withdrawal_pending":
            result = _load(record)
            if (result.get("admission_sha256") != _sha(_encoded(receipt))
                    or result.get("restored_sha256") != receipt["before_sha256"]):
                raise ValueError("dream withdrawal receipt changed")
            if _sha(current) not in (receipt["before_sha256"], receipt["after_sha256"]):
                raise ValueError("dream source changed during withdrawal")
        else:
            result = {"status": "prepared", "candidate": identity, "reason": reason,
                      "restored_sha256": receipt["before_sha256"], "admission_sha256": _sha(_encoded(receipt))}
            if _sha(current) != receipt["after_sha256"]:
                raise ValueError("dream source changed; preserve later edits before reversal")
            _write(record, _encoded(result))
        original = _read(Path(receipt["backup"]), LIMIT)
        _write(target, original, mode=target.stat().st_mode & 0o777)
        result["status"] = "withdrawn"
        _write(record, _encoded(result))
        return result


def stage(corpus, *, limit=8):
    if type(limit) is not int or not 1 <= limit <= 32:
        raise ValueError("dream staging limit must be 1 to 32")
    root, store = _store(corpus)
    report = dreaming.dream_v1(root, apply=False)
    candidates = [v for v in report["promoted"] if v["kind"] == "orphan_inbound_link"]
    rows = []
    remaining = 0
    with (_store_lock(store) if candidates else nullcontext()):
        folder = _candidate_folder(store)
        existing = {path.stem for path in folder.glob("*.json")}
        free = max(0, MAX_CANDIDATES - len(existing))
        seen = set(existing)
        for candidate in candidates:
            value = _candidate(root, candidate["source"], candidate["orphan"], "dreaming-v1-orphan")
            identity = value["id"]
            path = folder / (identity + ".json")
            if identity in existing and _load(path) != value:
                raise ValueError("dream candidate changed")
            if identity in seen:
                continue
            seen.add(identity)
            if len(rows) >= min(limit, free):
                remaining += 1
                continue
            folder.mkdir(exist_ok=True)
            _write(path, _encoded(value))
            rows.append(value)
    return {"mode": "candidate_only", "admitted": 0, "candidates": rows,
            "remaining_scored": remaining, "storage_remaining": free - len(rows),
            "semantic_precision": "NOT_QUALIFIED", "model_calls": 0}


def list_candidates(corpus):
    root, store = _store(corpus)
    folder = _candidate_folder(store)
    if not folder.exists():
        return {"candidates": []}
    paths = sorted(folder.glob("*.json"))
    if len(paths) > MAX_CANDIDATES:
        raise ValueError("dream candidate storage limit exceeded")
    return {"candidates": [read(root, path.stem) for path in paths]}


def add_parser(subparsers):
    parser = subparsers.add_parser("dream", help="stage candidate knowledge links; independent gates own admission")
    actions = parser.add_subparsers(dest="dream_action", required=True)
    for name in ("stage", "list", "show", "admit", "withdraw"):
        action = actions.add_parser(name)
        action.add_argument("corpus")
        if name == "stage":
            action.add_argument("--limit", type=int, default=8)
        elif name != "list":
            action.add_argument("candidate")
        if name == "admit":
            action.add_argument("--plan", required=True)
            action.add_argument("--node", type=int, required=True)
        if name == "withdraw":
            action.add_argument("--reason", required=True)


def command(args):
    try:
        if args.dream_action == "stage":
            result = stage(args.corpus, limit=args.limit)
        elif args.dream_action == "list":
            result = list_candidates(args.corpus)
        elif args.dream_action == "show":
            result = read(args.corpus, args.candidate)
        elif args.dream_action == "withdraw":
            result = withdraw(args.corpus, args.candidate, reason=args.reason)
        else:
            result = admit(args.corpus, args.candidate, args.plan, args.node)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"status": "REFUSED", "error": str(error)}))
        return 2
