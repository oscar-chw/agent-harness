"""Offline owner-local laptop kit. Uses the existing, tested harness installer."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

LIMIT = 16 * 1024 * 1024


def read(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing or linked kit file: " + path.name)
    with path.open("rb") as handle:
        body = handle.read(LIMIT + 1)
    if len(body) > LIMIT:
        raise ValueError("kit file exceeds size limit")
    return body


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate manifest key")
        result[key] = value
    return result


def validate(bundle):
    manifest = json.loads(read(bundle / "MANIFEST.json"), object_pairs_hook=unique)
    if not re.fullmatch(r"[a-zA-Z0-9._-]{1,40}", manifest.get("version", "")):
        raise ValueError("invalid version")
    for key in ("wheel", "knowledge"):
        entry = manifest[key]
        name = entry["file"]
        if (not name or PurePosixPath(name).name != name or "\\" in name or ":" in name
                or hashlib.sha256(read(bundle / name)).hexdigest() != entry["sha256"]):
            raise ValueError("changed or invalid " + key)
    expected = {entry["path"]: entry for entry in manifest["knowledge"]["files"]}
    if len(expected) != len(manifest["knowledge"]["files"]):
        raise ValueError("duplicate knowledge entry")
    with zipfile.ZipFile(bundle / manifest["knowledge"]["file"]) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError("archive membership changed")
        if len(names) > 1000 or sum(i.file_size for i in archive.infolist()) > LIMIT:
            raise ValueError("knowledge archive exceeds budget")
        for info in archive.infolist():
            name = info.filename
            path = PurePosixPath(name)
            if (path.is_absolute() or "\\" in name or ":" in name
                    or any(p in ("", ".", "..") for p in name.split("/"))
                    or stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG)):
                raise ValueError("unsafe knowledge archive member")
            body = archive.read(info)
            if (len(body) != expected[name]["bytes"]
                    or hashlib.sha256(body).hexdigest() != expected[name]["sha256"]):
                raise ValueError("knowledge content changed")
    return manifest


def publish_knowledge(bundle, manifest, target):
    if validate(bundle) != manifest:
        raise ValueError("manifest changed during installation")
    if target.is_symlink():
        raise ValueError("knowledge destination is linked")
    if target.exists():
        for entry in manifest["knowledge"]["files"]:
            body = read(target / entry["path"])
            if hashlib.sha256(body).hexdigest() != entry["sha256"]:
                raise ValueError("existing knowledge changed; preserving your version")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".harness-knowledge-", dir=target.parent))
    try:
        with zipfile.ZipFile(bundle / manifest["knowledge"]["file"]) as archive:
            for entry in manifest["knowledge"]["files"]:
                path = stage / entry["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(entry["path"]))
        stage.rename(target)
    finally:
        if stage.exists():
            shutil.rmtree(stage)  # Only this invocation's unpublished staging directory.


def restore_command(python, home, hh, *, windows):
    argv = [str(python), "-I", "-m", "agent_harness.cli", "--home", str(home), "uninstall"]
    if windows:
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        return "$env:HARNESS_HOME = " + quote(hh) + "; & " + " ".join(map(quote, argv))
    return "HARNESS_HOME=" + shlex.quote(str(hh)) + " " + shlex.join(argv)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify kit only; write nothing")
    parser.add_argument("--home", type=Path, help="test/alternate user home")
    parser.add_argument("--tools", default="codex", help="default codex; optionally codex,copilot-vscode")
    args = parser.parse_args()
    if sys.version_info < (3, 9):
        raise ValueError("Python 3.9 or newer is required")
    bundle = Path(__file__).resolve().parent
    manifest = validate(bundle)
    if args.check:
        print("KIT VERIFIED: artifact hashes, archive paths and knowledge bytes")
        return
    home = (args.home or Path.home()).expanduser().resolve()
    hh = (home / ".agent-harness" if args.home else
          Path(os.environ.get("HARNESS_HOME", str(home / ".agent-harness"))).expanduser().resolve())
    identity = manifest["version"] + "-" + manifest["wheel"]["sha256"][:12]
    # Like pipx, keep the interpreter outside the bounded knowledge/data store.
    # This relocates runtime bytes; it does not reduce the total installation size.
    runtime = home / ".local/share/agent-harness/runtime" / identity
    python = runtime / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        subprocess.run([sys.executable, "-m", "venv", str(runtime)], check=True)
    subprocess.run([str(python), "-I", "-m", "pip", "install", "--no-index", "--no-deps",
                    "--no-cache-dir", "--force-reinstall",
                    str(bundle / manifest["wheel"]["file"])], check=True)
    knowledge = hh / "profile/knowledge" / ("harness-" + manifest["knowledge"]["sha256"][:16])
    publish_knowledge(bundle, manifest, knowledge)
    env = dict(os.environ, HARNESS_HOME=str(hh))
    command = [str(python), "-I", "-m", "agent_harness.cli", "--home", str(home)]
    subprocess.run(command + ["install", "--yes", "--tools", args.tools, "--permission-profile",
                             "preserve", "--profile", str(hh / "profile")], env=env, check=True)
    subprocess.run(command + ["doctor"], env=env, check=True)
    print("Installed. Open a new Codex session to load its MCP configuration.")
    print("Knowledge: " + str(knowledge))
    print("Restore previous tool configuration (PowerShell):" if os.name == "nt" else
          "Restore previous tool configuration:")
    print(restore_command(python, home, hh, windows=os.name == "nt"))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile,
            subprocess.CalledProcessError) as error:
        print("INSTALL STOPPED: " + str(error), file=sys.stderr)
        sys.exit(1)
