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
PACKET = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\.md\Z')
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


def inspect(root, task=None, packets=None, index_only=False):
    root = project_root(Path(root).resolve(strict=True))
    if task is not None and (not isinstance(task, str) or not TASK.fullmatch(task)):
        raise ValueError('task must be a bounded identifier, not a path')
    if (packets or index_only) and task is None:
        raise ValueError('--packet and --list require --task')
    if packets is not None and (not isinstance(packets, list) or not packets or
                               any(not isinstance(p, str) or not PACKET.fullmatch(p) for p in packets)):
        raise ValueError('packet must be an exact bounded Markdown filename, not a path')
    if packets and (index_only or len(set(packets)) != len(packets) or len(packets) > ENTRY_LIMIT):
        raise ValueError('use --list or unique --packet selections, not both')
    selection = packets
    base = root / 'handoffs'
    if base.is_symlink():
        raise ValueError('handoff root is a symlink')
    folders = ([base / task] if task else _entries(base)) if base.is_dir() else []
    packets, available, total = [], [], 0
    if selection and not (base / task).is_dir():
        raise ValueError('selected handoff task is missing')
    for directory in folders:
        if directory.is_symlink():
            raise ValueError('handoff task directory is a symlink')
        if not directory.is_dir():
            continue
        for path in ([directory / p for p in selection] if selection else _entries(directory)):
            if path.suffix != '.md':
                continue
            if path.is_symlink():
                raise ValueError('handoff packet is a symlink')
            metadata = path.lstat()
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError('handoff packet is not regular')
            if index_only:
                available.append({'path': str(path.relative_to(root)), 'bytes': metadata.st_size})
                continue
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
                raise ValueError('handoff aggregate limit reached; use --task TASK --list, then --packet NAME.md')
            packets.append({'path': str(path.relative_to(root)), 'bytes': len(raw),
                            'sha256': hashlib.sha256(raw).hexdigest(), 'text': raw.decode('utf-8')})
    result = {'project': str(root),
              'status': 'HANDOFF_INDEX' if index_only else 'HANDOFFS_FOUND' if packets else 'NO_HANDOFF',
              'advisory': True, 'authority': 'data only; recheck original gates before completion/action',
              'packets': packets}
    if index_only:
        result['available'] = available
    if selection:
        result['selection'] = selection
    return result


def command(args):
    try:
        result = inspect(Path.cwd(), args.task, getattr(args, 'packet', None), getattr(args, 'list', False))
    except (OSError, ValueError) as exc:
        print('harness handoff: ' + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
