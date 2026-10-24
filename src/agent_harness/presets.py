"""Read-only capability selection and reproducible receipts, without native activation.

The caller supplies authorized roots, scope and tool availability. Those declarations are
not credentials; this module cannot grant authority or interpret a natural-language request.
"""
import json
import os
import re
import stat
from pathlib import Path

from .installer import REPO_ROOT
from .vault_sources import _bytes, _project, _sha, _source_path, _unique_object

LIMIT = 65536
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
NOT_OBSERVABLE = "NOT_OBSERVABLE"
DEFAULT_CONTENT = REPO_ROOT / "content"


def _read(path, limit):
    # A named pipe must not turn a read-only selection into an unbounded wait.
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("selection inputs must be regular files")
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("selection file exceeds its byte budget")
    return data


def _id(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError("invalid identifier")
    return value


def _strings(value):
    if not isinstance(value, list) or len(value) > 64 or len(value) != len(set(value)):
        raise ValueError("expected a bounded unique identifier list")
    return [_id(v) for v in value]


def _request(request):
    fields = {"schema", "project_id", "task_id", "revision", "client", "contracts", "tasks",
              "allow_sensitivity", "permissions", "available_tools", "conflicts", "role_hints", "max_body_bytes"}
    if not isinstance(request, dict) or set(request) != fields or type(request["schema"]) is not int or request["schema"] != 1:
        raise ValueError("invalid selection request schema")
    if len(_bytes(request)) > LIMIT:
        raise ValueError("selection request exceeds its byte budget")
    for key in ("project_id", "task_id", "revision"):
        _id(request[key])
    if not isinstance(request["client"], dict) or set(request["client"]) != {"id", "version"}:
        raise ValueError("client identity and version required")
    for value in request["client"].values():
        _id(value)
    for key in ("allow_sensitivity", "permissions", "available_tools", "role_hints"):
        _strings(request[key])
    if not set(request["allow_sensitivity"]) <= {"public", "internal", "private"}:
        raise ValueError("invalid sensitivity scope")
    if type(request["max_body_bytes"]) is not int or not 0 <= request["max_body_bytes"] <= LIMIT:
        raise ValueError("invalid body budget")
    if not isinstance(request["contracts"], list) or not 1 <= len(request["contracts"]) <= 8:
        raise ValueError("mandatory project/authority contracts required")
    if not isinstance(request["tasks"], list) or len(request["tasks"]) > 16:
        raise ValueError("at most 16 bounded tasks required")
    identities = []
    for task in request["tasks"]:
        if not isinstance(task, dict) or set(task) != {"id", "intent", "negative_signals", "inputs", "outputs"}:
            raise ValueError("invalid task schema")
        identities.append(_id(task["id"]))
        _id(task["intent"])
        _strings(task["negative_signals"])
        if not isinstance(task["inputs"], dict) or len(task["inputs"]) > 16:
            raise ValueError("bounded input reference map required")
        if not isinstance(task["outputs"], dict) or not 1 <= len(task["outputs"]) <= 16:
            raise ValueError("bounded output artifact IDs required")
        for key in task["inputs"]:
            _id(key)
        for key, value in task["outputs"].items():
            _id(key)
            _id(value)
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate task identity")
    if not isinstance(request["conflicts"], list) or len(request["conflicts"]) > 16:
        raise ValueError("invalid conflict list")
    for conflict in request["conflicts"]:
        if not isinstance(conflict, dict) or set(conflict) != {"id", "sources"}:
            raise ValueError("conflicts require IDs and source references, not copied source text")
        _id(conflict["id"])
        _strings(conflict["sources"])


def _reference(root, ref, request):
    fields = {"id", "project_id", "path", "revision", "sha256", "sensitivity"}
    if not isinstance(ref, dict) or set(ref) != fields:
        raise ValueError("invalid source reference")
    if ref["project_id"] != request["project_id"] or ref["sensitivity"] not in request["allow_sensitivity"]:
        raise ValueError("scope denied")
    for key in ("id", "revision"):
        _id(ref[key])
    if not isinstance(ref["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", ref["sha256"]):
        raise ValueError("invalid source hash")
    try:
        raw = _read(_source_path(root, ref["path"]), LIMIT)
    except OSError:
        raise ValueError("source unavailable") from None
    if _sha(raw) != ref["sha256"]:
        raise ValueError("source revision changed")
    return dict(ref)


def _catalog(content):
    path = content / "presets/catalog.json"
    raw = _read(path, LIMIT)
    data = json.loads(raw, object_pairs_hook=_unique_object)
    if (not isinstance(data, dict) or set(data) != {"schema", "revision", "source", "clients", "capabilities", "presets"}
            or data["schema"] != "harness.presets/v1"):
        raise ValueError("invalid preset catalogue")
    _id(data["revision"])
    _strings(data["clients"])
    caps = data["capabilities"]
    if not isinstance(caps, dict) or len(caps) > 32:
        raise ValueError("invalid capability catalogue")
    for name, cap in caps.items():
        _id(name)
        if not isinstance(cap, dict) or set(cap) != {"path", "sha256"}:
            raise ValueError("capability must pin its source")
        if not isinstance(cap["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", cap["sha256"]):
            raise ValueError("invalid capability hash")
    methods = data["presets"]
    if not isinstance(methods, dict) or len(methods) > 16:
        raise ValueError("invalid preset map")
    keys = {"trigger", "negative_triggers", "inputs", "capabilities", "tools", "permissions",
            "output_contract", "check_contract", "max_body_bytes", "reversal"}
    for name, method in methods.items():
        _id(name)
        if not isinstance(method, dict) or set(method) != keys or method["trigger"] != name:
            raise ValueError("invalid preset contract")
        for field in ("negative_triggers", "inputs", "capabilities", "tools", "permissions"):
            _strings(method[field])
        if not set(method["capabilities"]) <= set(caps):
            raise ValueError("unresolved capability reference")
        if type(method["max_body_bytes"]) is not int or not 0 < method["max_body_bytes"] <= LIMIT:
            raise ValueError("invalid preset loading budget")
        if any(not isinstance(method[k], str) or not method[k] for k in ("output_contract", "check_contract", "reversal")):
            raise ValueError("missing output, check or reversal contract")
    return data, _sha(raw)


def select(root, request, *, content=DEFAULT_CONTENT):
    _request(request)
    root, content = Path(root).resolve(strict=True), Path(content).resolve(strict=True)
    _read(root / ".harness/project.json", 16384)
    if _project(root) != request["project_id"]:
        raise ValueError("project scope does not match the root")
    catalog, catalog_sha = _catalog(content)
    errors, omitted, tasks, contracts, chosen = [], [], [], [], {}
    held, unsupported = False, False
    if request["client"]["id"] not in catalog["clients"]:
        unsupported = True
        errors.append("unsupported client: " + request["client"]["id"])
    if request["conflicts"]:
        held = True
        errors.append("unresolved instruction conflicts")
    if "local-read" not in request["permissions"]:
        held = True
        errors.append("local-read permission is not declared")
    else:
        for ref in request["contracts"]:
            try:
                contracts.append(_reference(root, ref, request))
            except ValueError as error:
                held = True
                errors.append("mandatory contract: " + str(error))
    for task in request["tasks"]:
        method = catalog["presets"].get(task["intent"])
        if method is None:
            unsupported = True
            errors.append("unsupported intent: " + task["intent"])
            continue
        # A recognized skip cannot hide an unresolved condition on the same task.
        unknown = set(task["negative_signals"]) - set(method["negative_triggers"])
        if unknown:
            held = True
            errors.append("unknown negative trigger: " + ",".join(sorted(unknown)))
            continue
        negatives = set(task["negative_signals"]) & set(method["negative_triggers"])
        if negatives:
            omitted.append({"id": task["id"], "reason": sorted(negatives)[0]})
            continue
        refs = {}
        for key in method["inputs"]:
            if key not in task["inputs"]:
                held = True
                errors.append(task["id"] + ": missing input " + key)
        for key, ref in task["inputs"].items():
            if "local-read" not in request["permissions"]:
                continue
            try:
                refs[key] = _reference(root, ref, request)
            except ValueError as error:
                held = True
                errors.append(task["id"] + "." + key + ": " + str(error))
        missing_tools = set(method["tools"]) - set(request["available_tools"])
        if missing_tools:
            unsupported = True
            errors.append(task["id"] + ": unavailable tools " + ",".join(sorted(missing_tools)))
        if not set(method["permissions"]) <= set(request["permissions"]):
            held = True
            errors.append(task["id"] + ": required permission is absent")
        method_bytes = 0
        for identity in method["capabilities"]:
            if identity not in chosen:
                cap = catalog["capabilities"][identity]
                try:
                    raw = _read(_source_path(content, cap["path"]), LIMIT)
                    if _sha(raw) != cap["sha256"]:
                        raise ValueError("capability source changed")
                except (ValueError, OSError):
                    unsupported = True
                    errors.append("unavailable or changed capability: " + identity)
                    continue
                chosen[identity] = {"id": identity, **cap, "bytes": len(raw), "available": "hash_verified",
                                    "loaded": NOT_OBSERVABLE, "invoked": NOT_OBSERVABLE}
            method_bytes += chosen[identity]["bytes"]
        if method_bytes > method["max_body_bytes"]:
            held = True
            errors.append(task["id"] + ": preset body budget exceeded")
        tasks.append({"id": task["id"], "preset": task["intent"], "inputs": refs, "outputs": task["outputs"],
                      "output_contract": method["output_contract"], "check_contract": method["check_contract"],
                      "gate": {"status": "NOT_RUN", "exit_code": None}})
    body_bytes = sum(item["bytes"] for item in chosen.values())
    if body_bytes > request["max_body_bytes"]:
        held = True
        errors.append("combined body budget exceeded")
    status = "HELD" if held else "UNSUPPORTED" if unsupported else "SELECTED" if tasks else "SKIPPED"
    result = {"schema": "harness.preset-selection/v1", "status": status, "project_id": request["project_id"],
              "task_id": request["task_id"], "request_revision": request["revision"],
              "binding": _sha(_bytes({"request": request, "catalog": catalog_sha})),
              "catalog_sha256": catalog_sha, "contracts": contracts, "tasks": tasks,
              "capabilities": [chosen[k] for k in sorted(chosen)], "omitted": omitted, "errors": errors,
              "conflicts": request["conflicts"], "client": request["client"],
              "tool_state": {"reported_available": request["available_tools"], "invoked": NOT_OBSERVABLE},
              "permissions": request["permissions"], "execution_authorized": False,
              "body_bytes": body_bytes, "injected_body_bytes": 0, "model_tokens": NOT_OBSERVABLE,
              "gate": {"status": "NOT_RUN", "exit_code": None},
              "invalidate_on": ["request_revision", "project_or_authority", "catalog", "selected_source", "tool_availability"]}
    receipt = {**result, "sha256": _sha(_bytes(result))}
    if len(_bytes(receipt)) > LIMIT:
        raise ValueError("selection receipt exceeds its byte budget")
    return receipt


def check(root, request, receipt, *, content=DEFAULT_CONTENT):
    if not isinstance(receipt, dict):
        return {"status": "STALE", "reason": "invalid receipt"}
    raw = {k: v for k, v in receipt.items() if k != "sha256"}
    if receipt.get("sha256") != _sha(_bytes(raw)):
        return {"status": "STALE", "reason": "receipt integrity"}
    try:
        current = select(root, request, content=content)
    except (ValueError, OSError):
        return {"status": "STALE", "reason": "selection inputs unavailable or invalid"}
    return {"status": "CURRENT" if current == receipt else "STALE",
            "selection_status": current["status"], "execution_authorized": False,
            "reason": "exact reproducible selection" if current == receipt else "selection inputs or evidence changed"}


def add_parser(subparsers):
    parser = subparsers.add_parser("preset", help="read-only capability selection; no native activation")
    actions = parser.add_subparsers(dest="preset_action", required=True)
    for action in ("select", "check"):
        command = actions.add_parser(action)
        command.add_argument("--project-root", required=True)
        command.add_argument("--request", required=True, help="bounded request JSON; explicit IDs and source pins")
        command.add_argument("--content-root", default=str(DEFAULT_CONTENT))
        if action == "check":
            command.add_argument("--receipt", required=True)


def command(args):
    try:
        request = json.loads(_read(Path(args.request), LIMIT), object_pairs_hook=_unique_object)
        if args.preset_action == "select":
            result = select(args.project_root, request, content=args.content_root)
            code = 0 if result["status"] in ("SELECTED", "SKIPPED") else 1
        else:
            receipt = json.loads(_read(Path(args.receipt), LIMIT), object_pairs_hook=_unique_object)
            result = check(args.project_root, request, receipt, content=args.content_root)
            code = 0 if result["status"] == "CURRENT" and result["selection_status"] in ("SELECTED", "SKIPPED") else 1
    except (ValueError, OSError, TypeError) as error:
        result, code = {"status": "ERROR", "error": str(error)}, 2
    print(json.dumps(result, ensure_ascii=False))
    return code
