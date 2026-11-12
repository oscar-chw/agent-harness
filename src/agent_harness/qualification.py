"""Check requirement coverage and current artifact bindings, never authenticate claims.

A structurally valid receipt can still be fabricated by its author. This reader
does not execute checks, infer source support or confer release authority.
"""
from __future__ import annotations

import hashlib
from contextlib import ExitStack
import json
import os
from pathlib import Path
import re
import stat

FILE_LIMIT = 1024 * 1024
TOTAL_LIMIT = 16 * FILE_LIMIT
MANIFEST_LIMIT = 2 * FILE_LIMIT
IMPLEMENTATION = {'present', 'partial', 'missing', 'unknown'}
QUALIFICATION = {'qualified', 'partial', 'not_run', 'unknown'}
AXES = ('implementation', 'local_qualification', 'native_qualification')
SHA = re.compile(r'[0-9a-f]{64}\Z')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, label, limit=8192):
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= limit,
            'invalid ' + label)
    return value


def identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


class Bindings:
    def __init__(self, root):
        try:
            self.root = Path(root).resolve(strict=True)
        except (OSError, ValueError, RuntimeError) as error:
            raise ValueError('qualification root unavailable') from error
        require(self.root.is_dir(), 'qualification root must be a directory')
        self.cache = {}
        self.total = 0

    def path(self, name):
        text(name, 'binding path', 4096)
        relative = Path(name)
        require(not relative.is_absolute() and relative.parts and '..' not in relative.parts,
                'binding path must remain project-relative')
        require(not any(p in {'.ssh', 'Keychains', 'auth.json'} or p.startswith('.env')
                        for p in relative.parts), 'credential path is not qualification evidence')
        path = self.root
        for part in relative.parts:
            path = path / part
            require(not path.is_symlink(), 'symlink binding is not allowed')
        return path

    def read_current(self, name):
        """Read this selected project revision; callers may bind its exact bytes.

        Open every relative component against an already opened directory so
        replacing a checked path with a symlink cannot redirect the actual read.
        This does not authenticate the source author or establish historical truth.
        """
        self.path(name)
        if name not in self.cache:
            try:
                require(hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY'),
                        'race-safe project reads unavailable on this platform')
                with ExitStack() as opened:
                    # Known evidence needs traversal, not permission to list a directory.
                    search = getattr(os, 'O_SEARCH', getattr(os, 'O_PATH', os.O_RDONLY))
                    directory_flags = search | os.O_DIRECTORY | os.O_NOFOLLOW
                    parent = os.open(self.root, directory_flags)
                    opened.callback(os.close, parent)
                    parts = Path(name).parts
                    for part in parts[:-1]:
                        parent = os.open(part, directory_flags, dir_fd=parent)
                        opened.callback(os.close, parent)
                    fd = os.open(parts[-1], os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW,
                                 dir_fd=parent)
                    opened.callback(os.close, fd)
                    before = os.fstat(fd)
                    require(stat.S_ISREG(before.st_mode), 'binding is not a regular file')
                    require(before.st_size <= FILE_LIMIT, 'binding exceeds per-file limit')
                    with os.fdopen(fd, 'rb', closefd=False) as handle:
                        blob = handle.read(FILE_LIMIT + 1)
                    after = os.fstat(fd)
                require(len(blob) <= FILE_LIMIT, 'binding exceeds per-file limit')
                require(identity(before) == identity(after), 'binding changed during read')
                require(identity(self.path(name).stat()) == identity(after), 'binding replaced during read')
            except OSError as error:
                raise ValueError('qualification binding unavailable') from error
            self.total += len(blob)
            require(self.total <= TOTAL_LIMIT, 'qualification evidence exceeds aggregate limit')
            self.cache[name] = (blob, identity(after))
        return self.cache[name][0]

    def read(self, reference):
        require(isinstance(reference, dict), 'binding must be an object')
        expected = reference.get('sha256')
        require(isinstance(expected, str) and SHA.fullmatch(expected) is not None,
                'invalid binding hash')
        blob = self.read_current(reference.get('path'))
        require(hashlib.sha256(blob).hexdigest() == expected, 'qualification binding hash mismatch')
        return blob

    def finish(self):
        for name, (_, observed) in self.cache.items():
            path = self.path(name)
            try:
                require(identity(path.stat()) == observed, 'qualification binding changed after read')
            except OSError as error:
                raise ValueError('qualification binding disappeared') from error


def _source(bindings, reference):
    try:
        return bindings.read(reference).decode('utf-8')
    except UnicodeError as error:
        raise ValueError('requirement source must be UTF-8') from error


def _sections(source):
    headings = list(re.finditer(r'^(\d{1,2})\. [^\n]+$', source, re.M))
    require([int(m[1]) for m in headings] == list(range(1, 12)),
            'source must retain numbered sections 1 through 11')
    return {i + 1: source[m.end():headings[i + 1].start() if i + 1 < len(headings) else len(source)]
            for i, m in enumerate(headings)}


def _evidence(bindings, evidence, axis, status, expected_subjects):
    require(isinstance(evidence, list) and len(evidence) <= 64, 'invalid evidence list')
    if status in {'present', 'partial', 'qualified'}:
        require(bool(evidence), 'claimed capability needs evidence')
    receipt_found = False
    for reference in evidence:
        require(isinstance(reference, dict), 'evidence entry must be an object')
        text(reference.get('why'), 'evidence rationale')
        bindings.read(reference)
        receipt = reference.get('receipt')
        if receipt is not None:
            require(isinstance(receipt, dict), 'invalid execution receipt')
            level = 'native' if axis == 'native_qualification' else 'local'
            require(receipt.get('level') == level, 'receipt level does not match qualification axis')
            require(type(receipt.get('exit_code')) is int and receipt['exit_code'] == 0,
                    'execution receipt did not pass')
            text(receipt.get('command'), 'receipt command')
            subjects = receipt.get('subjects')
            require(isinstance(subjects, list) and 1 <= len(subjects) <= 64,
                    'receipt must bind its current subjects')
            for subject in subjects:
                bindings.read(subject)
            require(expected_subjects <= {(s['path'], s['sha256']) for s in subjects},
                    'receipt does not bind the implementation subjects')
            receipt_found = True
    if status == 'qualified':
        require(receipt_found, 'qualified claim requires an execution receipt')


def _clause(bindings, clause, prefix, source, seen):
    require(isinstance(clause, dict), 'clause must be an object')
    key = text(clause.get('id'), 'clause ID', 128)
    require(key not in seen, 'duplicate clause ID')
    require(key.startswith(prefix) and len(key) > len(prefix), 'clause belongs to another section')
    seen.add(key)
    text(clause.get('requirement'), 'requirement')
    quote = text(clause.get('source_quote'), 'source quote')
    require(quote in source, 'source quote is not in its declared section')
    implementation = clause.get('implementation')
    require(isinstance(implementation, dict) and isinstance(implementation.get('evidence'), list),
            'missing implementation evidence list')
    expected_subjects = set()
    for reference in implementation['evidence']:
        require(isinstance(reference, dict), 'implementation evidence must be an object')
        bindings.read(reference)
        expected_subjects.add((reference['path'], reference['sha256']))
    complete = True
    for axis in AXES:
        value = clause.get(axis)
        require(isinstance(value, dict), 'missing qualification axis: ' + axis)
        status = value.get('status')
        allowed = IMPLEMENTATION if axis == 'implementation' else QUALIFICATION
        require(isinstance(status, str) and status in allowed, 'invalid qualification status')
        _evidence(bindings, value.get('evidence'), axis, status, expected_subjects)
        complete = complete and status == ('present' if axis == 'implementation' else 'qualified')
    require(isinstance(clause.get('gap'), str) and isinstance(clause.get('next_check'), str),
            'clause must retain gap and next check')
    if not complete:
        text(clause['gap'], 'unmet gap')
        text(clause['next_check'], 'next check')
    return complete


def validate(manifest, root):
    require(isinstance(manifest, dict), 'qualification manifest must be an object')
    try:
        size = len(json.dumps(manifest, allow_nan=False).encode('utf-8'))
    except (ValueError, TypeError, RecursionError) as error:
        raise ValueError('qualification manifest must be bounded JSON') from error
    require(size <= MANIFEST_LIMIT, 'qualification manifest exceeds size limit')
    require(manifest.get('schema') == 'harness.requirements/v1', 'unsupported qualification schema')
    bindings = Bindings(root)
    sources = _sections(_source(bindings, manifest.get('source')))
    sections = manifest.get('sections')
    require(isinstance(sections, list) and len(sections) == 11,
            'all eleven owner sections must remain represented')
    seen_sections, seen_clauses, incomplete = set(), set(), []
    for section in sections:
        require(isinstance(section, dict), 'section must be an object')
        number = section.get('source_section')
        require(type(number) is int and number in sources, 'invalid source section')
        key = f'H05-{number:02}'
        require(section.get('id') == key and key not in seen_sections, 'duplicate or invalid section ID')
        seen_sections.add(key)
        text(section.get('title'), 'section title')
        clauses = section.get('clauses')
        require(isinstance(clauses, list) and bool(clauses), 'empty requirement section')
        for clause in clauses:
            require(len(seen_clauses) < 2048, 'too many requirement clauses')
            try:
                complete = _clause(bindings, clause, key + '.', sources[number], seen_clauses)
            except ValueError as error:
                label = clause.get('id', key) if isinstance(clause, dict) else key
                raise ValueError(f'{label}: {error}') from error
            if not complete:
                incomplete.append(clause['id'])
    extensions = manifest.get('extensions', [])
    require(isinstance(extensions, list), 'extensions must be a list')
    for clause in extensions:
        require(isinstance(clause, dict), 'extension must be an object')
        require(len(seen_clauses) < 2048, 'too many requirement clauses')
        source = _source(bindings, clause.get('source'))
        if not _clause(bindings, clause, 'V2-', source, seen_clauses):
            incomplete.append(clause['id'])
    bindings.finish()
    return {'status': 'CONTRACT_VALID', 'requirements': len(seen_clauses),
            'complete': not incomplete, 'incomplete': incomplete,
            'scope': 'coverage_and_current_bindings_only'}


def load(path):
    """Reject duplicate JSON keys instead of accepting whichever status came last."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    try:
        with Path(path).open('rb') as handle:
            raw = handle.read(MANIFEST_LIMIT + 1)
        require(len(raw) <= MANIFEST_LIMIT, 'qualification manifest exceeds size limit')
        return json.loads(raw, object_pairs_hook=unique)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('qualification manifest cannot be read') from error
