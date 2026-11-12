"""Opt-in gate input/result bindings; no scheduler or authority interpreter.

Receipt files are immutable by content address. The graph's atomic replacement publishes a
reference only after its receipt exists. Hashes detect drift, not same-user fabrication of both
graph and evidence. Artifact reads are bounded observations, not a filesystem-wide snapshot.
"""
import hashlib
import json
import os
import re
import stat
import tempfile
import uuid
from pathlib import Path

MARKER = "## versions: v1"
REF = re.compile(r" @version=([0-9a-f]{64})$")
AUDIT = re.compile(r"^\d{4}-\d\d-\d\dT[\d:]+Z (?:exit -?\d+ |NOT_RUN |VERSION INVALIDATED |released — |gate ran to exit )")
MUTABLE = {"owner", "lease", "version_claim", "version_run"}
FILE_LIMIT = 16 * 1024 * 1024
READ_LIMIT = 64 * 1024 * 1024
RECEIPT_LIMIT = 65536
STORE_LIMIT = 64 * 1024 * 1024
STORE_FILES = 10000


def raw_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def digest(value):
    return hashlib.sha256(raw_json(value)).hexdigest()


def enabled(lines, nodes):
    markers, fenced = [], False
    for line in lines:
        if re.match(r"^\s*(```|~~~)", line):
            fenced = not fenced
        elif not fenced and line.startswith("## versions:"):
            markers.append(line)
    if markers and markers != [MARKER]:
        raise ValueError("expected exactly one '## versions: v1' marker")
    if not markers and any(REF.search(note) or "VERSION INVALIDATED" in note
                           for n in nodes.values() for note in n["notes"]):
        raise ValueError("version evidence remains but its versions marker is missing")
    if not markers and any(n["fields"].get("version_claim") or n["fields"].get("version_run") for n in nodes.values()):
        raise ValueError("version claim remains but its versions marker is missing")
    return bool(markers)


class Versions:
    def __init__(self, path, lines, nodes):
        self.path, self.nodes = Path(path), nodes
        self.root = self.path.parent.resolve().parent
        self.directory = self.path.with_suffix(".versions")
        self.cache, self.states = {}, {}
        self.read_bytes = 0
        excluded = {n["line"] for n in nodes.values()}
        for n in nodes.values():
            excluded.update(i for i in n["note_lines"] if AUDIT.match(lines[i].strip()))
        self.policy = digest([line.strip() for i, line in enumerate(lines) if i not in excluded and line.strip()])

    def paths(self, node, field):
        raw = node["fields"].get(field, "")
        names = [p.strip() for p in raw.split(",")] if raw else []
        if len(names) > 32 or len(names) != len(set(names)):
            raise ValueError(f"{field}: at most 32 unique file paths required")
        for name in names:
            p = Path(name)
            if (not name or len(name) > 512 or p.is_absolute() or "\\" in name or ":" in name
                    or any(part in (".", "..") for part in name.split("/"))
                    or name.split("/")[0] == self.path.parent.name):
                raise ValueError(f"{field}: invalid project-relative path or plan control input: {name!r}")
            current = self.root
            for part in p.parts:
                current = current / part
                if current.is_symlink():
                    raise ValueError(f"{field}: redirected path {name!r}")
        return sorted(names)

    def files(self, names):
        result = {}
        for name in names:
            if name not in self.cache:
                path = self.root / name
                # O_NONBLOCK avoids hanging on a FIFO before fstat can reject it.
                fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
                with os.fdopen(fd, "rb") as stream:
                    before = os.fstat(stream.fileno())
                    if not stat.S_ISREG(before.st_mode) or before.st_size > FILE_LIMIT:
                        raise ValueError(f"not a regular file within the 16 MiB bound: {name}")
                    sha, count = hashlib.sha256(), 0
                    while True:
                        chunk = stream.read(1024 * 1024)
                        if not chunk:
                            break
                        sha.update(chunk)
                        count += len(chunk)
                        self.read_bytes += len(chunk)
                        if count > FILE_LIMIT or self.read_bytes > READ_LIMIT:
                            raise ValueError("version observation exceeds its byte budget")
                    after = os.fstat(stream.fileno())
                current = path.stat()
                stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_mode)
                if count != before.st_size or stamp(before) != stamp(after) or stamp(after) != stamp(current):
                    raise ValueError(f"file changed during version observation: {name}")
                self.cache[name] = {"sha256": sha.hexdigest(), "bytes": count,
                                    "executable": bool(before.st_mode & 0o111)}
            result[name] = self.cache[name]
        return result

    def definition(self, node):
        return digest({"id": node["id"], "title": node["title"],
                       "fields": {k: v for k, v in node["fields"].items() if k not in MUTABLE}})

    def parents(self, node):
        raw = node["fields"].get("needs", "")
        try:
            ids = [int(v.strip()) for v in raw.split(",") if v.strip()]
        except ValueError:
            raise ValueError("invalid dependency identity") from None
        return sorted(set(ids))

    def last_receipt(self, node):
        for note in reversed(node["notes"]):
            if "VERSION INVALIDATED" in note or re.match(r"^\d{4}-.* NOT_RUN ", note):
                return None
            if re.match(r"^\d{4}-\d\d-\d\dT[\d:]+Z exit -?\d+ ", note):
                match = REF.search(note)
                return match[1] if match else None
        return None

    def receipt(self, identity, nid):
        if self.directory.is_symlink():
            raise ValueError("version receipt directory is redirected")
        path = self.directory / (identity + ".json")
        if path.is_symlink() or not path.is_file() or path.stat().st_size > RECEIPT_LIMIT:
            raise ValueError("version receipt is missing, redirected or oversized")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != identity:
            raise ValueError("version receipt hash mismatch")
        data = json.loads(raw)
        if (not isinstance(data, dict) or raw_json(data) != raw or set(data) != {"schema", "node", "run_id", "checked_at", "binding", "outputs", "exit_code"}
                or data["schema"] != "plan.result/v1" or type(data["node"]) is not int or data["node"] != nid
                or type(data["exit_code"]) is not int or data["exit_code"] != 0
                or not isinstance(data["run_id"], str) or not re.fullmatch(r"[0-9a-f]{32}", data["run_id"])
                or not isinstance(data["binding"], dict) or not isinstance(data["outputs"], dict)):
            raise ValueError("invalid version receipt schema")
        return data

    def capture(self, nid):
        node = self.nodes[nid]
        ins, outs, checks = self.paths(node, "inputs"), self.paths(node, "outputs"), self.paths(node, "checks")
        if (set(ins) | set(checks)) & set(outs):
            raise ValueError("inputs/checks and outputs must be disjoint")
        files, parents = self.files(ins), {}
        for parent in self.parents(node):
            if parent not in self.nodes or self.state(parent)["state"] != "current":
                raise ValueError(f"dependency {parent} has no current accepted result")
            parents[str(parent)] = self.state(parent)["receipt"]
        return {"definition": self.definition(node), "policy": self.policy, "inputs": files,
                "checks": self.files(checks), "parents": parents}

    def state(self, nid):
        # Resolve parents first without using the Python stack: plan file order is arbitrary.
        stack, visiting = [(nid, False)], set()
        while stack:
            current, finish = stack.pop()
            if current in self.states:
                continue
            if finish:
                visiting.discard(current)
                self._state(current)
            elif current in visiting:
                self.states[current] = {"state": "held", "reason": "version dependency cycle", "receipt": None}
            else:
                visiting.add(current)
                stack.append((current, True))
                if self.nodes[current]["mark"] == "x":
                    try:
                        parents = self.parents(self.nodes[current])
                    except ValueError:
                        parents = []  # _state records the invalid definition as stale.
                    stack.extend((p, False) for p in reversed(parents) if p in self.nodes and p not in self.states)
        return self.states[nid]

    def _state(self, nid):
        if nid in self.states:
            return self.states[nid]
        node = self.nodes[nid]
        ref = self.last_receipt(node)
        result = {"state": "pending", "reason": "no current result", "receipt": ref}
        try:
            ins, outs, checks = self.paths(node, "inputs"), self.paths(node, "outputs"), self.paths(node, "checks")
            if (set(ins) | set(checks)) & set(outs):
                raise ValueError("inputs/checks and outputs must be disjoint")
            self.files(ins)
            self.files(checks)
        except (ValueError, OSError) as error:
            result.update(state="held", reason=str(error))
        else:
            if node["mark"] == ">":
                result.update(state="running", reason="lease remains owned; gate must recheck claimed inputs")
            elif node["mark"] == "x":
                if not ref or node["fields"].get("version_run"):
                    result.update(state="stale", reason="missing completed version receipt")
                else:
                    try:
                        receipt = self.receipt(ref, nid)
                    except (ValueError, OSError) as error:
                        result.update(state="held", reason=str(error))
                    else:
                        try:
                            current = self.capture(nid)
                            outputs = self.files(outs)
                            if current != receipt["binding"] or outputs != receipt["outputs"]:
                                raise ValueError("declared inputs, outputs, definition or dependency result changed")
                        except (ValueError, OSError) as error:
                            result.update(state="stale", reason=str(error))
                        else:
                            result.update(state="current", reason="current bound gate result")
        self.states[nid] = result
        return result

    def annotate(self):
        for nid, node in self.nodes.items():
            result = self.state(nid)
            node["_versioned"] = True
            node["_version_state"] = result
            if node["mark"] == "x" and result["state"] != "current":
                node["_version_stale"] = result["reason"]
            if result["state"] == "held":
                node["_version_hold"] = result["reason"]

    def publish(self, nid, binding, checked_at, run_id):
        outputs = self.files(self.paths(self.nodes[nid], "outputs"))
        data = {"schema": "plan.result/v1", "node": nid, "run_id": run_id,
                "checked_at": checked_at, "binding": binding, "outputs": outputs, "exit_code": 0}
        raw = raw_json(data)
        if len(raw) > RECEIPT_LIMIT:
            raise ValueError("version receipt exceeds its byte budget")
        if self.directory.is_symlink():
            raise ValueError("version receipt directory is redirected")
        self.directory.mkdir(exist_ok=True)
        # Retention is explicit: refuse more evidence rather than deleting old receipts.
        total, count = len(raw), 1
        with os.scandir(self.directory) as entries:
            for entry in entries:
                info = entry.stat(follow_symlinks=False)
                if not stat.S_ISREG(info.st_mode):
                    raise ValueError("version receipt store contains a non-regular entry")
                total += info.st_size
                count += 1
                if total > STORE_LIMIT or count > STORE_FILES:
                    raise ValueError("version receipt store is full; retain/archive evidence before extending it")
        identity = hashlib.sha256(raw).hexdigest()
        target = self.directory / (identity + ".json")
        fd, name = tempfile.mkstemp(prefix=".pending-", dir=self.directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(name, target)
            except FileExistsError:
                if target.is_symlink() or target.read_bytes() != raw:
                    raise ValueError("version receipt identity collision") from None
        finally:
            os.unlink(name)
        return identity


def claim(path, lines, nodes, nid):
    state = Versions(path, lines, nodes)
    if state.state(nid)["state"] == "held":
        raise ValueError(state.state(nid)["reason"])
    return digest(state.capture(nid))


def nonce():
    return uuid.uuid4().hex
