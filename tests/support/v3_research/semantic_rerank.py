"""H2 node 6 — semantic rerank eval path (EVAL tooling, NOT production kb.py).

Contract (docs/v3/h2-rerank-contract-20261110.md, pre-registered):
  candidates = baseline-identical in-process FTS5 k=10 hits
  score      = cosine(mean-pool GloVe(query), mean-pool GloVe(page)) per hit's PAGE
  order      = (-cosine, baseline_rank) — deterministic tie-break
  miss rule  = suppress ALL hits iff top page cosine < TAU (0.50, v2 freeze prior)

Import-safe WITHOUT numpy (the /usr/bin/python3 pytest core has none): the
numpy-dependent parts (GloVe load, query pooling) import numpy lazily inside
functions. Everything the unit tests cover is pure stdlib.
"""
import hashlib
import math
import re

WORD = re.compile(r'[a-z0-9]+')
TAU = 0.50          # pre-registered miss threshold (v2 freeze a1_miss_rule); never tuned on H2 data
DIM = 100


# ---------------------------------------------------------------- pure core
def tokenize(text):
    """lowercase [a-z0-9]+ tokens (v2 PoC recipe)."""
    return WORD.findall(text.lower())


def mean_pool_pure(tokens, vec_map):
    """Mean of in-vocab token vectors. OOV tokens skipped and counted.

    vec_map: dict token -> sequence of DIM floats.
    Returns (vector list[float] or None when no in-vocab token, n_oov).
    """
    acc = None
    n_oov = 0
    n_in = 0
    for tok in tokens:
        vec = vec_map.get(tok)
        if vec is None:
            n_oov += 1
            continue
        if acc is None:
            acc = [0.0] * len(vec)
        for i, x in enumerate(vec):
            acc[i] += x
        n_in += 1
    if acc is None or n_in == 0:
        return None, n_oov
    return [x / n_in for x in acc], n_oov


def cosine_pure(a, b):
    """Cosine similarity; 0.0 when either vector is None or zero-norm."""
    if a is None or b is None:
        return 0.0
    dot = na = nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def rerank_hits(hits, page_cosine):
    """Order candidate hits by (-page cosine, baseline rank). Deterministic.

    hits: [{'id','page','score','rank',...}] with rank = baseline rank (1-based).
    page_cosine: dict page -> float; a page missing from the map scores 0.0
    (must not happen with a complete cache — recorded, not hidden).
    Returns a NEW list of dicts: input hit + 'cosine' + rerank 'rank' (1-based).
    """
    keyed = sorted(hits, key=lambda h: (-page_cosine.get(h['page'], 0.0), h['rank']))
    return [dict(h, cosine=round(page_cosine.get(h['page'], 0.0), 6), rerank_rank=i + 1)
            for i, h in enumerate(keyed)]


def apply_miss_rule(ranked_hits, tau=TAU):
    """Honest-miss rule: suppress ALL hits iff the top page cosine < tau.

    Returns (reported_hits, miss, top_cosine). Empty input is already a miss.
    """
    top = ranked_hits[0]['cosine'] if ranked_hits else None
    if top is None or top < tau:
        return [], True, top
    return list(ranked_hits), False, top


def page_ranks(ranked_hits):
    """page -> rank of its first occurrence in the reranked hit list."""
    out = {}
    for h in ranked_hits:
        out.setdefault(h['page'], h['rerank_rank'] if 'rerank_rank' in h else h['rank'])
    return out


# ------------------------------------------------------- frozen class rules
def class_pass(qdef, pranks, reported_hits):
    """Evaluate the PRE-REGISTERED per-class pass rules on a reranked result.

    qdef: frozen query record (class, expected_pages, pass_rule, successor /
          superseded for E). pranks: page_ranks() of the FULL reranked list
          (pre miss-rule — class membership is judged on the ranking; the miss
          rule only decides what gets REPORTED). reported_hits: post-miss-rule.
    Returns {'pass': bool, 'detail': {...}}.

    Rules (contract): A/D expected page top-3; B/C top-5 (k from the frozen
    pass_rule); E successor above superseded within top-10; F honest miss =
    zero reported hits. A query whose expected page was suppressed by the miss
    rule CANNOT pass A–E (a suppressed answer is a reported miss).
    """
    cls = qdef['class']
    if cls == 'F':
        return {'pass': len(reported_hits) == 0,
                'detail': {'reported_hits': len(reported_hits)}}
    if not reported_hits:
        return {'pass': False, 'detail': {'suppressed_by_miss_rule': True}}
    k = qdef.get('pass_rule', {}).get('k', 10)
    expected = qdef.get('expected_pages', [])
    exp_rank = next((pranks[p] for p in expected if p in pranks), None)
    if cls in ('A', 'B', 'C', 'D'):
        return {'pass': exp_rank is not None and exp_rank <= k,
                'detail': {'expected_rank': exp_rank, 'k': k}}
    if cls == 'E':
        sup = pranks.get(qdef['superseded'])
        return {'pass': exp_rank is not None and exp_rank <= 10
                and (sup is None or exp_rank < sup),
                'detail': {'successor_rank': exp_rank, 'superseded_rank': sup}}
    raise ValueError('unknown query class: %r' % cls)


# ------------------------------------------------------------- binding check
def verify_cache_binding(cache, freeze_doc, glove_sha256, freeze_json_sha256,
                         contract_sha256=None):
    """Stdlib binding verification of an embeddings cache against the freeze.

    Returns a list of problems ([] == bound). Used by the eval runner, the
    master check, and the mutation controls (which prove it refuses drift).
    """
    problems = []
    cb = cache.get('binding', {})
    if cb.get('glove_sha256') != glove_sha256:
        problems.append('cache glove sha256 mismatch')
    if cb.get('corpus_sha256') != freeze_doc['corpus']['corpus_sha256']:
        problems.append('cache corpus sha256 mismatch')
    if cb.get('freeze_json_sha256') != freeze_json_sha256:
        problems.append('cache freeze-json sha256 mismatch')
    if contract_sha256 is not None and cb.get('contract_sha256') != contract_sha256:
        problems.append('cache contract sha256 mismatch (pre-registration broken)')
    freeze_pages = {r['path']: r['sha256'] for r in freeze_doc['corpus']['pages']}
    pages = cache.get('pages', {})
    missing = sorted(set(freeze_pages) - set(pages))
    extra = sorted(set(pages) - set(freeze_pages))
    if missing or extra:
        problems.append('cache page set != freeze page set (missing=%d extra=%d)'
                        % (len(missing), len(extra)))
    for rel, entry in pages.items():
        if rel in freeze_pages and entry.get('page_sha256') != freeze_pages[rel]:
            problems.append('cache page hash mismatch: %s' % rel)
        if len(entry.get('vector', [])) != DIM:
            problems.append('cache vector dim != %d: %s' % (DIM, rel))
    return problems


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------- numpy-dependent (lazy imports)
def load_glove(path):
    """v2 PoC recipe: skip malformed lines, float32 matrix. Returns (index, matrix)."""
    import numpy
    vocab, rows = [], []
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            parts = line.rstrip().split(' ')
            if len(parts) != DIM + 1:
                continue
            vocab.append(parts[0])
            rows.append([float(x) for x in parts[1:]])
    matrix = numpy.asarray(rows, dtype=numpy.float32)
    return dict(zip(vocab, range(len(vocab)))), matrix


def pool_text_numpy(text, index, matrix):
    """Mean-pool a text with the loaded GloVe matrix. Returns (vector, counts)."""
    toks = tokenize(text)
    ids = [index[t] for t in toks if t in index]
    counts = {'tokens': len(toks), 'oov': len(toks) - len(ids)}
    if not ids:
        return None, counts
    return matrix[ids].mean(axis=0), counts
