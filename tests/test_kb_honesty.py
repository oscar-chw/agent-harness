"""Public L2 fidelity checks. Original corpus checks are retained in eval/private_reference."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO / "tests/support/v3_research"))
from agent_harness.mcp import kb as kb_mod  # noqa: E402
import l2_rule as l2  # noqa: E402
import hybrid_scorer as hs  # noqa: E402

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
