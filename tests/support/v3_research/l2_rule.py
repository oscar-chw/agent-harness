"""H6a — FROZEN L2 rule, byte-copied from H3's hybrid_scorer.py.

PROVENANCE: every top-level definition below is a verbatim copy of the
same-named object in .harness-work/v3-h3-hybrid/hybrid_scorer.py (the module
whose sha256 is bound into the H3 eval artifact 18d4fe09…). tests/test_h6a_l2
_candidacy.py proves the copy byte-exact per object (inspect.getsource
equality); any edit here invalidates the H3 confirmation this candidacy rests
on. The rule parameters are FROZEN: stoplist, tokenizer, bigram adjacency,
coverage statistic, threshold 1.0. Pure stdlib, numpy-free.
"""
import re

WORD = re.compile(r'[a-z0-9]+')

STOPLIST = frozenset('''
a an the is are was were be been being do does did have has had having
i you he she it we they me him her us them my your his its our their
what which who whom when where why how
should would can could may might must shall will ought
to of in on at for with by from about between into over under
and or but not no nor any all both each this that these those there here
than then so such as if while because until again once just also very
isn aren wasn weren don doesn didn won wouldn couldn shouldn hasn haven
s t d ll re ve m o
'''.split())

MIN_TOKEN_LEN = 2

def tokenize(text):
    return WORD.findall(text.lower())

def content_tokens(text):
    return [t for t in tokenize(text)
            if len(t) >= MIN_TOKEN_LEN and t not in STOPLIST]

def content_bigrams(text):
    """Ordered ADJACENT raw-token pairs where both tokens are content tokens.

    Adjacency is in the raw token stream (order preserved) — a bigram is the
    query's compound phrase evidence, e.g. ('serial','number').
    """
    toks = tokenize(text)
    out = []
    for a, b in zip(toks, toks[1:]):
        if (len(a) >= MIN_TOKEN_LEN and len(b) >= MIN_TOKEN_LEN
                and a not in STOPLIST and b not in STOPLIST):
            out.append((a, b))
    return out

def page_bigram_set(text):
    """The set of adjacent both-content token pairs in a page (same rule as
    the query side, so membership tests are symmetric)."""
    return set(content_bigrams(text))

def evidence_report(query_text, candidate_pages, page_bigrams):
    """Rule L inputs. page_bigrams: page -> bigram set. Returns the evidence
    matrix row: the query's content bigrams, which appear in which candidate
    page, and the rule outcomes."""
    bigrams = content_bigrams(query_text)
    matched = {}
    for bg in bigrams:
        for p in candidate_pages:
            if bg in page_bigrams.get(p, set()):
                matched.setdefault(bg, []).append(p)
    missing = [bg for bg in bigrams if bg not in matched]
    return {'content_bigrams': [list(b) for b in bigrams],
            'n_content_bigrams': len(bigrams),
            'applicable': len(bigrams) > 0,
            'matched': {'%s %s' % b: v for b, v in matched.items()},
            'missing': ['%s %s' % b for b in missing],
            'any_bigram_present': len(matched) > 0}

def rule_L(report):
    """Honest miss iff the rule applies and NO content bigram appears in ANY
    candidate page."""
    return bool(report['applicable'] and not report['any_bigram_present'])

def max_coverage(query_text, candidate_token_sets):
    """Best content-token coverage over the query's candidates.

    coverage(page) = |Q ∩ P| / |Q| where Q = DISTINCT query content tokens,
    P = the page's content-token set. Returns 0.0 when there are no
    candidates or the query has no content tokens (rule L2 is then decided
    by rule_L alone; coverage cannot rescue an empty candidate set).
    """
    q = set(content_tokens(query_text))
    if not q or not candidate_token_sets:
        return 0.0
    best = 0.0
    for tokens in candidate_token_sets:
        cov = len(q & tokens) / len(q)
        if cov > best:
            best = cov
    return best

def rule_L2(report, best_cov):
    """Amendment-1 refinement (pre-registered 2026-11-10 before any L2 run):
    honest miss iff rule_L fires AND best candidate content-token coverage
    is < 1.0 — a lexically COMPLETE candidate (paraphrase explanation
    available) overrides the missing-bigram signal."""
    return bool(rule_L(report) and best_cov < 1.0)
