"""Verify and install the runtime and local knowledge pack in order, offline."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

LIMIT = 16 * 1024 * 1024
CHILDREN = ('runtime/install.py', 'knowledge/add-knowledge.py')


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate manifest key')
        result[key] = value
    return result


def read(path, limit=LIMIT):
    if path.is_symlink() or not path.is_file():
        raise ValueError('missing or linked bundle file: ' + path.name)
    with path.open('rb') as handle:
        body = handle.read(limit + 1)
    if len(body) > limit:
        raise ValueError('bundle file exceeds size limit: ' + path.name)
    return body


def validate(root):
    manifest = json.loads(read(root / 'BUNDLE.json', 2 * 1024 * 1024), object_pairs_hook=unique)
    if not isinstance(manifest, dict) or manifest.get('schema') != 'harness.laptop-bundle/v1':
        raise ValueError('unsupported bundle manifest')
    files = manifest.get('files')
    if not isinstance(files, dict) or not 2 <= len(files) <= 64:
        raise ValueError('invalid bundle file list')
    if any(child not in files for child in CHILDREN):
        raise ValueError('missing installer entry point')
    for name, digest in files.items():
        if (not isinstance(name, str) or not name or '\\' in name or ':' in name
                or any(p in ('', '.', '..') for p in name.split('/'))
                or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest)):
            raise ValueError('invalid bundle member')
        path = root
        for part in name.split('/'):
            path = path / part
            if path.is_symlink():
                raise ValueError('linked bundle member: ' + name)
        if hashlib.sha256(read(path)).hexdigest() != digest:
            raise ValueError('bundle content changed: ' + name)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle-dir', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--home', type=Path, help='explicit alternate user home')
    parser.add_argument('--tools', default='codex', help='default codex; optionally codex,copilot-vscode')
    parser.add_argument('--check', action='store_true', help='verify only; install nothing')
    args = parser.parse_args()
    root = args.bundle_dir.resolve()
    validate(root)
    selected_home = (args.home or Path.home()).expanduser().resolve()
    store = (selected_home / '.agent-harness' if args.home else
             Path(os.environ.get('HARNESS_HOME', str(selected_home / '.agent-harness'))).expanduser().resolve())
    env = dict(os.environ, HARNESS_HOME=str(store))
    home = ['--home', str(selected_home)] if args.home else []
    for index, child in enumerate(CHILDREN):
        command = [sys.executable, str(root / child)]
        if args.check:
            command += ['--check']
        else:
            command += home
            if index == 0:
                command += ['--tools', args.tools]
        try:
            result = subprocess.run(command, check=False, env=env)
        except OSError as error:
            state = 'runtime completed; knowledge not started' if index else 'runtime not started; knowledge not started'
            print('Bundle: ' + state + '; launch failed: ' + str(error) +
                  '; no whole-install rollback was performed.', file=sys.stderr)
            return 2
        if result.returncode:
            state = 'runtime completed; knowledge failed' if index else 'runtime failed; knowledge not started'
            print('Bundle: ' + state + '; no whole-install rollback was performed.', file=sys.stderr)
            return result.returncode
    print('BUNDLE VERIFIED; no installation performed.' if args.check else
          'Runtime and knowledge installed. Open a fresh agent session. Live laptop behavior remains to be checked.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('Bundle refused: ' + str(error), file=sys.stderr)
        raise SystemExit(2)
