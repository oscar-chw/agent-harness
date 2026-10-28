"""Bounded memoization of pure short-word stemming, never query/document results."""
from agent_harness.mcp import kb


def test_repeated_short_terms_do_not_repeat_suffix_scanning(monkeypatch):
    suffixes = kb._SUFFIXES
    calls = []
    class Counted:
        def __iter__(self):
            calls.append(1)
            return iter(suffixes)
    monkeypatch.setattr(kb, '_SUFFIXES', Counted())
    if hasattr(kb, '_short_stem'):
        kb._short_stem.cache_clear()
    assert kb.tokens('canaryquiver '*100) == ['canaryquiver']*100
    assert len(calls) == 1


def test_large_terms_are_not_retained_in_the_short_word_cache(monkeypatch):
    suffixes = kb._SUFFIXES
    calls = []
    class Counted:
        def __iter__(self):
            calls.append(1)
            return iter(suffixes)
    monkeypatch.setattr(kb, '_SUFFIXES', Counted())
    long_word = 'q'*4096
    assert kb.tokens(long_word+' '+long_word) == [long_word,long_word]
    assert len(calls) == 2


def test_short_word_cache_is_bounded_and_preserves_normalization():
    cache = getattr(kb, '_short_stem', None)
    assert cache is not None
    cache.cache_clear()
    for i in range(3000):
        assert kb.tokens(f'cachecanary{i}') == [f'cachecanary{i}']
    assert cache.cache_info().currsize <= 1024
    assert kb.tokens('ROTATION rotating configured 日期') == ['rot','rot','configur','日期']
    before = cache.cache_info().currsize
    assert kb.tokens('z'*10000) == ['z'*10000]
    assert cache.cache_info().currsize == before
