"""H2 node 6 unit tests — numpy-free core of the semantic rerank eval path.

Runs under /usr/bin/python3 (3.9.6, pytest 8.4.2, NO numpy) per the H1/H2
gate convention: the module under test keeps its numpy parts lazy, so the
pure core (tokenize / mean-pool / cosine / rerank ordering / miss rule /
frozen class rules / cache binding verification) is fully testable here.
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WORK = REPO / 'tests/support/v3_research'
sys.path.insert(0, str(WORK))

import semantic_rerank as sr  # noqa: E402


# ---------------------------------------------------------------- tokenize
def test_tokenize_lowercases_and_splits():
    assert sr.tokenize('Hello, World! foo-bar RTX6000') == \
        ['hello', 'world', 'foo', 'bar', 'rtx6000']


def test_tokenize_digits_kept():
    assert sr.tokenize('10gbase-t over cat6a') == ['10gbase', 't', 'over', 'cat6a']


def test_tokenize_empty():
    assert sr.tokenize('') == []
    assert sr.tokenize('—…—') == []


# ------------------------------------------------------------- mean pooling
def test_mean_pool_pure_known_value():
    vecs = {'a': [1.0, 0.0], 'b': [0.0, 2.0]}
    pooled, oov = sr.mean_pool_pure(['a', 'b'], vecs)
    assert oov == 0
    assert pooled == [0.5, 1.0]


def test_mean_pool_skips_and_counts_oov():
    vecs = {'a': [1.0, 1.0]}
    pooled, oov = sr.mean_pool_pure(['a', 'zzqxit', 'zzqxit'], vecs)
    assert oov == 2
    assert pooled == [1.0, 1.0]


def test_mean_pool_all_oov_is_none():
    pooled, oov = sr.mean_pool_pure(['zzqxit'], {})
    assert pooled is None
    assert oov == 1


# ------------------------------------------------------------------ cosine
def test_cosine_pure_known_values():
    assert sr.cosine_pure([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert sr.cosine_pure([1.0, 2.0], [1.0, 2.0]) == pytest.approx(1.0)
    assert sr.cosine_pure([1.0, 0.0], [2.0, 0.0]) == pytest.approx(1.0)
    assert sr.cosine_pure([0.0, 0.0], [1.0, 0.0]) == 0.0
    assert sr.cosine_pure(None, [1.0]) == 0.0


# ---------------------------------------------------------------- reranking
def _hits():
    return [
        {'id': 'p1.md#top', 'page': 'p1.md', 'score': 0.9, 'rank': 1},
        {'id': 'p2.md#top', 'page': 'p2.md', 'score': 0.8, 'rank': 2},
        {'id': 'p3.md#top', 'page': 'p3.md', 'score': 0.7, 'rank': 3},
        {'id': 'p1.md#s2', 'page': 'p1.md', 'score': 0.6, 'rank': 4},
    ]


def test_rerank_orders_by_cosine_then_baseline_rank():
    cos = {'p1.md': 0.40, 'p2.md': 0.90, 'p3.md': 0.90}
    out = sr.rerank_hits(_hits(), cos)
    # p2 and p3 tie on cosine -> baseline rank breaks the tie (2 < 3)
    assert [h['page'] for h in out] == ['p2.md', 'p3.md', 'p1.md', 'p1.md']
    assert [h['rerank_rank'] for h in out] == [1, 2, 3, 4]
    assert out[0]['cosine'] == 0.90


def test_rerank_is_deterministic():
    cos = {'p1.md': 0.5, 'p2.md': 0.5, 'p3.md': 0.5}
    a = sr.rerank_hits(_hits(), cos)
    b = sr.rerank_hits(_hits(), cos)
    assert a == b
    # all ties -> baseline order preserved exactly
    assert [h['rank'] for h in a] == [1, 2, 3, 4]


def test_rerank_missing_page_scores_zero():
    out = sr.rerank_hits([{'id': 'x.md#top', 'page': 'x.md', 'score': 0.5, 'rank': 1}], {})
    assert out[0]['cosine'] == 0.0


# --------------------------------------------------------------- miss rule
def test_miss_rule_suppresses_below_tau():
    ranked = [{'page': 'p1.md', 'cosine': 0.49, 'rerank_rank': 1},
              {'page': 'p2.md', 'cosine': 0.20, 'rerank_rank': 2}]
    reported, miss, top = sr.apply_miss_rule(ranked, tau=0.50)
    assert reported == [] and miss is True and top == 0.49


def test_miss_rule_keeps_at_tau():
    ranked = [{'page': 'p1.md', 'cosine': 0.50, 'rerank_rank': 1}]
    reported, miss, top = sr.apply_miss_rule(ranked, tau=0.50)
    assert len(reported) == 1 and miss is False and top == 0.50


def test_miss_rule_empty_input_is_miss():
    reported, miss, top = sr.apply_miss_rule([], tau=0.50)
    assert reported == [] and miss is True and top is None


def test_page_ranks_first_occurrence():
    ranked = [{'page': 'p1.md', 'rerank_rank': 1}, {'page': 'p2.md', 'rerank_rank': 2},
              {'page': 'p1.md', 'rerank_rank': 3}]
    assert sr.page_ranks(ranked) == {'p1.md': 1, 'p2.md': 2}


# -------------------------------------------------------- frozen class rules
def _q(cls, pages, k=5, **kw):
    q = {'class': cls, 'expected_pages': pages, 'pass_rule': {'k': k}}
    q.update(kw)
    return q


def test_class_a_top3_rule():
    q = _q('A', ['p1.md'], k=3)
    assert sr.class_pass(q, {'p1.md': 3}, [{'page': 'p1.md'}])['pass'] is True
    assert sr.class_pass(q, {'p1.md': 4}, [{'page': 'p1.md'}])['pass'] is False
    assert sr.class_pass(q, {}, [])['pass'] is False  # suppressed = miss = fail


def test_class_b_top5_boundary():
    q = _q('B', ['p1.md'], k=5)
    assert sr.class_pass(q, {'p1.md': 5}, [{}])['pass'] is True
    assert sr.class_pass(q, {'p1.md': 6}, [{}])['pass'] is False


def test_class_e_successor_above_superseded():
    q = _q('E', ['new.md'], successor='new.md', superseded='old.md')
    assert sr.class_pass(q, {'new.md': 1, 'old.md': 9}, [{}])['pass'] is True
    assert sr.class_pass(q, {'new.md': 5, 'old.md': 2}, [{}])['pass'] is False
    assert sr.class_pass(q, {'new.md': 3}, [{}])['pass'] is True  # superseded absent


def test_class_f_honest_miss():
    q = _q('F', [])
    assert sr.class_pass(q, {}, [])['pass'] is True
    assert sr.class_pass(q, {'p1.md': 1}, [{'page': 'p1.md'}])['pass'] is False


def test_answerable_query_suppressed_by_miss_rule_fails():
    """A suppressed answer is a reported miss — it cannot pass A–E even when the
    rerank ranking itself was correct."""
    q = _q('A', ['p1.md'], k=3)
    out = sr.class_pass(q, {'p1.md': 1}, [])
    assert out['pass'] is False
    assert out['detail']['suppressed_by_miss_rule'] is True


# ----------------------------------------------------- cache binding verify
def _freeze_doc():
    return {'corpus': {'corpus_sha256': 'c0ffee',
                       'pages': [{'path': 'memory/a.md', 'sha256': 'aaa', 'bytes': 1},
                                 {'path': 'memory/b.md', 'sha256': 'bbb', 'bytes': 1}]}}


def _cache():
    return {'binding': {'glove_sha256': 'g1', 'corpus_sha256': 'c0ffee',
                        'freeze_json_sha256': 'f1', 'contract_sha256': 'ct1'},
            'pages': {'memory/a.md': {'page_sha256': 'aaa', 'vector': [0.0] * 100},
                      'memory/b.md': {'page_sha256': 'bbb', 'vector': [0.0] * 100}}}


def test_binding_clean():
    assert sr.verify_cache_binding(_cache(), _freeze_doc(), 'g1', 'f1', 'ct1') == []


def test_binding_refuses_tampered_page_hash():
    cache = _cache()
    cache['pages']['memory/a.md']['page_sha256'] = 'tampered'
    problems = sr.verify_cache_binding(cache, _freeze_doc(), 'g1', 'f1', 'ct1')
    assert any('memory/a.md' in p for p in problems)


def test_binding_refuses_wrong_glove_hash():
    problems = sr.verify_cache_binding(_cache(), _freeze_doc(), 'WRONG', 'f1', 'ct1')
    assert any('glove' in p for p in problems)


def test_binding_refuses_missing_and_extra_pages_and_bad_dim():
    cache = _cache()
    del cache['pages']['memory/b.md']
    cache['pages']['memory/rogue.md'] = {'page_sha256': 'x', 'vector': [0.0] * 3}
    problems = sr.verify_cache_binding(cache, _freeze_doc(), 'g1', 'f1', 'ct1')
    assert any('page set' in p for p in problems)
    assert any('dim' in p for p in problems)


def test_binding_refuses_contract_drift():
    problems = sr.verify_cache_binding(_cache(), _freeze_doc(), 'g1', 'f1', 'ct2')
    assert any('contract' in p for p in problems)


def test_module_imports_without_numpy():
    """The pure core must not need numpy (the /usr/bin/python3 gate has none)."""
    assert 'numpy' not in sys.modules or sr.cosine_pure([1.0], [1.0]) == pytest.approx(1.0)
