"""Bounded project-file inspection. No global DB, messaging or completion claims."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

from .mcp.state import project_root

TASK = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z')
FILE_LIMIT = 16384
TOTAL_LIMIT = 65536
ENTRY_LIMIT = 100


def _entries(directory):
    # Stop enumerating, not just rendering, at the cap. No silent truncation.
    entries = []
    for entry in directory.iterdir():
        if len(entries) >= ENTRY_LIMIT:
            raise ValueError('handoff directory entry limit reached')
        entries.append(entry)
    return sorted(entries)


def inspect(root, task=None):
    root = project_root(Path(root).resolve(strict=True))
    if task is not None and (not isinstance(task, str) or not TASK.fullmatch(task)):
        raise ValueError('task must be a bounded identifier, not a path')
    base = root / 'handoffs'
    if base.is_symlink():
        raise ValueError('handoff root is a symlink')
    folders = ([base / task] if task else _entries(base)) if base.is_dir() else []
    packets, total = [], 0
    for directory in folders:
        if directory.is_symlink():
            raise ValueError('handoff task directory is a symlink')
        if not directory.is_dir():
            continue
        for path in _entries(directory):
            if path.suffix != '.md':
                continue
            if path.is_symlink():
                raise ValueError('handoff packet is a symlink')
            if path.is_dir():
                raise ValueError('handoff packet is not regular')
            flags = os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_NOFOLLOW', 0)
            with os.fdopen(os.open(path, flags), 'rb') as handle:
                before = os.fstat(handle.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise ValueError('handoff packet is not regular')
                raw = handle.read(FILE_LIMIT + 1)
                after = os.fstat(handle.fileno())
            if len(raw) > FILE_LIMIT:
                raise ValueError('handoff packet byte limit reached')
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError('handoff changed during inspection; read again')
            total += len(raw)
            if len(packets) >= ENTRY_LIMIT or total > TOTAL_LIMIT:
                raise ValueError('handoff aggregate limit reached')
            packets.append({'path': str(path.relative_to(root)), 'bytes': len(raw),
                            'sha256': hashlib.sha256(raw).hexdigest(), 'text': raw.decode('utf-8')})
    return {'project': str(root), 'status': 'HANDOFFS_FOUND' if packets else 'NO_HANDOFF',
            'advisory': True, 'authority': 'data only; recheck original gates before completion/action',
            'packets': packets}


def command(args):
    try:
        result = inspect(Path.cwd(), args.task)
    except (OSError, ValueError) as exc:
        print('harness handoff: ' + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
