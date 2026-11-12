"""Coverage and byte bindings cannot turn implementation into native proof."""
import copy
import hashlib
import os

import pytest


def test_readable_binding_in_non_listable_directory_remains_accessible(tmp_path):
    from agent_harness.qualification import Bindings
    directory = tmp_path / 'traverse-only'
    directory.mkdir()
    evidence = directory / 'known.txt'
    evidence.write_bytes(b'Known permitted evidence.\n')
    directory.chmod(0o111)
    try:
        # Root and ACL-granted callers can list despite mode bits; their known
        # file still must remain readable. The nonprivileged case detects the regression.
        if not os.access(directory, os.R_OK):
            with pytest.raises(PermissionError):
                os.listdir(directory)
        bindings = Bindings(tmp_path)
        assert bindings.read({'path': 'traverse-only/known.txt',
                              'sha256': hashlib.sha256(evidence.read_bytes()).hexdigest()}) == evidence.read_bytes()
        bindings.finish()
    finally:
        directory.chmod(0o700)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def contract(tmp_path):
    source = tmp_path / 'owner.txt'
    source.write_text('Owner introduction\n' + ''.join(
        f'{i}. SECTION {i}\nRequirement {i} needs actual proof.\n\n' for i in range(1, 12)))
    code = tmp_path / 'code.py'
    code.write_text('value = 1\n')
    evidence = {'path': 'code.py', 'sha256': sha(code), 'why': 'fixture implementation'}
    sections = []
    for i in range(1, 12):
        sections.append({'id': f'H05-{i:02}', 'source_section': i, 'title': f'Section {i}',
                         'clauses': [{'id': f'H05-{i:02}.01', 'requirement': f'Requirement {i}',
                                      'source_quote': f'Requirement {i} needs actual proof.',
                                      'implementation': {'status': 'present', 'evidence': [copy.deepcopy(evidence)]},
                                      'local_qualification': {'status': 'not_run', 'evidence': []},
                                      'native_qualification': {'status': 'not_run', 'evidence': []},
                                      'gap': 'No native run', 'next_check': 'Run independent fixture'}]})
    return tmp_path, {'schema': 'harness.requirements/v1',
                      'source': {'path': 'owner.txt', 'sha256': sha(source)}, 'sections': sections}


def validate(*args):
    from agent_harness.qualification import validate as check
    return check(*args)


def test_honest_incomplete_contract_is_valid_but_not_complete(contract):
    root, manifest = contract
    result = validate(manifest, root)
    assert result['status'] == 'CONTRACT_VALID'
    assert result['requirements'] == 11
    assert result['complete'] is False


@pytest.mark.parametrize('change', ['missing_section', 'duplicate_section', 'empty_clauses',
                                    'duplicate_clause', 'borrowed_quote', 'wrong_prefix', 'missing_gap'])
def test_contract_does_not_hide_coverage_or_provenance_gaps(contract, change):
    root, m = contract
    clause = m['sections'][0]['clauses'][0]
    if change == 'missing_section': m['sections'].pop()
    if change == 'duplicate_section': m['sections'].append(copy.deepcopy(m['sections'][0]))
    if change == 'empty_clauses': m['sections'][0]['clauses'] = []
    if change == 'duplicate_clause': m['sections'][0]['clauses'].append(copy.deepcopy(clause))
    if change == 'borrowed_quote': clause['source_quote'] = 'Requirement 2 needs actual proof.'
    if change == 'wrong_prefix': clause['id'] = 'H05-02.99'
    if change == 'missing_gap': clause['gap'] = ''
    with pytest.raises(ValueError): validate(m, root)


@pytest.mark.parametrize('path', ['/absolute.txt', '../outside.txt', '.env'])
def test_evidence_scope_is_not_widened(contract, path):
    root, m = contract
    m['sections'][0]['clauses'][0]['implementation']['evidence'][0]['path'] = path
    with pytest.raises(ValueError): validate(m, root)


def test_changed_artifact_invalidates_old_hash(contract):
    root, m = contract
    (root / 'code.py').write_text('value = 2\n')
    with pytest.raises(ValueError, match='hash|binding|changed'): validate(m, root)


def test_symlink_evidence_cannot_escape_selected_project(contract):
    root, m = contract
    target = root / 'alias.py'
    target.symlink_to(root / 'code.py')
    m['sections'][0]['clauses'][0]['implementation']['evidence'][0]['path'] = 'alias.py'
    with pytest.raises(ValueError): validate(m, root)


@pytest.mark.parametrize('axis', ['local_qualification', 'native_qualification'])
def test_code_or_document_reference_is_not_an_execution_receipt(contract, axis):
    root, m = contract
    clause = m['sections'][0]['clauses'][0]
    clause[axis] = {'status': 'qualified', 'evidence': copy.deepcopy(clause['implementation']['evidence'])}
    with pytest.raises(ValueError, match='receipt'): validate(m, root)


@pytest.mark.parametrize('exit_code', [True, 1, None])
def test_failed_or_missing_or_boolean_execution_cannot_qualify(contract, exit_code):
    root, m = contract
    clause = m['sections'][0]['clauses'][0]
    ref = copy.deepcopy(clause['implementation']['evidence'][0])
    ref['receipt'] = {'level': 'native', 'command': 'fixture only', 'exit_code': exit_code,
                      'subjects': [{'path': 'code.py', 'sha256': sha(root / 'code.py')}]}
    clause['native_qualification'] = {'status': 'qualified', 'evidence': [ref]}
    with pytest.raises(ValueError): validate(m, root)


def test_receipt_for_old_subject_cannot_qualify_current_code(contract):
    root, m = contract
    clause = m['sections'][0]['clauses'][0]
    ref = copy.deepcopy(clause['implementation']['evidence'][0])
    ref['receipt'] = {'level': 'native', 'command': 'fixture only', 'exit_code': 0,
                      'subjects': [{'path': 'code.py', 'sha256': '0' * 64}]}
    clause['native_qualification'] = {'status': 'qualified', 'evidence': [ref]}
    with pytest.raises(ValueError): validate(m, root)


def test_success_receipt_for_another_subject_cannot_qualify_this_implementation(contract):
    root, m = contract
    (root / 'unrelated.py').write_text('unrelated = True\n')
    clause = m['sections'][0]['clauses'][0]
    ref = copy.deepcopy(clause['implementation']['evidence'][0])
    ref['receipt'] = {'level': 'native', 'command': 'another successful fixture', 'exit_code': 0,
                      'subjects': [{'path': 'unrelated.py', 'sha256': sha(root / 'unrelated.py')}]}
    clause['native_qualification'] = {'status': 'qualified', 'evidence': [ref]}
    with pytest.raises(ValueError, match='subject'): validate(m, root)


def test_valid_execution_metadata_does_not_authenticate_an_actual_run(contract):
    root, m = contract
    for section in m['sections']:
        clause = section['clauses'][0]
        for axis, level in [('local_qualification', 'local'), ('native_qualification', 'native')]:
            ref = copy.deepcopy(clause['implementation']['evidence'][0])
            ref['receipt'] = {'level': level, 'command': 'authored fixture, not a real model run',
                              'exit_code': 0, 'subjects': [{'path': 'code.py', 'sha256': sha(root / 'code.py')}]}
            clause[axis] = {'status': 'qualified', 'evidence': [ref]}
    result = validate(m, root)
    assert result['complete'] is True
    assert result['scope'] == 'coverage_and_current_bindings_only'


def test_bad_json_duplicate_keys_are_not_resolved_by_last_value(tmp_path):
    from agent_harness.qualification import load
    path = tmp_path / 'manifest.json'
    path.write_text('{"schema":"wrong","schema":"harness.requirements/v1"}')
    with pytest.raises(ValueError, match='duplicate'):
        load(path)


def test_later_owner_requirement_is_not_lost_from_aggregate(contract):
    root, m = contract
    extension = copy.deepcopy(m['sections'][0]['clauses'][0])
    extension['id'] = 'V2-interruption-recovery'
    extension['source'] = copy.deepcopy(m['source'])
    m['extensions'] = [extension]
    result = validate(m, root)
    assert result['requirements'] == 12
    assert 'V2-interruption-recovery' in result['incomplete']
