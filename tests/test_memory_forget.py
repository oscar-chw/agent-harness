"""Unit tests for agent_harness.memory_forget (H5 node 6).

All fixtures are synthetic tmp_path corpora; the tests never read the live
memory corpus, never touch the frozen H1 snapshot, never touch the network,
and never call a model. The certification tests build a real KB (SQLite FTS5)
index over the tmp corpus — the index is the seam certification must interrogate.
"""
import json
from pathlib import Path

import pytest

from agent_harness import memory_consolidate as mc
from agent_harness import memory_forget as mf


TARGET = 'memory/zqx-budget.md'
CONTENT_PROBE = 'taskset -c 10-19'
IDENTITY_PROBE = 'zqx-budget'


def write_page(root: Path, rel: str, body: str, modified: str = '') -> Path:
    fm = '---\nname: %s\n' % Path(rel).stem
    if modified:
        fm += 'metadata:\n  modified: %s\n' % modified
    fm += '---\n\n'
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(fm + body, encoding='utf-8')
    return p


def make_corpus(root: Path) -> Path:
    """A 3-page corpus: the target fact page (orphan), a MEMORY.md index naming
    it (the index line restates the fact — it must be redacted), one other page."""
    write_page(root, 'memory/MEMORY.md',
               '- [zqx budget](zqx-budget.md) — taskset -c 10-19, stop by CPU-busy\n'
               '- [other](other-page.md) — unrelated spindle notes\n')
    write_page(root, TARGET,
               'The zqx session gets `taskset -c 10-19` and 4 virtual GPUs.\n'
               'Stop when CPU busy > 85%.\n', '2026-10-01T00:00:00Z')
    write_page(root, 'memory/other-page.md',
               'Spindle collocation notes, unrelated to any budget.\n',
               '2026-10-02T00:00:00Z')
    return root


def probes():
    return [{'probe': CONTENT_PROBE, 'kind': 'content'},
            {'probe': IDENTITY_PROBE, 'kind': 'identity'}]


def root_pages_hash(root: Path) -> str:
    pages = mc.load_pages(root)
    return mc.corpus_root_hash([pg.sha256 for pg in pages])


def make_freeze(root: Path, out: Path) -> Path:
    pages = mc.load_pages(root)
    recs = [{'path': pg.rel, 'bytes': len(pg.data), 'sha256': pg.sha256} for pg in pages]
    doc = {'corpus': {'pages': recs, 'page_order': [pg.rel for pg in pages],
                      'corpus_sha256': mc.corpus_root_hash([pg.sha256 for pg in pages])}}
    out.write_text(json.dumps(doc))
    return out


def do_unlearn(root: Path, tmp_path: Path):
    escrow = tmp_path / 'escrow'
    return mf.unlearn(root, TARGET, authority='test-owner', reason='unit test',
                      escrow_dir=escrow, apply=True), escrow


def do_certify(root: Path, tmp_path: Path, escrow, **kw):
    return mf.certify(root, TARGET, probes=probes(), escrow_dir=escrow,
                      kb_home=tmp_path / 'kb-home', **kw)


# ---------------------------------------------------------------- unlearn

def test_unlearn_dry_run_changes_nothing(tmp_path):
    src = make_corpus(tmp_path / 'corpus')
    before = {p.relative_to(src).as_posix(): p.read_bytes()
              for p in sorted(src.rglob('*')) if p.is_file()}
    report = mf.unlearn(src, TARGET, authority='a', reason='r',
                        escrow_dir=tmp_path / 'escrow', apply=False)
    assert report['dry_run'] is True
    assert not (tmp_path / 'escrow').exists()
    assert not (src / 'tombstones').exists()
    after = {p.relative_to(src).as_posix(): p.read_bytes()
             for p in sorted(src.rglob('*')) if p.is_file()}
    assert after == before
    assert report['tombstone_record']['page'] == TARGET     # planned, not written


def test_unlearn_apply_removes_page_escrows_and_tombstones(tmp_path):
    src = make_corpus(tmp_path / 'corpus')
    page_sha = mc._sha256((src / TARGET).read_bytes())
    before_root = root_pages_hash(src)
    report, escrow = do_unlearn(src, tmp_path)
    assert report['dry_run'] is False
    assert not (src / TARGET).exists()                       # content exits the corpus
    sealed = escrow / ('%s.md' % page_sha)
    assert sealed.is_file() and mc._sha256(sealed.read_bytes()) == page_sha
    rec = report['tombstone_record']
    for field in mf.REQUIRED_TOMBSTONE_FIELDS:
        assert field in rec, field
    assert rec['page_sha256'] == page_sha
    assert rec['prev_hash'] == mf.GENESIS_HASH
    assert mf.record_hash(rec) == rec['record_hash']
    assert rec['corpus_pages_sha256_before'] == before_root
    assert report['corpus_pages_sha256']['after'] != before_root
    assert mf.verify_ledger(mf.load_ledger(src)) == []


def test_unlearn_redacts_index_lines_with_hash_receipts(tmp_path):
    src = make_corpus(tmp_path / 'corpus')
    mem_before = mc._sha256((src / 'memory/MEMORY.md').read_bytes())
    report, escrow = do_unlearn(src, tmp_path)
    mem_after_text = (src / 'memory/MEMORY.md').read_text()
    assert IDENTITY_PROBE not in mem_after_text
    assert CONTENT_PROBE not in mem_after_text
    assert '- [other](other-page.md)' in mem_after_text     # nothing else redacted
    red = report['tombstone_record']['redactions']
    assert len(red) == 1 and red[0]['file'] == 'memory/MEMORY.md'
    assert red[0]['before_sha256'] == mem_before
    assert red[0]['after_sha256'] == mc._sha256((src / 'memory/MEMORY.md').read_bytes())
    # the redacted line TEXT lives only in the escrow, never in ledger or receipt
    escrowed = json.loads((escrow / ('%s.redactions.json' %
                                     report['tombstone_record']['page_sha256'])).read_text())
    assert any(CONTENT_PROBE in l['text'] for l in escrowed[0]['lines'])
    assert CONTENT_PROBE not in (src / mf.LEDGER_REL).read_text()


def test_unlearn_refusals(tmp_path):
    src = make_corpus(tmp_path / 'corpus')
    with pytest.raises(ValueError):                          # missing page
        mf.unlearn(src, 'memory/nope.md', authority='a', reason='r',
                   escrow_dir=tmp_path / 'escrow', apply=True)
    with pytest.raises(ValueError):                          # escrow inside the boundary
        mf.unlearn(src, TARGET, authority='a', reason='r',
                   escrow_dir=src / 'tombstones' / 'escrow', apply=True)
    do_unlearn(src, tmp_path)
    with pytest.raises(ValueError):                          # already tombstoned
        mf.unlearn(src, TARGET, authority='a', reason='r',
                   escrow_dir=tmp_path / 'escrow', apply=True)


def test_unlearn_freeze_binding_and_drift_refusal(tmp_path):
    src = make_corpus(tmp_path / 'corpus')
    freeze = make_freeze(src, tmp_path / 'freeze.json')
    report = mf.unlearn(src, TARGET, authority='a', reason='r',
                        escrow_dir=tmp_path / 'escrow', freeze=freeze, apply=False)
    assert report['binding']['verified'] is True
    write_page(src, 'memory/other-page.md', 'drifted\n', '2026-10-02T00:00:00Z')
    with pytest.raises(ValueError):
        mf.unlearn(src, TARGET, authority='a', reason='r',
                   escrow_dir=tmp_path / 'escrow2', freeze=freeze, apply=True)
    assert (src / TARGET).is_file()                          # refused before any write
    assert not (tmp_path / 'escrow2').exists()


# ---------------------------------------------------------------- certify

def test_certify_green_on_sound_unlearn(tmp_path):
    src = make_corpus(tmp_path / 'corpus')
    _, escrow = do_unlearn(src, tmp_path)
    cert = do_certify(src, tmp_path, escrow)
    assert cert['ok'] is True, [c for c in cert['checks'] if not c['ok']]


def test_certify_red_on_stale_index(tmp_path):
    from agent_harness.mcp import kb as kb_mod
    src = make_corpus(tmp_path / 'corpus')
    kb_home = tmp_path / 'kb-home'
    kb = kb_mod.KB(home=kb_home, paths=[src / 'memory'], db_path=kb_home / 'index.sqlite')
    kb.refresh()                                             # index WITH the page
    pre = kb.search(CONTENT_PROBE, k=10)
    assert any(h['path'] == TARGET for h in pre)             # control: retrievable
    kb.refresh = lambda: {'files': 3, 'changed': 0, 'removed': 0}  # stale: never rewalk
    _, escrow = do_unlearn(src, tmp_path)
    cert = mf.certify(src, TARGET, probes=probes(), escrow_dir=escrow,
                      kb_factory=lambda root: kb)
    kb.close()
    assert cert['ok'] is False
    failed = {c['name'] for c in cert['checks'] if not c['ok']}
    assert 'index_absence' in failed or 'retrieval_absence' in failed


def test_certify_red_on_quoted_text_leak(tmp_path):
    src = make_corpus(tmp_path / 'corpus')
    write_page(src, 'memory/leaker.md',
               'Quoting the budget: `taskset -c 10-19` and linking [[zqx-budget]].\n',
               '2026-10-03T00:00:00Z')
    _, escrow = do_unlearn(src, tmp_path)
    cert = do_certify(src, tmp_path, escrow)
    assert cert['ok'] is False
    content = [c for c in cert['checks'] if c['name'] == 'content_absence'][0]
    assert content['ok'] is False and 'memory/leaker.md' in content['detail']


def test_certify_red_on_tampered_ledger(tmp_path):
    src = make_corpus(tmp_path / 'corpus')
    _, escrow = do_unlearn(src, tmp_path)
    ledger = src / mf.LEDGER_REL
    rec = json.loads(ledger.read_text().splitlines()[0])
    del rec['authority']                                     # incomplete tombstone
    ledger.write_text(json.dumps(rec) + '\n', encoding='utf-8')
    cert = do_certify(src, tmp_path, escrow)
    assert cert['ok'] is False
    assert any(c['name'] == 'tombstone_integrity' and not c['ok'] for c in cert['checks'])


def test_certify_red_on_broken_chain(tmp_path):
    src = make_corpus(tmp_path / 'corpus')
    _, escrow = do_unlearn(src, tmp_path)
    ledger = src / mf.LEDGER_REL
    rec = json.loads(ledger.read_text().splitlines()[0])
    rec['reason'] = 'edited after the fact'                  # any edit breaks record_hash
    ledger.write_text(json.dumps(rec) + '\n', encoding='utf-8')
    cert = do_certify(src, tmp_path, escrow)
    assert cert['ok'] is False
    assert any(c['name'] == 'tombstone_integrity' and not c['ok'] for c in cert['checks'])


def test_certify_red_on_escrow_mismatch(tmp_path):
    src = make_corpus(tmp_path / 'corpus')
    report, escrow = do_unlearn(src, tmp_path)
    sealed = escrow / ('%s.md' % report['tombstone_record']['page_sha256'])
    sealed.write_bytes(sealed.read_bytes() + b' ')           # escrow no longer binds
    cert = do_certify(src, tmp_path, escrow)
    assert cert['ok'] is False
    assert any(c['name'] == 'tombstone_integrity' and not c['ok'] for c in cert['checks'])


def test_certify_red_on_amnesia(tmp_path):
    src = make_corpus(tmp_path / 'corpus')
    (src / TARGET).unlink()                                  # erased with NO record
    cert = mf.certify(src, TARGET, probes=probes(),
                      kb_home=tmp_path / 'kb-home')
    assert cert['ok'] is False
    tomb = [c for c in cert['checks'] if c['name'] == 'tombstone_integrity'][0]
    assert tomb['ok'] is False and 'no tombstone record' in tomb['detail']


def test_certify_red_on_content_probe_inside_ledger(tmp_path):
    src = make_corpus(tmp_path / 'corpus')
    _, escrow = do_unlearn(src, tmp_path)
    ledger = src / mf.LEDGER_REL
    with ledger.open('a', encoding='utf-8') as f:            # a record leaking content
        f.write(json.dumps({'note': 'the budget was taskset -c 10-19'}) + '\n')
    cert = do_certify(src, tmp_path, escrow)
    assert cert['ok'] is False
    failed = {c['name'] for c in cert['checks'] if not c['ok']}
    assert 'content_free_record' in failed


def test_certify_green_requires_others_preserved(tmp_path):
    src = make_corpus(tmp_path / 'corpus')
    freeze = make_freeze(src, tmp_path / 'freeze.json')
    _, escrow = do_unlearn(src, tmp_path)
    cert = do_certify(src, tmp_path, escrow, freeze=freeze)
    assert cert['ok'] is True
    (src / 'memory/other-page.md').unlink()                  # lose an unrelated fact
    cert2 = mf.certify(src, TARGET, probes=probes(), escrow_dir=escrow,
                       kb_home=tmp_path / 'kb-home2', freeze=freeze)
    assert cert2['ok'] is False
    assert any(c['name'] == 'others_preserved' and not c['ok'] for c in cert2['checks'])


# ---------------------------------------------------------------- relearn

def test_relearn_restore_is_byte_identical(tmp_path):
    src = make_corpus(tmp_path / 'corpus')
    page_bytes = (src / TARGET).read_bytes()
    mem_bytes = (src / 'memory/MEMORY.md').read_bytes()
    before_root = root_pages_hash(src)
    report, escrow = do_unlearn(src, tmp_path)
    tombstone_line = (src / mf.LEDGER_REL).read_text()
    out = mf.relearn(src, TARGET, authority='test-owner', reason='fact needed again',
                     escrow_dir=escrow, mode='restore', apply=True)
    assert (src / TARGET).read_bytes() == page_bytes
    assert (src / 'memory/MEMORY.md').read_bytes() == mem_bytes
    assert root_pages_hash(src) == before_root               # whole corpus restored
    assert out['relearn_record']['mode'] == 'restore'
    assert out['matches_pre_unlearn_root'] is True
    lines = (src / mf.LEDGER_REL).read_text().splitlines()
    assert len(lines) == 2                                   # append, never edit
    assert lines[0] == tombstone_line.strip()
    assert mf.verify_ledger(mf.load_ledger(src)) == []
    states = mf.page_states(mf.load_ledger(src))
    assert states[TARGET] == 'relearned'


def test_relearn_supersede_writes_new_page_keeps_escrow_sealed(tmp_path):
    src = make_corpus(tmp_path / 'corpus')
    report, escrow = do_unlearn(src, tmp_path)
    sealed = escrow / ('%s.md' % report['tombstone_record']['page_sha256'])
    sealed_bytes = sealed.read_bytes()
    new_body = b'---\nname: zqx-budget\n---\n\n2026-11-10 re-measured: the zqx session now gets taskset -c 20-29.\n'
    out = mf.relearn(src, TARGET, authority='test-owner', reason='new measurement',
                     escrow_dir=escrow, mode='supersede', new_bytes=new_body, apply=True)
    assert (src / TARGET).read_bytes() == new_body
    assert sealed.read_bytes() == sealed_bytes               # old bytes stay sealed
    rec = out['relearn_record']
    assert rec['mode'] == 'supersede'
    assert rec['new_page_sha256'] == mc._sha256(new_body)
    assert rec['supersedes_seq'] == report['tombstone_record']['seq']
    assert mf.verify_ledger(mf.load_ledger(src)) == []


def test_relearn_refusals(tmp_path):
    src = make_corpus(tmp_path / 'corpus')
    with pytest.raises(ValueError):                          # never tombstoned
        mf.relearn(src, TARGET, authority='a', reason='r',
                   escrow_dir=tmp_path / 'escrow', mode='restore', apply=True)
    report, escrow = do_unlearn(src, tmp_path)
    with pytest.raises(ValueError):                          # supersede needs new bytes
        mf.relearn(src, TARGET, authority='a', reason='r',
                   escrow_dir=escrow, mode='supersede', apply=True)
    sealed = escrow / ('%s.md' % report['tombstone_record']['page_sha256'])
    sealed.write_bytes(b'forged')
    with pytest.raises(ValueError):                          # escrow hash mismatch
        mf.relearn(src, TARGET, authority='a', reason='r',
                   escrow_dir=escrow, mode='restore', apply=True)
    assert not (src / TARGET).exists()                       # refused before any write


# ---------------------------------------------------------------- the ledger

def test_ledger_append_only_edit_of_earlier_record_is_caught(tmp_path):
    src = make_corpus(tmp_path / 'corpus')
    _, escrow = do_unlearn(src, tmp_path)
    mf.relearn(src, TARGET, authority='a', reason='r', escrow_dir=escrow,
               mode='restore', apply=True)
    ledger = src / mf.LEDGER_REL
    lines = ledger.read_text().splitlines()
    rec0 = json.loads(lines[0])
    rec0['authority'] = 'someone-else'                       # rewrite history
    lines[0] = json.dumps(rec0)
    ledger.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    problems = mf.verify_ledger(mf.load_ledger(src))
    assert problems and any('record_hash' in p or 'chain' in p for p in problems)


def test_consolidation_skips_tombstoned_page(tmp_path):
    src = tmp_path / 'corpus'
    write_page(src, 'memory/MEMORY.md', '- [hub](hub.md) index\n')
    write_page(src, 'memory/hub.md',
               'Tuplespace greeble fluxcap budget notes.\n', '2026-08-01T00:00:00Z')
    write_page(src, 'memory/linker.md', 'Cites [[hub]] as the hub page.\n',
               '2026-08-02T00:00:00Z')
    write_page(src, 'memory/zqx-budget.md',
               'Tuplespace greeble fluxcap orphan carrying taskset -c 10-19.\n',
               '2026-10-01T00:00:00Z')
    pre = mc.consolidate(src, apply=False)
    assert any('zqx-budget' in json.dumps(a) for a in pre['actions'])  # control
    do_unlearn(src, tmp_path)
    post = mc.consolidate(src, apply=False)
    assert not any('zqx-budget' in json.dumps(a) for a in post['actions'])
    assert not any(r['path'] == TARGET for r in post['retention'])
    assert not any('tombstones' in json.dumps(a) for a in post['actions'])
