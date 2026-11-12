"""H3 node 6 — hybrid scoring + lexical-evidence rule (EVAL tooling, not production).

Contract: docs/v3/h3-hybrid-contract-20261110.md (pre-registered).
  BAND(delta): consecutive lexical gaps <= delta chain into tie groups; within
               a group order by (-cosine, baseline_rank); groups never
               interleave. A lexical lead > delta is unbridgeable.
  ADD(w):      score' = lex + w*cosine; order by (-score', baseline_rank).
  Rule L:      no query content bigram in ANY candidate page -> honest miss.
  Rule L':     L, only when top lexical score < 0.30 (diagnostic).
  Rule L2:     L AND best candidate content-token coverage < 1.0
               (contract amendment 1, pre-registered after L's failure,
               before any L2 run).

Pure stdlib — importable and testable under /usr/bin/python3 (no numpy).
"""
import hashlib
import re

WORD = re.compile(r'[a-z0-9]+')

# Pre-registered stoplist (question words, auxiliaries, function words,
# contractions split by the tokenizer). Fixed in the H3 contract; the sorted
# list is embedded in corpus-stats-20261110.json for audit.
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
DELTA_BAND = 0.10          # pre-registered BAND bound
W_ADD = 0.15               # pre-registered ADD bound
LPRIME_LEX_GATE = 0.30     # pre-registered L' lexical gate


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


def stats_bigrams_to_tuples(entry):
    """Convert a corpus-stats page entry's JSON-friendly string list
    ('rack unit') back to the tuple sets evidence_report compares against.
    The stats artifact stores strings; the rule compares tuples — this loader
    is the ONLY sanctioned conversion (regression-tested: H3's first eval run
    compared tuples against strings and rule L over-fired on everything)."""
    return set(tuple(b.split(' ', 1)) for b in entry.get('bigrams', []))


# ------------------------------------------------------------------ H3a forms
def band_groups(hits, delta=DELTA_BAND):
    """Maximal chains of hits (baseline lexical order, scores desc) whose
    consecutive score gaps are <= delta. Returns list of groups (lists)."""
    groups = []
    for h in hits:
        if groups and groups[-1][-1]['score'] - h['score'] <= delta:
            groups[-1].append(h)
        else:
            groups.append([h])
    return groups


def band_rerank(hits, page_cosine, delta=DELTA_BAND):
    """Order: groups keep lexical order; within a group, (-cosine, baseline rank).
    A lexical lead > delta is unbridgeable. Deterministic."""
    out = []
    for group in band_groups(hits, delta):
        out.extend(sorted(group, key=lambda h: (-page_cosine.get(h['page'], 0.0), h['rank'])))
    return [dict(h, cosine=round(page_cosine.get(h['page'], 0.0), 6), h3_rank=i + 1)
            for i, h in enumerate(out)]


def additive_rerank(hits, page_cosine, w=W_ADD):
    """score' = lex + w*cosine (6dp); order by (-score', baseline rank)."""
    scored = [(h, round(h['score'] + w * page_cosine.get(h['page'], 0.0), 6)) for h in hits]
    scored.sort(key=lambda hs: (-hs[1], hs[0]['rank']))
    return [dict(h, cosine=round(page_cosine.get(h['page'], 0.0), 6),
                 hybrid_score=s, h3_rank=i + 1)
            for i, (h, s) in enumerate(scored)]


# ------------------------------------------------------------- H3b evidence
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


def rule_L_prime(report, top_lexical_score, gate=LPRIME_LEX_GATE):
    """Diagnostic: L gated on weak lexical evidence."""
    return bool(top_lexical_score < gate and rule_L(report))


# ------------------------------------------------- amendment-1 refinement (L2)
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


# --------------------------------------------------------------- binding check
def verify_stats_binding(stats, freeze_doc):
    """Stdlib binding verification of corpus-stats against the freeze.
    Returns a list of problems ([] == bound)."""
    problems = []
    b = stats.get('binding', {})
    if b.get('corpus_sha256') != freeze_doc['corpus']['corpus_sha256']:
        problems.append('stats corpus sha256 mismatch')
    freeze_pages = {r['path']: r['sha256'] for r in freeze_doc['corpus']['pages']}
    pages = stats.get('pages', {})
    missing = sorted(set(freeze_pages) - set(pages))
    extra = sorted(set(pages) - set(freeze_pages))
    if missing or extra:
        problems.append('stats page set != freeze page set (missing=%d extra=%d)'
                        % (len(missing), len(extra)))
    for rel, entry in pages.items():
        if rel in freeze_pages and entry.get('page_sha256') != freeze_pages[rel]:
            problems.append('stats page hash mismatch: %s' % rel)
        if 'bigrams' not in entry or 'n_tokens' not in entry:
            problems.append('stats entry incomplete: %s' % rel)
    if b.get('stoplist') != sorted(STOPLIST):
        problems.append('stats stoplist mismatch (rule definition drift)')
    return problems


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()
