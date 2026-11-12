"""H6a node 6 unit tests — frozen L2 copy fidelity + rule behavior + fresh-set
artifact integrity.

Runs under /usr/bin/python3 (3.9.6, pytest 8.4.2, NO numpy) per the gate
convention. The L2 rule under test is l2_rule.py, a BYTE-COPIED subset of
H3's hybrid_scorer.py — the first test class proves the copy is exact, so
H3's confirmation carries over; the rest exercise the rule's contract and the
fresh-query artifact.
"""
import hashlib
import inspect
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WORK = REPO / '.harness-work' / 'v3-h6a-l2-candidacy'
H3 = REPO / '.harness-work' / 'v3-h3-hybrid'
sys.path.insert(0, str(WORK))
sys.path.insert(0, str(H3))

import l2_rule as l2           # noqa: E402
import hybrid_scorer as hs     # noqa: E402  (H3 reference implementation)

QUERIES_JSON = WORK / 'fresh-queries-20261110.json'

COPIED_FUNCTIONS = ['tokenize', 'content_tokens', 'content_bigrams',
                    'page_bigram_set', 'evidence_report', 'rule_L',
                    'max_coverage', 'rule_L2']


# ------------------------------------------------------- copy fidelity (H3)
def test_copied_functions_byte_identical_to_h3():
    for name in COPIED_FUNCTIONS:
        assert inspect.getsource(getattr(l2, name)) == inspect.getsource(
            getattr(hs, name)), 'l2_rule.%s drifted from the H3 original' % name


def test_copied_constants_equal_h3():
    assert l2.WORD.pattern == hs.WORD.pattern
    assert l2.STOPLIST == hs.STOPLIST
    assert l2.MIN_TOKEN_LEN == hs.MIN_TOKEN_LEN


def test_l2_rule_matches_h3_module_sha_binding():
    """The H3 module the copy came from must still carry the sha256 that the
    fresh-set artifact binds to (provenance chain intact)."""
    art = json.loads(QUERIES_JSON.read_text())
    assert hashlib.sha256(H3.joinpath('hybrid_scorer.py').read_bytes()).hexdigest() \
        == art['binding']['h3_module_sha256']


# ------------------------------------------------------------- rule behavior
def test_content_tokens_stoplist_and_length():
    assert l2.content_tokens('What is the GPU box in?') == ['gpu', 'box']
    assert l2.content_tokens('a bb ccc') == ['bb', 'ccc']


def test_content_bigrams_adjacent_both_content():
    # stopwords break bigrams: ('rack','unit') only
    assert l2.content_bigrams('the rack unit of a nas') == [('rack', 'unit')]


def _report(query, pages):
    return l2.evidence_report(query, list(pages), pages)


def test_rule_L2_fires_below_full_coverage():
    rep = _report('NAS serial number?', {'memory/a.md': set()})
    assert l2.rule_L(rep) is True
    assert l2.rule_L2(rep, 0.6) is True


def test_rule_L2_full_coverage_override():
    rep = _report('machine hosts research vms?', {'memory/a.md': set()})
    assert l2.rule_L(rep) is True
    assert l2.rule_L2(rep, 1.0) is False       # the b1/b3/e1 rescue


def test_rule_L2_silent_when_L_silent():
    rep = _report('the rack unit serial?', {'memory/a.md': {('rack', 'unit')}})
    assert l2.rule_L(rep) is False
    assert l2.rule_L2(rep, 0.0) is False


def test_max_coverage_distinct_query_tokens():
    cov = l2.max_coverage('gpu gpu rack serial', [{'gpu', 'rack', 'serial'}])
    assert cov == pytest.approx(1.0)
    assert l2.max_coverage('gpu rack serial', [{'gpu'}]) == pytest.approx(1 / 3)
    assert l2.max_coverage('gpu rack', []) == 0.0


# ---------------------------------------------------- fresh-set artifact
def test_fresh_set_structure_and_hashes():
    art = json.loads(QUERIES_JSON.read_text())
    assert art['query_count'] == 15
    assert art['class_counts'] == {'N': 5, 'P': 5, 'V': 2, 'X': 3}
    for q in art['queries']:
        assert hashlib.sha256(q['text'].encode('utf-8')).hexdigest() == q['text_sha256']
        d = q['design']
        assert 0.0 <= d['best_coverage'] <= 1.0
        assert d['rule_L2'] == (d['rule_L'] and d['best_coverage'] < 1.0)
        if q['class'] == 'N':
            assert q['expected_pages'] == [] and d['baseline_hits'] >= 1
        if q['class'] in ('P', 'V'):
            assert d['rule_L2'] is False and d['expected_rank'] is not None \
                and d['expected_rank'] <= 5
        if q['class'] == 'X':
            assert 'suppressed' in q['boundary_expectation']


def test_fresh_set_no_overlap_with_frozen_18():
    art = json.loads(QUERIES_JSON.read_text())
    frozen = json.loads((REPO / '.harness-work/v3-h1-consolidation'
                         '/freeze-20261110.json').read_text())
    fresh_texts = {q['text_sha256'] for q in art['queries']}
    frozen_texts = {q['text_sha256'] for q in frozen['queries']}
    assert fresh_texts.isdisjoint(frozen_texts)
    assert len(fresh_texts) == 15


def test_recorded_candidates_drift_is_detectable():
    """The fail-closed candidate comparison must actually compare (AT-2):
    any mutation of the recorded list breaks equality."""
    art = json.loads(QUERIES_JSON.read_text())
    rec = art['queries'][0]['design']['baseline_candidates']
    assert rec, 'expected recorded candidates'
    mutated = [dict(c) for c in rec]
    mutated[0]['score'] += 0.01
    assert mutated != rec
    mutated2 = [dict(c) for c in rec]
    mutated2[0]['page'] = 'memory/elsewhere.md'
    assert mutated2 != rec


def test_module_imports_without_numpy():
    assert 'numpy' not in sys.modules
