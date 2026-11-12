"""Model-free memory consolidation pass v0 (H1, plan/v3-h1-consolidation node 7).

Operates on a COPY of a memory corpus (e.g. the frozen H1 snapshot), never on
the live store. Four arms, all model-free and stdlib-only:

  1. dup merge        — exact content-hash duplicates only: the loser moves to
                        ``archive/`` (never deleted). Near-duplicates (5-gram
                        shingle Jaccard >= 0.6) are *flagged for review*, never
                        auto-merged: one negation or number can change a fact.
  2. supersedes       — cross-page edge candidates: a newer page whose
                        correction/deprecation paragraph quotes a literal that
                        an older page still carries. Edges are fact-scoped
                        (the shared literals/tokens ARE the scope): the
                        superseded page stays authoritative for everything
                        else. Receipt-only in v0; no bytes change.
  3. conflict flags   — a page carrying withdrawal/negation language about a
                        literal that a newer page instructs. Receipt-only.
  4. reference-weighted decay — retention classes from wikilink in-degree
                        (load-bearing), NEVER recency alone: high in-degree
                        pages are protected regardless of age; orphans get
                        inbound-link *integration* proposals, not archival.
                        The only archivable pages are exact-dup losers.

Dry-run is the default: all actions are computed and receipted, no byte moves.
``apply=True`` requires an explicit separate destination directory. Every run
is hash-bound (optionally verified against a freeze manifest) and writes a
receipt with per-page before/after sha256 and an output root hash.

Fact preservation invariant (checked on apply): every input page's sha256 is
present in the output either as a live page or under ``archive/``.

Usage counters: corpus pages carry none (they live in the MCP index of the
harness's separate JSON memory store — corpus-survey-20261110 finding), so the
decay signal is the wikilink graph alone; the receipt records this.

CLI:
    python3 -m agent_harness.memory_consolidate --src CORPUS [--freeze FREEZE_JSON]
        [--apply --dst DIR] [--out REPORT_JSON]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

SHINGLE = 5
NEAR_DUP_JACCARD = 0.6          # survey convention; near-dups are review flags, never merges
PROTECTED_INDEGREE = 5          # load-bearing threshold: never a decay candidate
ORPHAN_LINK_MIN_SHARED = 3      # distinctive shared tokens needed to propose an inbound link
ORPHAN_LINK_MAX_PER_ORPHAN = 3  # inbound proposals per orphan
ORPHAN_LINK_MAX_PER_SOURCE = 2  # a popular page is not stuffed with orphan links
DATE_RE = re.compile(r'20\d\d-\d\d-\d\d')

# A "correction" paragraph explicitly says an earlier statement was wrong or
# replaced. Deliberately narrow: 'correct' as an adjective does not match.
MARKER_CORRECTION = re.compile(
    r'(?i)\b(supersed\w+|corrects\b|corrected\b|correction\b|retract\w*|was wrong\b|'
    r'were wrong\b|replaced by|replaces the|no longer true)\b')
# A "withdrawal/deprecation" paragraph forbids or retires a named thing.
MARKER_WITHDRAWAL = re.compile(
    r'(?i)\b(withdrawn|never\b.{0,40}\b(?:use|change|touch|run|propose)|'
    r'should not be re-?proposed|no longer\b|must not\b|stop using)\b')
# Bare "do not" is mostly narrative ("a password I do not handle") — it only
# counts in imperative position: start of a line/bullet, or right after : ; —.
MARKER_DO_NOT_IMPERATIVE = re.compile(
    r'(?im)(?:^\s*(?:[-*>]|\*\*|#+)?\s*|[:;—]\s*)do not\b')

_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{1,}")
_STOP = frozenset(
    """the a an and or of to in on for with without is are was were be been being it its this that
    these those i you he she we they them his her their our your my me him us not no never do does did
    have has had can could will would should must may might shall if then else when where which who
    whom why how what all any both each few more most other some such only own same so than too very
    just but by from at as into over under again further once here there about above below between
    use used using user users page pages see related note notes true false none yes new old via per
    """.split())


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _stem(path: str) -> str:
    return Path(path).stem


def _wikilinks(text: str) -> List[str]:
    return re.findall(r'\[\[([^\]]+)\]\]', text)


def _frontmatter_modified(text: str) -> str:
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end > 0:
            m = re.search(r'^\s*modified:\s*(\S+)', text[3:end], re.M)
            if m:
                return m.group(1).strip()
    return ''


def _body(text: str) -> str:
    """Page content without the frontmatter block: metadata keys are not content."""
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end > 0:
            return text[end + 4:]
    return text


def _tokens(text: str) -> List[str]:
    out = []
    for m in _WORD.finditer(text):
        w = m.group(0).lower().strip('.-_')
        if w and w not in _STOP and len(w) > 2:
            out.append(w)
    return out


def _shingles(text: str) -> Set[Tuple[str, ...]]:
    words = re.findall(r'\w+', text.lower())
    return set(tuple(words[i:i + SHINGLE]) for i in range(max(0, len(words) - SHINGLE + 1)))


def _jaccard(a: Set, b: Set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _paragraphs(text: str) -> List[str]:
    return [p for p in re.split(r'\n\s*\n', text) if p.strip()]


def _literals(text: str) -> Set[str]:
    """Quoted/backticked spans, LAN dotted suffixes and measured figures — the
    form in which this corpus pins a checkable claim."""
    out: Set[str] = set()
    out.update(m.group(1) for m in re.finditer(r'`([^`]{3,})`', text))
    out.update(m.group(1) for m in re.finditer(r'"([^"]{3,})"', text))
    out.update(m.group(0) for m in re.finditer(r'(?<![\w/])\.\d{1,3}\b', text))
    out.update(m.group(0) for m in re.finditer(
        r'\b\d+(?:\.\d+)?\s?(?:Mb/s|MB/s|Gb/s|GB|TB|MB|Gb|Mb|GiB|MiB)\b', text))
    return {t.strip() for t in out if len(t.strip()) >= 3}


_WEAK_LITERAL = re.compile(r'\.\d{1,3}')  # LAN dotted suffix: deictic, weak scope evidence


def _scope_ok(matched: Sequence[str], shared: Sequence[str]) -> bool:
    """Fact-scope sufficiency. A strong literal (backtick/quote/measurement) plus
    2 distinctive shared tokens suffices; when every matched literal is a bare
    dotted suffix (.10/.18 — meaningful only inside the LAN map) demand 3."""
    strong = any(not _WEAK_LITERAL.fullmatch(l) for l in matched)
    return len(shared) >= (2 if strong else 3)


class Page:
    def __init__(self, rel: str, data: bytes):
        self.rel = rel
        self.data = data
        self.sha256 = _sha256(data)
        self.text = data.decode('utf-8', 'replace')
        self.body = _body(self.text)
        self.stem = _stem(rel)
        self.modified = _frontmatter_modified(self.text)
        self.links = _wikilinks(self.body)
        self.shingles = _shingles(self.body)
        self.token_set = set(_tokens(self.body))

    def to_dict(self) -> dict:
        return {'path': self.rel, 'bytes': len(self.data), 'sha256': self.sha256,
                'modified': self.modified}


def load_pages(root: Path) -> List[Page]:
    """All *.md under root, sorted by relpath; an archive/ subfolder is output, not input."""
    pages = []
    for p in sorted(root.rglob('*.md')):
        rel = p.relative_to(root).as_posix()
        if rel.split('/', 1)[0] == 'archive':
            continue
        pages.append(Page(rel, p.read_bytes()))
    return pages


def corpus_root_hash(digests: Sequence[str]) -> str:
    """Freeze/survey convention: sha256 over the concatenated per-page hex digests."""
    return hashlib.sha256(''.join(digests).encode()).hexdigest()


def build_graph(pages: Sequence[Page]) -> Counter:
    """Wikilink in-degree, survey convention: raw [[target]] matched against page stems."""
    indeg: Counter = Counter()
    for pg in pages:
        for link in pg.links:
            indeg[link] += 1
    return indeg


def _distinctive_df_cap(n_pages: int) -> int:
    return max(2, int(math.ceil(0.06 * n_pages)))


def _df(pages: Sequence[Page]) -> Dict[str, int]:
    df: Dict[str, int] = {}
    for pg in pages:
        for t in pg.token_set:
            df[t] = df.get(t, 0) + 1
    return df


def _shared_distinctive(a: Page, b: Page, df: Dict[str, int], cap: int) -> Set[str]:
    return {t for t in (a.token_set & b.token_set) if 2 <= df.get(t, 0) <= cap}


def _literal_df(pages: Sequence[Page]) -> Dict[str, int]:
    """Document frequency of every literal that appears in a marker paragraph.
    A literal carried by many pages (`.py`, `find`, `fix`, `.18`) is corpus
    vocabulary, not a fact scope; the arms only trust literals with df <= cap."""
    cand: Set[str] = set()
    for pg in pages:
        corrections, withdrawals = _marker_paragraphs(pg)
        for para in corrections + withdrawals:
            cand |= _literals(para)
    return {l: sum(1 for pg in pages if l in pg.body) for l in cand}


# --------------------------------------------------------------------------- arms

def arm_dup_merge(pages: Sequence[Page], indeg: Counter) -> Tuple[List[dict], List[dict]]:
    """Exact duplicates -> merge action (archive the loser, keep the most load-bearing).
    Near duplicates -> review flag only."""
    merges, flags = [], []
    by_hash: Dict[str, List[Page]] = {}
    for pg in pages:
        by_hash.setdefault(pg.sha256, []).append(pg)
    for h, group in sorted(by_hash.items()):
        if len(group) < 2:
            continue
        keeper = sorted(group, key=lambda p: (-indeg.get(p.stem, 0), p.rel))[0]
        losers = [p for p in group if p is not keeper]
        merges.append({'kind': 'dup_merge', 'keeper': keeper.rel,
                       'archive': [p.rel for p in losers], 'sha256': h,
                       'rule': 'keeper = highest wikilink in-degree, ties broken by relpath'})
    for i in range(len(pages)):
        for j in range(i + 1, len(pages)):
            if pages[i].sha256 == pages[j].sha256:
                continue  # byte-identical pairs are exact dups, not near-dup noise
            sim = _jaccard(pages[i].shingles, pages[j].shingles)
            if sim >= NEAR_DUP_JACCARD:
                flags.append({'kind': 'near_dup_review', 'a': pages[i].rel, 'b': pages[j].rel,
                              'jaccard': round(sim, 3),
                              'rule': 'near-duplicates are flagged for human review, never merged'})
    return merges, flags


def _marker_paragraphs(pg: Page) -> Tuple[List[str], List[str]]:
    corrections, withdrawals = [], []
    for para in _paragraphs(pg.body):
        if MARKER_CORRECTION.search(para):
            corrections.append(para)
        if MARKER_WITHDRAWAL.search(para) or MARKER_DO_NOT_IMPERATIVE.search(para):
            withdrawals.append(para)
    return corrections, withdrawals


def _effective_date(pg: Page, paras: Sequence[str]) -> str:
    """Ordering evidence: frontmatter modified, else the newest date inside the
    page's own marker paragraphs. '' means no usable ordering evidence."""
    if pg.modified:
        return pg.modified
    dates = sorted(d for para in paras for d in DATE_RE.findall(para))
    return dates[-1] if dates else ''


def arm_supersedes(pages: Sequence[Page], df: Dict[str, int], cap: int,
                   lit_df: Dict[str, int]) -> Tuple[List[dict], List[dict]]:
    """Edge candidate successor A -> superseded B when one correction paragraph
    in A quotes a rare literal that older B still carries, and the pages share
    distinctive tokens. Scoping is per paragraph: one marker paragraph is one
    correction event; literals common across the corpus (df > cap) are not
    evidence. The matched literals and tokens are the recorded fact scope: B
    stays authoritative for everything outside it. Undirected pairs (no
    ordering evidence) are reported as version candidates instead of guessed
    edges. MEMORY.md is the hand-curated index, not a fact page: excluded."""
    edges, candidates = [], []
    pages = [p for p in pages if p.stem != 'MEMORY']
    for a in pages:
        corrections, _ = _marker_paragraphs(a)
        for para in corrections:
            lits = {l for l in _literals(para) if lit_df.get(l, 0) <= cap}
            if not lits:
                continue
            a_date = _effective_date(a, [para])
            for b in pages:
                if b is a:
                    continue
                matched = sorted(l for l in lits if l in b.body)
                if not matched:
                    continue
                shared = sorted(_shared_distinctive(a, b, df, cap))
                if not _scope_ok(matched, shared):
                    continue
                b_date = _effective_date(b, [])
                evidence = {'matched_literals': matched[:8], 'shared_tokens': shared[:12],
                            'a_date': a_date or None, 'b_date': b_date or None,
                            'marker_excerpt': para.strip().splitlines()[0][:200]}
                if a_date and b_date and a_date > b_date:
                    edges.append({'kind': 'supersedes_edge', 'successor': a.rel,
                                  'superseded': b.rel, 'fact_scope': evidence,
                                  'rule': 'fact-scoped: superseded page retained and stays '
                                          'authoritative outside the matched scope'})
                else:
                    candidates.append({'kind': 'version_candidate_undirected', 'a': a.rel, 'b': b.rel,
                                       'fact_scope': evidence,
                                       'rule': 'no reliable ordering evidence; not directed'})
    return edges, candidates


def arm_conflicts(pages: Sequence[Page], df: Dict[str, int], cap: int,
                  lit_df: Dict[str, int]) -> List[dict]:
    """Flag pairs where an older page's withdrawal paragraph forbids a rare
    literal that a newer page still instructs. Per-paragraph scoping and the
    literal df guard apply as in arm_supersedes. Flags are review records;
    neither page is changed. MEMORY.md is excluded both ways."""
    flags = []
    pages = [p for p in pages if p.stem != 'MEMORY']
    for a in pages:
        _, withdrawals = _marker_paragraphs(a)
        for para in withdrawals:
            lits = {l for l in _literals(para) if lit_df.get(l, 0) <= cap}
            if not lits:
                continue
            a_date = _effective_date(a, [para])
            for b in pages:
                if b is a:
                    continue
                b_date = _effective_date(b, [])
                if a_date and b_date and b_date <= a_date:
                    continue  # conflict = the NEWER page still instructs it
                matched = sorted(l for l in lits if l in b.body)
                if not matched:
                    continue
                shared = sorted(_shared_distinctive(a, b, df, cap))
                if not _scope_ok(matched, shared):
                    continue
                flags.append({'kind': 'conflict_flag', 'withdrawing_page': a.rel,
                              'instructing_page': b.rel,
                              'fact_scope': {'matched_literals': matched[:8],
                                             'shared_tokens': shared[:12],
                                             'a_date': a_date or None, 'b_date': b_date or None,
                                             'withdrawal_excerpt': para.strip().splitlines()[0][:200]},
                              'rule': 'review record only; neither page is changed by v0'})
    return flags


def arm_decay(pages: Sequence[Page], indeg: Counter, df: Dict[str, int], cap: int,
              indeg_stem: Optional[Counter] = None) -> Tuple[List[dict], List[dict]]:
    """Reference-weighted retention. Recency is NEVER the sole signal:
    protected = in-degree >= PROTECTED_INDEGREE (regardless of age);
    orphans (in-degree 0) get inbound-link integration proposals from their
    closest non-orphan neighbours (graph connectivity, the actual deficit —
    BM25 already ranks these pages on content). MEMORY.md is the owner's
    hand-curated index: never mutated by v0."""
    retention, proposals = [], []
    for pg in pages:
        d = indeg.get(pg.stem, 0)
        retention.append({'path': pg.rel, 'indegree': d,
                          'class': 'protected' if d >= PROTECTED_INDEGREE
                                   else ('orphan' if d == 0 and pg.stem != 'MEMORY' else 'retained')})
    non_orphans = [pg for pg in pages
                   if indeg.get(pg.stem, 0) > 0 and pg.stem != 'MEMORY']
    per_source: Counter = Counter()
    for pg in pages:
        if pg.stem == 'MEMORY' or indeg.get(pg.stem, 0) != 0:
            continue
        scored = []
        for src in non_orphans:
            shared = _shared_distinctive(pg, src, df, cap)
            if len(shared) >= ORPHAN_LINK_MIN_SHARED:
                scored.append((len(shared), sorted(shared), src))
        scored.sort(key=lambda x: (-x[0], x[2].rel))
        picked = 0
        for _, shared, src in scored:
            if picked >= ORPHAN_LINK_MAX_PER_ORPHAN:
                break
            if per_source[src.rel] >= ORPHAN_LINK_MAX_PER_SOURCE:
                continue
            if pg.stem in src.links:
                continue
            per_source[src.rel] += 1
            picked += 1
            proposals.append({'kind': 'orphan_inbound_link', 'orphan': pg.rel, 'source': src.rel,
                              'shared_tokens': shared,
                              'rule': 'append a [[wikilink]] on the source page pointing at the '
                                      'orphan; page names are the only tokens added'})
    return retention, proposals


# --------------------------------------------------------------------------- the pass

def _verify_freeze(pages: Sequence[Page], freeze_path: Path) -> dict:
    doc = json.loads(Path(freeze_path).read_text())
    recorded = {r['path']: r for r in doc['corpus']['pages']}
    live = {pg.rel: pg for pg in pages}
    problems = []
    if set(recorded) != set(live):
        problems.append('page set differs from freeze: missing=%s extra=%s'
                        % (sorted(set(recorded) - set(live)), sorted(set(live) - set(recorded))))
    for rel, pg in live.items():
        r = recorded.get(rel)
        if r and (r['sha256'] != pg.sha256 or r['bytes'] != len(pg.data)):
            problems.append('hash mismatch vs freeze: %s' % rel)
    order = doc['corpus']['page_order']
    if not problems and all(rel in live for rel in order):
        # the freeze orders pages memory/*.md then root *.md; compare by digest multiset per order
        by_rel = {pg.rel: pg.sha256 for pg in pages}
        if corpus_root_hash([by_rel[rel] for rel in order]) != doc['corpus']['corpus_sha256']:
            problems.append('corpus root hash differs from freeze')
    if problems:
        raise ValueError('freeze binding failed: ' + '; '.join(problems))
    return {'freeze_json': str(freeze_path),
            'freeze_json_sha256': _sha256(Path(freeze_path).read_bytes()),
            'corpus_sha256': doc['corpus']['corpus_sha256'], 'verified': True}


def consolidate(src: Path, dst: Optional[Path] = None, freeze: Optional[Path] = None,
                apply: bool = False) -> dict:
    """Run the v0 pass. Dry-run unless apply=True; apply requires dst != src."""
    src = Path(src)
    if apply:
        if dst is None:
            raise ValueError('apply requires an explicit --dst; the pass never writes in place')
        if Path(dst).resolve() == src.resolve():
            raise ValueError('--dst must differ from --src; the source corpus is read-only')
    pages = load_pages(src)
    binding = _verify_freeze(pages, Path(freeze)) if freeze else {'verified': False}
    indeg = build_graph(pages)
    df = _df(pages)
    cap = _distinctive_df_cap(len(pages))

    merges, near_flags = arm_dup_merge(pages, indeg)
    arm_pages = [p for p in pages if p.stem != 'MEMORY']  # index page: no fact scopes
    lit_df = _literal_df(arm_pages)
    edges, version_candidates = arm_supersedes(pages, df, cap, lit_df)
    conflicts = arm_conflicts(pages, df, cap, lit_df)
    retention, link_proposals = arm_decay(pages, indeg, df, cap)
    # never propose inbound links to a page this same pass is archiving
    archived_rels = {rel for m in merges for rel in m['archive']}
    link_proposals = [p for p in link_proposals if p['orphan'] not in archived_rels]

    actions: List[dict] = []
    for m in merges:
        m['applied'] = False
        actions.append(m)
    for f in near_flags + edges + version_candidates + conflicts:
        f['applied'] = False
        actions.append(f)  # receipt-only arms never apply bytes
    for p in link_proposals:
        p['applied'] = False
        actions.append(p)

    report = {
        'tool': 'agent_harness.memory_consolidate v0',
        'created_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'dry_run': not apply,
        'src': str(src),
        'dst': str(dst) if dst else None,
        'binding': binding,
        'usage_signal': {'available': False,
                         'note': 'corpus pages carry no uses counters (they live in the MCP '
                                 'index of the separate harness JSON memory store — survey '
                                 '2026-11-10); decay is weighted by wikilink in-degree only, '
                                 'never recency alone'},
        'pages': len(pages),
        'counts': {'exact_dup_groups': len(merges), 'near_dup_review': len(near_flags),
                   'supersedes_edges': len(edges),
                   'version_candidates_undirected': len(version_candidates),
                   'conflict_flags': len(conflicts),
                   'orphan_inbound_link_proposals': len(link_proposals),
                   'pages_archived': 0, 'pages_mutated': 0},
        'actions': actions,
        'retention': retention,
        'output': {'root_sha256': None, 'archived': [], 'mutated': []},
        'fact_preservation': {'ok': None,
                              'rule': 'every input page sha256 must be present in the output '
                                      'as a live page or under archive/'},
    }

    if not apply:
        report['output']['root_sha256'] = corpus_root_hash([pg.sha256 for pg in pages])
        return report

    # ---- apply on the destination copy ------------------------------------
    dst = Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    if freeze:  # the copy must still match the freeze before any mutation
        _verify_freeze(load_pages(dst), Path(freeze))

    archived, mutated = [], []
    live_pages = {pg.rel: pg for pg in load_pages(dst)}

    for m in merges:
        for loser_rel in m['archive']:
            src_file = dst / loser_rel
            if not src_file.is_file():  # already archived by an earlier group
                continue
            data = src_file.read_bytes()
            arc = dst / 'archive' / loser_rel
            arc.parent.mkdir(parents=True, exist_ok=True)
            arc.write_bytes(data)
            src_file.unlink()
            archived.append({'path': loser_rel, 'sha256': _sha256(data),
                             'archive_path': arc.relative_to(dst).as_posix()})
            live_pages.pop(loser_rel, None)
            m['applied'] = True

    for p in link_proposals:
        src_page = live_pages.get(p['source'])
        if src_page is None:
            continue
        line = '\nRelated (consolidation v0, model-free): [[%s]]\n' % _stem(p['orphan'])
        before = src_page.data
        after = before + line.encode('utf-8')
        (dst / src_page.rel).write_bytes(after)
        mutated.append({'path': src_page.rel, 'before_sha256': _sha256(before),
                        'after_sha256': _sha256(after),
                        'change': 'append inbound link to orphan %s' % p['orphan']})
        live_pages[p['source']] = Page(src_page.rel, after)
        p['applied'] = True

    out_pages = load_pages(dst)
    out_hashes = {pg.sha256 for pg in out_pages}
    for f in sorted((dst / 'archive').rglob('*.md')) if (dst / 'archive').is_dir() else []:
        out_hashes.add(_sha256(f.read_bytes()))
    in_hashes = {pg.sha256 for pg in pages}
    mutated_before = {m['before_sha256'] for m in mutated}
    lost = sorted(h for h in in_hashes - out_hashes if h not in mutated_before)
    report['fact_preservation'] = {'ok': not lost, 'lost_sha256': sorted(lost),
                                   'rule': report['fact_preservation']['rule']
                                   + '; a mutated page\'s pre-mutation sha256 is receipted '
                                     'in output.mutated[].before_sha256'}
    report['counts']['pages_archived'] = len(archived)
    report['counts']['pages_mutated'] = len(mutated)
    report['output'] = {'root_sha256': corpus_root_hash([pg.sha256 for pg in out_pages]),
                        'archived': archived, 'mutated': mutated}
    if lost:
        raise ValueError('fact preservation violated; missing sha256: %s' % lost)
    return report


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog='python3 -m agent_harness.memory_consolidate')
    ap.add_argument('--src', required=True, help='corpus copy to read (never mutated)')
    ap.add_argument('--freeze', help='freeze manifest to hash-bind and verify against')
    ap.add_argument('--apply', action='store_true', help='write a consolidated copy (default: dry-run)')
    ap.add_argument('--dst', help='destination directory for --apply (required then)')
    ap.add_argument('--out', help='write the receipt JSON here')
    a = ap.parse_args(argv)
    try:
        report = consolidate(Path(a.src), Path(a.dst) if a.dst else None,
                             Path(a.freeze) if a.freeze else None, apply=a.apply)
    except ValueError as exc:
        print('REFUSED: %s' % exc, file=sys.stderr)
        return 2
    text = json.dumps(report, indent=2) + '\n'
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text, encoding='utf-8')
    c = report['counts']
    print(json.dumps({'dry_run': report['dry_run'], 'pages': report['pages'],
                      'binding_verified': report['binding'].get('verified', False),
                      'counts': c,
                      'fact_preservation_ok': report['fact_preservation']['ok']}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
