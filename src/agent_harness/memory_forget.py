"""Certified unlearning + relearning for a memory corpus copy (H5, plan/v3-h5-unlearning).

Doctrine tension, resolved: the harness doctrine is archive-never-delete — but that
is the CONSOLIDATION doctrine (memory_consolidate.py): deprecation INSIDE the corpus
boundary, bytes recoverable under archive/. Certified unlearning is a distinct,
explicitly owner-authorised operation: the page's CONTENT exits the corpus boundary
entirely (moved to a hash-bound escrow outside the corpus root; the escrow exists so
relearn can restore — destroying it instead is a policy choice at the call site, and
certification enumerates it as a declared residual copy either way). What the corpus
keeps is the TOMBSTONE RECORD in an append-only hash-chained ledger
(``tombstones/ledger.jsonl``, a non-indexed suffix outside every retrieval surface):
page identity, sha256 of the erased bytes, redaction receipts, time, reason,
authority, chain hash. The chain records THAT we forgot, never WHAT — certification
asserts no content probe string appears in the ledger.

Relearn is a new ledger record superseding the tombstone, never an edit:
  - restore   — explicit reversal: the escrowed page bytes and redacted index lines
                are returned byte-identically (same authority required); the record
                binds the restored sha256 and the tombstone's pre-unlearn corpus
                root hash, so the restored state is self-verifying.
  - supersede — a brand-new page carries the new evidence; the sealed bytes stay
                escrowed; the record binds the new page's sha256.

Dry-run is the default for both operations. Certification (``certify``) is a
separate, fail-closed step that never trusts a receipt: it re-interrogates the
corpus bytes, the SQLite/FTS5 raw tables (not just the kb_live join — a stale or
permission-blocked file leaves residual rows), the retrieval surface, the
consolidation arms, and the ledger, and reports ok=False with named failed checks.

CLI:
    python3 -m agent_harness.memory_forget unlearn --corpus DIR --page REL \
        --authority STR --reason STR --escrow DIR [--freeze F] [--apply] [--out R]
    python3 -m agent_harness.memory_forget relearn --corpus DIR --page REL \
        --authority STR --reason STR --escrow DIR [--mode restore|supersede] \
        [--new-page FILE] [--apply] [--out R]
    python3 -m agent_harness.memory_forget certify --corpus DIR --page REL \
        --probes-file F [--escrow DIR] [--kb-home DIR] [--freeze F] [--out R]

Stdlib only (Python 3.9-safe), model-free, no network. Never operates on the live
memory store: the caller passes a corpus copy; freeze binding is optional but
recommended.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from agent_harness import memory_consolidate as mc

LEDGER_REL = 'tombstones/ledger.jsonl'
GENESIS_HASH = '0' * 64

REQUIRED_TOMBSTONE_FIELDS = (
    'seq', 'kind', 'page', 'page_sha256', 'page_bytes', 'created_utc',
    'authority', 'reason', 'escrow_sha256', 'redactions', 'inbound_wikilinks',
    'corpus_pages_sha256_before', 'prev_hash', 'record_hash')
REQUIRED_RELEARN_FIELDS = (
    'seq', 'kind', 'page', 'mode', 'created_utc', 'authority', 'reason',
    'supersedes_seq', 'prev_hash', 'record_hash')
# H6b additive amendment: a write-time guard (memory_guard) receipts each refused
# re-admission of tombstoned content into the SAME chain. The record carries
# identity + hashes + matched leg NAMES only — never content.
REQUIRED_BACKFLOW_REFUSED_FIELDS = (
    'seq', 'kind', 'page', 'candidate_sha256', 'tombstone_record_hash',
    'legs', 'path', 'degraded', 'created_utc', 'authority',
    'prev_hash', 'record_hash')

_WORD = re.compile(r'\w+')


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _canonical(rec: dict) -> bytes:
    """Canonical bytes for hashing: sorted keys, no record_hash inside itself."""
    return json.dumps({k: v for k, v in rec.items() if k != 'record_hash'},
                      sort_keys=True, separators=(',', ':')).encode('utf-8')


def record_hash(rec: dict) -> str:
    return _sha256(_canonical(rec))


def ledger_path(corpus_root: Path) -> Path:
    return Path(corpus_root) / LEDGER_REL


def load_ledger(corpus_root: Path) -> List[dict]:
    p = ledger_path(corpus_root)
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(encoding='utf-8').splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def verify_ledger(records: Sequence[dict]) -> List[str]:
    """Append-only chain integrity: seqs 1..n, prev_hash links, record_hash
    recomputed, required fields per kind. Any edit of an earlier record breaks
    its record_hash and every later prev_hash — both are reported."""
    problems = []
    prev = GENESIS_HASH
    for i, rec in enumerate(records, start=1):
        if rec.get('seq') != i:
            problems.append('record %d: seq %r breaks contiguity' % (i, rec.get('seq')))
        if rec.get('prev_hash') != prev:
            problems.append('record %d: prev_hash does not chain from record %d' % (i, i - 1))
        kind = rec.get('kind')
        required = {'tombstone': REQUIRED_TOMBSTONE_FIELDS,
                    'relearn': REQUIRED_RELEARN_FIELDS,
                    'backflow_refused': REQUIRED_BACKFLOW_REFUSED_FIELDS}.get(kind)
        if required is None:
            problems.append('record %d: unknown kind %r' % (i, kind))
        else:
            missing = [f for f in required if f not in rec]
            if missing:
                problems.append('record %d: missing fields %s' % (i, missing))
        if 'record_hash' not in rec:
            problems.append('record %d: no record_hash' % i)
        elif record_hash(rec) != rec['record_hash']:
            problems.append('record %d: record_hash mismatch (content edited after append)' % i)
        prev = rec.get('record_hash', prev)
    return problems


def page_states(records: Sequence[dict]) -> Dict[str, str]:
    """Latest lifecycle state per page: 'tombstoned' or 'relearned'."""
    states: Dict[str, str] = {}
    for rec in records:
        if rec.get('kind') == 'tombstone':
            states[rec['page']] = 'tombstoned'
        elif rec.get('kind') == 'relearn':
            states[rec['page']] = 'relearned'
    return states


def _latest_tombstone(records: Sequence[dict], page_rel: str) -> Optional[dict]:
    tomb = None
    for rec in records:
        if rec.get('page') != page_rel:
            continue
        if rec['kind'] == 'tombstone':
            tomb = rec
        elif rec['kind'] == 'relearn':
            tomb = None                      # superseded; a new tombstone may follow
    return tomb


def _corpus_pages_root_hash(corpus_root: Path) -> str:
    return mc.corpus_root_hash([pg.sha256 for pg in mc.load_pages(corpus_root)])


def _check_escrow_outside(corpus_root: Path, escrow_dir: Path) -> Path:
    corpus_root = Path(corpus_root).resolve()
    escrow_dir = Path(escrow_dir).resolve()
    if escrow_dir == corpus_root or corpus_root in escrow_dir.parents:
        raise ValueError('escrow must be OUTSIDE the corpus boundary: %s is inside %s'
                         % (escrow_dir, corpus_root))
    return escrow_dir


def dependency_surface(corpus_root: Path, page_rel: str) -> dict:
    """The erasure surface of a page: inbound wikilinks, MEMORY.md index lines
    naming it (redaction candidates), plain name mentions (recorded, NOT
    auto-redacted — fact-level closure on third-party pages is a separate,
    human-gated decision), and the page's own outgoing wikilinks.

    Index lines are scanned on raw BYTES and stored with their exact terminator
    ('raw'), so redaction and restore are byte-exact round-trips, verified by
    file hash."""
    corpus_root = Path(corpus_root)
    stem = Path(page_rel).stem
    pages = mc.load_pages(corpus_root)
    inbound, mentions, index_lines = [], [], []
    target = None
    for pg in pages:
        if pg.rel == page_rel:
            target = pg
            continue
        if stem in pg.links:
            inbound.append(pg.rel)
        if stem in pg.text:
            mentions.append(pg.rel)
    mem = corpus_root / 'memory/MEMORY.md'
    if mem.is_file():
        needle = stem.encode('utf-8')
        for i, raw in enumerate(mem.read_bytes().splitlines(keepends=True), start=1):
            if needle in raw:
                index_lines.append({'line_no': i,
                                    'text': raw.decode('utf-8', 'replace').rstrip('\r\n'),
                                    'raw': raw.decode('utf-8', 'replace'),
                                    'line_sha256': _sha256(raw)})
    return {'inbound_wikilinks': sorted(inbound),
            'name_mentions': sorted(mentions),
            'index_lines': index_lines,
            'outgoing_wikilinks': sorted(set(target.links)) if target else []}


def _append_record(corpus_root: Path, rec: dict) -> dict:
    records = load_ledger(corpus_root)
    rec['seq'] = len(records) + 1
    rec['prev_hash'] = records[-1]['record_hash'] if records else GENESIS_HASH
    rec['record_hash'] = record_hash(rec)
    lp = ledger_path(corpus_root)
    lp.parent.mkdir(parents=True, exist_ok=True)
    with lp.open('a', encoding='utf-8') as f:
        f.write(json.dumps(rec, sort_keys=True) + '\n')
    return rec


def append_refusal(corpus_root: Path, *, page: str, candidate_sha256: str,
                   tombstone_record_hash: str, legs: Sequence[str], path: str,
                   degraded: bool, authority: str,
                   created_utc: Optional[str] = None) -> dict:
    """H6b: receipt one refused re-admission of tombstoned content.

    Content-free by contract: the candidate is named by its sha256 only, the
    matched legs by name only. Appended to the SAME hash-chained ledger as the
    tombstone it defends, so the chain's own integrity rule protects the refusal
    history. A repeated refusal of the same candidate at the same seam is not
    re-receipted (idempotent for polling seams like Memory.sync): the existing
    record is returned instead.
    """
    corpus_root = Path(corpus_root)
    for rec in load_ledger(corpus_root):
        if (rec.get('kind') == 'backflow_refused'
                and rec.get('candidate_sha256') == candidate_sha256
                and rec.get('tombstone_record_hash') == tombstone_record_hash
                and rec.get('path') == path):
            return rec
    rec = {'kind': 'backflow_refused', 'page': page,
           'candidate_sha256': candidate_sha256,
           'tombstone_record_hash': tombstone_record_hash,
           'legs': sorted(legs), 'path': path, 'degraded': bool(degraded),
           'created_utc': created_utc or _utcnow(), 'authority': authority}
    return _append_record(corpus_root, rec)


def _redact_lines(path: Path, line_nos: Sequence[int]) -> None:
    """Remove 1-based lines, preserving every other byte exactly."""
    raw = path.read_bytes().splitlines(keepends=True)
    keep = [ln for i, ln in enumerate(raw, start=1) if i not in set(line_nos)]
    path.write_bytes(b''.join(keep))


def _restore_lines(path: Path, lines: Sequence[dict], expected_sha256: str) -> None:
    """Reinsert escrowed lines at their original 1-based positions; verify the
    reconstructed file byte-hash equals the recorded pre-redaction hash."""
    raw = path.read_bytes().splitlines(keepends=True)
    for item in sorted(lines, key=lambda d: d['line_no']):
        raw.insert(item['line_no'] - 1, item['raw'].encode('utf-8'))
    data = b''.join(raw)
    if _sha256(data) != expected_sha256:
        raise ValueError('redaction restore of %s would not reproduce the recorded '
                         'before_sha256 — refusing to write' % path)
    path.write_bytes(data)


def unlearn(corpus_root: Path, page_rel: str, *, authority: str, reason: str,
            escrow_dir: Path, apply: bool = False,
            freeze: Optional[Path] = None) -> dict:
    """Plan (dry-run, default) or execute the certified erasure of one page.

    Execute order is fail-closed: escrow bytes are written and re-verified BEFORE
    any corpus byte changes; the tombstone record is appended after the mutation;
    certify() is the independent step that proves the end state (a crash between
    steps leaves a state certification rejects — erasure without a record, or a
    record without erasure, both fail).
    """
    corpus_root = Path(corpus_root)
    page_path = corpus_root / page_rel
    if not page_path.is_file():
        raise ValueError('page not in corpus: %s' % page_rel)
    records = load_ledger(corpus_root)
    if _latest_tombstone(records, page_rel) is not None:
        raise ValueError('page is already tombstoned: %s' % page_rel)
    escrow_dir = _check_escrow_outside(corpus_root, Path(escrow_dir))

    pages = mc.load_pages(corpus_root)
    binding = mc._verify_freeze(pages, Path(freeze)) if freeze else {'verified': False}
    root_before = _corpus_pages_root_hash(corpus_root)
    data = page_path.read_bytes()
    page_sha = _sha256(data)
    surface = dependency_surface(corpus_root, page_rel)

    redactions = []
    if surface['index_lines']:
        mem = corpus_root / 'memory/MEMORY.md'
        redactions.append({'file': 'memory/MEMORY.md',
                           'before_sha256': _sha256(mem.read_bytes()),
                           'after_sha256': None,      # filled on apply
                           'lines': surface['index_lines']})

    receipt = {
        'tool': 'agent_harness.memory_forget (H5)',
        'op': 'unlearn', 'dry_run': not apply, 'created_utc': _utcnow(),
        'corpus_root': str(corpus_root), 'page': page_rel,
        'page_sha256': page_sha, 'page_bytes': len(data),
        'authority': authority, 'reason': reason, 'binding': binding,
        'dependency_surface': surface,
        'escrow': {'dir': str(escrow_dir), 'files': []},
        'corpus_pages_sha256': {'before': root_before, 'after': None},
        'declared_residuals': 'the escrow, any frozen snapshots, and the live corpus '
                              'retain the bytes; certification covers THIS corpus '
                              'root only, and enumerates rather than hides the rest',
    }

    # The planned tombstone record (written to the ledger only on apply).
    record = {
        'kind': 'tombstone', 'page': page_rel, 'page_sha256': page_sha,
        'page_bytes': len(data), 'created_utc': receipt['created_utc'],
        'authority': authority, 'reason': reason,
        'escrow_sha256': page_sha,           # the escrow file IS the page bytes
        'redactions': [{k: v for k, v in r.items() if k != 'lines'}
                       | {'line_nos': [l['line_no'] for l in r['lines']]}
                       for r in redactions] if redactions else [],
        'inbound_wikilinks': surface['inbound_wikilinks'],
        'name_mentions': surface['name_mentions'],
        'corpus_pages_sha256_before': root_before,
    }
    receipt['tombstone_record'] = record

    if not apply:
        return receipt

    # 1. escrow first: page bytes + redaction line texts, re-verified after write
    escrow_dir.mkdir(parents=True, exist_ok=True)
    page_escrow = escrow_dir / ('%s.md' % page_sha)
    page_escrow.write_bytes(data)
    if _sha256(page_escrow.read_bytes()) != page_sha:
        raise ValueError('escrow write verification failed for %s' % page_escrow)
    receipt['escrow']['files'].append(
        {'path': str(page_escrow), 'sha256': page_sha, 'what': 'page bytes'})
    if redactions:
        red_escrow = escrow_dir / ('%s.redactions.json' % page_sha)
        red_escrow.write_text(json.dumps(redactions, indent=2) + '\n', encoding='utf-8')
        receipt['escrow']['files'].append(
            {'path': str(red_escrow), 'sha256': _sha256(red_escrow.read_bytes()),
             'what': 'redacted line texts with original positions'})

    # 2. mutate the corpus: page out; index lines redacted with hash receipts
    page_path.unlink()
    for r in redactions:
        f = corpus_root / r['file']
        _redact_lines(f, [l['line_no'] for l in r['lines']])
        r['after_sha256'] = _sha256(f.read_bytes())
    for rec_red, r in zip(record['redactions'], redactions):
        rec_red['after_sha256'] = r['after_sha256']

    # 3. the audit record
    record = _append_record(corpus_root, record)
    receipt['tombstone_record'] = record
    receipt['corpus_pages_sha256']['after'] = _corpus_pages_root_hash(corpus_root)
    return receipt


def relearn(corpus_root: Path, page_rel: str, *, authority: str, reason: str,
            escrow_dir: Path, mode: str = 'restore',
            new_bytes: Optional[bytes] = None, apply: bool = False) -> dict:
    """Reverse or supersede a tombstone. Appends a relearn record; the tombstone
    itself is never edited or deleted (additive amendments only).

    restore:   the escrowed page bytes and redacted index lines return
               byte-identically; the record binds the restored sha256.
    supersede: new_bytes (new evidence) is written at page_rel; the sealed bytes
               stay escrowed; the record binds the new page's sha256.
    """
    corpus_root = Path(corpus_root)
    escrow_dir = Path(escrow_dir)
    records = load_ledger(corpus_root)
    tomb = _latest_tombstone(records, page_rel)
    if tomb is None:
        raise ValueError('page is not currently tombstoned: %s' % page_rel)
    if mode not in ('restore', 'supersede'):
        raise ValueError('unknown relearn mode: %s' % mode)

    page_escrow = escrow_dir / ('%s.md' % tomb['page_sha256'])
    receipt = {
        'tool': 'agent_harness.memory_forget (H5)',
        'op': 'relearn', 'mode': mode, 'dry_run': not apply, 'created_utc': _utcnow(),
        'corpus_root': str(corpus_root), 'page': page_rel,
        'authority': authority, 'reason': reason,
        'supersedes_record_hash': tomb['record_hash'],
    }

    if mode == 'restore':
        if not page_escrow.is_file():
            raise ValueError('escrow copy missing: %s — restore impossible' % page_escrow)
        data = page_escrow.read_bytes()
        if _sha256(data) != tomb['page_sha256']:
            raise ValueError('escrow hash mismatch: %s no longer binds to the '
                             'tombstoned page' % page_escrow)
        if (corpus_root / page_rel).is_file():
            raise ValueError('a page already occupies %s — refusing to overwrite' % page_rel)
        redactions = []
        red_escrow = escrow_dir / ('%s.redactions.json' % tomb['page_sha256'])
        if red_escrow.is_file():
            redactions = json.loads(red_escrow.read_text())
        receipt['restores_sha256'] = tomb['page_sha256']
        receipt['redactions_restored'] = [
            {'file': r['file'], 'line_nos': [l['line_no'] for l in r['lines']]}
            for r in redactions]
        new_sha = None
    else:
        if new_bytes is None:
            raise ValueError('supersede mode requires new_bytes (the new evidence)')
        if (corpus_root / page_rel).is_file():
            raise ValueError('a page already occupies %s — refusing to overwrite' % page_rel)
        data = new_bytes
        redactions = []
        new_sha = _sha256(new_bytes)
        receipt['new_page_sha256'] = new_sha
        receipt['sealed_bytes_stay_escrowed'] = str(page_escrow)

    record = {
        'kind': 'relearn', 'page': page_rel, 'mode': mode,
        'created_utc': receipt['created_utc'], 'authority': authority, 'reason': reason,
        'supersedes_seq': tomb['seq'],
        'restores_sha256': tomb['page_sha256'] if mode == 'restore' else None,
        'new_page_sha256': new_sha,
    }
    receipt['relearn_record'] = record
    if not apply:
        return receipt

    if mode == 'restore':
        (corpus_root / page_rel).parent.mkdir(parents=True, exist_ok=True)
        (corpus_root / page_rel).write_bytes(data)
        for r in redactions:
            f = corpus_root / r['file']
            _restore_lines(f, r['lines'], r['before_sha256'])
    else:
        (corpus_root / page_rel).parent.mkdir(parents=True, exist_ok=True)
        (corpus_root / page_rel).write_bytes(new_bytes)

    record = _append_record(corpus_root, record)
    receipt['relearn_record'] = record
    receipt['corpus_pages_sha256_after'] = _corpus_pages_root_hash(corpus_root)
    receipt['matches_pre_unlearn_root'] = (
        mode == 'restore'
        and receipt['corpus_pages_sha256_after'] == tomb['corpus_pages_sha256_before'])
    return receipt


# ---------------------------------------------------------------- certification

def _check(name: str, ok: bool, detail: str = '') -> dict:
    return {'name': name, 'ok': bool(ok), 'detail': detail}


def certify(corpus_root: Path, page_rel: str, *, probes: Sequence[dict],
            kb_home: Optional[Path] = None,
            kb_factory: Optional[Callable[[Path], object]] = None,
            escrow_dir: Optional[Path] = None,
            freeze: Optional[Path] = None,
            run_consolidation: bool = True) -> dict:
    """Fail-closed proof of absence for a tombstoned page. Never trusts receipts:
    re-interrogates corpus bytes, the ledger, the SQLite/FTS5 raw tables, the
    retrieval surface, and the consolidation arms.

    probes: [{'probe': str, 'kind': 'content'|'identity'|...}] — content probes
    must be absent from live pages AND from the ledger; identity probes absent
    from live pages and retrieval but REQUIRED in the ledger (the record names
    what was forgotten).
    """
    corpus_root = Path(corpus_root)
    checks: List[dict] = []
    content_probes = [p['probe'] for p in probes if p.get('kind') == 'content']
    identity_probes = [p['probe'] for p in probes if p.get('kind') == 'identity']
    gated = content_probes + identity_probes

    # ---- corpus bytes -------------------------------------------------------
    page_gone = not (corpus_root / page_rel).is_file()
    live_pages = mc.load_pages(corpus_root)
    live_hashes = {pg.sha256 for pg in live_pages}
    records = load_ledger(corpus_root)
    tomb = _latest_tombstone(records, page_rel)
    target_sha = tomb['page_sha256'] if tomb else None
    sha_present = target_sha in live_hashes if target_sha else None
    checks.append(_check(
        'file_absence', page_gone and sha_present is not True,
        'page file present=%s; tombstoned sha256 present among live pages=%s'
        % (not page_gone, sha_present)))

    leakers = {probe: [pg.rel for pg in live_pages if probe in pg.text]
               for probe in gated}
    leakers = {p: rels for p, rels in leakers.items() if rels}
    checks.append(_check('content_absence', not leakers,
                         'probe strings on live pages: %s' % leakers or 'clean'))

    # ---- the audit record ----------------------------------------------------
    problems = verify_ledger(records)
    if tomb is None:
        checks.append(_check('tombstone_integrity', False,
                             'no tombstone record for %s (erasure without a record '
                             'is indistinguishable from loss)' % page_rel))
    else:
        missing = [f for f in REQUIRED_TOMBSTONE_FIELDS if f not in tomb]
        detail = 'chain problems=%s missing=%s' % (problems, missing)
        if escrow_dir is not None:
            esc = Path(escrow_dir) / ('%s.md' % tomb['page_sha256'])
            if not esc.is_file():
                detail += '; escrow missing'
                problems.append('escrow copy missing')
            elif _sha256(esc.read_bytes()) != tomb['page_sha256']:
                detail += '; escrow hash mismatch'
                problems.append('escrow hash mismatch')
        checks.append(_check('tombstone_integrity', not problems and not missing, detail))

    ledger_bytes = ledger_path(corpus_root).read_bytes() if ledger_path(corpus_root).is_file() else b''
    ledger_leaks = [p for p in content_probes if p.encode() in ledger_bytes]
    identity_recorded = all(p in tomb.get('page', '') or p.encode() in ledger_bytes
                            for p in identity_probes) if tomb else False
    checks.append(_check('content_free_record', not ledger_leaks,
                         'content probes in ledger: %s' % ledger_leaks or 'clean; '
                         'identity recorded=%s' % identity_recorded))

    # ---- the index raw tables + retrieval surface ----------------------------
    kb = None
    try:
        if kb_factory is not None:
            kb = kb_factory(corpus_root)
        else:
            from agent_harness.mcp import kb as kb_mod
            if kb_home is None:
                raise ValueError('certify needs kb_home or kb_factory')
            kb = kb_mod.KB(home=Path(kb_home), paths=[corpus_root / 'memory'],
                           db_path=Path(kb_home) / 'index.sqlite')
        kb.refresh()
        c = kb.con
        n_sec = c.execute('SELECT COUNT(*) FROM kb_sections WHERE rel=?',
                          (page_rel,)).fetchone()[0]
        n_files = c.execute('SELECT COUNT(*) FROM kb_files WHERE rel=?',
                            (page_rel,)).fetchone()[0]
        fts_hits = []
        if kb.fts:
            for probe in gated:
                toks = sorted({t for t in (w.lower() for w in _WORD.findall(probe))
                               if len(t) > 2})
                if not toks:
                    continue
                n = c.execute('SELECT COUNT(*) FROM kb_fts WHERE kb_fts MATCH ?',
                              (' AND '.join('"%s"' % t.replace('"', '') for t in toks),)
                              ).fetchone()[0]
                if n:
                    fts_hits = [r[0] for r in c.execute(
                        'SELECT s.rel FROM kb_fts f JOIN kb_sections s ON s.rowid=f.rowid '
                        'WHERE kb_fts MATCH ? LIMIT 5',
                        (' AND '.join('"%s"' % t.replace('"', '') for t in toks),))]
                    fts_hits.append((probe, n, fts_hits))
        # instr over cached bodies: exact substring absence in the index
        instr_hits = {p: c.execute('SELECT COUNT(*) FROM kb_sections WHERE instr(body,?)>0',
                                   (p,)).fetchone()[0] for p in gated}
        instr_hits = {p: n for p, n in instr_hits.items() if n}
        try:
            kb.get(page_rel)
            get_absent = False
        except KeyError:
            get_absent = True
        except Exception:
            get_absent = False
        toc_has = any(e['path'] == page_rel for e in kb.toc())
        checks.append(_check(
            'index_absence',
            n_sec == 0 and n_files == 0 and not fts_hits and not instr_hits
            and get_absent and not toc_has,
            'sections=%d files=%d fts_probe_hits=%s instr=%s kb_get_absent=%s toc_has=%s'
            % (n_sec, n_files, fts_hits or 0, instr_hits or 0, get_absent, toc_has)))

        retr = {}
        for probe in gated:
            hits = kb.search(probe, k=10)
            bad = [h for h in hits
                   if h['path'] == page_rel or probe in h.get('snippet', '')]
            retr[probe] = {'hits': len(hits), 'bad': bad}
        bad_retr = {p: r['bad'] for p, r in retr.items() if r['bad']}
        checks.append(_check('retrieval_absence', not bad_retr,
                             'probe hits naming the target or quoting it: %s'
                             % bad_retr or 'clean'))
    except Exception as exc:                                  # fail closed
        checks.append(_check('index_absence', False, 'exception: %r' % exc))
        checks.append(_check('retrieval_absence', False, 'exception: %r' % exc))
    finally:
        if kb is not None and kb_factory is None:
            kb.close()

    # ---- consolidation arms ---------------------------------------------------
    if run_consolidation:
        try:
            rep = mc.consolidate(corpus_root, apply=False)
            stem = Path(page_rel).stem
            touching = [a.get('kind') for a in rep['actions']
                        if stem in json.dumps(a) or page_rel in json.dumps(a)]
            in_retention = any(r['path'] == page_rel for r in rep['retention'])
            ledger_as_page = any('tombstones' in r['path'] for r in rep['retention'])
            checks.append(_check(
                'consolidation_skip',
                not touching and not in_retention and not ledger_as_page,
                'actions naming target=%s; in retention=%s; ledger treated as page=%s; '
                'pages=%d' % (touching, in_retention, ledger_as_page, rep['pages'])))
        except Exception as exc:
            checks.append(_check('consolidation_skip', False, 'exception: %r' % exc))

    # ---- everything else preserved (optional freeze binding) ------------------
    if freeze is not None:
        try:
            doc = json.loads(Path(freeze).read_text())
            recorded = {r['path']: r for r in doc['corpus']['pages']}
            live = {pg.rel: pg for pg in live_pages}
            redacted = {r['file']: r for r in (tomb or {}).get('redactions', [])}
            lost, drifted = [], []
            for rel, r in recorded.items():
                if rel == page_rel:
                    continue
                cur = live.get(rel)
                if cur is None:
                    lost.append(rel)
                elif rel in redacted:
                    if cur.sha256 != redacted[rel]['after_sha256'] \
                            or r['sha256'] != redacted[rel]['before_sha256']:
                        drifted.append(rel)
                elif cur.sha256 != r['sha256']:
                    drifted.append(rel)
            extra = sorted(set(live) - set(recorded))
            checks.append(_check('others_preserved', not lost and not drifted and not extra,
                                 'lost=%s drifted=%s extra=%s' % (lost, drifted, extra)))
        except Exception as exc:
            checks.append(_check('others_preserved', False, 'exception: %r' % exc))

    ok = all(c['ok'] for c in checks)
    return {
        'tool': 'agent_harness.memory_forget certify (H5)',
        'created_utc': _utcnow(), 'corpus_root': str(corpus_root), 'page': page_rel,
        'ok': ok, 'checks': checks,
        'binding': {
            'ledger_sha256': _sha256(ledger_bytes) if ledger_bytes else None,
            'module_sha256': _sha256(Path(__file__).read_bytes()),
            'consolidate_module_sha256': _sha256(Path(mc.__file__).read_bytes()),
            'freeze_json_sha256': _sha256(Path(freeze).read_bytes()) if freeze else None,
        },
        'erasure_levels': {
            'L1_content': 'content probes absent from live pages, ledger, index, retrieval',
            'L2_identity': 'identity probes absent from live pages and retrieval; '
                           'identity is preserved in the non-indexed ledger by design',
            'L3_existence': 'NOT claimed: the ledger names the page; GDPR-grade '
                            'pseudonymised records are future work',
        },
        'declared_residuals': 'certification covers this corpus root; escrow, frozen '
                              'snapshots and the live corpus are enumerated residuals',
    }


# ---------------------------------------------------------------- CLI

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog='python3 -m agent_harness.memory_forget')
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('unlearn', 'relearn'):
        sp = sub.add_parser(name)
        sp.add_argument('--corpus', required=True)
        sp.add_argument('--page', required=True)
        sp.add_argument('--authority', required=True)
        sp.add_argument('--reason', required=True)
        sp.add_argument('--escrow', required=True)
        sp.add_argument('--apply', action='store_true')
        sp.add_argument('--out')
        if name == 'unlearn':
            sp.add_argument('--freeze')
        else:
            sp.add_argument('--mode', default='restore', choices=['restore', 'supersede'])
            sp.add_argument('--new-page')
    sp = sub.add_parser('certify')
    sp.add_argument('--corpus', required=True)
    sp.add_argument('--page', required=True)
    sp.add_argument('--probes-file', required=True)
    sp.add_argument('--escrow')
    sp.add_argument('--kb-home')
    sp.add_argument('--freeze')
    sp.add_argument('--no-consolidation', action='store_true')
    sp.add_argument('--out')
    a = ap.parse_args(argv)

    try:
        if a.cmd == 'unlearn':
            out = unlearn(Path(a.corpus), a.page, authority=a.authority, reason=a.reason,
                          escrow_dir=Path(a.escrow), apply=a.apply,
                          freeze=Path(a.freeze) if a.freeze else None)
        elif a.cmd == 'relearn':
            new_bytes = Path(a.new_page).read_bytes() if a.new_page else None
            out = relearn(Path(a.corpus), a.page, authority=a.authority, reason=a.reason,
                          escrow_dir=Path(a.escrow), mode=a.mode,
                          new_bytes=new_bytes, apply=a.apply)
        else:
            pdoc = json.loads(Path(a.probes_file).read_text())
            probes = pdoc['probes'] if isinstance(pdoc, dict) else pdoc
            out = certify(Path(a.corpus), a.page, probes=probes,
                          escrow_dir=Path(a.escrow) if a.escrow else None,
                          kb_home=Path(a.kb_home) if a.kb_home else None,
                          freeze=Path(a.freeze) if a.freeze else None,
                          run_consolidation=not a.no_consolidation)
    except ValueError as exc:
        print('REFUSED: %s' % exc, file=sys.stderr)
        return 2
    text = json.dumps(out, indent=2) + '\n'
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text, encoding='utf-8')
    if a.cmd == 'certify':
        print(json.dumps({'ok': out['ok'],
                          'failed': [c['name'] for c in out['checks'] if not c['ok']]},
                         indent=2))
        return 0 if out['ok'] else 1
    print(json.dumps({'op': out['op'], 'dry_run': out['dry_run'], 'page': out['page'],
                      'binding_verified': out.get('binding', {}).get('verified', None)},
                     indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
