"""Read-only accounting and scoped export preparation for an existing project vault.

No export, migration, pruning or native-store scan is performed. The caller must already be
authorized for the project and requested records. A prepared manifest is not a restorable backup.
"""
import argparse
import json
import os
import stat
from pathlib import Path

from .presets import _read
from .project_memory import ProjectMemory, _scope_lists
from .vault_sources import _area, _bytes, _project, _sha, _unique_object


def _class(relative):
    if relative == "project.json":
        return "metadata"
    if relative.startswith("sources/"):
        return "retained-sources"
    if relative.startswith("records/"):
        return "retained-records"
    if relative in ("index.sqlite", "index.sqlite-wal", "index.sqlite-shm"):
        return "derived"
    return "unclassified"


def inventory(root, project_id, *, max_files=10000, max_scan_bytes=64 * 1024 * 1024):
    if any(type(n) is not int or n <= 0 for n in (max_files, max_scan_bytes)):
        raise ValueError("inventory budget must be positive")
    root = Path(root).resolve(strict=True)
    area = _area(root)
    _read(area / "project.json", 16384)
    if _project(root) != project_id:
        raise ValueError("project identity does not match accounting root")
    files, pending, visited, total = [], [area], 0, 0
    by_class = {key: 0 for key in ("metadata", "retained-sources", "retained-records", "derived", "unclassified")}
    while pending:
        directory = pending.pop()
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("inventory directory boundary changed")
        with os.scandir(directory) as entries:
            for entry in entries:
                visited += 1
                if visited > max_files:
                    raise ValueError("inventory entry budget exceeded; no partial accounting")
                info = entry.stat(follow_symlinks=False)
                path = Path(entry.path)
                if stat.S_ISDIR(info.st_mode):
                    pending.append(path)
                    continue
                if not stat.S_ISREG(info.st_mode):
                    raise ValueError("inventory contains a symlink or nonregular file")
                total += info.st_size
                if total > max_scan_bytes:
                    raise ValueError("inventory byte budget exceeded; no partial accounting")
                relative = path.relative_to(area).as_posix()
                category = _class(relative)
                by_class[category] += info.st_size
                files.append({"path": relative, "bytes": info.st_size, "class": category,
                              "identity": [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]})
    return {"schema": "harness.vault-accounting/v1", "project_id": project_id,
            "scope": "project-.harness-only", "logical_bytes": total, "by_class": by_class,
            "files": sorted(files, key=lambda entry: entry["path"]), "pruned": False,
            "limits": {"entries": max_files, "logical_bytes": max_scan_bytes},
            "disk_allocation": "NOT_MEASURED", "native_stores": "NOT_SCANNED"}


def prepare(root, project_id, *, receipts, allowed_sensitivities, allowed_scopes, layers,
            max_bytes=16 * 1024 * 1024):
    if not isinstance(receipts, list) or not 1 <= len(receipts) <= 64:
        raise ValueError("export preparation needs 1..64 explicit receipts")
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError("export budget must be positive")
    sensitivity, scopes, selected_layers = _scope_lists(allowed_sensitivities, allowed_scopes, layers)
    receipts = json.loads(_bytes(receipts))
    before = inventory(root, project_id)
    memory = ProjectMemory(root, project_id)
    area = _area(memory.root)
    selected = {"project.json"}
    seen, retained = set(), []
    pending = receipts.copy()
    while pending:
        ref = pending.pop()
        # Check declared access for every selected and historical revision before sources.
        result = memory.read_scoped(ref, allowed_sensitivities=sensitivity, allowed_scopes=scopes,
                                    layers=selected_layers, historical=True, max_bytes=128 * 1024)
        key = _sha(_bytes(ref))
        if key in seen:
            continue
        seen.add(key)
        retained.append(ref)
        selected.add(f"records/{ref['sequence']:08}.json")
        item = result["item"]
        for source in item["provenance"]:
            selected.add("sources/" + source["source"]["source_id"] + ".json")
        if item["supersedes"] is not None:
            pending.append(item["supersedes"])
        if len(seen) > 10000:
            raise ValueError("export history budget exceeded")
    paths = {entry["path"]: entry for entry in before["files"]}
    files, total = [], 0
    for relative in sorted(selected):
        if relative not in paths:
            raise ValueError("retained export input is missing")
        raw = _read(area / relative, max_bytes)
        total += len(raw)
        if total > max_bytes:
            raise ValueError("export byte budget exceeded; history was not omitted")
        files.append({"path": relative, "bytes": len(raw), "sha256": _sha(raw), "class": paths[relative]["class"]})
    if inventory(root, project_id) != before:
        raise ValueError("storage changed during preparation; retry from a stable snapshot")
    return {"schema": "harness.vault-export-plan/v1", "project_id": project_id,
            "status": "PREPARED_NO_EXPORT", "copied": False, "files": files, "bytes": total,
            "requested_receipts": receipts, "retained_receipts": sorted(retained, key=lambda ref: ref["sequence"]),
            "scope": {"sensitivities": sensitivity, "items": scopes, "layers": selected_layers},
            "source_mode": "retained-history", "journal_mode": "selected-item-lineage-not-full-global-journal",
            "restore": "NOT_IMPLEMENTED", "native_backup": False, "budget_bytes": max_bytes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inventory", "prepare"))
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--request", type=Path, help="bounded JSON with receipts and explicit access filters")
    parser.add_argument("--max-bytes", type=int, default=16 * 1024 * 1024)
    args = parser.parse_args()
    try:
        if args.action == "inventory":
            result = inventory(args.project_root, args.project_id)
        else:
            if args.request is None:
                raise ValueError("prepare requires an explicit request file")
            request = json.loads(_read(args.request, 65536), object_pairs_hook=_unique_object)
            if not isinstance(request, dict) or set(request) != {"receipts", "allowed_sensitivities", "allowed_scopes", "layers"}:
                raise ValueError("invalid export request schema")
            result = prepare(args.project_root, args.project_id, max_bytes=args.max_bytes, **request)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({"status": "ERROR", "reason": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
