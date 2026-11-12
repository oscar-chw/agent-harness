"""Preserve original checks while making the distributed evaluation scope explicit."""
import ast
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil

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
    'test_jev_decisions.py': ('jev_recorded_corpus.py', 23),
    'test_plugin_loop.py': ('plugin_recorded_corpus.py', 14),
    'test_settlement.py': ('settlement_recorded_context.py', 17),
}
PRIVATE_ONLY = {
    'test_h6a_l2_candidacy.py': (
        'test_l2_rule_matches_h3_module_sha_binding',
        'test_fresh_set_structure_and_hashes',
        'test_fresh_set_no_overlap_with_frozen_18',
        'test_recorded_candidates_drift_is_detectable',
    ),
    'test_kb_honesty.py': (
        'test_flag_off_byte_identical_to_recorded',
        'test_flag_off_unset_and_empty_and_false_all_inactive',
        'test_flag_on_suppression_matches_recorded_outcomes',
        'test_flag_on_nonfiring_byte_identical_to_flag_off',
        'test_flag_on_boundary_cases',
    ),
    'test_jev_decisions.py': ('TestValidRecord.test_real_h6a_record_verifies_on_disk',),
    'test_plugin_loop.py': ('PluginLoopTest.test_real_lever_candidate_admits_against_live_tree',),
    'test_settlement.py': ('SettlementTest.test_real_v3_plans_have_zero_failed_actions',),
}
FUNCTION_COUNTS = {
    'test_h6a_l2_candidacy.py': 14,
    'test_kb_honesty.py': 12,
    'test_jev_decisions.py': 26,
    'test_plugin_loop.py': 19,
    'test_settlement.py': 22,
}
# Original public test/helper function ASTs at the publication checkout's HEAD.
# Module-level path changes are permitted by the public-corpus extraction.
PURE_FUNCTION_HASHES = {
    'test_h2_semantic_rerank.py': '9f2e80d96dc849175259071967f7ec196d761780188f378b68d90f2796cb8003',
    'test_h3_hybrid.py': '77669b94e8a604617266c6fc7752ca69817b3227072e52b0646ef709a61fbe55',
}


def _dump(definition):
    # Preserve the manifest's Python 3.9 representation across the CI matrix.
    for node in ast.walk(definition):
        if getattr(node, 'type_params', None) == []:
            node._fields = tuple(field for field in node._fields if field != 'type_params')
    options = {'include_attributes': False}
    if 'show_empty' in inspect.signature(ast.dump).parameters:
        options['show_empty'] = True
    return ast.dump(definition, **options)


def _definitions(path):
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    functions, classes = {}, {}

    def visit(nodes, prefix=''):
        for node in nodes:
            if isinstance(node, ast.ClassDef):
                name = prefix + node.name
                assert name not in classes, 'duplicate class ' + name
                visit(node.body, name + '.')
                node.body = []
                classes[name] = _dump(node)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = prefix + node.name
                assert name not in functions, 'duplicate function ' + name
                functions[name] = _dump(node)
    visit(tree.body)
    return functions, classes


def _functions(path):
    return _definitions(path)[0]


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
    assert manifest['original_function_count'] == 93
    assert manifest['original_test_count'] == 75
    assert manifest['private_isolated_check_count'] == 12
    for filename, (private_name, count) in PRIVATE_CHECKS.items():
        entry = manifest['files'][filename]
        assert entry['private_check'] == 'eval/private_reference/' + private_name
        expected = entry['original_test_functions']
        assert len(expected) == count
        functions = _functions(PRIVATE / private_name)
        assert {name for name in functions if name.rsplit('.', 1)[-1].startswith('test_')} == set(expected)
        _assert_preserved(functions, expected)
        assert len(entry['original_functions']) == FUNCTION_COUNTS[filename]
        assert set(functions) == set(entry['original_functions'])
        _assert_preserved(functions, entry['original_functions'])
        assert entry['private_only_tests'] == list(PRIVATE_ONLY[filename])
    assert manifest['files']['test_settlement.py']['requires_original_signing_context'] is True


@pytest.mark.parametrize('filename', PRIVATE_CHECKS)
def test_public_pure_retained_assertions_match_original_hashes(filename):
    manifest = json.loads((PRIVATE / 'MANIFEST.json').read_text(encoding='utf-8'))
    functions, classes = _definitions(REPO / 'tests' / filename)
    entry = manifest['files'][filename]
    private, private_classes = _definitions(REPO / entry['private_check'])
    expected_tests = set(entry['original_test_functions']) - set(PRIVATE_ONLY[filename])
    if filename in RETAINED:
        assert expected_tests == set(RETAINED[filename])
        helpers = {'_report'} if filename == 'test_h6a_l2_candidacy.py' else {'inspect_source'}
        expected_functions = expected_tests | helpers
    else:
        expected_functions = set(entry['original_functions']) - set(PRIVATE_ONLY[filename])
    assert set(functions) == expected_functions
    _assert_preserved(functions, {name: entry['original_functions'][name] for name in expected_functions})
    assert classes == private_classes
    assert all(functions[name] == private[name] for name in functions)


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


def test_class_method_paths_preserve_distinct_assertions(tmp_path):
    path = tmp_path / 'methods.py'
    path.write_text('class First:\n    def test_value(self):\n        assert 2 + 2 == 4\n'
                    'class Second:\n    def test_value(self):\n        assert 3 + 3 == 6\n', encoding='utf-8')
    functions = _functions(path)
    assert set(functions) == {'First.test_value', 'Second.test_value'}
    expected = {name: _sha(source) for name, source in functions.items()}
    path.write_text(path.read_text().replace('assert 3 + 3 == 6', 'assert True'), encoding='utf-8')
    with pytest.raises(AssertionError, match='Second.test_value'):
        _assert_preserved(_functions(path), expected)


@pytest.mark.parametrize('private_name, method, public_files, missing_binding', [
    ('jev_recorded_corpus.py', 'TestValidRecord::test_real_h6a_record_verifies_on_disk', (
        'docs/v3/jev/h6a-l2-candidacy-20261111.json',
        'docs/v3/h6a-l2-candidacy-verdict-20261110.md',
        'docs/v3/h6a-l2-candidacy-contract-20261110.md',
    ), '.harness-work/v3-h6a-l2-candidacy/eval-h6a-20261110.json'),
    ('plugin_recorded_corpus.py', 'PluginLoopTest::test_real_lever_candidate_admits_against_live_tree', (
        'docs/v3/plugin-candidates/lever-pattern-20261111.json',
        'docs/v3/plugin-registry-20261111.json',
        'docs/v3/rea/lever-20261105.json',
        'docs/v3/jev/lever-pattern-adoption-20261111.json',
        'docs/v2/references/lever-20261105.md',
        'docs/v3/rea-support-design-20261111.md',
        'docs/v3/rea-support-v0-verdict-20261111.md',
        'plan/v3-rea-support.md',
    ), '.harness-work/eval-pipeline-20261110/runs/run-20261111T005928Z-2deaf2a8.json'),
])
def test_original_private_method_fails_on_missing_historical_binding(
        tmp_path, private_name, method, public_files, missing_binding):
    from agent_harness import jev, plugin_loop

    research_root = tmp_path / 'public-prerequisites-only'
    for name in public_files:
        source = REPO / name
        assert source.is_file() and not source.is_symlink()
        target = research_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    assert not (research_root / '.harness-work').exists()
    if private_name == 'jev_recorded_corpus.py':
        record = research_root / 'docs/v3/jev/h6a-l2-candidacy-20261111.json'
        with pytest.raises(jev.JevError) as error:
            jev.verify_record(str(record), str(research_root))
        assert 'bound input not found on disk: ' + missing_binding in str(error.value)
    else:
        candidate = json.loads((research_root / public_files[0]).read_text(encoding='utf-8'))
        entry = plugin_loop.admit(candidate, str(research_root), '2026-11-11')
        assert entry['status'] == 'refused'
        assert entry['detail'].startswith('typed decision refused')
        assert 'receipt not found on disk: ' + missing_binding in entry['detail']

    bootstrap = (
        'import sys\n'
        'sys.path[:0] = sys.argv[1:3]\n'
        'import pytest\n'
        'raise SystemExit(pytest.main(sys.argv[3:]))\n'
    )
    node_id = str(PRIVATE / private_name) + '::' + method
    result = subprocess.run(
        [sys.executable, '-I', '-B', '-c', bootstrap, str(REPO / 'src'),
         str(Path(pytest.__file__).resolve().parent.parent),
         '-q', '--tb=short', '-p', 'no:cacheprovider', node_id],
        cwd=REPO,
        env={'PATH': os.defpath, 'HARNESS_RESEARCH_ROOT': str(research_root),
             'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'},
        capture_output=True, text=True, timeout=30,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert 'FAILED eval/private_reference/' + private_name + '::' + method in output, output
    assert '1 failed' in output and 'ERROR collecting' not in output, output
    assert 'ModuleNotFoundError' not in output and 'SyntaxError' not in output, output
    assert not (research_root / missing_binding).exists()


def test_original_settlement_method_fails_without_its_private_research_root(tmp_path):
    research_root = tmp_path / 'absent-original-signing-root'
    assert not research_root.exists()
    bootstrap = (
        'import sys\n'
        'sys.path[:0] = sys.argv[1:3]\n'
        'import pytest\n'
        'raise SystemExit(pytest.main(sys.argv[3:]))\n'
    )
    method = 'SettlementTest::test_real_v3_plans_have_zero_failed_actions'
    node_id = str(PRIVATE / 'settlement_recorded_context.py') + '::' + method
    result = subprocess.run(
        [sys.executable, '-I', '-B', '-c', bootstrap, str(REPO / 'src'),
         str(Path(pytest.__file__).resolve().parent.parent),
         '-q', '--tb=short', '-p', 'no:cacheprovider', node_id],
        cwd=REPO,
        env={'PATH': os.defpath, 'HARNESS_RESEARCH_ROOT': str(research_root),
             'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'},
        capture_output=True, text=True, timeout=30,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert 'FAILED eval/private_reference/settlement_recorded_context.py::' + method in output, output
    assert 'plan file not found: ' + str(research_root / 'plan/v3-rea-support.md') in output, output
    assert '1 failed' in output and 'ERROR collecting' not in output, output
    assert 'ModuleNotFoundError' not in output and 'SyntaxError' not in output, output
    assert not research_root.exists()


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
