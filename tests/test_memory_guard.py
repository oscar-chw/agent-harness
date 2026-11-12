"""H6b backflow guard: a tombstoned fact must not be silently re-admitted.

The guard derives its blocklist FROM the H5 tombstone ledger (single source of
truth): entries exist iff the page is currently tombstoned, so relearn reopens
admission by construction. Refusals are content-free and receipted into the
same hash-chained ledger (additive amendment: kind='backflow_refused').

Match legs (pre-registered in plan/v3-h6b-backflow-guard.md):
  L1 exact-bytes, L2 normalized-body, L3 unique-literal (df==1),
  L4 distinctive-token (>=4 shared; advisory unless l4_blocks=True).
"""
import json
import shutil
from pathlib import Path

import pytest

from agent_harness import memory_forget as mf
from agent_harness import memory_guard as mg
from agent_harness.mcp.memory import Memory
from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize

TARGET = 'memory/zeta-budget.md'
UNIQUE_LITERAL = 'zeta-run --cores 11-42'

PAGES = {
    'memory/MEMORY.md': ('# Memory index\n\n- [alpha setup](alpha-setup.md)\n'
                         '- [beta notes](beta-notes.md)\n- [gamma plan](gamma-plan.md)\n'
                         '- [delta run](delta-run.md)\n'),
    'memory/alpha-setup.md': ('# Alpha setup\n\nalpha setup uses quorum sensing and '
                              'gasket mounts on the rack.\n'),
    'memory/beta-notes.md': '# Beta notes\n\nbeta prefers mesa builds for the fleet.\n',
    'memory/gamma-plan.md': '# Gamma plan\n\ngamma tracks trellis wiring in the rack.\n',
    'memory/delta-run.md': '# Delta run\n\ndelta stores binder clips by the door.\n',
    TARGET: ('---\ncreated: 2026-01-01\n---\n# Zeta budget\n\n'
             'On the zeta build box, jobs pin with `zeta-run --cores 11-42` and may use the\n'
             'quorum mesa trellis binder gasket channels. Stop by RAM pressure, not queue depth.\n'),
}

NEAR_VERBATIM = ('---\ncreated: 2099-12-31\nmodified: 2099-12-31\n---\n\n# Zeta budget\n\n'
                 'On the zeta build box, jobs pin with `zeta-run --cores 11-42` and may use the\n'
                 'quorum mesa trellis binder gasket channels.\n\n'
                 'Stop by RAM pressure, not queue depth.\n')
PARAPHRASE = ('when running zeta jobs on the build box, pin them with '
              'zeta-run --cores 11-42 and stop on memory pressure')
L4_CANDIDATE = 'quorum mesa trellis binder — roll the fleet upgrade safely'
L4_BELOW_THRESHOLD = 'quorum mesa gasket on the shelf'
UNRELATED = 'the design review moved to Thursday afternoon'


def _write_corpus(root: Path) -> None:
    for rel, text in PAGES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')


def _refs(corpus: Path):
    return [p.read_text(encoding='utf-8') for p in sorted((corpus / 'memory').glob('*.md'))]


@pytest.fixture
def guarded(tmp_path):
    corpus = tmp_path / 'corpus'
    _write_corpus(corpus)
    escrow = tmp_path / 'escrow'
    mf.unlearn(corpus, TARGET, authority='test-authority', reason='unit test',
               escrow_dir=escrow, apply=True)
    guard = mg.Guard(ledger_root=corpus, escrow_dir=escrow, reference_texts=_refs(corpus))
    return {'corpus': corpus, 'escrow': escrow, 'guard': guard, 'tmp': tmp_path}


def _ledger(corpus: Path):
    return mf.load_ledger(corpus)


def _refusals(corpus: Path):
    return [r for r in _ledger(corpus) if r.get('kind') == 'backflow_refused']


# --------------------------------------------------------------- blocklist

def test_blocklist_entries_only_while_tombstoned(guarded):
    g = guarded['guard']
    assert [e['page'] for e in g.entries] == [TARGET]
    mf.relearn(guarded['corpus'], TARGET, authority='test-authority',
               reason='reopen', escrow_dir=guarded['escrow'], mode='restore', apply=True)
    g2 = mg.Guard(ledger_root=guarded['corpus'], escrow_dir=guarded['escrow'],
                  reference_texts=_refs(guarded['corpus']))
    assert g2.entries == []
    assert g2.check(PAGES[TARGET], path='corpus_page')['admit'] is True


# --------------------------------------------------------------- match legs

def test_leg1_exact_bytes_refused(guarded):
    v = guarded['guard'].check(PAGES[TARGET], path='corpus_page')
    assert v['admit'] is False
    assert 'exact_bytes' in v['refused']['legs']
    assert v['refused']['page'] == TARGET


def test_leg2_normalized_body_refused(guarded):
    v = guarded['guard'].check(NEAR_VERBATIM, path='corpus_page')
    assert v['admit'] is False
    assert 'normalized_body' in v['refused']['legs']


def test_leg3_paraphrase_with_unique_literal_refused(guarded):
    v = guarded['guard'].check(PARAPHRASE, path='mem_add')
    assert v['admit'] is False
    assert v['refused']['legs'] == ['unique_literal']


def test_leg4_distinctive_tokens_block_when_enabled(guarded):
    g = mg.Guard(ledger_root=guarded['corpus'], escrow_dir=guarded['escrow'],
                 reference_texts=_refs(guarded['corpus']), l4_blocks=True)
    v = g.check(L4_CANDIDATE, path='mem_add')
    assert v['admit'] is False
    assert v['refused']['legs'] == ['distinctive_tokens']


def test_leg4_advisory_by_default(guarded):
    v = guarded['guard'].check(L4_CANDIDATE, path='mem_add')
    assert v['admit'] is True
    assert 'distinctive_tokens' in v['signals']


def test_leg4_below_threshold_admits(guarded):
    g = mg.Guard(ledger_root=guarded['corpus'], escrow_dir=guarded['escrow'],
                 reference_texts=_refs(guarded['corpus']), l4_blocks=True)
    assert g.check(L4_BELOW_THRESHOLD, path='mem_add')['admit'] is True


def test_unrelated_text_admitted(guarded):
    v = guarded['guard'].check(UNRELATED, path='mem_add')
    assert v['admit'] is True and v['refused'] is None and v['receipt'] is None


def test_reference_pages_do_not_false_positive(guarded):
    """Mini sweep: every live page of the fixture corpus must be admitted."""
    g = guarded['guard']
    for p in sorted((guarded['corpus'] / 'memory').glob('*.md')):
        v = g.check(p.read_text(encoding='utf-8'), path='corpus_page')
        assert v['admit'] is True, 'false positive on %s' % p.name


# --------------------------------------------------------------- refusal contract

def test_refusal_is_content_free(guarded):
    v = guarded['guard'].check(PARAPHRASE, path='mem_add')
    blob = json.dumps(v) + json.dumps(_refusals(guarded['corpus']))
    for content in (UNIQUE_LITERAL, 'quorum', 'mesa', 'queue depth', 'RAM pressure'):
        assert content not in blob
    assert v['refused']['tombstone']  # identity + hash only


def test_refusal_receipt_chain_valid(guarded):
    before = len(_ledger(guarded['corpus']))
    guarded['guard'].check(PARAPHRASE, path='mem_add')
    records = _ledger(guarded['corpus'])
    assert len(records) == before + 1
    rec = records[-1]
    assert rec['kind'] == 'backflow_refused' and rec['path'] == 'mem_add'
    assert mf.verify_ledger(records) == []
    assert mf.page_states(records) == {TARGET: 'tombstoned'}  # refusals never change state


def test_receipt_deduped(guarded):
    guarded['guard'].check(PARAPHRASE, path='mem_add')
    guarded['guard'].check(PARAPHRASE, path='mem_add')
    assert len(_refusals(guarded['corpus'])) == 1


def test_mixed_ledger_amendment_is_additive(guarded):
    """A ledger with refusal records verifies; a pure tombstone+relearn ledger
    (H5's shape) still verifies under the amended rules."""
    guarded['guard'].check(PARAPHRASE, path='mem_add')
    assert mf.verify_ledger(_ledger(guarded['corpus'])) == []
    mf.relearn(guarded['corpus'], TARGET, authority='test-authority',
               reason='reopen', escrow_dir=guarded['escrow'], mode='restore', apply=True)
    records = _ledger(guarded['corpus'])
    assert [r['kind'] for r in records] == ['tombstone', 'backflow_refused', 'relearn']
    assert mf.verify_ledger(records) == []
    assert mf.page_states(records) == {TARGET: 'relearned'}


def test_refusal_record_required_fields_enforced(guarded):
    guarded['guard'].check(PARAPHRASE, path='mem_add')
    lp = mf.ledger_path(guarded['corpus'])
    records = _ledger(guarded['corpus'])
    bad = dict(records[-1])
    del bad['legs']
    lines = lp.read_text(encoding='utf-8').splitlines()
    lines[-1] = json.dumps(bad, sort_keys=True)
    lp.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    problems = mf.verify_ledger(_ledger(guarded['corpus']))
    assert any('missing fields' in p for p in problems)


# --------------------------------------------------------------- fail-closed / degraded

def test_corrupt_ledger_refuses_everything(guarded, tmp_path):
    lp = mf.ledger_path(guarded['corpus'])
    rec = json.loads(lp.read_text(encoding='utf-8').splitlines()[0])
    rec['record_hash'] = '0' * 64
    lp.write_text(json.dumps(rec, sort_keys=True) + '\n', encoding='utf-8')
    before = lp.read_text(encoding='utf-8')
    v = guarded['guard'].check(UNRELATED, path='mem_add')
    assert v['admit'] is False
    assert v['state'] == 'corrupt'
    assert v['refused']['legs'] == ['ledger_integrity']
    assert v['problems']
    assert lp.read_text(encoding='utf-8') == before  # nothing chained onto a broken ledger


def test_torn_ledger_refuses_everything(guarded):
    lp = mf.ledger_path(guarded['corpus'])
    with lp.open('a', encoding='utf-8') as f:
        f.write('{"seq": 2, "kin')  # a torn write
    v = guarded['guard'].check(UNRELATED, path='mem_add')
    assert v['admit'] is False and v['state'] == 'corrupt'


def test_no_ledger_guard_inactive(tmp_path):
    corpus = tmp_path / 'corpus'
    _write_corpus(corpus)  # never unlearned: no tombstones/ dir at all
    g = mg.Guard(ledger_root=corpus, escrow_dir=tmp_path / 'escrow',
                 reference_texts=_refs(corpus))
    v = g.check(PAGES[TARGET], path='corpus_page')
    assert v['admit'] is True and v['state'] == 'inactive' and v['receipt'] is None


def test_missing_escrow_degrades_loudly(guarded):
    shutil.rmtree(guarded['escrow'])
    g = mg.Guard(ledger_root=guarded['corpus'], escrow_dir=guarded['escrow'],
                 reference_texts=_refs(guarded['corpus']))
    v1 = g.check(PAGES[TARGET], path='corpus_page')
    assert v1['admit'] is False and v1['refused']['legs'] == ['exact_bytes']
    assert v1['degraded'] is True
    v2 = g.check(PARAPHRASE, path='mem_add')  # known limit: L3 needs the escrow
    assert v2['admit'] is True and v2['degraded'] is True


# --------------------------------------------------------------- audit side

def test_audit_store_flags_blocked_and_stays_silent_on_clean(guarded):
    texts = {'clean': UNRELATED, 'blocked': PARAPHRASE}
    out = guarded['guard'].audit_store(list(texts.values()))
    assert out['state'] == 'ok'
    assert len(out['findings']) == 1
    f = out['findings'][0]
    assert f['page'] == TARGET and f['legs'] == ['unique_literal']
    assert json.dumps(out).find(UNIQUE_LITERAL) == -1  # findings are content-free
    assert _refusals(guarded['corpus']) == []  # audit never appends receipts
    assert guarded['guard'].audit_store([UNRELATED])['findings'] == []


# --------------------------------------------------------------- JSON-store wiring

def test_mem_add_refused_with_receipt(guarded):
    home = guarded['tmp'] / 'h'
    m = Memory(home=home, project=guarded['tmp'], guard=guarded['guard'])
    res = m.mem_add('pin zeta jobs with `zeta-run --cores 11-42`')
    assert res['ok'] is False
    assert res['refused']['page'] == TARGET
    assert not list((home / 'memory' / 'user').glob('*.json'))  # nothing written
    assert len(_refusals(guarded['corpus'])) == 1
    ok = m.mem_add(UNRELATED)  # unrelated content still flows in the same run
    assert ok.get('id') and not ok.get('duplicate')
    m.close()


def test_lesson_add_refused(guarded):
    home = guarded['tmp'] / 'h2'
    m = Memory(home=home, project=guarded['tmp'], guard=guarded['guard'])
    res = m.lesson_add(mistake='ran zeta jobs unpinned',
                       fix='pin with `zeta-run --cores 11-42`', trigger='zeta jobs')
    assert res['ok'] is False
    assert not list((home / 'lessons').glob('*.json'))
    m.close()


def test_sync_quarantines_dropped_file(guarded):
    home = guarded['tmp'] / 'h3'
    m = Memory(home=home, project=guarded['tmp'], guard=guarded['guard'])
    d = home / 'memory' / 'user'
    d.mkdir(parents=True)
    item = {'id': 'm-aaaaaaaa0000', 'text': 'pin zeta jobs with `zeta-run --cores 11-42`',
            'tags': [], 'created': 1.0, 'updated': 1.0, 'uses': 0}
    (d / 'm-aaaaaaaa0000.json').write_text(json.dumps(item), encoding='utf-8')
    m.sync()
    assert (d / 'm-aaaaaaaa0000.json').is_file()  # the user's file is never touched
    assert m.con.execute("SELECT COUNT(*) FROM mem_items WHERE id='m-aaaaaaaa0000'").fetchone()[0] == 0
    assert all(UNIQUE_LITERAL not in i['text'] for i in m.mem_search('zeta-run', k=5))
    assert len(_refusals(guarded['corpus'])) == 1
    m.sync()  # idempotent: the same blocked file is not re-receipted
    assert len(_refusals(guarded['corpus'])) == 1
    m.close()


def test_sync_unindexes_previously_admitted_blocked_file(guarded):
    """Admitted before the tombstone existed; the next guarded sync must drop it
    from the index (the file stays on disk)."""
    home = guarded['tmp'] / 'h4'
    m1 = Memory(home=home, project=guarded['tmp'])  # no guard: admitted
    r = m1.mem_add('pin zeta jobs with `zeta-run --cores 11-42`')
    assert r.get('id')
    m1.close()
    m2 = Memory(home=home, project=guarded['tmp'], guard=guarded['guard'])
    m2.sync()
    row = m2.con.execute('SELECT COUNT(*) FROM mem_items WHERE id=?', (r['id'],)).fetchone()[0]
    assert row == 0
    assert list((home / 'memory' / 'user').glob('*.json'))  # file preserved
    m2.close()


# --------------------------------------------------------------- ProjectMemory wiring

def _project_store(root: Path, guard):
    root.mkdir(parents=True, exist_ok=True)
    project_id = initialize(root)
    (root / 'source.txt').write_text('the standup note\n', encoding='utf-8')
    source = SourceVault(root, project_id).capture('source.txt')
    item = {'id': 'claim', 'project_id': project_id, 'layer': 'project_facts',
            'kind': 'fact', 'scope': 'project', 'text': 'x',
            'provenance': [{'source': source, 'start_line': 1, 'end_line': 1}],
            'confidence': 'user_stated', 'sensitivity': 'internal',
            'access_boundary': 'local_user', 'owner': 'fixture', 'freshness': 'current'}
    return ProjectMemory(root, project_id, guard=guard), item


def test_project_memory_append_blocked_and_clean(guarded):
    store, item = _project_store(guarded['tmp'] / 'proj', guarded['guard'])
    blocked = dict(item, text='pin zeta jobs with `zeta-run --cores 11-42`')
    with pytest.raises(ValueError) as exc:
        store.append(blocked, expected=None)
    assert UNIQUE_LITERAL not in str(exc.value)  # content-free refusal
    rec = _refusals(guarded['corpus'])
    assert len(rec) == 1 and rec[0]['path'] == 'project_memory'
    clean = dict(item, text='the standup moved to 09:30')
    receipt = store.append(clean, expected=None)
    assert receipt['id'] == 'claim'
    assert store.read(receipt, allowed_sensitivities=['internal'])['item']['text'] \
        == 'the standup moved to 09:30'
