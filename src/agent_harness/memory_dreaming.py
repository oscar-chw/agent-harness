"""Model-free dreaming control loop v0 (H4, plan/v3-h4-dreaming node 6).

H1 (memory_consolidate) is the MECHANISM: it proposes consolidation candidates.
H4 is the CONTROL LOOP above it, modeled on OpenClaw's dreaming gates
(docs/v3/oss-mechanics-20261110.md) and adapted model-free per local-first
constraints (docs/v3/h4-dreaming-contract-20261110.md — thresholds frozen there
BEFORE any gated run):

  Light — runs the H1 mechanism on a corpus COPY and stages the raw candidate
          set (receipt only; never touches the corpus).
  REM   — scores and ranks every candidate (receipt only).
  Deep  — the ONLY phase with corpus write scope, and only for promoted
          orphan-inbound-link appends; supersedes edges promote to the review
          ledger (receipt-level); conflict flags, undirected version candidates
          and dup merges are review-only (an archival is a human decision).

Trigger model (when a dream runs): bootstrap (no prior dream), or
sessions_since_last_dream >= 5, or pages_changed_since_last_dream >= 10;
a second Deep run in the same session is a no-op. Not-triggered => Deep refuses
(fail-closed); Light/REM may run as a survey.

Promotion gates are ALL-required (OpenClaw posture). Scores are model-free:
idf-weighted lexical support, page-stem cluster membership, wikilink in-degree
authority, literal-context agreement, date-gap ordering confidence. Dry-run is
the default; apply requires an explicit dst != src; MEMORY.md and archive/ are
never writable; nothing is ever deleted. Every decision is receipted
(promote-explain), and any gate override is receipted loudly.

Zero model calls, zero network, stdlib only.

CLI:
    python3 -m agent_harness.memory_dreaming --src CORPUS --work-dir DIR
        [--state STATE_JSON] [--freeze FREEZE_JSON] [--apply --dst DIR]
        [--out REPORT_JSON]
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from agent_harness import memory_consolidate as mc

# ---------------------------------------------------------------------------
# Frozen defaults (docs/v3/h4-dreaming-contract-20261110.md). Configurable so
# unit tests can scale them to tiny synthetic corpora; the H4 eval uses these.
# ---------------------------------------------------------------------------
TRIGGER_MIN_SESSIONS = 5
TRIGGER_MIN_PAGES_CHANGED = 10
LEX_SAT = 14.0                 # idf-mass saturation, calibrated for N=133
ORPHAN_MIN_SUPPORT = 4         # |shared distinctive tokens| (H1 proposes at >= 3)
ORPHAN_MIN_LEX = 0.35
ORPHAN_MIN_SCORE = 0.55
EDGE_MIN_CTX = 0.5             # >= 2 shared content tokens between the paragraphs
EDGE_MIN_SCORE = 0.55

W_ORPHAN = {'lex': 0.45, 'clust': 0.25, 'auth': 0.20, 'sub': 0.10}
W_EDGE = {'scope': 0.35, 'ctx': 0.30, 'date': 0.20, 'auth': 0.15}

PHASES = ('light', 'rem', 'deep')

APPEND_LINE = '\nRelated (dreaming v0, promoted): [[%s]]\n'


class PhaseScopeError(ValueError):
    """A write was attempted outside the current phase's allowed surface."""


class PhaseGuard:
    """Fail-closed write-scope enforcement. Every write the dreaming pass makes
    goes through check(); violations are recorded AND raised. Write kinds:
      receipt            — any phase, under work_dir only
      ledger             — deep only, under work_dir only
      orphan_link_append — deep only, under dst_root, memory/*.md, never
                           MEMORY.md, never under archive/
    """

    def __init__(self, phase: str, dst_root: Optional[Path] = None,
                 work_dir: Optional[Path] = None):
        if phase not in PHASES:
            raise ValueError('unknown phase: %r' % (phase,))
        self.phase = phase
        self.dst_root = Path(dst_root).resolve() if dst_root else None
        self.work_dir = Path(work_dir).resolve() if work_dir else None
        self.allowed: List[dict] = []
        self.refused: List[dict] = []

    def _under(self, root: Optional[Path], target: Path) -> bool:
        if root is None:
            return False
        try:
            target.resolve().relative_to(root)
            return True
        except ValueError:
            return False

    def check(self, kind: str, target: Path) -> dict:
        target = Path(target)
        ok, reason = False, ''
        if kind == 'receipt':
            ok = self._under(self.work_dir, target)
            reason = 'receipts must live under the dreaming work dir'
        elif kind == 'ledger':
            ok = self.phase == 'deep' and self._under(self.work_dir, target)
            reason = 'ledger writes are deep-phase only and live under the work dir'
        elif kind == 'orphan_link_append':
            if self.phase != 'deep':
                reason = 'corpus writes are deep-phase only (light/rem stage and score)'
            elif not self._under(self.dst_root, target):
                reason = 'corpus writes stay inside the explicit dst root'
            else:
                rel = target.resolve().relative_to(self.dst_root).as_posix()  # type: ignore
                parts = rel.split('/')
                if parts[0] == 'archive':
                    reason = 'archive/ is output-only, never written by promotion'
                elif target.stem == 'MEMORY':
                    reason = 'MEMORY.md is the owner-curated index: never writable'
                elif not (len(parts) == 2 and parts[0] == 'memory'
                          and target.suffix == '.md'):
                    reason = 'orphan-link appends target memory/*.md source pages only'
                else:
                    ok = True
        else:
            reason = 'unknown write kind: %r' % (kind,)
        rec = {'phase': self.phase, 'kind': kind, 'target': str(target),
               'allowed': ok, 'reason': '' if ok else reason}
        (self.allowed if ok else self.refused).append(rec)
        if not ok:
            raise PhaseScopeError('%s write refused in %s phase: %s (%s)'
                                  % (kind, self.phase, reason, target))
        return rec


# ---------------------------------------------------------------------------
# Trigger model
# ---------------------------------------------------------------------------

def evaluate_trigger(state: Optional[dict], session_id: Optional[str] = None,
                     min_sessions: int = TRIGGER_MIN_SESSIONS,
                     min_pages_changed: int = TRIGGER_MIN_PAGES_CHANGED) -> dict:
    """Deterministic trigger, receipted either way. state keys:
    sessions_since_last_dream, pages_changed_since_last_dream, last_dream_session.
    Missing/empty state = bootstrap (the corpus has never been dreamed over)."""
    state = state or {}
    sessions = int(state.get('sessions_since_last_dream') or 0)
    changed = int(state.get('pages_changed_since_last_dream') or 0)
    last = state.get('last_dream_session')
    reasons = []
    triggered = False
    if not last:
        triggered = True
        reasons.append('bootstrap: no prior dream recorded')
    elif session_id is not None and last == session_id:
        reasons.append('cooldown: a dream already ran in this session (no-op)')
    else:
        if sessions >= min_sessions:
            triggered = True
            reasons.append('sessions_since_last_dream %d >= %d' % (sessions, min_sessions))
        if changed >= min_pages_changed:
            triggered = True
            reasons.append('pages_changed_since_last_dream %d >= %d' % (changed, min_pages_changed))
        if not triggered:
            reasons.append('below threshold: sessions %d < %d and pages_changed %d < %d'
                           % (sessions, min_sessions, changed, min_pages_changed))
    return {'triggered': triggered, 'reasons': reasons,
            'state': {'sessions_since_last_dream': sessions,
                      'pages_changed_since_last_dream': changed,
                      'last_dream_session': last},
            'session_id': session_id,
            'rule': 'bootstrap OR sessions >= %d OR pages_changed >= %d; same-session '
                    're-run is a no-op; not triggered => Deep refuses (fail-closed)'
                    % (min_sessions, min_pages_changed)}


# ---------------------------------------------------------------------------
# Scoring (model-free; signals per contract §3)
# ---------------------------------------------------------------------------

def _idf(token: str, df: Dict[str, int], n_pages: int) -> float:
    return math.log(n_pages / max(1, df.get(token, 1)))


def _stem_set(pages: Sequence[mc.Page]) -> set:
    return {pg.stem for pg in pages}


def score_orphan_link(cand: dict, pages_by_rel: Dict[str, mc.Page], indeg,
                      df: Dict[str, int], n_pages: int, stems: set,
                      lex_sat: float = LEX_SAT) -> dict:
    """Score one orphan_inbound_link candidate. Returns signals + composite."""
    shared = list(cand.get('shared_tokens', []))
    orphan = pages_by_rel.get(cand['orphan'])
    s_lex = min(1.0, sum(_idf(t, df, n_pages) for t in shared) / lex_sat) if shared else 0.0
    s_clust = 1.0 if any(t in stems for t in shared) else 0.0
    s_auth = min(1.0, indeg.get(mc._stem(cand['source']), 0) / 10.0)
    s_sub = min(1.0, (len(orphan.data) / 2000.0)) if orphan else 0.0
    score = (W_ORPHAN['lex'] * s_lex + W_ORPHAN['clust'] * s_clust
             + W_ORPHAN['auth'] * s_auth + W_ORPHAN['sub'] * s_sub)
    return {'kind': 'orphan_inbound_link', 'orphan': cand['orphan'],
            'source': cand['source'], 'n_shared': len(shared),
            'signals': {'s_lex': round(s_lex, 4), 's_clust': s_clust,
                        's_auth': round(s_auth, 4), 's_sub': round(s_sub, 4),
                        'source_indegree': indeg.get(mc._stem(cand['source']), 0),
                        'orphan_bytes': len(orphan.data) if orphan else 0,
                        'cluster_tokens': sorted(t for t in shared if t in stems)},
            'score': round(score, 4)}


def _parse_dt(d: str) -> Optional[datetime]:
    if not d:
        return None
    try:
        return datetime.strptime(d[:19], '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        m = mc.DATE_RE.search(d)
        return datetime.strptime(m.group(0), '%Y-%m-%d') if m else None


def _marker_paragraph(page: mc.Page, excerpt: str) -> str:
    for para in mc._paragraphs(page.body):
        if excerpt and excerpt[:60] in para:
            return para
    return excerpt


def _literal_paragraph_tokens(page: mc.Page, literal: str) -> set:
    toks: set = set()
    for para in mc._paragraphs(page.body):
        if literal in para:
            toks |= set(mc._tokens(para))
    return toks


def score_supersedes_edge(cand: dict, pages_by_rel: Dict[str, mc.Page], indeg) -> dict:
    """Score one supersedes_edge candidate. s_ctx measures whether the
    correction paragraph and the superseded page's literal-bearing paragraphs
    talk about the same thing (context agreement)."""
    fs = cand.get('fact_scope', {})
    matched = [l for l in fs.get('matched_literals', [])]
    strong = [l for l in matched if not mc._WEAK_LITERAL.fullmatch(l)]
    shared = fs.get('shared_tokens', [])
    a = pages_by_rel.get(cand['successor'])
    b = pages_by_rel.get(cand['superseded'])
    s_scope = min(1.0, (len(strong) + len(shared) / 4.0) / 3.0)
    best_ctx = 0
    if a is not None and b is not None and strong:
        wa = set(mc._tokens(_marker_paragraph(a, fs.get('marker_excerpt', ''))))
        for l in strong:
            wb = _literal_paragraph_tokens(b, l)
            best_ctx = max(best_ctx, len(wa & wb))
    s_ctx = min(1.0, best_ctx / 4.0)
    da, db = _parse_dt(fs.get('a_date') or ''), _parse_dt(fs.get('b_date') or '')
    gap_days = (da - db).days if (da and db) else 0
    s_date = min(1.0, max(0, gap_days) / 14.0)
    s_auth = min(1.0, indeg.get(mc._stem(cand['successor']), 0) / 10.0)
    score = (W_EDGE['scope'] * s_scope + W_EDGE['ctx'] * s_ctx
             + W_EDGE['date'] * s_date + W_EDGE['auth'] * s_auth)
    return {'kind': 'supersedes_edge', 'successor': cand['successor'],
            'superseded': cand['superseded'],
            'signals': {'s_scope': round(s_scope, 4), 's_ctx': round(s_ctx, 4),
                        's_date': round(s_date, 4), 's_auth': round(s_auth, 4),
                        'strong_literals': strong, 'weak_literals_dropped':
                        [l for l in matched if l not in strong],
                        'ctx_shared_tokens': best_ctx, 'date_gap_days': gap_days},
            'score': round(score, 4)}


# ---------------------------------------------------------------------------
# Gates (ALL required; OpenClaw posture)
# ---------------------------------------------------------------------------

def gate_orphan_link(sc: dict, min_support: int = ORPHAN_MIN_SUPPORT,
                     min_lex: float = ORPHAN_MIN_LEX,
                     min_score: float = ORPHAN_MIN_SCORE) -> Tuple[bool, List[str]]:
    failed = []
    if sc['n_shared'] < min_support:
        failed.append('G-Support(|shared|=%d < %d)' % (sc['n_shared'], min_support))
    if sc['signals']['s_lex'] < min_lex:
        failed.append('G-Lex(%.3f < %.2f)' % (sc['signals']['s_lex'], min_lex))
    if sc['score'] < min_score:
        failed.append('G-Score(%.3f < %.2f)' % (sc['score'], min_score))
    return (not failed, failed)


def gate_supersedes_edge(sc: dict, min_ctx: float = EDGE_MIN_CTX,
                         min_score: float = EDGE_MIN_SCORE) -> Tuple[bool, List[str]]:
    failed = []
    if not sc['signals']['strong_literals']:
        failed.append('G-StrongLit(0 strong literals; weak dotted-suffix only)')
    if sc['signals']['s_ctx'] < min_ctx:
        failed.append('G-Ctx(%.3f < %.2f)' % (sc['signals']['s_ctx'], min_ctx))
    if sc['score'] < min_score:
        failed.append('G-Score(%.3f < %.2f)' % (sc['score'], min_score))
    return (not failed, failed)


# ---------------------------------------------------------------------------
# Hygiene metrics
# ---------------------------------------------------------------------------

def hygiene(pages: Sequence[mc.Page]) -> dict:
    indeg = mc.build_graph(pages)
    hist = {'0': 0, '1-2': 0, '3-4': 0, '>=5': 0}
    orphans = []
    for pg in pages:
        if pg.stem == 'MEMORY':
            continue
        d = indeg.get(pg.stem, 0)
        if d == 0:
            hist['0'] += 1
            orphans.append(pg.rel)
        elif d <= 2:
            hist['1-2'] += 1
        elif d <= 4:
            hist['3-4'] += 1
        else:
            hist['>=5'] += 1
    return {'pages': len(pages), 'orphan_count': len(orphans),
            'orphans': sorted(orphans), 'indegree_hist': hist,
            'indegree_top10': [[k, v] for k, v in indeg.most_common(10)]}


# ---------------------------------------------------------------------------
# The dreaming pass
# ---------------------------------------------------------------------------

def dream(src: Path, dst: Optional[Path] = None, work_dir: Optional[Path] = None,
          state: Optional[dict] = None, freeze: Optional[Path] = None,
          apply: bool = False, session_id: Optional[str] = None,
          gate_overrides: Optional[dict] = None,
          now: Optional[str] = None) -> dict:
    """Run one dreaming pass over a corpus COPY (never the live store).

    Dry-run by default. apply=True requires a triggered state and an explicit
    dst != src; the only corpus writes are promoted orphan-link appends (Deep
    phase, PhaseGuard-enforced). gate_overrides lowers/raises thresholds and is
    receipted loudly (mutation-control hook).
    """
    src = Path(src)
    if apply:
        if dst is None:
            raise ValueError('apply requires an explicit --dst; dreaming never writes in place')
        if Path(dst).resolve() == src.resolve():
            raise ValueError('--dst must differ from --src; the source corpus is read-only')
    ov = dict(gate_overrides or {})
    thresholds = {'trigger_min_sessions': int(ov.get('trigger_min_sessions', TRIGGER_MIN_SESSIONS)),
                  'trigger_min_pages_changed': int(ov.get('trigger_min_pages_changed',
                                                          TRIGGER_MIN_PAGES_CHANGED)),
                  'lex_sat': float(ov.get('lex_sat', LEX_SAT)),
                  'orphan_min_support': int(ov.get('orphan_min_support', ORPHAN_MIN_SUPPORT)),
                  'orphan_min_lex': float(ov.get('orphan_min_lex', ORPHAN_MIN_LEX)),
                  'orphan_min_score': float(ov.get('orphan_min_score', ORPHAN_MIN_SCORE)),
                  'edge_min_ctx': float(ov.get('edge_min_ctx', EDGE_MIN_CTX)),
                  'edge_min_score': float(ov.get('edge_min_score', EDGE_MIN_SCORE))}

    pages = mc.load_pages(src)
    binding = mc._verify_freeze(pages, Path(freeze)) if freeze else {'verified': False}
    trigger = evaluate_trigger(state, session_id=session_id,
                               min_sessions=thresholds['trigger_min_sessions'],
                               min_pages_changed=thresholds['trigger_min_pages_changed'])
    if apply and not trigger['triggered']:
        raise ValueError('dreaming trigger did not fire; Deep phase refuses '
                         '(fail-closed). Reasons: %s' % '; '.join(trigger['reasons']))

    indeg = mc.build_graph(pages)
    df = mc._df(pages)
    n_pages = len(pages)
    stems = _stem_set(pages)
    pages_by_rel = {pg.rel: pg for pg in pages}
    guard_receipts: List[dict] = []

    def run_guard(phase: str, writes: Sequence[Tuple[str, Path]]) -> None:
        g = PhaseGuard(phase, dst_root=dst if apply else None, work_dir=work_dir)
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
            scored.append(score_orphan_link(c, pages_by_rel, indeg, df, n_pages,
                                            stems, lex_sat=thresholds['lex_sat']))
        elif c['kind'] == 'supersedes_edge':
            scored.append(score_supersedes_edge(c, pages_by_rel, indeg))
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
            ok, failed = gate_orphan_link(sc, thresholds['orphan_min_support'],
                                          thresholds['orphan_min_lex'],
                                          thresholds['orphan_min_score'])
            rec = {'kind': c['kind'], 'orphan': c['orphan'], 'source': c['source'],
                   'score': sc['score'], 'signals': sc['signals'], 'applied': False}
            if ok:
                rec['explain'] = ('promote: all gates pass; append [[%s]] on %s'
                                  % (mc._stem(c['orphan']), c['source']))
                promoted.append(rec)
            else:
                rec['explain'] = 'demote: ' + '; '.join(failed)
                demoted.append(rec)
        elif c['kind'] == 'supersedes_edge':
            sc = next(s for s in scored
                      if s['kind'] == 'supersedes_edge'
                      and s['successor'] == c['successor'] and s['superseded'] == c['superseded'])
            ok, failed = gate_supersedes_edge(sc, thresholds['edge_min_ctx'],
                                              thresholds['edge_min_score'])
            rec = {'kind': c['kind'], 'successor': c['successor'],
                   'superseded': c['superseded'], 'fact_scope': c['fact_scope'],
                   'score': sc['score'], 'signals': sc['signals']}
            if ok:
                rec['explain'] = ('promote: all gates pass; review-ledger entry '
                                  '(corpus keeps both pages, fact-scoped)')
                promoted.append(rec)
            else:
                rec['explain'] = 'demote: ' + '; '.join(failed)
                demoted.append(rec)
        else:
            review_only.append({'kind': c['kind'], 'candidate': c,
                                'explain': 'review-only in v0 (no ordering evidence / human '
                                           'judgement required); carried to the ledger, '
                                           'never auto-promoted'})

    link_promotions = [p for p in promoted if p['kind'] == 'orphan_inbound_link']
    edge_promotions = [p for p in promoted if p['kind'] == 'supersedes_edge']

    # promotion -> Deep-phase writes (dry-run: computed and receipted only)
    planned_writes = [{'kind': 'orphan_link_append', 'target_page': p['source'],
                       'append': APPEND_LINE % mc._stem(p['orphan']),
                       'orphan': p['orphan']} for p in link_promotions]
    if apply:
        deep_guard = PhaseGuard('deep', dst_root=Path(dst), work_dir=work_dir)
        for w in planned_writes:
            deep_guard.check('orphan_link_append', Path(dst) / w['target_page'])  # scope check pre-write
        guard_receipts.extend(deep_guard.allowed)

    report = {
        'tool': 'agent_harness.memory_dreaming v0',
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
        'hygiene': {'before': hygiene(pages), 'after': None},
        'counts': {'candidates': len(candidates), 'scored': len(scored),
                   'promoted_orphan_links': len(link_promotions),
                   'promoted_supersedes_edges': len(edge_promotions),
                   'demoted': len(demoted), 'review_only': len(review_only),
                   'pages_mutated': 0, 'pages_archived': 0},
        'fact_preservation': {'ok': None,
                              'rule': 'every input page sha256 present in the output as a '
                                      'live page or a receipted mutation hash; H4 archives '
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
        after = before + (APPEND_LINE % mc._stem(p['orphan'])).encode('utf-8')
        (dst / src_page.rel).write_bytes(after)
        mutated.append({'path': src_page.rel, 'before_sha256': mc._sha256(before),
                        'after_sha256': mc._sha256(after),
                        'change': 'append inbound link to orphan %s (dreaming v0, promoted)'
                                  % p['orphan']})
        live_pages[p['source']] = mc.Page(src_page.rel, after)
        p['applied'] = True

    # review ledger (Deep phase, work dir scope)
    if work_dir:
        ledger = {'dream_ledger': 'v0', 'session_id': session_id,
                  'promoted_supersedes_edges': edge_promotions,
                  'promoted_orphan_links': [p['orphan'] + ' <- ' + p['source']
                                            for p in link_promotions],
                  'review_only': review_only,
                  'demoted': [{'kind': d['kind'], 'score': d['score'],
                               'explain': d['explain']} for d in demoted]}
        lg = PhaseGuard('deep', dst_root=dst, work_dir=work_dir)
        lg_path = Path(work_dir) / 'dream-ledger.json'
        md_path = Path(work_dir) / 'DREAMS.md'
        guard_receipts.append(lg.check('ledger', lg_path))
        guard_receipts.append(lg.check('ledger', md_path))
        lg_path.write_text(json.dumps(ledger, indent=2) + '\n', encoding='utf-8')
        lines = ['# DREAMS — dreaming v0 ledger (%s)' % (session_id or 'no-session'), '',
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
    report['hygiene']['after'] = hygiene(out_pages)
    if lost:
        raise ValueError('fact preservation violated; missing sha256: %s' % lost)
    return report


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog='python3 -m agent_harness.memory_dreaming')
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
        report = dream(Path(a.src), Path(a.dst) if a.dst else None,
                       Path(a.work_dir) if a.work_dir else None,
                       state=state, freeze=Path(a.freeze) if a.freeze else None,
                       apply=a.apply, session_id=a.session_id)
    except (ValueError, PhaseScopeError) as exc:
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
