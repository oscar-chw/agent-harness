"""Portable selected-evidence archives. No extraction, native restore, upload or authority grant."""
import argparse
import base64
import binascii
import json
import os
import re
import tempfile
import uuid
from datetime import datetime
from pathlib import Path, PurePosixPath

from .presets import _read
from .project_memory import CONTRACT, FIELDS, GENERATED, _scope_lists, _validate, _validate_receipt
from .vault_export import prepare
from .vault_sources import _area, _bytes, _lines, _sha, _unique_object

ARCHIVE_LIMIT = 32 * 1024 * 1024
PAYLOAD_LIMIT = 16 * 1024 * 1024
HEX = re.compile(r"[0-9a-f]{64}\Z")
ARCHIVE_PATH = re.compile(r"(?:project\.json|sources/[0-9a-f]{64}\.json|records/[0-9]{8}\.json)\Z")
PLAN_FIELDS = {"schema", "project_id", "status", "copied", "files", "bytes", "requested_receipts",
               "retained_receipts", "scope", "source_mode", "journal_mode", "restore", "native_backup", "budget_bytes"}


def _limit(value, ceiling):
    if type(value) is not int or not 0 < value <= ceiling:
        raise ValueError("archive budget must be positive and within the hard ceiling")


def _hash(value):
    if not isinstance(value, str) or not HEX.fullmatch(value):
        raise ValueError("expected SHA-256 pin is required")


def _plan(plan, project_id):
    if not isinstance(project_id, str) or str(uuid.UUID(project_id)) != project_id:
        raise ValueError("canonical project UUID required")
    if (not isinstance(plan, dict) or set(plan) != PLAN_FIELDS
            or plan["schema"] != "harness.vault-export-plan/v1" or plan["project_id"] != project_id
            or plan["status"] != "PREPARED_NO_EXPORT" or plan["copied"] is not False
            or plan["native_backup"] is not False or plan["restore"] != "NOT_IMPLEMENTED"
            or plan["source_mode"] != "retained-history"
            or plan["journal_mode"] != "selected-item-lineage-not-full-global-journal"):
        raise ValueError("invalid scoped evidence-export plan")
    _limit(plan["budget_bytes"], PAYLOAD_LIMIT)
    scope = plan["scope"]
    if not isinstance(scope, dict) or set(scope) != {"sensitivities", "items", "layers"}:
        raise ValueError("explicit archive scope required")
    _scope_lists(scope["sensitivities"], scope["items"], scope["layers"])
    for name, maximum in (("requested_receipts", 64), ("retained_receipts", 10000)):
        refs = plan[name]
        if not isinstance(refs, list) or not 1 <= len(refs) <= maximum:
            raise ValueError("bounded nonempty archive receipts required")
        for ref in refs:
            _validate_receipt(ref, project_id)
        if len({_sha(_bytes(ref)) for ref in refs}) != len(refs):
            raise ValueError("duplicate archive receipt")
    files = plan["files"]
    if not isinstance(files, list) or not 1 <= len(files) <= 10000:
        raise ValueError("bounded file manifest required")
    names, total = set(), 0
    for entry in files:
        if (not isinstance(entry, dict) or set(entry) != {"path", "bytes", "sha256", "class"}
                or not isinstance(entry["path"], str) or not ARCHIVE_PATH.fullmatch(entry["path"])
                or type(entry["bytes"]) is not int or entry["bytes"] < 0):
            raise ValueError("invalid retained archive path or metadata")
        _hash(entry["sha256"])
        category = "metadata" if entry["path"] == "project.json" else "retained-" + entry["path"].split("/")[0]
        if entry["path"] in names or entry["class"] != category:
            raise ValueError("duplicate or misclassified archive input")
        names.add(entry["path"])
        total += entry["bytes"]
    if ("project.json" not in names or type(plan["bytes"]) is not int or total != plan["bytes"]
            or total > plan["budget_bytes"]):
        raise ValueError("archive aggregate byte budget or project manifest mismatch")


def _records(plan, decoded, project_id):
    project = json.loads(decoded["project.json"], object_pairs_hook=_unique_object)
    if (not isinstance(project, dict) or type(project.get("schema")) is not int
            or project["schema"] != 1 or project.get("project_id") != project_id):
        raise ValueError("archive project identity mismatch")
    scope = plan["scope"]
    by_ref, needed = {}, {"project.json"}
    for ref in plan["retained_receipts"]:
        path = f"records/{ref['sequence']:08}.json"
        raw = decoded.get(path)
        if raw is None or _sha(raw) != ref["sha256"]:
            raise ValueError("retained record is missing or disagrees with its receipt")
        event = json.loads(raw, object_pairs_hook=_unique_object)
        if (not isinstance(event, dict) or set(event) != {"schema", "sequence", "previous", "item"}
                or type(event["schema"]) is not int or event["schema"] != 1
                or type(event["sequence"]) is not int or event["sequence"] != ref["sequence"] or _bytes(event) != raw):
            raise ValueError("invalid retained event")
        if event["previous"] is not None:
            _hash(event["previous"])
        if (event["sequence"] == 1) != (event["previous"] is None):
            raise ValueError("invalid retained global predecessor shape")
        item = event["item"]
        if not isinstance(item, dict) or set(item) != FIELDS | GENERATED:
            raise ValueError("invalid retained item schema")
        _validate({key: item[key] for key in FIELDS}, project_id)
        if item["id"] != ref["id"] or type(item["revision"]) is not int or item["revision"] != ref["revision"]:
            raise ValueError("retained record identity mismatch")
        if any(not isinstance(item[k], str) for k in ("created_at", "updated_at")):
            raise ValueError("invalid retained timestamps")
        try:
            created, updated = (datetime.fromisoformat(item[k]) for k in ("created_at", "updated_at"))
        except ValueError:
            # Parser errors can contain the source value; do not echo private archived data.
            raise ValueError("invalid retained timestamps") from None
        if created.tzinfo is None or updated.tzinfo is None or created > updated:
            raise ValueError("invalid retained timestamp order")
        if (item["scope"] not in scope["items"] or item["layer"] not in scope["layers"]
                or item["sensitivity"] not in scope["sensitivities"]):
            raise PermissionError("retained record is outside the declared archive scope")
        by_ref[_sha(_bytes(ref))] = item
        needed.add(path)
        for provenance in item["provenance"]:
            source = provenance["source"]
            if (set(source) != {"project_id", "source_id", "source", "sha256", "line_count"}
                    or source["project_id"] != project_id or type(source["line_count"]) is not int):
                raise ValueError("invalid retained source receipt")
            _hash(source["source_id"])
            _hash(source["sha256"])
            relative = source["source"]
            if not isinstance(relative, str) or not relative or "\x00" in relative:
                raise ValueError("invalid source provenance path")
            original = PurePosixPath(relative)
            if not original.parts or original.is_absolute() or ".." in original.parts or original.parts[0] == ".harness":
                raise ValueError("source provenance leaves the original project")
            path = "sources/" + source["source_id"] + ".json"
            raw = decoded.get(path)
            if raw is None or _sha(raw) != source["source_id"]:
                raise ValueError("retained source missing or corrupt")
            snapshot = json.loads(raw, object_pairs_hook=_unique_object)
            if (not isinstance(snapshot, dict) or set(snapshot) != {"schema", "project_id", "source", "sha256", "text"}
                    or type(snapshot["schema"]) is not int or snapshot["schema"] != 1 or snapshot["project_id"] != project_id
                    or snapshot["source"] != source["source"] or snapshot["sha256"] != source["sha256"]
                    or not isinstance(snapshot["text"], str) or _bytes(snapshot) != raw
                    or _sha(snapshot["text"].encode("utf-8")) != source["sha256"]):
                raise ValueError("retained source metadata mismatch")
            lines = len(_lines(snapshot["text"]))
            if lines != source["line_count"] or not 1 <= provenance["start_line"] <= provenance["end_line"] <= lines:
                raise ValueError("retained source span mismatch")
            needed.add(path)
    for ref in plan["requested_receipts"]:
        if _sha(_bytes(ref)) not in by_ref:
            raise ValueError("requested receipt is absent")
    for item in by_ref.values():
        prior = item["supersedes"]
        if prior is None:
            if item["revision"] != 1:
                raise ValueError("selected lineage lost its first revision")
        else:
            _validate_receipt(prior, project_id)
            old = by_ref.get(_sha(_bytes(prior)))
            if (old is None or old["revision"] + 1 != item["revision"]
                    or any(old[key] != item[key] for key in CONTRACT)
                    or old["created_at"] != item["created_at"]
                    or datetime.fromisoformat(old["updated_at"]) > datetime.fromisoformat(item["updated_at"])):
                raise ValueError("selected revision lineage is missing or inconsistent")
    if set(decoded) != needed:
        raise ValueError("archive contains unreferenced payloads")


def _verify_bytes(raw, project_id, sha256, max_payload_bytes):
    _hash(sha256)
    if _sha(raw) != sha256:
        raise ValueError("archive differs from the externally supplied digest")
    bundle = json.loads(raw, object_pairs_hook=_unique_object)
    if (not isinstance(bundle, dict) or set(bundle) != {"schema", "project_id", "plan", "plan_sha256", "payloads"}
            or bundle["schema"] != "harness.vault-evidence-archive/v1"
            or bundle["project_id"] != project_id or _bytes(bundle) != raw):
        raise ValueError("invalid canonical archive or project scope")
    plan = bundle["plan"]
    _plan(plan, project_id)
    if digest_plan(plan) != bundle["plan_sha256"]:
        raise ValueError("archive plan digest mismatch")
    payloads = bundle["payloads"]
    if not isinstance(payloads, dict) or set(payloads) != {f["path"] for f in plan["files"]}:
        raise ValueError("missing or extra archive payload")
    decoded, total = {}, 0
    for entry in plan["files"]:
        encoded = payloads[entry["path"]]
        if not isinstance(encoded, str):
            raise ValueError("archive payload must be encoded text")
        if entry["bytes"] > max_payload_bytes - total:
            raise ValueError("archive decoded-payload budget exceeded")
        if len(encoded) != 4 * ((entry["bytes"] + 2) // 3):
            raise ValueError("encoded payload length disagrees with its pinned size")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            raise ValueError("invalid payload encoding") from None
        total += len(data)
        if total > max_payload_bytes:
            raise ValueError("archive decoded-payload budget exceeded")
        if len(data) != entry["bytes"] or _sha(data) != entry["sha256"]:
            raise ValueError("archive payload hash or size mismatch")
        decoded[entry["path"]] = data
    _records(plan, decoded, project_id)
    return {"status": "VERIFIED_EVIDENCE_ONLY", "project_id": project_id, "sha256": sha256,
            "archive_bytes": len(raw), "payload_bytes": total, "files": len(decoded),
            "record_revisions": len(plan["retained_receipts"]), "native_restore": False,
            "execution_authorized": False, "extracted": False}


def digest_plan(plan):
    return _sha(_bytes(plan))


def verify(path, *, project_id, sha256, max_archive_bytes=ARCHIVE_LIMIT, max_payload_bytes=PAYLOAD_LIMIT):
    _limit(max_archive_bytes, ARCHIVE_LIMIT)
    _limit(max_payload_bytes, PAYLOAD_LIMIT)
    return _verify_bytes(_read(Path(path), max_archive_bytes), project_id, sha256, max_payload_bytes)


def create(root, project_id, plan, destination, *, plan_sha256, max_archive_bytes=ARCHIVE_LIMIT):
    _limit(max_archive_bytes, ARCHIVE_LIMIT)
    _hash(plan_sha256)
    if digest_plan(plan) != plan_sha256:
        raise ValueError("prepared plan differs from its supplied digest")
    plan = json.loads(_bytes(plan))
    _plan(plan, project_id)
    root = Path(root).resolve(strict=True)
    destination = Path(destination)
    parent = destination.parent.resolve(strict=True)
    if destination.is_symlink() or destination.exists() or parent.is_relative_to(root):
        raise ValueError("archive destination must be new and outside the source project")
    destination = parent / destination.name
    scope = plan["scope"]
    def current():
        return prepare(root, project_id, receipts=plan["requested_receipts"], allowed_sensitivities=scope["sensitivities"],
                       allowed_scopes=scope["items"], layers=scope["layers"], max_bytes=plan["budget_bytes"])
    if current() != plan:
        raise ValueError("prepared manifest is stale or changed")
    payloads = {}
    for entry in plan["files"]:
        data = _read(_area(root) / entry["path"], entry["bytes"])
        if len(data) != entry["bytes"] or _sha(data) != entry["sha256"]:
            raise ValueError("selected source changed during archive assembly")
        payloads[entry["path"]] = base64.b64encode(data).decode("ascii")
    raw = _bytes({"schema": "harness.vault-evidence-archive/v1", "project_id": project_id,
                  "plan": plan, "plan_sha256": plan_sha256, "payloads": payloads})
    if len(raw) > max_archive_bytes:
        raise ValueError("archive encoded-byte budget exceeded")
    result = _verify_bytes(raw, project_id, _sha(raw), PAYLOAD_LIMIT)
    if current() != plan:
        raise ValueError("source changed while assembling archive")
    pending = None
    try:
        with tempfile.NamedTemporaryFile(dir=parent, prefix=".archive-pending-", delete=False) as handle:
            pending = Path(handle.name)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        # No-replace publication; no in-place fallback, including on unsupported filesystems.
        os.link(pending, destination)
    finally:
        if pending is not None:
            pending.unlink()
    return {**result, "status": "ARCHIVED_EVIDENCE_ONLY", "path": str(destination)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("create")
    for name in ("project-root", "project-id", "plan", "plan-sha", "destination"):
        p.add_argument("--" + name, required=True)
    p = sub.add_parser("verify")
    for name in ("project-id", "bundle", "sha"):
        p.add_argument("--" + name, required=True)
    args = parser.parse_args()
    try:
        if args.action == "create":
            plan = json.loads(_read(args.plan, 2 * 1024 * 1024), object_pairs_hook=_unique_object)
            result = create(args.project_root, args.project_id, plan, args.destination, plan_sha256=args.plan_sha)
        else:
            result = verify(args.bundle, project_id=args.project_id, sha256=args.sha)
        print(json.dumps(result))
        return 0
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({"status": "ERROR", "reason": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
