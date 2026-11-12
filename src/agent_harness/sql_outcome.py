"""Bounded local SQL consequence checks, not a judge of native reasoning or safety.

Fixtures/expected rows are explicit caller inputs, not authenticated independent
oracles. Execute the submitted query in fresh in-memory databases; never replace
it with a preselected correct query. No model, connector, disk database or writes.
"""
import hashlib
import json
import math
import re
import sqlite3

IDENTIFIER = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,63}\Z')
FUNCTIONS = {'sum', 'total', 'count', 'min', 'max', 'coalesce', 'ifnull', 'nullif',
             'abs', 'round', 'length', 'lower', 'upper'}
MAX_ROWS = 256


def _encoded(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                          separators=(',', ':')).encode('utf-8')
    except (TypeError, ValueError, UnicodeError) as error:
        raise ValueError('SQL fixture/result is not finite JSON data') from error


def _scalar(value):
    return (value is None or type(value) is int or
            (type(value) is str and len(value.encode('utf-8')) <= 4096) or
            (type(value) is float and math.isfinite(value)))


def _rows(value, columns=None):
    if not isinstance(value, list) or len(value) > MAX_ROWS:
        raise ValueError('SQL fixture/result row limit exceeded')
    width = columns
    for row in value:
        if not isinstance(row, list) or not row or len(row) > 32 or any(not _scalar(v) for v in row):
            raise ValueError('SQL fixture/result has invalid cells')
        if width is None:
            width = len(row)
        if len(row) != width:
            raise ValueError('SQL fixture/result has inconsistent row widths')


def _validate(cases):
    if not isinstance(cases, list) or not 1 <= len(cases) <= 16:
        raise ValueError('SQL outcome needs one to sixteen cases')
    raw = _encoded(cases)
    if len(raw) > 131072:
        raise ValueError('SQL fixture byte limit exceeded')
    ids = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {'id', 'tables', 'expected', 'ordered'}:
            raise ValueError('SQL case fields are incomplete or unknown')
        identity = case['id']
        if not isinstance(identity, str) or not IDENTIFIER.fullmatch(identity) or identity in ids:
            raise ValueError('SQL case identities must be unique bounded identifiers')
        ids.add(identity)
        if type(case['ordered']) is not bool:
            raise ValueError('SQL case ordering must be explicit')
        tables = case['tables']
        if not isinstance(tables, dict) or not 1 <= len(tables) <= 16:
            raise ValueError('SQL case needs one to sixteen tables')
        names = set()
        for name, table in tables.items():
            if (not isinstance(name, str) or not IDENTIFIER.fullmatch(name) or
                    name.lower().startswith('sqlite_') or name.lower() in names):
                raise ValueError('invalid or duplicate SQL fixture table')
            names.add(name.lower())
            if not isinstance(table, dict) or set(table) != {'columns', 'rows'}:
                raise ValueError('SQL table fields are incomplete or unknown')
            cols = table['columns']
            if (not isinstance(cols, list) or not 1 <= len(cols) <= 32 or
                    any(not isinstance(c, str) or not IDENTIFIER.fullmatch(c) for c in cols) or
                    len({c.lower() for c in cols}) != len(cols)):
                raise ValueError('invalid or duplicate SQL fixture columns')
            _rows(table['rows'], len(cols))
        _rows(case['expected'])
    return raw


def _execute(query, tables):
    db = sqlite3.connect(':memory:')
    try:
        db.execute('PRAGMA temp_store=MEMORY')
        for name, table in tables.items():
            columns = ','.join('"' + col + '"' for col in table['columns'])
            db.execute('CREATE TABLE "' + name + '" (' + columns + ')')
            placeholders = ','.join('?' for _ in table['columns'])
            db.executemany('INSERT INTO "' + name + '" VALUES (' + placeholders + ')', table['rows'])
        allowed_tables = {name.lower() for name in tables}

        def authorize(action, first, second, database, trigger):
            if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE):
                return sqlite3.SQLITE_OK
            # SQLite's count/unused-column optimization reports a table read with
            # empty column and no database name. The table must still be a fixture.
            if (action == sqlite3.SQLITE_READ and isinstance(first, str) and
                    first.lower() in allowed_tables and
                    (database == 'main' or (database is None and second == ''))):
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_FUNCTION and isinstance(second, str) and second.lower() in FUNCTIONS:
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY

        ticks = 0

        def progress():
            nonlocal ticks
            ticks += 1
            return int(ticks >= 1000)

        db.set_authorizer(authorize)
        db.set_progress_handler(progress, 50)
        cursor = db.execute(query)
        rows = [list(row) for row in cursor.fetchmany(MAX_ROWS + 1)]
        _rows(rows)
        if len(_encoded(rows)) > 65536:
            raise ValueError('SQL result byte limit exceeded')
        return rows
    finally:
        db.close()


def evaluate_query(query, cases):
    """A PASS is only equality with all supplied expected rows under these bounds."""
    if not isinstance(query, str) or not query.strip() or len(query.encode('utf-8')) > 8192:
        raise ValueError('SQL query must be nonempty UTF-8 text within 8192 bytes')
    fixtures = _validate(cases)
    results = []
    for case in cases:
        try:
            observed = _execute(query, case['tables'])
        except (sqlite3.Error, ValueError, OverflowError) as error:
            results.append({'id': case['id'], 'passed': False, 'execution': 'ERROR',
                            'error': str(error)[:512]})
            continue
        expected = case['expected']
        if case['ordered']:
            equal = observed == expected
        else:
            # Preserve multiplicity while ignoring order; JSON keys avoid mixed-type sorting.
            equal = sorted(observed, key=_encoded) == sorted(expected, key=_encoded)
        results.append({'id': case['id'], 'passed': equal, 'execution': 'EXECUTED', 'observed': observed})
    return {'schema': 'harness.sql-outcome/v1', 'scope': 'bounded_fixture_outcomes_only',
            'status': 'PASS' if all(c['passed'] for c in results) else 'FAIL',
            'query_sha256': hashlib.sha256(query.encode('utf-8')).hexdigest(),
            'fixtures_sha256': hashlib.sha256(fixtures).hexdigest(),
            'cases': results, 'native_quality': 'NOT_RUN'}
