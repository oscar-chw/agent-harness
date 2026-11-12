"""H3 node 6 unit tests — pure-python core of the hybrid scorer + evidence rule.

Runs under /usr/bin/python3 (3.9.6, pytest 8.4.2, NO numpy) per the H1/H2/H3
gate convention. Covers: tokenize/stoplist rules, content bigrams (raw
adjacency, both-content), band grouping + ordering, additive scoring, rule L
and L', amendment-1 rule L2 (coverage override), and corpus-stats binding
verification.
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WORK = REPO / '.harness-work' / 'v3-h3-hybrid'
sys.path.insert(0, str(WORK))

import hybrid_scorer as hs  # noqa: E402


# --------------------------------------------------------- tokens / bigrams
def test_content_tokens_filter_stopwords_and_len1():
    assert hs.content_tokens('What is the GPU box in?') == ['gpu', 'box']
    assert hs.content_tokens("the Mac's network") == ['mac', 'network']


def test_content_bigrams_raw_adjacency_both_content():
    # 'the' breaks adjacency: (nas, rack) adjacent, (rack, unit) adjacent,
    # (serial, number) adjacent; pairs crossing stopwords are NOT bigrams.
    assert hs.content_bigrams("What is the NAS rack unit's serial number?") == \
        [('nas', 'rack'), ('rack', 'unit'), ('serial', 'number')]


def test_content_bigrams_empty_when_single_content_token():
    assert hs.content_bigrams('What is replication?') == []


def test_page_bigram_set_matches_query_side():
    page = 'The DIMM serial number 121C8E65 is failing'
    assert ('serial', 'number') in hs.page_bigram_set(page)
    assert ('number', 'serial') not in hs.page_bigram_set(page)  # ordered


# --------------------------------------------------------------- BAND form
def _hits(scores):
    return [{'id': 'p%d.md#top' % i, 'page': 'p%d.md' % i, 'score': s, 'rank': i + 1}
            for i, s in enumerate(scores)]


def test_band_groups_chain_consecutive_gaps():
    hits = _hits([0.50, 0.45, 0.44, 0.20])   # gaps .05, .01 chain; .24 breaks
    groups = hs.band_groups(hits, delta=0.10)
    assert [[h['page'] for h in g] for g in groups] == [['p0.md', 'p1.md', 'p2.md'], ['p3.md']]


def test_band_boundary_gap_exactly_delta_chains():
    hits = _hits([0.50, 0.40])
    assert len(hs.band_groups(hits, delta=0.10)) == 1
    assert len(hs.band_groups(hits, delta=0.099)) == 2


def test_band_rerank_orders_within_group_by_cosine_then_baseline_rank():
    hits = _hits([0.50, 0.45, 0.20])
    cos = {'p0.md': 0.50, 'p1.md': 0.90, 'p2.md': 0.99}
    out = hs.band_rerank(hits, cos, delta=0.10)
    # p0/p1 in one group (gap .05): p1 wins on cosine. p2's group is separate:
    # the 0.25 lexical lead is unbridgeable even with the best cosine.
    assert [h['page'] for h in out] == ['p1.md', 'p0.md', 'p2.md']
    assert [h['h3_rank'] for h in out] == [1, 2, 3]


def test_band_rerank_deterministic_and_never_interleaves_groups():
    hits = _hits([0.90, 0.40, 0.35])
    cos = {'p0.md': 0.10, 'p1.md': 0.99, 'p2.md': 0.98}
    a = hs.band_rerank(hits, cos, delta=0.10)
    b = hs.band_rerank(hits, cos, delta=0.10)
    assert a == b
    assert a[0]['page'] == 'p0.md'   # lexical lead 0.50 unbridgeable


# ---------------------------------------------------------------- ADD form
def test_additive_scoring_and_tie_break():
    hits = _hits([0.50, 0.48, 0.48])
    cos = {'p0.md': 0.50, 'p1.md': 0.80, 'p2.md': 0.80}
    out = hs.additive_rerank(hits, cos, w=0.15)
    assert [h['page'] for h in out] == ['p1.md', 'p2.md', 'p0.md']  # tie -> baseline rank
    assert out[0]['hybrid_score'] == pytest.approx(round(0.48 + 0.15 * 0.80, 6))


def test_additive_bound_caps_semantic_swing():
    # w=0.15: a lexical lead of 0.16 can never be crossed by cosine alone
    hits = _hits([0.66, 0.50])
    cos = {'p0.md': 0.0, 'p1.md': 1.0}
    out = hs.additive_rerank(hits, cos, w=0.15)
    assert out[0]['page'] == 'p0.md'


# -------------------------------------------------------------- evidence rule
def _pages():
    return {'memory/a.md': {('rack', 'unit')}, 'memory/b.md': set()}


def test_rule_L_fires_when_no_bigram_anywhere():
    rep = hs.evidence_report('NAS serial number?', ['memory/a.md', 'memory/b.md'], _pages())
    # ('serial','number') absent from both pages
    assert rep['applicable'] and not rep['any_bigram_present']
    assert hs.rule_L(rep) is True


def test_rule_L_holds_when_any_bigram_present():
    report = hs.evidence_report('the rack unit serial?', ['memory/a.md'], _pages())
    assert ['rack', 'unit'] in report['content_bigrams']
    assert report['matched'] == {'rack unit': ['memory/a.md']}
    assert report['any_bigram_present']
    assert hs.rule_L(report) is False


def test_rule_L_inapplicable_without_bigrams():
    rep = hs.evidence_report('what is replication', ['memory/a.md'], _pages())
    assert rep['applicable'] is False
    assert hs.rule_L(rep) is False


def test_rule_L_prime_lexical_gate():
    rep = hs.evidence_report('NAS serial number?', ['memory/a.md'], _pages())
    assert hs.rule_L_prime(rep, 0.29) is True
    assert hs.rule_L_prime(rep, 0.30) is False   # gate is strict <


# ------------------------------------------- amendment-1 refinement (rule L2)
def test_max_coverage_best_over_candidates():
    # query content tokens: {gpu, rack, serial}; page a has 2/3, page b has 3/3
    q = 'gpu rack serial?'
    cov = hs.max_coverage(q, [{'gpu', 'rack'}, {'gpu', 'rack', 'serial'}])
    assert cov == pytest.approx(1.0)
    assert hs.max_coverage(q, [{'gpu', 'rack'}]) == pytest.approx(2 / 3)
    assert hs.max_coverage(q, []) == 0.0
    assert hs.max_coverage('what is the', [{'gpu'}]) == 0.0   # no content tokens


def test_rule_L2_full_coverage_overrides_L():
    # L fires (bigram absent) but some candidate holds ALL query content
    # tokens -> the paraphrase override stays L2's hand (the b1/b3/e1 case).
    rep = hs.evidence_report('machine hosts research vms?', ['memory/a.md'], _pages())
    assert hs.rule_L(rep) is True
    assert hs.rule_L2(rep, 1.0) is False


def test_rule_L2_fires_below_full_coverage():
    # f1-shaped: L fires and best coverage 0.60 < 1.0 -> L2 fires.
    rep = hs.evidence_report('NAS serial number?', ['memory/a.md'], _pages())
    assert hs.rule_L2(rep, 0.60) is True
    assert hs.rule_L2(rep, 0.999999) is True


def test_rule_L2_never_fires_without_L():
    rep = hs.evidence_report('the rack unit serial?', ['memory/a.md'], _pages())
    assert hs.rule_L(rep) is False
    assert hs.rule_L2(rep, 0.0) is False


def test_stats_string_bigrams_roundtrip_to_tuples():
    """Regression: the stats artifact stores bigrams as strings; evidence
    matching must compare tuples. (First H3 eval run compared tuples to
    strings — rule L matched nothing and over-fired on every query.)"""
    entry = {'bigrams': ['rack unit', 'gpu box']}
    converted = hs.stats_bigrams_to_tuples(entry)
    assert converted == {('rack', 'unit'), ('gpu', 'box')}
    rep = hs.evidence_report('the rack unit?', ['memory/a.md'], {'memory/a.md': converted})
    assert rep['any_bigram_present'] and hs.rule_L(rep) is False


# ------------------------------------------------------------- stats binding
def _freeze_doc():
    return {'corpus': {'corpus_sha256': 'c0ffee',
                       'pages': [{'path': 'memory/a.md', 'sha256': 'aaa', 'bytes': 1},
                                 {'path': 'memory/b.md', 'sha256': 'bbb', 'bytes': 1}]}}


def _stats():
    return {'binding': {'corpus_sha256': 'c0ffee', 'stoplist': sorted(hs.STOPLIST)},
            'pages': {'memory/a.md': {'page_sha256': 'aaa', 'n_tokens': 3, 'bigrams': ['x y']},
                      'memory/b.md': {'page_sha256': 'bbb', 'n_tokens': 2, 'bigrams': []}}}


def test_stats_binding_clean():
    assert hs.verify_stats_binding(_stats(), _freeze_doc()) == []


def test_stats_binding_refuses_tampered_page_hash():
    stats = _stats()
    stats['pages']['memory/a.md']['page_sha256'] = 'tampered'
    assert any('memory/a.md' in p for p in hs.verify_stats_binding(stats, _freeze_doc()))


def test_stats_binding_refuses_page_set_and_stoplist_drift():
    stats = _stats()
    del stats['pages']['memory/b.md']
    assert any('page set' in p for p in hs.verify_stats_binding(stats, _freeze_doc()))
    stats2 = _stats()
    stats2['binding']['stoplist'] = ['the']
    assert any('stoplist' in p for p in hs.verify_stats_binding(stats2, _freeze_doc()))


def test_module_imports_without_numpy():
    assert 'numpy' not in sys.modules
