"""Unit tests for agent_harness.memory_dreaming (H4 node 6).

All fixtures are synthetic tmp_path corpora; the tests never read the live
memory corpus, never touch the network, and never call a model. Tiny synthetic
corpora have tiny idf masses, so gate thresholds are scaled through the
receipted gate_overrides hook where a test needs promotion to fire; the
contract defaults are asserted separately.
"""
import json
from pathlib import Path

import pytest

from agent_harness import memory_consolidate as mc
from agent_harness import memory_dreaming as md


def write_page(root: Path, rel: str, body: str, modified: str = '') -> Path:
    fm = '---\nname: %s\n' % Path(rel).stem
    if modified:
        fm += 'metadata:\n  modified: %s\n' % modified
    fm += '---\n\n'
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(fm + body, encoding='utf-8')
    return p


def hashes_under(root: Path):
    return {md.mc._sha256(p.read_bytes()) for p in sorted(root.rglob('*.md'))}


# Contract defaults are the frozen ones (docs/v3/h4-dreaming-contract-20261110.md)
def test_contract_defaults():
    assert md.TRIGGER_MIN_SESSIONS == 5
    assert md.TRIGGER_MIN_PAGES_CHANGED == 10
    assert md.LEX_SAT == 14.0
    assert md.ORPHAN_MIN_SUPPORT == 4
    assert md.ORPHAN_MIN_LEX == 0.35
    assert md.ORPHAN_MIN_SCORE == 0.55
    assert md.EDGE_MIN_CTX == 0.5
    assert md.EDGE_MIN_SCORE == 0.55


# ------------------------------------------------------------------ trigger

def test_trigger_bootstrap_fires():
    t = md.evaluate_trigger(None)
    assert t['triggered'] is True and 'bootstrap' in t['reasons'][0]


def test_trigger_thresholds_and_refusal():
    assert md.evaluate_trigger({'sessions_since_last_dream': 5,
                                'pages_changed_since_last_dream': 0,
                                'last_dream_session': 's0'})['triggered'] is True
    assert md.evaluate_trigger({'sessions_since_last_dream': 1,
                                'pages_changed_since_last_dream': 10,
                                'last_dream_session': 's0'})['triggered'] is True
    t = md.evaluate_trigger({'sessions_since_last_dream': 4,
                             'pages_changed_since_last_dream': 9,
                             'last_dream_session': 's0'}, session_id='s1')
    assert t['triggered'] is False and 'below threshold' in t['reasons'][-1]


def test_trigger_cooldown_same_session_noop():
    t = md.evaluate_trigger({'sessions_since_last_dream': 99,
                             'pages_changed_since_last_dream': 99,
                             'last_dream_session': 's1'}, session_id='s1')
    assert t['triggered'] is False and 'cooldown' in t['reasons'][0]


# ------------------------------------------------------------------ scorers

def test_scorers_bounded_and_deterministic(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'memory/hub.md', 'Greeble fluxcap tuplespace operator manual.\n'
               'See [[other]].\n', '2026-08-01T00:00:00Z')
    write_page(src, 'memory/other.md', 'Cites [[hub]] back.\n', '2026-08-02T00:00:00Z')
    write_page(src, 'memory/orph.md', 'Greeble fluxcap tuplespace measurements nobody '
               'links to.\n', '2026-08-03T00:00:00Z')
    pages = mc.load_pages(src)
    by_rel = {pg.rel: pg for pg in pages}
    indeg = mc.build_graph(pages)
    df = mc._df(pages)
    stems = md._stem_set(pages)
    cand = {'kind': 'orphan_inbound_link', 'orphan': 'memory/orph.md',
            'source': 'memory/hub.md', 'shared_tokens': ['greeble', 'fluxcap', 'tuplespace']}
    s1 = md.score_orphan_link(cand, by_rel, indeg, df, len(pages), stems)
    s2 = md.score_orphan_link(cand, by_rel, indeg, df, len(pages), stems)
    assert s1 == s2                                    # deterministic
    for v in s1['signals'].values():
        if isinstance(v, float):
            assert 0.0 <= v <= 1.0
    assert 0.0 <= s1['score'] <= 1.0
    assert s1['n_shared'] == 3 and s1['signals']['s_lex'] > 0


def test_edge_scorer_context_agreement(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'memory/old.md', 'The widget-frob link runs at 1000 Mb/s; the gizmo '
               'switch is the limit.\n', '2026-08-01T00:00:00Z')
    write_page(src, 'memory/new.md', '**Correction 2026-09-01:** the 1000 Mb/s reading of '
               'the widget-frob gizmo link was wrong; measured throughput establishes '
               '5 Gb/s.\n', '2026-09-01T00:00:00Z')
    pages = mc.load_pages(src)
    by_rel = {pg.rel: pg for pg in pages}
    indeg = mc.build_graph(pages)
    mech = mc.consolidate(src, apply=False)
    edge = [a for a in mech['actions'] if a['kind'] == 'supersedes_edge'][0]
    sc = md.score_supersedes_edge(edge, by_rel, indeg)
    assert sc['signals']['strong_literals'] == ['1000 Mb/s']
    assert sc['signals']['ctx_shared_tokens'] >= 3      # widget-frob / gizmo / link / 1000
    assert sc['signals']['s_ctx'] >= 0.5
    assert sc['signals']['date_gap_days'] == 31
    # a well-scoped true edge promotes even at contract defaults
    ok, failed = md.gate_supersedes_edge(sc)
    assert ok, failed


def test_edge_weak_literal_gate_bites(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'memory/old.md', 'The alpha beta gamma route sits at .18 today.\n',
               '2026-08-01T00:00:00Z')
    write_page(src, 'memory/new.md', '**Correction 2026-09-01:** the .18 alpha beta gamma '
               'reading was wrong.\n', '2026-09-01T00:00:00Z')
    mech = mc.consolidate(src, apply=False)
    edges = [a for a in mech['actions'] if a['kind'] == 'supersedes_edge']
    assert len(edges) == 1                               # H1 scope rule met (3 shared tokens)
    pages = mc.load_pages(src)
    by_rel = {pg.rel: pg for pg in pages}
    sc = md.score_supersedes_edge(edges[0], by_rel, mc.build_graph(pages))
    assert sc['signals']['strong_literals'] == []        # '.18' is a weak dotted suffix
    ok, failed = md.gate_supersedes_edge(sc)
    assert not ok and any('G-StrongLit' in f for f in failed)


# ------------------------------------------------------------------- gates

def test_orphan_gates_all_required():
    base = {'n_shared': 5, 'signals': {'s_lex': 0.9}, 'score': 0.9}
    assert md.gate_orphan_link(base)[0] is True
    ok, failed = md.gate_orphan_link({**base, 'n_shared': 3})
    assert not ok and any('G-Support' in f for f in failed)
    ok, failed = md.gate_orphan_link({**base, 'signals': {'s_lex': 0.2}})
    assert not ok and any('G-Lex' in f for f in failed)
    ok, failed = md.gate_orphan_link({**base, 'score': 0.4})
    assert not ok and any('G-Score' in f for f in failed)
    # a single failing gate demotes even when the others pass with margin
    ok, failed = md.gate_orphan_link({'n_shared': 3, 'signals': {'s_lex': 1.0}, 'score': 0.99})
    assert not ok and len(failed) == 1


# --------------------------------------------------------------- phase guard

def test_phase_guard_scope_matrix(tmp_path):
    dst = tmp_path / 'dst'
    work = tmp_path / 'work'
    page = dst / 'memory' / 'hub.md'
    # light/rem: no corpus writes, no ledger writes
    for phase in ('light', 'rem'):
        g = md.PhaseGuard(phase, dst_root=dst, work_dir=work)
        with pytest.raises(md.PhaseScopeError):
            g.check('orphan_link_append', page)
        with pytest.raises(md.PhaseScopeError):
            g.check('ledger', work / 'dream-ledger.json')
        assert g.check('receipt', work / 'staged.json')['allowed'] is True
    g = md.PhaseGuard('deep', dst_root=dst, work_dir=work)
    assert g.check('orphan_link_append', page)['allowed'] is True
    assert g.check('ledger', work / 'DREAMS.md')['allowed'] is True
    with pytest.raises(md.PhaseScopeError):              # MEMORY.md never writable
        g.check('orphan_link_append', dst / 'memory' / 'MEMORY.md')
    with pytest.raises(md.PhaseScopeError):              # archive/ never writable
        g.check('orphan_link_append', dst / 'archive' / 'memory' / 'x.md')
    with pytest.raises(md.PhaseScopeError):              # outside dst root
        g.check('orphan_link_append', tmp_path / 'elsewhere' / 'memory' / 'x.md')
    with pytest.raises(md.PhaseScopeError):              # receipts stay in work dir
        g.check('receipt', tmp_path / 'receipt.json')
    with pytest.raises(md.PhaseScopeError):              # unknown write kind
        g.check('delete_page', page)
    assert len(g.refused) == 5 and len(g.allowed) == 2


# --------------------------------------------------------------- the pass

def _corpus_with_orphan(src: Path):
    write_page(src, 'MEMORY.md', '- [hub](hub.md) index line\n')
    write_page(src, 'memory/hub.md', 'The greeble fluxcap tuplespace zorble operator '
               'manual.\nSee [[other]] for context.\n', '2026-08-01T00:00:00Z')
    write_page(src, 'memory/other.md', 'Cites [[hub]] back.\n', '2026-08-02T00:00:00Z')
    write_page(src, 'memory/orph.md', 'Greeble fluxcap tuplespace zorble measurements '
               'nobody links to.\n', '2026-08-03T00:00:00Z')


PROMOTE_OVERRIDES = {'lex_sat': 1.0, 'orphan_min_support': 3,
                     'orphan_min_lex': 0.05, 'orphan_min_score': 0.05}


def test_dry_run_changes_nothing_but_receipts(tmp_path):
    src = tmp_path / 'src'
    _corpus_with_orphan(src)
    work = tmp_path / 'work'
    before = {p: p.read_bytes() for p in src.rglob('*.md')}
    r = md.dream(src, work_dir=work, gate_overrides=PROMOTE_OVERRIDES)
    assert r['dry_run'] is True
    assert not (tmp_path / 'dst').exists()
    assert {p: p.read_bytes() for p in src.rglob('*.md')} == before   # corpus untouched
    assert (work / 'staged-candidates.json').is_file()                # light receipt
    assert (work / 'scored-candidates.json').is_file()                # rem receipt
    assert not (work / 'dream-ledger.json').exists()                  # ledger is apply-only
    assert r['counts']['promoted_orphan_links'] == 1
    assert r['threshold_overrides_applied'] == PROMOTE_OVERRIDES      # receipted loudly
    assert r['threshold_override_note']


def test_apply_requires_trigger_and_dst(tmp_path):
    src = tmp_path / 'src'
    _corpus_with_orphan(src)
    with pytest.raises(ValueError):
        md.dream(src, None, apply=True)                                # no dst
    with pytest.raises(ValueError):
        md.dream(src, src, apply=True)                                 # dst == src
    with pytest.raises(ValueError):
        md.dream(src, tmp_path / 'dst', apply=True,
                 state={'sessions_since_last_dream': 0, 'pages_changed_since_last_dream': 0,
                        'last_dream_session': 's0'}, session_id='s1')  # not triggered
    assert not (tmp_path / 'dst').exists()                             # refused before writing


def test_apply_promotes_integrates_orphan_preserves_facts(tmp_path):
    src = tmp_path / 'src'
    _corpus_with_orphan(src)
    work = tmp_path / 'work'
    dst = tmp_path / 'dst'
    in_hashes = hashes_under(src)
    r = md.dream(src, dst, work, apply=True, session_id='s1',
                 gate_overrides=PROMOTE_OVERRIDES)
    assert r['dry_run'] is False and r['fact_preservation']['ok'] is True
    assert '[[orph]]' in (dst / 'memory' / 'hub.md').read_text()
    assert (dst / 'MEMORY.md').read_bytes() == (src / 'MEMORY.md').read_bytes()
    out_hashes = hashes_under(dst)
    assert in_hashes <= out_hashes | {m['before_sha256'] for m in r['output']['mutated']}
    after = r['hygiene']['after']
    assert after['orphan_count'] == r['hygiene']['before']['orphan_count'] - 1
    assert 'memory/orph.md' not in after['orphans']
    # ledger + narrative under the work dir
    ledger = json.loads((work / 'dream-ledger.json').read_text())
    assert ledger['promoted_orphan_links'] == ['memory/orph.md <- memory/hub.md']
    assert (work / 'DREAMS.md').is_file()
    # every corpus write receipted and in scope
    kinds = {w['kind'] for w in r['guard']['writes']}
    assert kinds <= {'receipt', 'ledger', 'orphan_link_append'}
    # idempotent: a second dream over the output finds nothing to promote
    r2 = md.dream(dst, tmp_path / 'dst2', apply=True, session_id='s2',
                  gate_overrides=PROMOTE_OVERRIDES)
    assert r2['counts']['promoted_orphan_links'] == 0
    assert r2['output']['root_sha256'] == r['output']['root_sha256']


def test_supersedes_promotes_to_ledger_never_corpus(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'memory/old.md', 'The widget-frob link runs at 1000 Mb/s; the gizmo '
               'switch is the limit.\n', '2026-08-01T00:00:00Z')
    write_page(src, 'memory/new.md', '**Correction 2026-09-01:** the 1000 Mb/s reading of '
               'the widget-frob gizmo link was wrong; measured throughput establishes '
               '5 Gb/s.\n', '2026-09-01T00:00:00Z')
    work = tmp_path / 'work'
    dst = tmp_path / 'dst'
    r = md.dream(src, dst, work, apply=True, session_id='s1')
    assert r['counts']['promoted_supersedes_edges'] == 1
    # corpus bytes of both pages unchanged — the edge lives in the ledger only
    assert (dst / 'memory' / 'old.md').read_bytes() == (src / 'memory' / 'old.md').read_bytes()
    assert (dst / 'memory' / 'new.md').read_bytes() == (src / 'memory' / 'new.md').read_bytes()
    ledger = json.loads((work / 'dream-ledger.json').read_text())
    assert len(ledger['promoted_supersedes_edges']) == 1
    assert ledger['promoted_supersedes_edges'][0]['successor'] == 'memory/new.md'
    assert r['output']['root_sha256'] == mc.corpus_root_hash(
        [pg.sha256 for pg in mc.load_pages(src)])                       # copy == source


def test_review_only_kinds_never_promoted(tmp_path):
    src = tmp_path / 'src'
    # the WITHDRAWAL page is the older one; the newer page still instructs the
    # withdrawn literal -> H1 conflict flag (review-only in dreaming v0).
    write_page(src, 'memory/old.md', 'The `zqx-route` path was withdrawn for zqx transfers '
               'and should not be re-proposed; zzqxit alpha bravo.\n', '2026-08-01T00:00:00Z')
    write_page(src, 'memory/new.md', 'For zqx transfers use `zqx-route`; zzqxit alpha '
               'bravo calibration payload.\n', '2026-09-01T00:00:00Z')
    mech = mc.consolidate(src, apply=False)
    assert any(a['kind'] == 'conflict_flag' for a in mech['actions'])      # fixture sanity
    r = md.dream(src, tmp_path / 'dst', tmp_path / 'work', apply=True, session_id='s1')
    assert r['counts']['promoted_supersedes_edges'] == 0                   # no correction marker
    kinds = {x['kind'] for x in r['review_only']}
    assert 'conflict_flag' in kinds
    assert r['counts']['promoted_orphan_links'] == 0


def test_low_quality_candidate_demoted_override_promotes(tmp_path):
    src = tmp_path / 'src'
    _corpus_with_orphan(src)
    r = md.dream(src)                                     # contract defaults on a tiny corpus
    assert r['counts']['promoted_orphan_links'] == 0      # demoted (tiny idf mass)
    d = r['demoted'][0]
    assert 'G-' in d['explain']
    r2 = md.dream(src, gate_overrides=PROMOTE_OVERRIDES)  # maliciously lowered thresholds
    assert r2['counts']['promoted_orphan_links'] == 1
    assert r2['threshold_override_note']                  # the lowering is receipted


def test_determinism_two_dry_runs_identical_modulo_timestamp(tmp_path):
    src = tmp_path / 'src'
    _corpus_with_orphan(src)
    r1 = md.dream(src, gate_overrides=PROMOTE_OVERRIDES, now='2026-11-10T00:00:00Z')
    r2 = md.dream(src, gate_overrides=PROMOTE_OVERRIDES, now='2026-11-10T00:00:00Z')
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)


def test_no_candidates_empty_pass_still_receipts(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'memory/a.md', 'Entirely standalone alpha page.\n', '2026-08-01T00:00:00Z')
    write_page(src, 'memory/b.md', 'Entirely standalone beta page.\n', '2026-08-02T00:00:00Z')
    r = md.dream(src, tmp_path / 'dst', tmp_path / 'work', apply=True, session_id='s1')
    assert r['counts']['candidates'] == 0
    assert r['counts']['promoted_orphan_links'] == 0
    assert r['fact_preservation']['ok'] is True
    assert r['output']['root_sha256'] == mc.corpus_root_hash(
        [pg.sha256 for pg in mc.load_pages(src)])
