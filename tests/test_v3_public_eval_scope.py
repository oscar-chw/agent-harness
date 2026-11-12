"""Preserve original checks while making the distributed evaluation scope explicit."""
import ast
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


REPO = Path(__file__).resolve().parents[1]
PRIVATE = REPO / 'eval' / 'private_reference'
RETAINED = {
    'test_h6a_l2_candidacy.py': (
        'test_copied_functions_byte_identical_to_h3',
        'test_copied_constants_equal_h3',
        'test_content_tokens_stoplist_and_length',
        'test_content_bigrams_adjacent_both_content',
        'test_rule_L2_fires_below_full_coverage',
        'test_rule_L2_full_coverage_override',
        'test_rule_L2_silent_when_L_silent',
        'test_max_coverage_distinct_query_tokens',
        'test_module_imports_without_numpy',
    ),
    'test_kb_honesty.py': (
        'test_embedded_rule_constants_equal_frozen_eval_module',
        'test_embedded_rule_functions_match_eval_module',
        'test_honesty_window_distinct_pages_of_top10_sections',
    ),
}
PRIVATE_CHECKS = {
    'test_h6a_l2_candidacy.py': ('h6a_recorded_corpus.py', 13),
    'test_kb_honesty.py': ('kb_honesty_corpus.py', 8),
}
# Original public test/helper function ASTs at the publication checkout's HEAD.
# Module-level path changes are permitted by the public-corpus extraction.
PURE_FUNCTION_HASHES = {
    'test_h2_semantic_rerank.py': '9f2e80d96dc849175259071967f7ec196d761780188f378b68d90f2796cb8003',
    'test_h3_hybrid.py': '77669b94e8a604617266c6fc7752ca69817b3227072e52b0646ef709a61fbe55',
}


def _functions(path):
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    functions = {}
    for function in tree.body:
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        assert function.name not in functions, 'duplicate function ' + function.name
        # Python 3.12 adds empty type_params to older source syntax. Preserve
        # the manifest's Python 3.9 AST representation across the CI matrix.
        for node in ast.walk(function):
            if getattr(node, 'type_params', None) == []:
                node._fields = tuple(field for field in node._fields if field != 'type_params')
        options = {'include_attributes': False}
        if 'show_empty' in inspect.signature(ast.dump).parameters:
            options['show_empty'] = True
        functions[function.name] = ast.dump(function, **options)
    return functions


def _sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _assert_preserved(functions, expected):
    assert expected, 'original function hashes are required'
    assert expected.keys() <= functions.keys(), 'original functions are missing'
    for name, digest in expected.items():
        assert _sha(functions[name]) == digest, 'function AST changed for ' + name


def test_manifest_declares_complete_original_private_scope():
    manifest = json.loads((PRIVATE / 'MANIFEST.json').read_text(encoding='utf-8'))
    assert manifest['schema'] == 'harness.public-private-eval-scope/v1'
    assert manifest['private_corpus'] == 'NOT_DISTRIBUTED'
    assert manifest['public_ci_private_corpus'] == 'NOT_RUN'
    assert set(manifest['files']) == set(PRIVATE_CHECKS)
    for filename, (private_name, count) in PRIVATE_CHECKS.items():
        entry = manifest['files'][filename]
        assert entry['private_check'] == 'eval/private_reference/' + private_name
        expected = entry['original_test_functions']
        assert len(expected) == count
        functions = _functions(PRIVATE / private_name)
        assert {name for name in functions if name.startswith('test_')} == set(expected)
        _assert_preserved(functions, expected)


@pytest.mark.parametrize('filename', RETAINED)
def test_public_pure_retained_assertions_match_original_hashes(filename):
    manifest = json.loads((PRIVATE / 'MANIFEST.json').read_text(encoding='utf-8'))
    functions = _functions(REPO / 'tests' / filename)
    assert {name for name in functions if name.startswith('test_')} == set(RETAINED[filename])
    expected = manifest['files'][filename]['original_test_functions']
    _assert_preserved(functions, {name: expected[name] for name in RETAINED[filename]})
    private = _functions(REPO / manifest['files'][filename]['private_check'])
    for name in functions:
        assert functions[name] == private[name], 'retained function changed for ' + name


@pytest.mark.parametrize('filename', PURE_FUNCTION_HASHES)
def test_h2_h3_public_function_assertions_remain_unchanged(filename):
    functions = _functions(REPO / 'tests' / filename)
    assert _sha(json.dumps(functions, sort_keys=True)) == PURE_FUNCTION_HASHES[filename]


@pytest.mark.parametrize('changed', ['removed', 'weakened', 'duplicate'])
def test_preservation_check_rejects_missing_or_changed_assertions(tmp_path, changed):
    path = tmp_path / 'check.py'
    path.write_text('def test_value():\n    assert 2 + 2 == 4\n', encoding='utf-8')
    expected = {name: _sha(source) for name, source in _functions(path).items()}
    replacements = {
        'removed': '',
        'weakened': 'def test_value():\n    assert True\n',
        'duplicate': 'def test_value():\n    assert 2 + 2 == 4\n'
                     'def test_value():\n    assert True\n',
    }
    path.write_text(replacements[changed], encoding='utf-8')
    with pytest.raises(AssertionError):
        _assert_preserved(_functions(path), expected)


def test_explicit_private_collection_fails_without_the_authorized_corpus(tmp_path):
    missing_root = tmp_path / 'absent-research-root'
    assert not missing_root.exists()
    bootstrap = (
        'import sys\n'
        'sys.path[:0] = sys.argv[1:3]\n'
        'import pytest\n'
        'raise SystemExit(pytest.main(sys.argv[3:]))\n'
    )
    result = subprocess.run(
        [sys.executable, '-I', '-B', '-c', bootstrap, str(REPO / 'src'),
         str(Path(pytest.__file__).resolve().parent.parent),
         '--collect-only', '-q', '-p', 'no:cacheprovider',
         str(PRIVATE / 'h6a_recorded_corpus.py'), str(PRIVATE / 'kb_honesty_corpus.py')],
        cwd=REPO,
        env={'PATH': os.defpath, 'HARNESS_RESEARCH_ROOT': str(missing_root),
             'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'},
        capture_output=True, text=True, timeout=30,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 2, output
    assert 'ERROR collecting eval/private_reference/h6a_recorded_corpus.py' in output, output
    assert 'ERROR collecting eval/private_reference/kb_honesty_corpus.py' in output, output
    assert 'ModuleNotFoundError' in output and 'l2_rule' in output, output
    assert 'SyntaxError' not in output, output
    assert not missing_root.exists()
