"""Scoped runtime wiring for the existing tombstone admission guard.

No ledger means inactive. Configuration selects an owner-managed corpus and its
external escrow, never a model-supplied project override. This checks supported
lexical backflow, not deletion from model weights or already-loaded context.
"""
import hashlib
import json
import os
from pathlib import Path

from .memory_guard import Guard
from .presets import _read
from .vault_sources import _source_path, _unique_object

SKIP = {"archive", "backup", "lib", "node_modules", "skill-packs", "tombstones"}


class Admission:
    def __init__(self, root, configuration):
        self.root = Path(root).resolve()
        self.configuration = Path(configuration)
        self._key = None
        self._guard = None
        self.state = "inactive"

    def _settings(self):
        if self.configuration.exists() or self.configuration.is_symlink():
            raw = _read(self.configuration, 4096)
            value = json.loads(raw, object_pairs_hook=_unique_object)
            if (not isinstance(value, dict) or set(value) != {"schema", "ledger_root", "escrow_dir"}
                    or type(value["schema"]) is not int or value["schema"] != 1
                    or any(not isinstance(value[k], str) or not Path(value[k]).is_absolute()
                           for k in ("ledger_root", "escrow_dir"))):
                raise ValueError("invalid scoped memory admission configuration")
            corpus, escrow = (Path(value[k]).resolve() for k in ("ledger_root", "escrow_dir"))
        else:
            raw = b"default-own-store"
            corpus = self.root
            escrow = self.root.parent / (self.root.name + "-escrow")
        if escrow == corpus or corpus in escrow.parents:
            raise ValueError("memory admission escrow must be outside its corpus")
        return corpus, escrow, hashlib.sha256(raw).hexdigest()

    def _references(self, corpus):
        paths, visited = [], 0
        for directory, folders, files in os.walk(corpus):
            folders[:] = sorted(n for n in folders if n not in SKIP and not n.startswith("."))
            visited += len(folders) + len(files)
            if visited > 4096:
                raise ValueError("memory admission reference discovery exceeds its bound")
            for name in sorted(files):
                if name.startswith(".") or not name.endswith(".md"):
                    continue
                path = _source_path(corpus, (Path(directory) / name).relative_to(corpus).as_posix())
                info = path.stat()
                paths.append((path, info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns))
                if len(paths) > 512:
                    raise ValueError("memory admission reference count exceeds its bound")
        return tuple(paths)

    def check(self, text, *, path):
        corpus, escrow, configuration = self._settings()
        ledger = corpus / "tombstones/ledger.jsonl"
        references = ()
        if ledger.exists() or ledger.is_symlink():
            _read(ledger, 4 * 1024 * 1024)
            references = self._references(corpus)
        key = (str(corpus), str(escrow), configuration, references)
        if key != self._key:
            bodies, total = [], 0
            for reference, *_ in references:
                raw = _read(reference, 65536)
                total += len(raw)
                if total > 8 * 1024 * 1024:
                    raise ValueError("memory admission reference bytes exceed their bound")
                bodies.append(raw.decode("utf-8", "replace"))
            self._guard = Guard(corpus, escrow_dir=escrow, reference_texts=bodies)
            self._key = key
        result = self._guard.check(text, path=path)
        self.state = self._guard.state
        return result
