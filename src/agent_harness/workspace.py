"""One optional project-local task workspace; inspect metadata, never prune evidence."""
from __future__ import annotations

import json
from pathlib import Path
import re
import stat
import sys

TASK = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z')
ENTRY_LIMIT = 1000
DEPTH_LIMIT = 16
SCRATCH_BYTES = 32 * 1024 * 1024


def _directory(path):
    if path.is_symlink():
        raise ValueError('workspace symlink refused: ' + path.name)
    if path.exists() and not path.is_dir():
        raise ValueError('workspace component must be a directory: ' + path.name)


def inspect(root, task, initialize=False):
    if not isinstance(task, str) or not TASK.fullmatch(task):
        raise ValueError('task must be a bounded identifier, not a path')
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('project must be a directory')
    base = root / '.harness-work'
    work = base / task
    for path in (base, work, work / 'scratch', work / 'outputs'):
        _directory(path)
    index = work / 'README.md'
    ignore = base / '.gitignore'
    for path in (index, ignore):
        if path.is_symlink():
            raise ValueError('workspace symlink refused: ' + path.name)
        if path.exists() and not path.is_file():
            raise ValueError('workspace index/ignore must be regular')
    # Validate all existing descendants before initialization writes anything.
    rows = _inventory(work) if work.is_dir() else []
    ignore_state = 'NOT_CHECKED'
    if initialize:
        for path in (base, work, work / 'scratch', work / 'outputs'):
            path.mkdir(mode=0o700, exist_ok=True)
        try:
            with ignore.open('x', encoding='utf-8') as handle:
                handle.write('*\n')
            ignore_state = 'CREATED'
        except FileExistsError:
            with ignore.open('rb') as handle:
                ignore_state = 'TEMPLATE_PRESENT' if handle.read(3) == b'*\n' else 'CUSTOM_UNVERIFIED'
        try:
            with index.open('x', encoding='utf-8') as handle:
                handle.write(f'# Task workspace: {task}\n\n'
                             'outputs/ — deliverables worth keeping; link the final result here.\n'
                             'scratch/ — intermediate logs and experiments, reused for this task.\n\n'
                             'Keep the current outcome, evidence links and next action in this index.\n'
                             'Original graph gates and handoff records remain authoritative.\n'
                             'Do not duplicate sources, transcripts or secrets.\n'
                             'No automatic deletion or completion inference.\n')
        except FileExistsError:
            pass  # Exclusive creation: preserve an existing writer's index.
        rows = _inventory(work)
    scratch = sum(row['bytes'] for row in rows if row['kind'] == 'scratch')
    visible, output_bytes = [], 0
    for row in rows:
        cost = len(json.dumps(row, ensure_ascii=False).encode('utf-8'))
        if len(visible) >= 40 or output_bytes + cost > 8192:
            break
        visible.append(row)
        output_bytes += cost
    complete = index.is_file() and all((work / name).is_dir() for name in ('scratch', 'outputs'))
    warnings = ['SCRATCH_BUDGET_EXCEEDED'] if scratch > SCRATCH_BYTES else []
    if ignore_state == 'CUSTOM_UNVERIFIED':
        warnings.append('EXISTING_IGNORE_NOT_VERIFIED')
    if len(visible) < len(rows):
        warnings.append('INVENTORY_SUMMARIZED')
    return {'schema': 'harness.workspace/v1', 'task': task,
            'status': ('AVAILABLE' if complete else 'INCOMPLETE') if work.is_dir() else 'NOT_CREATED',
            'completion': 'NOT_EVALUATED', 'workspace': f'.harness-work/{task}',
            'index': f'.harness-work/{task}/README.md',
            'files': visible, 'file_count': len(rows), 'omitted_files': len(rows) - len(visible),
            'total_bytes': sum(row['bytes'] for row in rows),
            'scratch_bytes': scratch,
            'ignore_rule': ignore_state,
            'warnings': warnings,
            'cleanup': 'NO_DELETION; review owned scratch separately',
            'authority': 'metadata only; use original gates and source evidence'}


def _inventory(work):
    rows, seen = [], 0

    def walk(directory, depth):
        nonlocal seen
        if depth > DEPTH_LIMIT:
            raise ValueError('workspace depth limit reached')
        for path in directory.iterdir():
            seen += 1
            if seen > ENTRY_LIMIT:
                raise ValueError('workspace entry limit reached')
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise ValueError('workspace symlink refused: ' + path.name)
            if stat.S_ISDIR(info.st_mode):
                walk(path, depth + 1)
            elif stat.S_ISREG(info.st_mode):
                rel = path.relative_to(work)
                kind = {'scratch': 'scratch', 'outputs': 'output'}.get(rel.parts[0], 'index')
                rows.append({'path': rel.as_posix(), 'bytes': info.st_size, 'kind': kind})
            else:
                raise ValueError('workspace entry is not regular: ' + path.name)
    walk(work, 0)
    return sorted(rows, key=lambda row: row['path'])


def command(args):
    try:
        result = inspect(Path.cwd(), args.task, args.init)
    except (OSError, ValueError) as exc:
        print('harness workspace: ' + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
