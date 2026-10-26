"""Read-only CLI/package provenance. Never executes discovered launchers or reads auth/config."""
import ast
import hashlib
import os
from pathlib import Path
import shutil
import stat
import sys

COMPONENTS = ("__init__.py", "cli.py", "workgraph/plan.py", "project_memory.py",
              "vault_retrieval.py", "scoped_state.py", "question_audit.py")
FILE_LIMIT = 1024 * 1024


def _file(path, boundary=None):
    path = Path(path)
    try:
        resolved = path.resolve(strict=True)
        if boundary is not None:
            try:
                resolved.relative_to(boundary.resolve())
            except ValueError:
                return {"path": str(path), "status": "OUTSIDE_PACKAGE"}, None
        if not stat.S_ISREG(resolved.stat().st_mode):
            return {"path": str(path), "resolved": str(resolved), "status": "NOT_REGULAR"}, None
        with resolved.open("rb") as handle:
            raw = handle.read(FILE_LIMIT + 1)
        if len(raw) > FILE_LIMIT:
            return {"path": str(path), "resolved": str(resolved), "status": "TOO_LARGE"}, None
        return {"path": str(path), "resolved": str(resolved), "status": "PRESENT", "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest()}, raw
    except FileNotFoundError:
        return {"path": str(path), "status": "MISSING"}, None
    except (OSError, RuntimeError) as error:
        return {"path": str(path), "status": "UNREADABLE", "error": type(error).__name__}, None


def _version(raw):
    if raw is None:
        return "NOT_OBSERVABLE"
    try:
        tree = ast.parse(raw)
    except (SyntaxError, ValueError):
        return "NOT_OBSERVABLE"
    values = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets):
            values.append(node.value.value if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) else None)
    return values[0] if len(values) == 1 and values[0] else "NOT_OBSERVABLE"


def _package(root):
    files, version = {}, "NOT_OBSERVABLE"
    for name in COMPONENTS:
        info, raw = _file(root / name, boundary=root)
        files[name] = info
        if name == "__init__.py":
            version = _version(raw)
    return {"root": str(root), "declared_version": version, "files": files}


def inspect_runtime(harness_home, *, package_root=None, search_path=None, launcher=None):
    """Current CLI or explicitly supplied source snapshot, not a native agent loading claim."""
    explicit = package_root is not None
    root = Path(package_root) if explicit else Path(__file__).resolve().parent
    current = _package(root)
    installed = _package(Path(harness_home) / "lib/agent_harness")
    commands = {}
    for name in ("harness", "plan"):
        selected = shutil.which(name, path=os.environ.get("PATH", "") if search_path is None else search_path)
        info = _file(selected)[0] if selected else {"status": "MISSING"}
        commands[name] = {"selected": selected, **info}
    invoked = _file(launcher if launcher is not None else sys.argv[0])[0]
    match = (invoked.get("resolved") == commands["harness"].get("resolved")
             if invoked.get("resolved") and commands["harness"].get("resolved") else None)
    differences = [name for name in COMPONENTS
                   if (current["files"][name]["status"], current["files"][name].get("sha256"))
                   != (installed["files"][name]["status"], installed["files"][name].get("sha256"))]
    statuses = [info["status"] for package in (current, installed) for info in package["files"].values()]
    if all(installed["files"][name]["status"] == "MISSING" for name in ("__init__.py", "cli.py")):
        comparison = "INSTALLED_PACKAGE_MISSING"
    elif any(status not in ("PRESENT", "MISSING") for status in statuses):
        comparison = "NOT_OBSERVABLE"
    else:
        comparison = "MIXED" if differences else "MATCHED_SELECTED_FILES"
    return {"schema": "harness.runtime-inventory/v1", "scope": "explicit package snapshot" if explicit else "current CLI process",
            "current": current, "installed": installed, "commands": commands, "invoked": invoked,
            "path_matches_invocation": match, "comparison": comparison, "differences": differences,
            "native_sessions": "NOT_OBSERVABLE"}


def render(report):
    return "\n".join([
        f"current   {report['current']['root']} (declared {report['current']['declared_version']})",
        f"installed {report['installed']['root']} — {report['comparison']}",
        f"PATH      harness={report['commands']['harness'].get('resolved', 'MISSING')}",
        f"plan      {report['commands']['plan'].get('resolved', 'MISSING')} (not executed)",
        "native    loading in other sessions: NOT_OBSERVABLE; selected-file comparison only",
    ])
