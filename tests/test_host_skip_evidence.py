"""New host reasons require a real capability condition, not just an excuse."""
from unittest import mock

import pytest

from tests import test_harness_best as audit

REASONS = [
    'SQLite build has no FTS5',
    'effective user can still read permission-revoked file',
    'effective user can still traverse revoked directory',
    'effective user can read revoked files',
]


def rejected(root, source):
    folder = root / 'tests'
    folder.mkdir(exist_ok=True)
    (folder / 'test_fixture.py').write_text(source)
    methods = [audit.TestV041().test_every_skip_in_the_suite_is_environmental,
               audit.TestV041b().test_every_skip_names_an_environmental_reason]
    failures = 0
    with mock.patch.object(audit, 'ROOT', root):
        for method in methods:
            try:
                method()
            except AssertionError:
                failures += 1
    return failures > 0


@pytest.mark.parametrize('reason', REASONS + ['server missing', 'POSIX named pipes unavailable'])
def test_unconditional_skip_remains_rejected_even_with_a_capability_label(tmp_path, reason):
    source = 'import pytest\n' + 'pytest.' + 'skip(' + repr(reason) + ')\n'
    assert rejected(tmp_path, source)


@pytest.mark.parametrize('reason', REASONS[1:])
def test_permission_capability_condition_is_accepted(tmp_path, reason):
    source = ('import os, pytest\ndef test_read():\n'
              '    if os.access("fixture", os.R_OK):\n        pytest.'
              + 'skip(' + repr(reason) + ')\n')
    assert not rejected(tmp_path, source)


def test_fts5_capability_decorator_is_accepted(tmp_path):
    source = ('import pytest\n@pytest.mark.' + 'skipif('
              'not fts5_available(), reason=' + repr(REASONS[0])
              + ')\ndef test_fts():\n    assert True\n')
    assert not rejected(tmp_path, source)


def test_comment_cannot_supply_a_capability_reason(tmp_path):
    source = ('import pytest\npytest.' + 'skip("server missing") # '
              + REASONS[0] + '\n')
    assert rejected(tmp_path, source)


def test_named_pipe_capability_condition_is_accepted(tmp_path):
    source = ('import os, pytest\n@pytest.mark.' + 'skipif('
              'not hasattr(os, "mkfifo"), reason="POSIX named pipes unavailable")\n'
              'def test_pipe():\n    assert True\n')
    assert not rejected(tmp_path, source)


@pytest.mark.parametrize('condition', ['True', 'not hasattr(os, "stat")'])
def test_named_pipe_label_does_not_excuse_an_unrelated_condition(tmp_path, condition):
    source = ('import os, pytest\n@pytest.mark.' + 'skipif(' + condition
              + ', reason="POSIX named pipes unavailable")\n'
              'def test_pipe():\n    assert True\n')
    assert rejected(tmp_path, source)
