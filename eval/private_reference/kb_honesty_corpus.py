"""H6a node 8 integration tests — the opt-in L2 honesty layer in kb.py.

Gate contract (AT-4, pre-registered):
  1. flag OFF (HARNESS_KB_HONESTY unset): results byte-identical to the
     recorded candidates for all 33 queries (15 fresh + frozen 18) over the
     frozen-corpus copy; the honesty maps are never built.
  2. flag ON: suppression per query == the recorded L2 outcomes exactly
     (fresh-set artifact for the 15, H3 eval artifact for the 18) — this is
     also the fidelity proof that section-reassembled page evidence matches
     the eval's raw-page evidence on every query.
  3. flag ON, non-firing queries: results byte-identical to flag OFF.
  4. embedded rule constants == the frozen eval module (stoplist, tokenizer,
     window).

Runs under /usr/bin/python3 (no numpy). Env var handled via monkeypatch;
each test builds its own KB over the H6a frozen-corpus copy with a tmp db.
"""
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(os.environ.get('HARNESS_RESEARCH_ROOT', Path(__file__).resolve().parents[2]))
WORK = REPO / '.harness-work' / 'v3-h6a-l2-candidacy'
H3 = REPO / '.harness-work' / 'v3-h3-hybrid'
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(WORK))
sys.path.insert(0, str(H3))

from agent_harness.mcp import kb as kb_mod                  # noqa: E402
import l2_rule as l2                                       # noqa: E402
import hybrid_scorer as hs                                 # noqa: E402

SNAP = WORK / 'frozen-corpus'
FRESH = json.loads((WORK / 'fresh-queries-20261110.json').read_text())
H3_ART = json.loads((H3 / 'eval-h3-20261110.json').read_text())

# (query_id, text, recorded candidates, recorded L2 outcome) for all 33
CASES = (
    [(q['id'], q['text'], q['design']['baseline_candidates'], q['design']['rule_L2'])
     for q in FRESH['queries']]
    + [(r['id'], r['text'],
        [{'rank': c['rank'], 'page': c['page'], 'score': c['score']} for c in r['candidates']],
        r['rule_L2']['miss'])
       for r in H3_ART['results']]
)


def _kb(tmp_path, name):
    return kb_mod.KB(home=tmp_path / name, paths=[SNAP / 'memory'],
                     db_path=tmp_path / name / 'index.sqlite')


def _pairs(hits):
    return [{'rank': i + 1, 'page': h['path'], 'score': h['score']}
            for i, h in enumerate(hits)]


@pytest.fixture(autouse=True)
def _no_honesty_env(monkeypatch):
    monkeypatch.delenv('HARNESS_KB_HONESTY', raising=False)


# ------------------------------------------------------------ AT-4.1 flag OFF
def test_flag_off_byte_identical_to_recorded(tmp_path):
    kb = _kb(tmp_path, 'off')
    try:
        for qid, text, recorded, _ in CASES:
            assert _pairs(kb.search(text, k=10)) == recorded, qid
        assert kb._honesty_maps is None     # flag off = the maps are never built
    finally:
        kb.close()


def test_flag_off_unset_and_empty_and_false_all_inactive(tmp_path):
    kb = _kb(tmp_path, 'off2')
    try:
        for val in (None, '', '0', 'false', 'no'):
            if val is None:
                os.environ.pop('HARNESS_KB_HONESTY', None)
            else:
                os.environ['HARNESS_KB_HONESTY'] = val
            assert kb_mod._honesty_enabled() is False
    finally:
        os.environ.pop('HARNESS_KB_HONESTY', None)
        kb.close()


# ------------------------------------------------------------- AT-4.2 flag ON
def test_flag_on_suppression_matches_recorded_outcomes(tmp_path, monkeypatch):
    monkeypatch.setenv('HARNESS_KB_HONESTY', '1')
    kb = _kb(tmp_path, 'on')
    try:
        for qid, text, _, expected_miss in CASES:
            hits = kb.search(text, k=10)
            assert (hits == []) == expected_miss, \
                '%s: suppression %s != recorded %s' % (qid, hits == [], expected_miss)
        assert kb._honesty_maps is not None
    finally:
        kb.close()


def test_flag_on_nonfiring_byte_identical_to_flag_off(tmp_path, monkeypatch):
    kb_off = _kb(tmp_path, 'off3')
    try:
        baseline = {qid: kb_off.search(text, k=10)
                    for qid, text, _, miss in CASES if not miss}
    finally:
        kb_off.close()
    monkeypatch.setenv('HARNESS_KB_HONESTY', '1')
    kb_on = _kb(tmp_path, 'on3')
    try:
        for qid, text, _, miss in CASES:
            if miss:
                continue
            assert kb_on.search(text, k=10) == baseline[qid], qid
    finally:
        kb_on.close()


def test_flag_on_boundary_cases(tmp_path, monkeypatch):
    """The three pre-registered boundary outcomes, named explicitly."""
    monkeypatch.setenv('HARNESS_KB_HONESTY', '1')
    kb = _kb(tmp_path, 'onx')
    try:
        by_id = {qid: text for qid, text, _, _ in CASES}
        assert kb.search(by_id['x1'], k=10) == []        # answerable, cov 0.75 -> suppressed
        assert kb.search(by_id['x2'], k=10) != []        # negative, cov 1.00 -> escapes
        assert kb.search(by_id['x3'], k=10) != []        # negative, bigram leg -> escapes
        assert kb.search(by_id['n1'], k=10) == []        # negative, cov 0.67 -> suppressed
        assert kb.search(by_id['p1'], k=10) != []        # paraphrase, cov 1.00 -> kept
    finally:
        kb.close()


# ------------------------------------------------- AT-4.4 frozen constants
def test_embedded_rule_constants_equal_frozen_eval_module():
    assert kb_mod._L2_STOPLIST == l2.STOPLIST == hs.STOPLIST
    assert kb_mod._L2_WORD.pattern == l2.WORD.pattern == hs.WORD.pattern
    assert kb_mod._L2_MIN_TOKEN_LEN == l2.MIN_TOKEN_LEN
    assert kb_mod.HONESTY_WINDOW == 10


def test_embedded_rule_functions_match_eval_module():
    texts = ['What is the hddpool pool GUID?', 'Which drives are failing outside the pool?',
             'Quirky zigzag jubilee tokens']
    for t in texts:
        assert kb_mod._l2_content_tokens(t) == l2.content_tokens(t)
        assert kb_mod._l2_content_bigrams(t) == l2.content_bigrams(t)


# ------------------------------------------------- window is load-bearing
def test_honesty_window_distinct_pages_of_top10_sections():
    """The evaluated window must be exactly the validated one: distinct pages
    of the top-10 scored sections (a section-rich page occupies multiple
    window slots, as in the H3/H6a eval)."""
    src = inspect_source(kb_mod.KB._honest_miss)
    assert 'HONESTY_WINDOW' not in src     # window selection happens in search()
    search_src = inspect_source(kb_mod.KB.search)
    assert 'nsmallest(HONESTY_WINDOW' in search_src.replace('heapq.', '')


def inspect_source(obj):
    import inspect
    return inspect.getsource(obj)
