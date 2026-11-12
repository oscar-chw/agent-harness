"""Model-free dreaming control loop v1 (H6c, plan/v3-h6c-dreaming-v1 node 7).

v1 implements the H4 verdict's model-free follow-ups (docs/v3/h4-dreaming-
verdict-20261110.md, what-follows #1/#2/#4), frozen in
docs/v3/h6c-dreaming-v1-contract-20261110.md BEFORE any v1 scoring run:

  edge arm   — s_ctx replaced by literal-local ±8-token windows, idf-weighted
               (BM25) overlap; a two-sided stance/negation signal is added:
               correction language required in the successor's marker
               paragraph (G-StanceA) and disqualifying in the superseded
               page's literal windows (G-StanceB: already-corrected =
               agreement, not supersession); s_auth log-scaled.
  orphan arm — s_lex recalibrated to BM25-style idf (v0's raw log(N/df)
               saturated at N=133); s_auth log-scaled (v0 gave hub sources a
               flat +0.20). s_clust/s_sub and all weights unchanged.

Trigger model, phases (Light/REM/Deep), PhaseGuard write surfaces, promotion
surfaces (deep-only orphan-link appends; supersedes edges to the ledger only),
dry-run default and fail-closed posture are REUSED from v0 unchanged — the H4
verdict cleared them; the failure was scoring. This module imports v0
(src/agent_harness/memory_dreaming.py, bytes untouched) for that machinery.

Zero model calls, zero network, stdlib only.

CLI:
    python3 -m agent_harness.memory_dreaming_v1 --src CORPUS --work-dir DIR
        [--state STATE_JSON] [--freeze FREEZE_JSON] [--apply --dst DIR]
        [--out REPORT_JSON]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from agent_harness import memory_consolidate as mc
from agent_harness import memory_dreaming as md

# ---------------------------------------------------------------------------
# Frozen v1 defaults (docs/v3/h6c-dreaming-v1-contract-20261110.md).
# ---------------------------------------------------------------------------
CTX_WINDOW = 8                 # literal-local window half-width, raw words
CTX_SAT_V1 = 6.0               # BM25-idf mass saturation for window overlap
LEX_SAT_V1 = 8.0               # BM25-idf mass saturation for orphan s_lex
EDGE_MIN_CTX_LOCAL = 0.5       # s_ctx_local >= 0.5  <=>  best mass >= 3.0
EDGE_MIN_SCORE_V1 = 0.55
ORPHAN_MIN_SUPPORT = md.ORPHAN_MIN_SUPPORT   # 4, unchanged
ORPHAN_MIN_LEX = md.ORPHAN_MIN_LEX           # 0.35, unchanged value, v1 signal
ORPHAN_MIN_SCORE = md.ORPHAN_MIN_SCORE       # 0.55, unchanged

STANCE_LEXICON = frozenset(
    'wrong corrects corrected superseded supersedes stale retracted retracts '
    'suspect unverified broken misleading outdated garbage invalid mistake '
    'beware fixed'.split())

W_EDGE_V1 = {'scope': 0.30, 'ctx': 0.30, 'date': 0.10, 'auth': 0.10,
             'stance': 0.20}
W_ORPHAN_V1 = md.W_ORPHAN      # weights unchanged; signals recalibrated

APPEND_LINE_V1 = '\nRelated (dreaming v1, promoted): [[%s]]\n'

_RAW_WORD = re.compile(r'\w+')


# ---------------------------------------------------------------------------
# v1 primitives
# ---------------------------------------------------------------------------

def raw_words(text: str) -> List[str]:
    """Raw lowercase words — stance matching needs words like 'not'/'no' that
    mc._tokens drops as stopwords; positions are in THIS stream."""
    return [m.group(0).lower() for m in _RAW_WORD.finditer(text)]


def literal_windows(text: str, literal: str, k: int = CTX_WINDOW) -> List[List[str]]:
    """Every ±k raw-word window around each occurrence of the literal (matched
    as a contiguous raw-word span); the literal span itself is excluded."""
    words = raw_words(text)
    lit = raw_words(literal)
    out: List[List[str]] = []
    if not lit:
        return out
    for i in range(len(words) - len(lit) + 1):
        if words[i:i + len(lit)] == lit:
            lo, hi = max(0, i - k), min(len(words), i + len(lit) + k)
            out.append(words[lo:i] + words[i + len(lit):hi])
    return out


def _content(window: Sequence[str]) -> set:
    """Content tokens of a raw-word window — delegated to mc._tokens so the
    window vocabulary and the corpus df share one token space by construction
    (hyphenated forms split identically, stopwords/short tokens dropped)."""
    return set(mc._tokens(' '.join(window)))


def idf_bm25(token: str, df: Dict[str, int], n_pages: int) -> float:
    """BM25-style idf: log(1 + (N - df + 0.5)/(df + 0.5)). Recalibrates v0's
    raw log(N/df), which saturated at N=133 on moderately generic tokens."""
    d = max(1, df.get(token, 1))
    return math.log(1.0 + (n_pages - d + 0.5) / (d + 0.5))


def s_auth_log(indeg_val: int, max_indeg: int) -> float:
    """Log-scaled authority: log(1+indeg)/log(1+max_indeg). 0 at indeg 0, 1 at
    the corpus max — hubs no longer collect v0's flat min(1, indeg/10) = 1.0."""
    if max_indeg <= 0:
        return 0.0
    return math.log(1.0 + max(0, indeg_val)) / math.log(1.0 + max_indeg)


def window_overlap_mass(wa: Sequence[str], wb: Sequence[str],
                        df: Dict[str, int], n_pages: int) -> Tuple[float, List[str]]:
    """BM25-idf mass of the content-token overlap between two windows."""
    ov = sorted(_content(wa) & _content(wb))
    return sum(idf_bm25(t, df, n_pages) for t in ov), ov


def has_stance(words: Sequence[str]) -> bool:
    """Exact raw-word membership — no substring bleed ('corrected errors' fires
    only if 'corrected' itself is in the window)."""
    return any(w in STANCE_LEXICON for w in words)


# ---------------------------------------------------------------------------
# v1 scorers
# ---------------------------------------------------------------------------

def score_orphan_link_v1(cand: dict, pages_by_rel: Dict[str, mc.Page], indeg,
                         df: Dict[str, int], n_pages: int, stems: set,
                         max_indeg: int, lex_sat: float = LEX_SAT_V1) -> dict:
    """v0's orphan scorer with BM25-idf s_lex and log-scaled s_auth; cluster /
    substance signals and all weights unchanged."""
    shared = list(cand.get('shared_tokens', []))
    orphan = pages_by_rel.get(cand['orphan'])
    s_lex = min(1.0, sum(idf_bm25(t, df, n_pages) for t in shared) / lex_sat) if shared else 0.0
    s_clust = 1.0 if any(t in stems for t in shared) else 0.0
    s_auth = s_auth_log(indeg.get(mc._stem(cand['source']), 0), max_indeg)
    s_sub = min(1.0, (len(orphan.data) / 2000.0)) if orphan else 0.0
    score = (W_ORPHAN_V1['lex'] * s_lex + W_ORPHAN_V1['clust'] * s_clust
             + W_ORPHAN_V1['auth'] * s_auth + W_ORPHAN_V1['sub'] * s_sub)
    return {'kind': 'orphan_inbound_link', 'orphan': cand['orphan'],
            'source': cand['source'], 'n_shared': len(shared),
            'signals': {'s_lex_v1': round(s_lex, 4), 's_clust': s_clust,
                        's_auth_v1': round(s_auth, 4), 's_sub': round(s_sub, 4),
                        'source_indegree': indeg.get(mc._stem(cand['source']), 0),
                        'orphan_bytes': len(orphan.data) if orphan else 0,
                        'cluster_tokens': sorted(t for t in shared if t in stems)},
            'score': round(score, 4)}


def score_supersedes_edge_v1(cand: dict, pages_by_rel: Dict[str, mc.Page], indeg,
                             df: Dict[str, int], n_pages: int, max_indeg: int) -> dict:
    """v1 edge scorer: literal-local idf-weighted context + two-sided stance.
    s_ctx_local measures whether the two pages' ±8-word neighbourhoods around
    the SAME strong literal share distinctive vocabulary; s_stance_net requires
    correction language in the successor's marker paragraph and none in the
    superseded page's literal windows (agreement is not supersession)."""
    fs = cand.get('fact_scope', {})
    matched = [l for l in fs.get('matched_literals', [])]
    strong = [l for l in matched if not mc._WEAK_LITERAL.fullmatch(l)]
    shared = fs.get('shared_tokens', [])
    a = pages_by_rel.get(cand['successor'])
    b = pages_by_rel.get(cand['superseded'])
    s_scope = min(1.0, (len(strong) + len(shared) / 4.0) / 3.0)
    best_mass, best_pair = 0.0, None
    stance_b = False
    if a is not None and b is not None and strong:
        for l in strong:
            wa_list = literal_windows(a.body, l)
            wb_list = literal_windows(b.body, l)
            for wb in wb_list:
                if has_stance(wb):
                    stance_b = True
            for wa in wa_list:
                for wb in wb_list:
                    mass, ov = window_overlap_mass(wa, wb, df, n_pages)
                    if mass > best_mass:
                        best_mass, best_pair = mass, (l, ov)
    s_ctx_local = min(1.0, best_mass / CTX_SAT_V1)
    stance_a = False
    if a is not None:
        marker = md._marker_paragraph(a, fs.get('marker_excerpt', ''))
        stance_a = has_stance(raw_words(marker))
    s_stance_net = 1.0 if (stance_a and not stance_b) else 0.0
    da, db = md._parse_dt(fs.get('a_date') or ''), md._parse_dt(fs.get('b_date') or '')
    gap_days = (da - db).days if (da and db) else 0
    s_date = min(1.0, max(0, gap_days) / 14.0)
    s_auth = s_auth_log(indeg.get(mc._stem(cand['successor']), 0), max_indeg)
    score = (W_EDGE_V1['scope'] * s_scope + W_EDGE_V1['ctx'] * s_ctx_local
             + W_EDGE_V1['date'] * s_date + W_EDGE_V1['auth'] * s_auth
             + W_EDGE_V1['stance'] * s_stance_net)
    return {'kind': 'supersedes_edge', 'successor': cand['successor'],
            'superseded': cand['superseded'],
            'signals': {'s_scope': round(s_scope, 4),
                        's_ctx_local': round(s_ctx_local, 4),
                        'ctx_best_mass': round(best_mass, 4),
                        'ctx_best_pair': best_pair,
                        's_date': round(s_date, 4),
                        's_auth_v1': round(s_auth, 4),
                        'stance_a': stance_a, 'stance_b': stance_b,
                        's_stance_net': s_stance_net,
                        'strong_literals': strong, 'weak_literals_dropped':
                        [l for l in matched if l not in strong],
                        'date_gap_days': gap_days},
            'score': round(score, 4)}


# ---------------------------------------------------------------------------
# v1 gates (ALL required; same posture as v0, new signal gates added)
# ---------------------------------------------------------------------------

def gate_orphan_link_v1(sc: dict, min_support: int = ORPHAN_MIN_SUPPORT,
                        min_lex: float = ORPHAN_MIN_LEX,
                        min_score: float = ORPHAN_MIN_SCORE) -> Tuple[bool, List[str]]:
    failed = []
    if sc['n_shared'] < min_support:
        failed.append('G-Support(|shared|=%d < %d)' % (sc['n_shared'], min_support))
    if sc['signals']['s_lex_v1'] < min_lex:
        failed.append('G-Lex(%.3f < %.2f)' % (sc['signals']['s_lex_v1'], min_lex))
    if sc['score'] < min_score:
        failed.append('G-Score(%.3f < %.2f)' % (sc['score'], min_score))
    return (not failed, failed)


def gate_supersedes_edge_v1(sc: dict, min_ctx_local: float = EDGE_MIN_CTX_LOCAL,
                            min_score: float = EDGE_MIN_SCORE_V1,
                            require_stance: bool = True) -> Tuple[bool, List[str]]:
    failed = []
    if not sc['signals']['strong_literals']:
        failed.append('G-StrongLit(0 strong literals; weak dotted-suffix only)')
    if sc['signals']['s_ctx_local'] < min_ctx_local:
        failed.append('G-CtxLocal(%.3f < %.2f)' % (sc['signals']['s_ctx_local'],
                                                   min_ctx_local))
    if require_stance:
        if not sc['signals']['stance_a']:
            failed.append('G-StanceA(no correction language in the successor '
                          'marker paragraph)')
        if sc['signals']['stance_b']:
            failed.append('G-StanceB(superseded-side literal window already carries '
                          'correction language — agreement, not supersession)')
    if sc['score'] < min_score:
        failed.append('G-Score(%.3f < %.2f)' % (sc['score'], min_score))
    return (not failed, failed)


# ---------------------------------------------------------------------------
# The v1 dreaming pass (orchestration mirrors v0; scorers/gates are v1)
# ---------------------------------------------------------------------------

def dream_v1(src: Path, dst: Optional[Path] = None, work_dir: Optional[Path] = None,
             state: Optional[dict] = None, freeze: Optional[Path] = None,
             apply: bool = False, session_id: Optional[str] = None,
             gate_overrides: Optional[dict] = None,
             now: Optional[str] = None) -> dict:
    """Run one v1 dreaming pass over a corpus COPY (never the live store).
    Same contract as v0 dream(): dry-run default; apply=True requires a
    triggered state and an explicit dst != src; the only corpus writes are
    promoted orphan-link appends (Deep phase, PhaseGuard-enforced);
    gate_overrides lowers/raises thresholds and is receipted loudly."""
    src = Path(src)
    if apply:
        if dst is None:
            raise ValueError('apply requires an explicit --dst; dreaming never writes in place')
        if Path(dst).resolve() == src.resolve():
            raise ValueError('--dst must differ from --src; the source corpus is read-only')
    ov = dict(gate_overrides or {})
    thresholds = {'trigger_min_sessions': int(ov.get('trigger_min_sessions', md.TRIGGER_MIN_SESSIONS)),
                  'trigger_min_pages_changed': int(ov.get('trigger_min_pages_changed',
                                                          md.TRIGGER_MIN_PAGES_CHANGED)),
                  'lex_sat_v1': float(ov.get('lex_sat_v1', LEX_SAT_V1)),
                  'orphan_min_support': int(ov.get('orphan_min_support', ORPHAN_MIN_SUPPORT)),
                  'orphan_min_lex': float(ov.get('orphan_min_lex', ORPHAN_MIN_LEX)),
                  'orphan_min_score': float(ov.get('orphan_min_score', ORPHAN_MIN_SCORE)),
                  'edge_min_ctx_local': float(ov.get('edge_min_ctx_local', EDGE_MIN_CTX_LOCAL)),
                  'edge_min_score': float(ov.get('edge_min_score', EDGE_MIN_SCORE_V1)),
                  'edge_require_stance': bool(ov.get('edge_require_stance', True))}

    pages = mc.load_pages(src)
    binding = mc._verify_freeze(pages, Path(freeze)) if freeze else {'verified': False}
    trigger = md.evaluate_trigger(state, session_id=session_id,
                                  min_sessions=thresholds['trigger_min_sessions'],
                                  min_pages_changed=thresholds['trigger_min_pages_changed'])
    if apply and not trigger['triggered']:
        raise ValueError('dreaming trigger did not fire; Deep phase refuses '
                         '(fail-closed). Reasons: %s' % '; '.join(trigger['reasons']))

    indeg = mc.build_graph(pages)
    df = mc._df(pages)
    n_pages = len(pages)
    max_indeg = max(indeg.values()) if indeg else 0
    stems = md._stem_set(pages)
    pages_by_rel = {pg.rel: pg for pg in pages}
    guard_receipts: List[dict] = []

    def run_guard(phase: str, writes: Sequence[Tuple[str, Path]]) -> None:
        g = md.PhaseGuard(phase, dst_root=dst if apply else None, work_dir=work_dir)
        for kind, target in writes:
            guard_receipts.append(g.check(kind, target))

    # ---- Light: generate + stage candidates (H1 mechanism, read-only) ------
    mech = mc.consolidate(src, freeze=freeze, apply=False)
    candidates = mech['actions']
    if work_dir:
        staged = Path(work_dir) / 'staged-candidates.json'
        run_guard('light', [('receipt', staged)])
        Path(work_dir).mkdir(parents=True, exist_ok=True)
        staged.write_text(json.dumps({'phase': 'light', 'counts': mech['counts'],
                                      'actions': candidates}, indent=2) + '\n', encoding='utf-8')

    # ---- REM: score + rank (receipt only) ----------------------------------
    scored: List[dict] = []
    for c in candidates:
        if c['kind'] == 'orphan_inbound_link':
            scored.append(score_orphan_link_v1(c, pages_by_rel, indeg, df, n_pages,
                                               stems, max_indeg,
                                               lex_sat=thresholds['lex_sat_v1']))
        elif c['kind'] == 'supersedes_edge':
            scored.append(score_supersedes_edge_v1(c, pages_by_rel, indeg, df,
                                                   n_pages, max_indeg))
    if work_dir:
        sc_path = Path(work_dir) / 'scored-candidates.json'
        run_guard('rem', [('receipt', sc_path)])
        sc_path.write_text(json.dumps({'phase': 'rem', 'scored': scored}, indent=2) + '\n',
                           encoding='utf-8')

    # ---- Deep: gate, then promote ------------------------------------------
    promoted, demoted, review_only = [], [], []
    for c in candidates:
        if c['kind'] == 'orphan_inbound_link':
            sc = next(s for s in scored
                      if s['kind'] == 'orphan_inbound_link'
                      and s['orphan'] == c['orphan'] and s['source'] == c['source'])
            ok, failed = gate_orphan_link_v1(sc, thresholds['orphan_min_support'],
                                             thresholds['orphan_min_lex'],
                                             thresholds['orphan_min_score'])
            rec = {'kind': c['kind'], 'orphan': c['orphan'], 'source': c['source'],
                   'score': sc['score'], 'signals': sc['signals'], 'applied': False}
            if ok:
                rec['explain'] = ('promote: all v1 gates pass; append [[%s]] on %s'
                                  % (mc._stem(c['orphan']), c['source']))
                promoted.append(rec)
            else:
                rec['explain'] = 'demote: ' + '; '.join(failed)
                demoted.append(rec)
        elif c['kind'] == 'supersedes_edge':
            sc = next(s for s in scored
                      if s['kind'] == 'supersedes_edge'
                      and s['successor'] == c['successor'] and s['superseded'] == c['superseded'])
            ok, failed = gate_supersedes_edge_v1(sc, thresholds['edge_min_ctx_local'],
                                                 thresholds['edge_min_score'],
                                                 thresholds['edge_require_stance'])
            rec = {'kind': c['kind'], 'successor': c['successor'],
                   'superseded': c['superseded'], 'fact_scope': c['fact_scope'],
                   'score': sc['score'], 'signals': sc['signals']}
            if ok:
                rec['explain'] = ('promote: all v1 gates pass; review-ledger entry '
                                  '(corpus keeps both pages, fact-scoped)')
                promoted.append(rec)
            else:
                rec['explain'] = 'demote: ' + '; '.join(failed)
                demoted.append(rec)
        else:
            review_only.append({'kind': c['kind'], 'candidate': c,
                                'explain': 'review-only in v1 (no ordering evidence / human '
                                           'judgement required); carried to the ledger, '
                                           'never auto-promoted'})

    link_promotions = [p for p in promoted if p['kind'] == 'orphan_inbound_link']
    edge_promotions = [p for p in promoted if p['kind'] == 'supersedes_edge']

    planned_writes = [{'kind': 'orphan_link_append', 'target_page': p['source'],
                       'append': APPEND_LINE_V1 % mc._stem(p['orphan']),
                       'orphan': p['orphan']} for p in link_promotions]
    if apply:
        deep_guard = md.PhaseGuard('deep', dst_root=Path(dst), work_dir=work_dir)
        for w in planned_writes:
            deep_guard.check('orphan_link_append', Path(dst) / w['target_page'])
        guard_receipts.extend(deep_guard.allowed)

    report = {
        'tool': 'agent_harness.memory_dreaming_v1 v1',
        'created_utc': now or datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'dry_run': not apply,
        'src': str(src), 'dst': str(dst) if dst else None,
        'work_dir': str(work_dir) if work_dir else None,
        'session_id': session_id,
        'binding': binding,
        'trigger': trigger,
        'thresholds': thresholds,
        'threshold_overrides_applied': ov,
        'threshold_override_note': ('non-default thresholds in force (mutation-control or '
                                    'test hook); receipted loudly' if ov else None),
        'phases': {
            'light': {'candidate_counts': mech['counts'],
                      'staged_receipt': str(Path(work_dir) / 'staged-candidates.json')
                      if work_dir else None},
            'rem': {'scored': len(scored),
                    'scored_receipt': str(Path(work_dir) / 'scored-candidates.json')
                    if work_dir else None},
            'deep': {'promoted': len(promoted), 'demoted': len(demoted),
                     'review_only': len(review_only),
                     'planned_corpus_writes': len(planned_writes)}},
        'promoted': promoted, 'demoted': demoted, 'review_only': review_only,
        'guard': {'writes': guard_receipts,
                  'rule': 'deep-only corpus writes (orphan-link appends on memory/*.md, '
                          'never MEMORY.md, never archive/); ledger/receipts under work dir'},
        'hygiene': {'before': md.hygiene(pages), 'after': None},
        'counts': {'candidates': len(candidates), 'scored': len(scored),
                   'promoted_orphan_links': len(link_promotions),
                   'promoted_supersedes_edges': len(edge_promotions),
                   'demoted': len(demoted), 'review_only': len(review_only),
                   'pages_mutated': 0, 'pages_archived': 0},
        'fact_preservation': {'ok': None,
                              'rule': 'every input page sha256 present in the output as a '
                                      'live page or a receipted mutation hash; H6c archives '
                                      'and deletes nothing'},
    }

    if not apply:
        report['hygiene']['after'] = 'projected: %d of %d orphans would leave the orphan set' % (
            len({p['orphan'] for p in link_promotions}),
            report['hygiene']['before']['orphan_count'])
        return report

    # ---- apply on the destination copy (Deep phase writes only) -------------
    dst = Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    if freeze:
        mc._verify_freeze(mc.load_pages(dst), Path(freeze))

    mutated = []
    live_pages = {pg.rel: pg for pg in mc.load_pages(dst)}
    for p in link_promotions:
        src_page = live_pages.get(p['source'])
        if src_page is None:
            continue
        before = src_page.data
        after = before + (APPEND_LINE_V1 % mc._stem(p['orphan'])).encode('utf-8')
        (dst / src_page.rel).write_bytes(after)
        mutated.append({'path': src_page.rel, 'before_sha256': mc._sha256(before),
                        'after_sha256': mc._sha256(after),
                        'change': 'append inbound link to orphan %s (dreaming v1, promoted)'
                                  % p['orphan']})
        live_pages[p['source']] = mc.Page(src_page.rel, after)
        p['applied'] = True

    # review ledger (Deep phase, work dir scope)
    if work_dir:
        ledger = {'dream_ledger': 'v1', 'session_id': session_id,
                  'promoted_supersedes_edges': edge_promotions,
                  'promoted_orphan_links': [p['orphan'] + ' <- ' + p['source']
                                            for p in link_promotions],
                  'review_only': review_only,
                  'demoted': [{'kind': d['kind'], 'score': d['score'],
                               'explain': d['explain']} for d in demoted]}
        lg = md.PhaseGuard('deep', dst_root=dst, work_dir=work_dir)
        lg_path = Path(work_dir) / 'dream-ledger.json'
        md_path = Path(work_dir) / 'DREAMS.md'
        guard_receipts.append(lg.check('ledger', lg_path))
        guard_receipts.append(lg.check('ledger', md_path))
        lg_path.write_text(json.dumps(ledger, indent=2) + '\n', encoding='utf-8')
        lines = ['# DREAMS — dreaming v1 ledger (%s)' % (session_id or 'no-session'), '',
                 'Promoted %d orphan inbound links, %d supersedes edges (ledger-only); '
                 '%d candidates demoted, %d review-only.'
                 % (len(link_promotions), len(edge_promotions), len(demoted), len(review_only)),
                 '', '## Promoted supersedes edges (review ledger; corpus keeps both pages)']
        for e in edge_promotions:
            lines.append('- `%s` supersedes `%s` (score %.3f, scope: %s)'
                         % (e['successor'], e['superseded'], e['score'],
                            ', '.join(e['signals']['strong_literals'][:3])))
        lines += ['', '## Promoted orphan inbound links (appended to the corpus copy)']
        for p in link_promotions:
            lines.append('- `%s` gains a link from `%s` (score %.3f)'
                         % (p['orphan'], p['source'], p['score']))
        md_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    out_pages = mc.load_pages(dst)
    out_hashes = {pg.sha256 for pg in out_pages}
    in_hashes = {pg.sha256 for pg in pages}
    mutated_before = {m['before_sha256'] for m in mutated}
    lost = sorted(h for h in in_hashes - out_hashes if h not in mutated_before)
    report['fact_preservation'] = {'ok': not lost, 'lost_sha256': lost,
                                   'rule': report['fact_preservation']['rule']}
    report['counts']['pages_mutated'] = len(mutated)
    report['output'] = {'root_sha256': mc.corpus_root_hash([pg.sha256 for pg in out_pages]),
                        'archived': [], 'mutated': mutated}
    report['hygiene']['after'] = md.hygiene(out_pages)
    if lost:
        raise ValueError('fact preservation violated; missing sha256: %s' % lost)
    return report


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog='python3 -m agent_harness.memory_dreaming_v1')
    ap.add_argument('--src', required=True, help='corpus copy to read (never mutated)')
    ap.add_argument('--work-dir', help='dreaming work dir for staged/scored/ledger receipts')
    ap.add_argument('--state', help='trigger state JSON (absent = bootstrap)')
    ap.add_argument('--freeze', help='freeze manifest to hash-bind and verify against')
    ap.add_argument('--apply', action='store_true', help='write promoted changes to --dst')
    ap.add_argument('--dst', help='destination corpus copy (required for --apply)')
    ap.add_argument('--session-id', help='session stamp for trigger cooldown')
    ap.add_argument('--out', help='write the dreaming receipt JSON here')
    a = ap.parse_args(argv)
    state = json.loads(Path(a.state).read_text()) if a.state else None
    try:
        report = dream_v1(Path(a.src), Path(a.dst) if a.dst else None,
                          Path(a.work_dir) if a.work_dir else None,
                          state=state, freeze=Path(a.freeze) if a.freeze else None,
                          apply=a.apply, session_id=a.session_id)
    except (ValueError, md.PhaseScopeError) as exc:
        print('REFUSED: %s' % exc, file=sys.stderr)
        return 2
    text = json.dumps(report, indent=2) + '\n'
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text, encoding='utf-8')
    print(json.dumps({'dry_run': report['dry_run'], 'triggered': report['trigger']['triggered'],
                      'binding_verified': report['binding'].get('verified', False),
                      'counts': report['counts'],
                      'fact_preservation_ok': report['fact_preservation']['ok']}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
