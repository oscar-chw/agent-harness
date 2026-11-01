"""Opt-in project source snapshots and exact citations; no native-store migration.

The caller supplies an already authorized project root and explicit source path. This is
not an authorization service or a sandbox against other processes running as the same user.
The index and model-facing retrieval layer are deliberately outside this filesystem pilot.
"""
import hashlib
import json
import os
import re
import tempfile
import uuid
from pathlib import Path

SOURCE_LIMIT = 1_048_576
_RECORD_LIMIT = 8 * SOURCE_LIMIT + 8192
_HEX = re.compile(r"[0-9a-f]{64}\Z")


def _bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _lines(text):
    # Match source editors' LF line numbers without splitting vertical tabs or Unicode
    # separators. Keep CR in CRLF verbatim so a citation can reproduce the source bytes.
    parts = text.split("\n")
    return [part + "\n" for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def _read(path, limit):
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"source budget exceeded: {path.name}")
    return data


def _source_path(root, relative):
    if not isinstance(relative, str) or not relative:
        raise ValueError("source path must be a nonempty relative string")
    raw = Path(relative)
    if not raw.parts or raw.is_absolute() or ".." in raw.parts or raw.parts[0] == ".harness":
        raise ValueError("source path crosses the project boundary")
    path = root / raw
    try:
        inside = path.resolve().relative_to(root)
    except ValueError:
        raise ValueError("source symlink crosses the project boundary") from None
    if not inside.parts or inside.parts[0] == ".harness":
        raise ValueError("source path points at internal project storage")
    return path


def _span(text, citation, start_line, end_line, max_bytes, historical=False):
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError("budget must be a positive integer")
    lines = _lines(text)
    end_line = len(lines) if end_line is None else end_line
    if (type(start_line) is not int or type(end_line) is not int
            or not 1 <= start_line <= end_line <= len(lines)):
        raise ValueError("invalid source line range")
    result = {"kind": "source-data", "text": "".join(lines[start_line - 1:end_line]),
              "historical": historical,
              "citation": {**citation, "start_line": start_line, "end_line": end_line}}
    if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > max_bytes:
        raise ValueError("resolved source and citation exceed budget")
    return result


def read_shared_source(root, *, vault_id, source, sha256, start_line=1, end_line=None, max_bytes=65536):
    """Read one approved, pinned shared source without creating any consumer-side store.

    The caller authorizes root/source and supplies the catalogue's digest. vault_id is a provenance
    label, not an authentication credential. The source remains in its one canonical shared root.
    """
    if not isinstance(vault_id, str) or not vault_id.strip():
        raise ValueError("shared vault identity is required")
    text = _shared_text(root, source, sha256)
    citation = {"vault_id": vault_id, "source": Path(source).as_posix(), "sha256": sha256}
    return _span(text, citation, start_line, end_line, max_bytes)


def _shared_text(root, source, sha256):
    if not isinstance(sha256, str) or not _HEX.fullmatch(sha256):
        raise ValueError("expected source digest must be a lowercase SHA-256")
    root = Path(root).resolve(strict=True)
    raw = _read(_source_path(root, source), SOURCE_LIMIT)
    if _sha(raw) != sha256:
        raise ValueError("source digest mismatch: source is stale relative to the approved pin")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("source must be UTF-8 text") from None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate catalogue field")
        result[key] = value
    return result


def read_shared_document(root, *, vault_id, manifest, manifest_sha256, document_id,
                         start_line=1, end_line=None, max_bytes=65536):
    """Consume a pinned QRV public catalogue without importing its executable code.

    Rights are preserved publisher declarations, not a new legal/publishing authorization.
    This first consumer accepts public paper/method notes; private editions need a separate
    explicit access contract. Unknown schemas and ambiguous identities fail rather than guess.
    """
    if not isinstance(vault_id, str) or not vault_id.strip():
        raise ValueError("shared vault identity is required")
    if not isinstance(document_id, str) or not document_id:
        raise ValueError("document identity is required")
    try:
        text = _shared_text(root, manifest, manifest_sha256)
    except ValueError as error:
        raise ValueError(f"manifest: {error}") from error
    catalogue = json.loads(text, object_pairs_hook=_unique_object)
    if (not isinstance(catalogue, dict) or catalogue.get("schema") != "quant-shared-notes/v1"
            or not isinstance(catalogue.get("revision"), str) or not catalogue["revision"]
            or not isinstance(catalogue.get("documents"), list)):
        raise ValueError("unsupported or invalid shared catalogue schema")
    documents = {}
    for item in catalogue["documents"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            raise ValueError("invalid catalogue document identity")
        if item["id"] in documents:
            raise ValueError("duplicate catalogue document identity")
        documents[item["id"]] = item
    if document_id not in documents:
        raise ValueError("document not listed in the pinned catalogue")
    doc = documents[document_id]
    if (doc.get("document_type") not in ("method_note", "paper_note")
            or any(not isinstance(doc.get(k), str) or not doc[k] for k in ("title", "path", "sha256"))):
        raise ValueError("invalid document metadata")
    rights, refs = doc.get("rights"), doc.get("source_refs")
    if (not isinstance(rights, dict) or rights.get("redistribution") != "public"
            or any(not isinstance(rights.get(k), str) or not rights[k] for k in ("license", "basis"))):
        raise ValueError("document has unknown or non-public rights")
    if (not isinstance(refs, list) or not refs
            or any(not isinstance(ref, dict) or any(not isinstance(ref.get(k), str) or not ref[k]
                   for k in ("uri", "kind", "revision")) for ref in refs)):
        raise ValueError("document provenance is incomplete")
    content = _shared_text(root, doc["path"], doc["sha256"])
    headers = [line.rstrip("\r\n") for line in _lines(content)[:2]]
    if headers != ["id: " + document_id, "title: " + doc["title"]]:
        raise ValueError("document header disagrees with catalogue identity/title")
    part = _span(content, {"vault_id": vault_id, "source": doc["path"], "sha256": doc["sha256"]},
                 start_line, end_line, max_bytes)
    result = {"schema": "harness.shared-document/v1", "kind": "source-data", "vault_id": vault_id,
              "document_id": document_id, "document_type": doc["document_type"], "title": doc["title"],
              "content": part["text"], "source_sha256": doc["sha256"],
              "manifest_sha256": manifest_sha256, "manifest_revision": catalogue["revision"],
              "source_refs": refs, "rights": rights, "citation": part["citation"]}
    if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > max_bytes:
        raise ValueError("document content and complete provenance exceed budget")
    return result


def _area(root):
    """Reject redirected storage, including its manifest, before reading or writing."""
    area = root / ".harness"
    for path in (area, area / "project.json", area / "sources"):
        if path.is_symlink():
            raise ValueError("project storage boundary contains a symlink")
    return area


def _project(root):
    data = json.loads(_read(_area(root) / "project.json", 16384))
    if not isinstance(data, dict) or type(data.get("schema")) is not int or data["schema"] != 1:
        raise ValueError("invalid project manifest schema")
    pid = data.get("project_id")
    if not isinstance(pid, str) or str(uuid.UUID(pid)) != pid:
        raise ValueError("invalid project identity")
    return pid


def _publish(path, data):
    """Publish complete bytes without replacing a competing or corrupted object.

    A hard link makes the completed temporary file visible atomically. A filesystem without
    that operation fails loudly; there is no unsafe in-place-write fallback. This is atomic
    visibility, not a claim of durability against power loss on every filesystem.
    """
    if path.is_symlink():
        raise ValueError("source storage boundary contains a symlink")
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".pending-", delete=False) as handle:
            temp = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp, path)
        except FileExistsError:
            if path.is_symlink() or _read(path, len(data)) != data:
                raise ValueError("source publication conflict or integrity failure") from None
    finally:
        if temp is not None:
            temp.unlink()


def initialize(root):
    """Explicitly create a stable project ID; preserve an existing valid identity."""
    root = Path(root).resolve(strict=True)
    area = _area(root)
    area.mkdir(exist_ok=True)
    (area / "sources").mkdir(exist_ok=True)
    path = area / "project.json"
    if not path.exists():
        data = _bytes({"schema": 1, "project_id": str(uuid.uuid4())})
        try:
            _publish(path, data)
        except ValueError:
            # Concurrent initialization may have published a different valid UUID. Reading
            # that complete manifest is safe; malformed or redirected state still fails.
            if not path.exists():
                raise
            return _project(root)
    return _project(root)


class SourceVault:
    def __init__(self, root, project_id):
        self.root = Path(root).resolve(strict=True)
        self.project_id = project_id
        self._check_project()

    def _check_project(self):
        if _project(self.root) != self.project_id:
            raise ValueError("project identity does not match authorized root")

    def _source_path(self, relative):
        return _source_path(self.root, relative)

    def capture(self, relative):
        """Snapshot one UTF-8 source without editing it; return an integrity-bound receipt."""
        self._check_project()
        path = self._source_path(relative)
        raw = _read(path, SOURCE_LIMIT)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("source must be UTF-8 text") from None
        record = {"schema": 1, "project_id": self.project_id,
                  "source": Path(relative).as_posix(), "sha256": _sha(raw), "text": text}
        data = _bytes(record)
        sid = _sha(data)
        _publish(_area(self.root) / "sources" / (sid + ".json"), data)
        return {"project_id": self.project_id, "source_id": sid, "source": record["source"],
                "sha256": record["sha256"], "line_count": len(_lines(text))}

    def resolve(self, ref, *, start_line=1, end_line=None, historical=False, max_bytes=65536):
        """Resolve an exact source span; stale originals require explicit historical mode.

        The entire returned JSON, including citation metadata, must fit the byte budget.
        Missing/corrupted sources are errors, never an empty search result or silent repair.
        """
        self._check_project()
        if not isinstance(ref, dict) or ref.get("project_id") != self.project_id:
            raise ValueError("source receipt belongs to another project")
        if (set(ref) != {"project_id", "source_id", "source", "sha256", "line_count"}
                or type(ref.get("line_count")) is not int):
            raise ValueError("invalid source receipt metadata")
        sid = ref.get("source_id")
        if not isinstance(sid, str) or not _HEX.fullmatch(sid):
            raise ValueError("invalid source identity")
        if type(historical) is not bool or type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("historical must be boolean and budget a positive integer")
        path = _area(self.root) / "sources" / (sid + ".json")
        if path.is_symlink():
            raise ValueError("source snapshot boundary contains a symlink")
        raw = _read(path, _RECORD_LIMIT)
        if _sha(raw) != sid:
            raise ValueError("source snapshot integrity failure")
        record = json.loads(raw)
        fields = {"schema", "project_id", "source", "sha256", "text"}
        if (not isinstance(record, dict) or set(record) != fields
                or record["schema"] != 1 or record["project_id"] != self.project_id
                or not isinstance(record["text"], str)
                or _sha(record["text"].encode("utf-8")) != record["sha256"]
                or ref.get("source") != record["source"] or ref.get("sha256") != record["sha256"]):
            raise ValueError("source receipt integrity failure")
        current_path = self._source_path(record["source"])
        if not historical and _sha(_read(current_path, SOURCE_LIMIT)) != record["sha256"]:
            raise ValueError("stale source: original changed; request historical evidence explicitly")
        lines = _lines(record["text"])
        if ref.get("line_count") != len(lines):
            raise ValueError("source receipt line count integrity failure")
        return _span(record["text"], ref, start_line, end_line, max_bytes, historical)
