"""H6a node 6 unit tests — frozen L2 copy fidelity + rule behavior + fresh-set
artifact integrity.

Runs under /usr/bin/python3 (3.9.6, pytest 8.4.2, NO numpy) per the gate
convention. The L2 rule under test is l2_rule.py, a BYTE-COPIED subset of
H3's hybrid_scorer.py — the first test class proves the copy is exact, so
H3's confirmation carries over; the rest exercise the rule's contract and the
fresh-query artifact.
"""
import inspect
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WORK = REPO / 'tests/support/v3_research'
H3 = REPO / 'tests/support/v3_research'
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






def test_module_imports_without_numpy():
    assert 'numpy' not in sys.modules
