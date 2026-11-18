"""Apply a pinned package update without rerunning application adapters."""
import argparse
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import sqlite3
import stat
import sys
from tempfile import NamedTemporaryFile


FILE_LIMIT = 2 * 1024 * 1024
STATE = Path("installed.json")
VERSION_FILE = Path("lib/agent_harness/__init__.py")
VSCODE_PROMPTS = Path("content/copilot/prompts")
APPLICATION_FILES = (
    ".codex/AGENTS.md", ".codex/config.toml", ".codex/hooks.json",
    ".claude/CLAUDE.md", ".claude/settings.json", ".claude.json",
    "Library/Application Support/Code/User/mcp.json",
    "Library/Application Support/Code/User/settings.json",
    ".config/Code/User/mcp.json", ".config/Code/User/settings.json",
)


def digest(data):
    return sha256(data).hexdigest()


def regular(root, relative, *, optional=False):
    path = root / relative
    if path.resolve() != path:
        raise ValueError(f"linked path refused: {relative}")
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except FileNotFoundError:
        if optional:
            return None
        raise
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > FILE_LIMIT:
            raise ValueError(f"invalid package file: {relative}")
        data = stream.read(FILE_LIMIT + 1)
        if len(data) > FILE_LIMIT:
            raise ValueError(f"package file exceeds its size budget: {relative}")
        return data, info.st_mode & 0o777


def installed_path(name):
    path = PurePosixPath(name)
    if (path.is_absolute() or ".." in path.parts or name != path.as_posix()
            or "\\" in name or ":" in name):
        raise ValueError("invalid manifest path")
    if path.parts[:2] == ("src", "agent_harness") and len(path.parts) > 2:
        return Path("lib", *path.parts[1:])
    if path.parts[:1] == ("content",) and len(path.parts) > 1:
        return Path(*path.parts)
    raise ValueError("manifest file outside package roots")


def is_protected(relative):
    name = relative.name.lower()
    return "hooks" in relative.parts or "guard" in name or "permission" in name


def expected_package(args):
    raw, _ = regular(args.manifest.parent, Path(args.manifest.name))
    if digest(raw) != args.manifest_sha256:
        raise ValueError("manifest digest changed")
    manifest = json.loads(raw)
    if (not re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
            or not re.fullmatch(r"[0-9a-f]{40}", manifest["build_commit"])):
        raise ValueError("expected a stable release and a full commit id")
    new = {}
    source_paths = set()
    for row in manifest["packaged_files"]:
        name = row["source"]
        relative = installed_path(name)
        data, mode = regular(args.source, Path(name))
        if relative in new or digest(data) != row["sha256"]:
            raise ValueError(f"duplicate or changed package file: {name}")
        new[relative] = (data, mode)
        source_paths.add(name)
    if VERSION_FILE not in new or json.dumps(manifest["version"]).encode() not in new[VERSION_FILE][0]:
        raise ValueError("package version differs from the manifest")
    # A removal belongs to an ordinary reviewed installation.
    for group in ("src/agent_harness", "content"):
        for path in (args.baseline / group).rglob("*"):
            if path.is_symlink() or (path.is_file() and path.relative_to(args.baseline).as_posix() not in source_paths
                                     and "__pycache__" not in path.parts):
                raise ValueError("baseline has a linked file or a package removal")
    old = {installed_path(name): regular(args.baseline, Path(name), optional=True)
           for name in source_paths}
    return manifest, old, new


def missing_prompt_repairs(args, entries, new):
    repairs = {}
    for entry in entries:
        target = Path(entry["path"])
        suffix = ".prompt.md"
        if (target.parent != args.harness_home / VSCODE_PROMPTS or not target.name.endswith(suffix)
                or entry.get("tools") != ["copilot-vscode"] or entry.get("kind") != "replace"):
            continue
        relative = target.relative_to(args.harness_home)
        if relative in new or regular(args.harness_home, relative, optional=True) is not None:
            continue
        if not args.restore_missing_vscode_prompts:
            raise ValueError(f"managed VS Code prompt is missing: {target.name}; "
                             "preview --restore-missing-vscode-prompts to check an exact repair")
        source = Path("content/prompts") / (target.name[:-len(suffix)] + ".md")
        pinned = new.get(source)
        if (pinned is None or entry.get("written") != "f:" + digest(pinned[0])
                or is_protected(relative)):
            raise ValueError(f"no release bytes match the installed record for {target.name}")
        repairs[relative] = (None, (pinned[0], 0o644))
    return repairs


def checks(args, manifest, old, new):
    live = {path: regular(args.harness_home, path, optional=True) for path in new}
    state_raw = regular(args.harness_home, STATE)
    state = json.loads(state_raw[0])
    if not isinstance(state["entries"], list) or not state["tools"]:
        raise ValueError("existing installation record missing")
    current = (all(live[p] is not None and live[p][0] == new[p][0] for p in new)
               and state.get("source_commit") == manifest["build_commit"])
    updates = missing_prompt_repairs(args, state["entries"], new)
    if not current:
        for path, before in live.items():
            source_old = old[path]
            if ((before is None) != (source_old is None)
                    or (before is not None and before[0] != source_old[0])):
                raise ValueError(f"installed payload differs from the baseline: {path}")
            data, mode = new[path]
            if before is None or before[0] != data:
                if is_protected(path):
                    raise ValueError(f"protected package file would change: {path}")
                updates[path] = (before, (data, mode if before is None else before[1]))
    changed_paths = {args.harness_home / path for path in updates}
    for name in APPLICATION_FILES:
        app_path = args.application_home / name
        if app_path.resolve() in changed_paths:
            raise ValueError(f"active application configuration points to a changed package file: {name}")
    if current:
        return updates
    for entry in state["entries"]:
        target = Path(entry["path"])
        relative = (target.relative_to(args.harness_home)
                    if target.is_relative_to(args.harness_home) else None)
        if relative in updates:
            entry["written"] = "f:" + digest(updates[relative][1][0])
        elif relative is not None and any(relative in path.parents for path in updates):
            raise ValueError(f"managed package directory needs an adapter update: {relative}")
    state.update(source=str(args.harness_home), source_commit=manifest["build_commit"])
    updates[STATE] = (state_raw, ((json.dumps(state, indent=2, sort_keys=True) + "\n").encode(), state_raw[1]))
    return updates


def replace(path, payload, *, exclusive=False):
    data, mode = payload
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = NamedTemporaryFile(dir=path.parent, delete=False)
    temporary = Path(stream.name)
    try:
        os.chmod(temporary, mode)
        with stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if exclusive:
            os.link(temporary, path)
        else:
            temporary.replace(path)
    finally:
        stream.close()
        temporary.unlink(missing_ok=True)


def apply(args, updates, new):
    args.backup.mkdir(mode=0o700)
    metadata = {}
    for path, (before, after) in updates.items():
        if before is not None:
            replace(args.backup / path, (before[0], 0o600))
            if regular(args.backup, path)[0] != before[0]:
                raise ValueError(f"rollback bytes failed verification: {path}")
        metadata[path.as_posix()] = {"before": digest(before[0]) if before else None,
                                    "before_mode": before[1] if before else None,
                                    "after": digest(after[0])}
    replace(args.backup / "transaction.json", (json.dumps(metadata, indent=2).encode() + b"\n", 0o600))
    written, directories = [], []
    try:
        for path in sorted(updates, key=lambda p: (p == STATE, p == VERSION_FILE, p)):
            before, after = updates[path]
            if regular(args.harness_home, path, optional=True) != before:
                raise ValueError(f"concurrent package edit: {path}")
            dest = args.harness_home / path
            directories.extend(parent for parent in dest.parents if not parent.exists())
            written.append(path)
            try:
                replace(dest, after, exclusive=before is None)
            except FileExistsError:
                if before is None:
                    written.pop()
                raise
        expected = {**new, **{path: after for path, (_, after) in updates.items()}}
        if any(regular(args.harness_home, path)[0] != pair[0] for path, pair in expected.items()):
            raise ValueError("installed package readback failed")
    except BaseException as original:
        for path in reversed(written):
            before, after = updates[path]
            current = regular(args.harness_home, path, optional=True)
            if current == before:
                continue
            if current != after:
                raise ValueError(f"rollback stopped at an external edit: {path}") from original
            dest = args.harness_home / path
            if before is None:
                dest.unlink()
            else:
                replace(dest, before)
        for parent in sorted(set(directories), key=lambda p: -len(p.parts)):
            if parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "source", "manifest", "harness-home", "backup"):
        parser.add_argument("--" + name, type=lambda path: Path(path).expanduser().absolute(), required=True)
    parser.add_argument("--application-home", type=lambda path: Path(path).expanduser().absolute())
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--restore-missing-vscode-prompts", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    args.application_home = args.application_home or args.harness_home.parent
    try:
        for path in (args.baseline, args.source, args.manifest, args.harness_home, args.backup):
            if path.resolve() != path:
                raise ValueError("linked or noncanonical update path")
        if any(args.backup.is_relative_to(p) for p in (args.harness_home, args.source, args.baseline)):
            raise ValueError("backup must be outside the installation and release sources")
        manifest, old, new = expected_package(args)
        updates = checks(args, manifest, old, new)
        status = "READY" if updates else "CURRENT"
        if args.apply and updates:
            lock_path = args.harness_home / "state/.self-update.lock"
            if lock_path.resolve() != lock_path:
                raise ValueError("linked update lock")
            lock_path.parent.mkdir(exist_ok=True)
            with closing(sqlite3.connect(str(lock_path), timeout=0)) as lock:
                lock.execute("BEGIN IMMEDIATE")
                updates = checks(args, manifest, old, new)
                if updates:
                    apply(args, updates, new)
                    status = "INSTALLED"
                else:
                    status = "CURRENT"
        print(json.dumps({"status": status, "version": manifest["version"],
                          "source_commit": manifest["build_commit"], "package_files": len(new),
                          "updated_paths": sum(path in new for path in updates),
                          "restored_vscode_prompts": sum(path.parent == VSCODE_PROMPTS
                                                         and path not in new for path in updates),
                          "backup": str(args.backup) if status == "INSTALLED" else None}))
        return 0
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error, KeyboardInterrupt) as error:
        print(f"payload update held: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    def interrupted(_signum, _frame):
        raise KeyboardInterrupt("interrupted")

    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(main())
