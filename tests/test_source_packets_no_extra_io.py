"""Optional source evidence reuses validation; review never writes or promotes."""
import pytest

from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize


@pytest.fixture
def record(tmp_path):
    identity = initialize(tmp_path)
    text = 'Release requires smoke tests and ticket-owner approval.\n'
    (tmp_path / 'original.md').write_text(text)
    source = SourceVault(tmp_path, identity).capture('original.md')
    store = ProjectMemory(tmp_path, identity)
    item = {'id': 'release-note', 'project_id': identity, 'layer': 'project_facts', 'kind': 'fact',
            'scope': 'task', 'text': 'Release requires smoke tests.',
            'provenance': [{'source': source, 'start_line': 1, 'end_line': 1}],
            'confidence': 'verified', 'sensitivity': 'public', 'access_boundary': 'local_user',
            'owner': 'fixture', 'freshness': 'current'}
    receipt = store.append(item, expected=None)
    return store, receipt, text


def test_source_review_uses_one_resolution_and_does_not_write_or_promote(record, monkeypatch):
    store, receipt, original = record
    policy = {'allowed_sensitivities': ['public'], 'allowed_scopes': ['task'], 'layers': ['project_facts']}
    before = {str(p.relative_to(store.root)): p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
    calls = []
    actual = SourceVault.resolve
    def observed(vault, ref, **kwargs):
        calls.append((ref, kwargs))
        return actual(vault, ref, **kwargs)
    monkeypatch.setattr(SourceVault, 'resolve', observed)
    result = store.read_scoped(receipt, include_sources=True, **policy)
    assert len(calls) == 1  # Validating and then re-reading every source doubles recovery work.
    assert result['source_spans'][0]['text'] == original
    assert result['item']['confidence'] == 'pending'
    assert result['kind'] == 'pending-memory-data'
    assert result['usable_for_current_decisions'] is False
    assert before == {str(p.relative_to(store.root)): p.read_bytes()
                      for p in store.root.rglob('*') if p.is_file()}
    calls.clear()
    default = store.read_scoped(receipt, **policy)
    assert len(calls) == 1
    assert {k: v for k, v in result.items() if k != 'source_spans'} == default


@pytest.mark.parametrize('invalid', [0, 1, [], 'yes'])
def test_source_review_switch_requires_a_real_boolean(record, invalid):
    store, receipt, _ = record
    with pytest.raises(ValueError, match='boolean'):
        store.read_scoped(receipt, include_sources=invalid,
            allowed_sensitivities=['public'], allowed_scopes=['task'], layers=['project_facts'])
