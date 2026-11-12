"""Unit tests for agent_harness.memory_dreaming_v1 (H6c node 7).

All fixtures are synthetic tmp_path corpora or hand-built df dicts; the tests
never read the live memory corpus, never touch the network, and never call a
model. Tiny synthetic corpora have tiny idf masses, so gate thresholds are
scaled through the receipted gate_overrides hook where a test needs promotion
to fire; the contract defaults are asserted separately.
"""
import json
from pathlib import Path

import pytest

from agent_harness import memory_consolidate as mc
from agent_harness import memory_dreaming as md
from agent_harness import memory_dreaming_v1 as mv


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
    return {mc._sha256(p.read_bytes()) for p in sorted(root.rglob('*.md'))}


# Frozen contract defaults (docs/v3/h6c-dreaming-v1-contract-20261110.md)
def test_contract_defaults_frozen():
    assert mv.CTX_WINDOW == 8
    assert mv.CTX_SAT_V1 == 6.0
    assert mv.LEX_SAT_V1 == 8.0
    assert mv.EDGE_MIN_CTX_LOCAL == 0.5
    assert mv.EDGE_MIN_SCORE_V1 == 0.55
    assert mv.ORPHAN_MIN_SUPPORT == 4
    assert mv.ORPHAN_MIN_LEX == 0.35
    assert mv.ORPHAN_MIN_SCORE == 0.55
    assert mv.W_EDGE_V1 == {'scope': 0.30, 'ctx': 0.30, 'date': 0.10,
                            'auth': 0.10, 'stance': 0.20}
    assert mv.STANCE_LEXICON == frozenset(
        'wrong corrects corrected superseded supersedes stale retracted retracts '
        'suspect unverified broken misleading outdated garbage invalid mistake '
        'beware fixed'.split())


# --------------------------------------------------------------- primitives

def test_literal_windows_positions_and_exclusion():
    text = ('alpha beta gamma delta epsilon zeta eta theta iota kappa '
            '1000 Mb/s lambda mu nu xi omicron pi rho sigma tau upsilon')
    ws = mv.literal_windows(text, '1000 Mb/s', k=8)
    assert len(ws) == 1
    w = ws[0]
    assert '1000' not in w and 'mb' not in w and 's' not in w     # span excluded
    assert w[:8] == 'gamma delta epsilon zeta eta theta iota kappa'.split()
    assert w[8:] == 'lambda mu nu xi omicron pi rho sigma'.split()
    assert mv.literal_windows(text, 'not present here') == []
    # four occurrences -> four windows
    ws2 = mv.literal_windows('x 1000 Mb/s y ' * 4, '1000 Mb/s', k=8)
    assert len(ws2) == 4


def test_content_matches_corpus_token_space():
    window = 'the widget-frob not only x7k an link'.split()
    assert mv._content(window) == set(mc._tokens(' '.join(window)))
    assert 'the' not in mv._content(window) and 'not' not in mv._content(window)
    assert 'an' not in mv._content(window)                       # len <= 2
    assert 'widget-frob' in mv._content(window)                  # _WORD keeps compounds
    assert 'link' in mv._content(window)


def test_idf_bm25_monotone_positive():
    n = 133
    vals = [mv.idf_bm25('t', {'t': d}, n) for d in (1, 2, 5, 10, 40, 80, 133)]
    assert all(v > 0 for v in vals)
    assert all(vals[i] > vals[i + 1] for i in range(len(vals) - 1))
    # rare tokens dominate generic ones at corpus scale (the v0 saturation fix)
    assert mv.idf_bm25('t', {'t': 2}, n) > 3 * mv.idf_bm25('t', {'t': 80}, n)


def test_s_auth_log_scaling():
    assert mv.s_auth_log(0, 20) == 0.0
    assert mv.s_auth_log(20, 20) == pytest.approx(1.0)
    vals = [mv.s_auth_log(i, 20) for i in range(21)]
    assert all(vals[i] <= vals[i + 1] for i in range(20))        # monotone
    assert mv.s_auth_log(10, 20) > 0.5                           # concave (log)
    assert mv.s_auth_log(5, 0) == 0.0                            # degenerate graph


def test_stance_exact_word_no_substring_bleed():
    assert mv.has_stance(['that', 'was', 'wrong']) is True
    assert mv.has_stance(['wrongly', 'diagnosed']) is False      # no substring
    assert mv.has_stance(['corrected', 'errors']) is True        # the word itself
    assert mv.has_stance(['measured', 'throughput']) is False


def test_window_overlap_mass_idf_weighted():
    df = {'x710': 2, 'intel': 3, 'live': 40, 'data': 60}
    rare, ov_r = mv.window_overlap_mass('the x710 intel card'.split(),
                                        'an x710 intel link'.split(), df, 133)
    generic, ov_g = mv.window_overlap_mass('the live data set'.split(),
                                           'a live data host'.split(), df, 133)
    assert sorted(ov_r) == ['intel', 'x710'] and sorted(ov_g) == ['data', 'live']
    assert rare > 2 * generic                                    # recalibration bites


# ----------------------------------------------------------------- scorers

def _scorer_env(tmp_path, pages_spec):
    src = tmp_path / 'src'
    for rel, body, mod in pages_spec:
        write_page(src, rel, body, mod)
    pages = mc.load_pages(src)
    return pages, {pg.rel: pg for pg in pages}, mc.build_graph(pages), mc._df(pages)


def test_orphan_scorer_v1_bounded_deterministic_recalibrated(tmp_path):
    pages, by_rel, indeg, _ = _scorer_env(tmp_path, [
        ('memory/hub.md', 'Rarething quixotal fluxgrid notes.\n', '2026-08-01T00:00:00Z'),
        ('memory/orph.md', 'Rarething quixotal fluxgrid measurements.\n', '2026-08-02T00:00:00Z')])
    df_rare = {'rarething': 2, 'quixotal': 2, 'fluxgrid': 3}
    df_generic = {'rarething': 60, 'quixotal': 70, 'fluxgrid': 80}
    cand = {'kind': 'orphan_inbound_link', 'orphan': 'memory/orph.md',
            'source': 'memory/hub.md',
            'shared_tokens': ['rarething', 'quixotal', 'fluxgrid']}
    s1 = mv.score_orphan_link_v1(cand, by_rel, indeg, df_rare, 133, set(), 20)
    s2 = mv.score_orphan_link_v1(cand, by_rel, indeg, df_rare, 133, set(), 20)
    s3 = mv.score_orphan_link_v1(cand, by_rel, indeg, df_generic, 133, set(), 20)
    assert s1 == s2                                              # deterministic
    assert 0.0 <= s1['score'] <= 1.0
    assert s1['signals']['s_lex_v1'] > 3 * s3['signals']['s_lex_v1']


EDGE_PAGES = [
    ('memory/old.md', 'The widget-frob link runs at 1000 Mb/s; the gizmo '
     'switch is the limit.\n', '2026-08-01T00:00:00Z'),
    ('memory/new.md', '**Correction 2026-09-01:** the 1000 Mb/s reading of '
     'the widget-frob gizmo link was wrong; measured throughput establishes '
     '5 Gb/s.\n', '2026-09-01T00:00:00Z'),
]


def test_edge_scorer_v1_local_windows_and_stance(tmp_path):
    src = tmp_path / 'src'
    for rel, body, mod in EDGE_PAGES:
        write_page(src, rel, body, mod)
    pages = mc.load_pages(src)
    by_rel = {pg.rel: pg for pg in pages}
    mech = mc.consolidate(src, apply=False)
    edge = [a for a in mech['actions'] if a['kind'] == 'supersedes_edge'][0]
    # realistic df: the shared window tokens are rare at corpus scale
    df = {t: 3 for t in ('widget', 'frob', 'gizmo', 'link', 'reading',
                         'switch', 'limit', 'runs', 'measured')}
    sc = mv.score_supersedes_edge_v1(edge, by_rel, mc.build_graph(pages), df, 133, 20)
    sig = sc['signals']
    assert sig['strong_literals'] == ['1000 Mb/s']
    assert sig['stance_a'] is True                               # 'wrong' in marker
    assert sig['stance_b'] is False                              # old page states it flat
    assert sig['s_stance_net'] == 1.0
    assert set(sig['ctx_best_pair'][1]) >= {'widget', 'frob', 'gizmo', 'link'}
    assert sig['s_ctx_local'] >= 0.5                             # 4 rare tokens ≈ mass 14
    assert sig['date_gap_days'] == 31
    ok, failed = mv.gate_supersedes_edge_v1(sc)
    assert ok, failed


def test_edge_stance_b_disqualifies_agreement(tmp_path):
    src = tmp_path / 'src'
    # the "superseded" page ALREADY carries correction language near the literal
    write_page(src, 'memory/old.md', 'Update: the widget-frob link at 1000 Mb/s was '
               'wrong too; the gizmo switch is not the limit after all.\n',
               '2026-08-01T00:00:00Z')
    write_page(src, 'memory/new.md', '**Correction 2026-09-01:** the 1000 Mb/s reading '
               'of the widget-frob gizmo link was wrong; measured throughput '
               'establishes 5 Gb/s.\n', '2026-09-01T00:00:00Z')
    pages = mc.load_pages(src)
    by_rel = {pg.rel: pg for pg in pages}
    mech = mc.consolidate(src, apply=False)
    edge = [a for a in mech['actions'] if a['kind'] == 'supersedes_edge'][0]
    df = {t: 3 for t in ('widget', 'frob', 'gizmo', 'link')}
    sc = mv.score_supersedes_edge_v1(edge, by_rel, mc.build_graph(pages), df, 133, 20)
    assert sc['signals']['stance_b'] is True
    assert sc['signals']['s_stance_net'] == 0.0
    ok, failed = mv.gate_supersedes_edge_v1(sc)
    assert not ok and any('G-StanceB' in f for f in failed)


def test_edge_stance_a_required(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'memory/old.md', 'The widget-frob link runs at 1000 Mb/s; the gizmo '
               'switch is the limit.\n', '2026-08-01T00:00:00Z')
    # newer page carries an H1 correction marker (so the edge is proposed) but
    # NO stance-lexicon word — 'correction' matches H1's MARKER_CORRECTION yet
    # is not itself stance vocabulary
    write_page(src, 'memory/new.md', '**Correction 2026-09-01:** the 1000 Mb/s reading of '
               'the widget-frob gizmo link measured throughput again today; '
               '5 Gb/s observed.\n', '2026-09-01T00:00:00Z')
    pages = mc.load_pages(src)
    by_rel = {pg.rel: pg for pg in pages}
    mech = mc.consolidate(src, apply=False)
    edges = [a for a in mech['actions'] if a['kind'] == 'supersedes_edge']
    assert len(edges) == 1                                   # fixture sanity: H1 proposed it
    df = {t: 3 for t in ('widget', 'frob', 'gizmo', 'link')}
    sc = mv.score_supersedes_edge_v1(edges[0], by_rel, mc.build_graph(pages), df, 133, 20)
    assert sc['signals']['stance_a'] is False
    ok, failed = mv.gate_supersedes_edge_v1(sc)
    assert not ok and any('G-StanceA' in f for f in failed)
    # and the stance override hook (mutation-control red direction) is receipted
    ok2, _ = mv.gate_supersedes_edge_v1(sc, min_ctx_local=0.01, min_score=0.0,
                                        require_stance=False)
    assert ok2


# ------------------------------------------------------------------- gates

def test_gates_v1_all_required():
    base_o = {'n_shared': 5, 'signals': {'s_lex_v1': 0.9}, 'score': 0.9}
    assert mv.gate_orphan_link_v1(base_o)[0] is True
    ok, failed = mv.gate_orphan_link_v1({**base_o, 'n_shared': 3})
    assert not ok and any('G-Support' in f for f in failed)
    ok, failed = mv.gate_orphan_link_v1({**base_o, 'signals': {'s_lex_v1': 0.2}})
    assert not ok and any('G-Lex' in f for f in failed)
    ok, failed = mv.gate_orphan_link_v1({**base_o, 'score': 0.4})
    assert not ok and any('G-Score' in f for f in failed)
    ok, failed = mv.gate_orphan_link_v1({'n_shared': 3, 'signals': {'s_lex_v1': 1.0},
                                         'score': 0.99})
    assert not ok and len(failed) == 1      # a single failing gate demotes
    sig = {'strong_literals': ['x'], 's_ctx_local': 0.9, 'stance_a': True,
           'stance_b': False}
    base_e = {'signals': sig, 'score': 0.9}
    assert mv.gate_supersedes_edge_v1(base_e)[0] is True
    for key, bad, gate in (('strong_literals', [], 'G-StrongLit'),
                           ('s_ctx_local', 0.1, 'G-CtxLocal'),
                           ('stance_a', False, 'G-StanceA'),
                           ('stance_b', True, 'G-StanceB')):
        s = dict(sig)
        s[key] = bad
        ok, failed = mv.gate_supersedes_edge_v1({'signals': s, 'score': 0.9})
        assert not ok and any(gate in f for f in failed), gate
    ok, failed = mv.gate_supersedes_edge_v1({'signals': sig, 'score': 0.4})
    assert not ok and any('G-Score' in f for f in failed)


def test_phase_guard_reused_from_v0(tmp_path):
    g = mv.md.PhaseGuard('light', dst_root=tmp_path / 'dst', work_dir=tmp_path / 'w')
    with pytest.raises(md.PhaseScopeError):
        g.check('orphan_link_append', tmp_path / 'dst' / 'memory' / 'x.md')


# --------------------------------------------------------------- the pass

def _corpus_with_orphan(src: Path):
    write_page(src, 'MEMORY.md', '- [hub](hub.md) index line\n')
    write_page(src, 'memory/hub.md', 'The greeble fluxcap tuplespace zorble operator '
               'manual.\nSee [[other]] for context.\n', '2026-08-01T00:00:00Z')
    write_page(src, 'memory/other.md', 'Cites [[hub]] back.\n', '2026-08-02T00:00:00Z')
    write_page(src, 'memory/orph.md', 'Greeble fluxcap tuplespace zorble measurements '
               'nobody links to.\n', '2026-08-03T00:00:00Z')


PROMOTE_OVERRIDES_V1 = {'lex_sat_v1': 0.5, 'orphan_min_support': 3,
                        'orphan_min_lex': 0.05, 'orphan_min_score': 0.05}
EDGE_OVERRIDES_V1 = {'edge_min_ctx_local': 0.01, 'edge_min_score': 0.05}


def test_dry_run_changes_nothing_but_receipts(tmp_path):
    src = tmp_path / 'src'
    _corpus_with_orphan(src)
    work = tmp_path / 'work'
    before = {p: p.read_bytes() for p in src.rglob('*.md')}
    r = mv.dream_v1(src, work_dir=work, gate_overrides=PROMOTE_OVERRIDES_V1)
    assert r['dry_run'] is True
    assert not (tmp_path / 'dst').exists()
    assert {p: p.read_bytes() for p in src.rglob('*.md')} == before
    assert (work / 'staged-candidates.json').is_file()
    assert (work / 'scored-candidates.json').is_file()
    assert not (work / 'dream-ledger.json').exists()
    assert r['counts']['promoted_orphan_links'] == 1
    assert r['threshold_overrides_applied'] == PROMOTE_OVERRIDES_V1
    assert r['threshold_override_note']


def test_apply_requires_trigger_and_dst(tmp_path):
    src = tmp_path / 'src'
    _corpus_with_orphan(src)
    with pytest.raises(ValueError):
        mv.dream_v1(src, None, apply=True)
    with pytest.raises(ValueError):
        mv.dream_v1(src, src, apply=True)
    with pytest.raises(ValueError):
        mv.dream_v1(src, tmp_path / 'dst', apply=True,
                    state={'sessions_since_last_dream': 0, 'pages_changed_since_last_dream': 0,
                           'last_dream_session': 's0'}, session_id='s1')
    assert not (tmp_path / 'dst').exists()


def test_apply_promotes_integrates_orphan_preserves_facts(tmp_path):
    src = tmp_path / 'src'
    _corpus_with_orphan(src)
    work, dst = tmp_path / 'work', tmp_path / 'dst'
    in_hashes = hashes_under(src)
    r = mv.dream_v1(src, dst, work, apply=True, session_id='s1',
                    gate_overrides=PROMOTE_OVERRIDES_V1)
    assert r['dry_run'] is False and r['fact_preservation']['ok'] is True
    assert '[[orph]]' in (dst / 'memory' / 'hub.md').read_text()
    assert 'dreaming v1' in (dst / 'memory' / 'hub.md').read_text()
    assert (dst / 'MEMORY.md').read_bytes() == (src / 'MEMORY.md').read_bytes()
    out_hashes = hashes_under(dst)
    assert in_hashes <= out_hashes | {m['before_sha256'] for m in r['output']['mutated']}
    after = r['hygiene']['after']
    assert after['orphan_count'] == r['hygiene']['before']['orphan_count'] - 1
    ledger = json.loads((work / 'dream-ledger.json').read_text())
    assert ledger['promoted_orphan_links'] == ['memory/orph.md <- memory/hub.md']
    r2 = mv.dream_v1(dst, tmp_path / 'dst2', apply=True, session_id='s2',
                     gate_overrides=PROMOTE_OVERRIDES_V1)
    assert r2['counts']['promoted_orphan_links'] == 0             # idempotent
    assert r2['output']['root_sha256'] == r['output']['root_sha256']


def test_edge_promotes_to_ledger_never_corpus_v1(tmp_path):
    src = tmp_path / 'src'
    for rel, body, mod in EDGE_PAGES:
        write_page(src, rel, body, mod)
    work, dst = tmp_path / 'work', tmp_path / 'dst'
    r = mv.dream_v1(src, dst, work, apply=True, session_id='s1',
                    gate_overrides=EDGE_OVERRIDES_V1)  # tiny corpus: scale gates, receipted
    assert r['counts']['promoted_supersedes_edges'] == 1
    assert (dst / 'memory' / 'old.md').read_bytes() == (src / 'memory' / 'old.md').read_bytes()
    assert (dst / 'memory' / 'new.md').read_bytes() == (src / 'memory' / 'new.md').read_bytes()
    ledger = json.loads((work / 'dream-ledger.json').read_text())
    assert len(ledger['promoted_supersedes_edges']) == 1
    assert r['output']['root_sha256'] == mc.corpus_root_hash(
        [pg.sha256 for pg in mc.load_pages(src)])


def test_edge_stance_gate_bites_end_to_end(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'memory/old.md', 'The widget-frob link runs at 1000 Mb/s; the gizmo '
               'switch is the limit.\n', '2026-08-01T00:00:00Z')
    write_page(src, 'memory/new.md', '**Correction 2026-09-01:** the 1000 Mb/s reading of '
               'the widget-frob gizmo link measured throughput again; 5 Gb/s seen.\n',
               '2026-09-01T00:00:00Z')
    r = mv.dream_v1(src, gate_overrides=EDGE_OVERRIDES_V1)
    assert r['counts']['promoted_supersedes_edges'] == 0
    d = [d for d in r['demoted'] if d['kind'] == 'supersedes_edge'][0]
    assert 'G-StanceA' in d['explain']
    # red direction: overriding the stance gate promotes, receipted loudly
    r2 = mv.dream_v1(src, gate_overrides={**EDGE_OVERRIDES_V1, 'edge_require_stance': False})
    assert r2['counts']['promoted_supersedes_edges'] == 1
    assert r2['threshold_overrides_applied'].get('edge_require_stance') is False
    assert r2['threshold_override_note']


def test_determinism_two_dry_runs_identical_v1(tmp_path):
    src = tmp_path / 'src'
    _corpus_with_orphan(src)
    r1 = mv.dream_v1(src, gate_overrides=PROMOTE_OVERRIDES_V1, now='2026-11-10T00:00:00Z')
    r2 = mv.dream_v1(src, gate_overrides=PROMOTE_OVERRIDES_V1, now='2026-11-10T00:00:00Z')
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)


def test_no_candidates_empty_pass_still_receipts_v1(tmp_path):
    src = tmp_path / 'src'
    write_page(src, 'memory/a.md', 'Entirely standalone alpha page.\n', '2026-08-01T00:00:00Z')
    write_page(src, 'memory/b.md', 'Entirely standalone beta page.\n', '2026-08-02T00:00:00Z')
    r = mv.dream_v1(src, tmp_path / 'dst', tmp_path / 'work', apply=True, session_id='s1')
    assert r['counts']['candidates'] == 0
    assert r['fact_preservation']['ok'] is True
    assert r['output']['root_sha256'] == mc.corpus_root_hash(
        [pg.sha256 for pg in mc.load_pages(src)])
