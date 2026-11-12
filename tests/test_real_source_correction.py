"""Real local report replay; byte provenance is distinct from truth or native recall."""
from pathlib import Path

import pytest

from agent_harness.mcp.kb import KB
from agent_harness.vault_sources import SourceVault, initialize

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'docs/v2/vault/README.md'
NEW = ROOT / 'docs/v2/vault/r5-reconciliation-20261103.md'


def test_actual_read_extent_correction_invalidates_current_pin_but_retains_history(tmp_path):
    docs = tmp_path / 'docs'
    docs.mkdir()
    page = docs / 'coverage.md'
    old_bytes, new_bytes = OLD.read_bytes(), NEW.read_bytes()
    assert old_bytes != new_bytes
    assert b'The last is the Alex Lavaee post' in old_bytes
    assert b'POST_TEXT_EXTENT_UNSPECIFIED' in new_bytes
    page.write_bytes(old_bytes)
    project_id = initialize(tmp_path)
    vault = SourceVault(tmp_path, project_id)
    old = vault.capture('docs/coverage.md')
    kb = KB(home=tmp_path / 'index', paths=[docs], fts=False)
    try:
        initial = kb.get('docs/coverage.md#coverage-that-can-be-claimed')
        assert 'one complete post text' in initial['text']
        page.write_bytes(new_bytes)
        with pytest.raises(ValueError, match='stale source'):
            vault.resolve(old)
        historical = vault.resolve(old, historical=True)
        assert historical['historical'] is True
        assert historical['text'].encode() == old_bytes
        current = vault.capture('docs/coverage.md')
        assert current['sha256'] != old['sha256']
        assert vault.resolve(current)['text'].encode() == new_bytes
        corrected = kb.get('docs/coverage.md#corrected-current-read-claim-originals-preserved')
        assert 'POST_TEXT_EXTENT_UNSPECIFIED' in corrected['text']
        assert 'not certify' in corrected['text']
        with pytest.raises(KeyError, match='no section'):
            kb.get('docs/coverage.md#coverage-that-can-be-claimed')
    finally:
        kb.close()
    cold = KB(home=tmp_path / 'index', paths=[docs], fts=False)
    try:
        assert 'POST_TEXT_EXTENT_UNSPECIFIED' in cold.get(
            'docs/coverage.md#corrected-current-read-claim-originals-preserved')['text']
    finally:
        cold.close()


def test_valid_source_bytes_do_not_authorize_another_project_receipt(tmp_path):
    permitted, foreign = tmp_path / 'permitted', tmp_path / 'foreign'
    permitted.mkdir()
    foreign.mkdir()
    for root in (permitted, foreign):
        (root / 'coverage.md').write_bytes(NEW.read_bytes())
    permitted_id, foreign_id = initialize(permitted), initialize(foreign)
    receipt = SourceVault(foreign, foreign_id).capture('coverage.md')
    with pytest.raises(ValueError, match='another project'):
        SourceVault(permitted, permitted_id).resolve(receipt)
