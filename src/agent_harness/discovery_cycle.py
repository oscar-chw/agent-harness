"""Bounded official-source discovery, separate from release installation and learning promotion.

A daily invocation records a proposal. It never executes retrieved instructions,
changes routing, starts models, installs packages or promotes learned procedures.
"""
from __future__ import annotations

import hashlib
import gzip
import os
import tempfile
import json
import math
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from . import installer as I, routing

SOURCES = ('https://learn.chatgpt.com/docs/models.md',
           'https://learn.chatgpt.com/docs/llms.txt')
DAY = 86400
MAX_BYTES = 262144
MAX_RUNS = 31
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_PAYLOAD_BYTES = 1024 * 1024
FETCH_SECONDS = 12


def registry(home: Path) -> dict:
    policy = I.load_toml((I.REPO_ROOT / 'content/discovery.toml').read_text())['family']
    observed = {m['slug']: m for m in routing.codex_models(home, ['list']) if isinstance(m['slug'], str)}
    families = {}
    for family, entry in policy.items():
        model = observed.get(entry['model'])
        levels = (model or {}).get('supported_reasoning_levels')
        levels = levels if isinstance(levels, list) else []
        efforts = sorted({e['effort'] for e in levels
                          if isinstance(e, dict) and isinstance(e.get('effort'), str)})
        status = ('UNAVAILABLE' if model is None else 'PAIR_UNSUPPORTED'
                  if entry['effort'] not in efforts else 'AVAILABLE_CANDIDATE')
        families[family] = dict(entry, status=status, supported_efforts=efforts)
    return {'schema': 'harness.model-registry/v1', 'provider': 'openai',
            'client': 'codex', 'observation': 'local_cache_not_live_dispatch',
            'official_source': 'https://learn.chatgpt.com/docs/models',
            'performance': 'NOT_MEASURED', 'families': families}


def routing_candidate(home: Path) -> dict:
    """A proposed override for the existing resolver, never a live configuration write."""
    families = registry(home)['families']
    if any(f['status'] != 'AVAILABLE_CANDIDATE' for f in families.values()):
        raise ValueError('all four exact model/effort pairs must be observed')
    mapping = {'quick': 'luna', 'standard': 'terra', 'deep': 'sol', 'review': 'astra'}
    return {'routing': {'progression': {'enabled': False}, 'tiers': {
        tier: {'codex': families[family]['model'], 'effort': families[family]['effort']}
        for tier, family in mapping.items()}}}


def reserve_decision(remaining, requested, *, reliable=False) -> str:
    """Never convert subscription percentages into a token balance."""
    if not reliable or type(remaining) is not int or remaining < 0:
        return 'UNKNOWN'
    if type(requested) is not int or requested <= 0:
        return 'PAUSE'
    return 'PAUSE' if remaining <= 12000 or remaining - requested < 10000 else 'ALLOW_BOUNDED'


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('official-source redirect refused')


def _fetch_worker(url: str) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': 'agent-harness-discovery/1'})
    with urllib.request.build_opener(_NoRedirect).open(req, timeout=10) as response:
        return response.read(MAX_BYTES + 1)


FETCH_WORKER = ("import sys; from agent_harness.discovery_cycle import _fetch_worker; "
                "sys.stdout.buffer.write(_fetch_worker(sys.argv[1]))")


def fetch_official(url: str) -> bytes:
    if url not in SOURCES:
        raise ValueError('source is not in the reviewed official-source list')
    # A socket timeout alone does not bound a slowly trickling response. The
    # child owns no grandchildren; subprocess.run kills and reaps it on timeout.
    import os
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    try:
        result = subprocess.run([sys.executable, '-c', FETCH_WORKER, url],
                                env=env, capture_output=True, timeout=FETCH_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise OSError('official fetch wall deadline exceeded') from exc
    if result.returncode:
        raise OSError('official source fetch failed')
    return result.stdout


def schedule(hh: Path) -> dict:
    return {'argv': [str(hh / 'bin/harness'), 'daily-discovery'],
            'interval_seconds': DAY, 'enabled': False,
            'activation': 'Requires a tested host scheduler; this only describes the command',
            'model_calls_per_run': 0, 'max_fetches_per_run': len(SOURCES)}


def history(hh: Path) -> list:
    path = hh / 'discovery/audit.sqlite'
    if not path.is_file():
        return []
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        return [dict(zip(('sequence', 'epoch', 'status', 'snapshot'), row)) for row in
                db.execute('SELECT id,epoch,status,snapshot FROM runs ORDER BY id DESC LIMIT 31')]
    finally:
        db.close()


def _rotate(db, root):
    """Archive exact rows before removing hot copies; retain cadence and last good baseline."""
    rows = db.execute('SELECT id,epoch,status,snapshot,payload FROM runs ORDER BY id').fetchall()
    keep = {rows[-1][0]}
    successful = [row[0] for row in rows if row[2] in ('PROPOSED', 'UNCHANGED')]
    if successful:
        keep.add(successful[-1])
    old = [row for row in rows if row[0] not in keep]
    if not old:
        return False
    raw = json.dumps(old, ensure_ascii=False, separators=(',', ':')).encode()
    digest = hashlib.sha256(raw).hexdigest()
    packed = gzip.compress(raw, mtime=0)
    directory = root / 'archives'
    directory.mkdir(exist_ok=True)
    path = directory / (digest + '.json.gz')
    if path.is_symlink():
        raise ValueError('archive target is linked')
    used = sum(p.stat().st_size for p in directory.iterdir() if p.is_file())
    if used + (0 if path.exists() else len(packed)) > MAX_ARCHIVE_BYTES:
        return False
    if not path.exists():
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(packed)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name == 'posix':
            fd = os.open(str(directory), os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    if gzip.decompress(path.read_bytes()) != raw:
        raise ValueError('archive verification failed; hot records retained')
    db.execute('INSERT OR IGNORE INTO archives(digest,path,records,bytes) VALUES(?,?,?,?)',
               (digest, str(path), len(old), path.stat().st_size))
    db.executemany('DELETE FROM runs WHERE id=?', [(row[0],) for row in old])
    return True


def archive_history(hh: Path) -> list:
    path = hh / 'discovery/audit.sqlite'
    if not path.is_file():
        return []
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='archives'").fetchone():
            return []
        return [dict(zip(('sha256', 'path', 'records', 'bytes'), row)) for row in
                db.execute('SELECT digest,path,records,bytes FROM archives ORDER BY rowid')]
    finally:
        db.close()


def run(hh: Path, home: Path, *, now=None, fetch=fetch_official) -> dict:
    now = time.time() if now is None else now
    if type(now) not in (int, float) or not math.isfinite(now) or now < 0:
        raise ValueError('invalid discovery clock')
    root = hh / 'discovery'
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(root / 'audit.sqlite'), timeout=1)
    try:
        db.execute('CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, epoch REAL NOT NULL, '
                   'status TEXT NOT NULL, snapshot TEXT, payload TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS archives (digest TEXT PRIMARY KEY, path TEXT NOT NULL, records INTEGER NOT NULL, bytes INTEGER NOT NULL)')
        # Serialize the short, bounded cycle: concurrent scheduled runs cannot duplicate a fetch.
        db.execute('BEGIN IMMEDIATE')
        last = db.execute('SELECT epoch FROM runs ORDER BY id DESC LIMIT 1').fetchone()
        if last and now - last[0] < DAY:
            return {'status': 'NOT_DUE', 'next_due': last[0] + DAY}
        if db.execute('SELECT count(*) FROM runs').fetchone()[0] >= MAX_RUNS:
            if not _rotate(db, root):
                return {'status': 'RETENTION_HOLD', 'reason': 'Archive capacity reached; retain or export verified archives before renewal'}
        prior = db.execute("SELECT snapshot FROM runs WHERE status IN ('PROPOSED','UNCHANGED') "
                           'ORDER BY id DESC LIMIT 1').fetchone()
        previous = prior[0] if prior else None
        sources = []
        try:
            for url in SOURCES:
                blob = fetch(url)
                if not isinstance(blob, bytes) or not 0 < len(blob) <= MAX_BYTES:
                    raise ValueError('empty or oversized official source')
                sources.append({'url': url, 'sha256': hashlib.sha256(blob).hexdigest(),
                                'text': blob.decode('utf-8')})
            payload = {'registry': registry(home), 'sources': sources}
            encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False)
            if len(encoded.encode()) > MAX_PAYLOAD_BYTES:
                raise ValueError('encoded source payload exceeds its storage bound')
            fingerprint = hashlib.sha256(encoded.encode()).hexdigest()
            status = 'UNCHANGED' if fingerprint == previous else 'PROPOSED'
            result = {'status': status, 'snapshot': fingerprint, 'previous': previous,
                      'activation': 'HELD', 'reason': 'Source change is evidence for review, not authority'}
        except (OSError, ValueError, UnicodeError) as exc:
            # Record failure without advancing the last successful baseline or logging response text.
            encoded = json.dumps({'failure_class': type(exc).__name__})
            fingerprint = None
            result = {'status': 'FETCH_FAILED', 'previous': previous, 'activation': 'HELD',
                      'reason': type(exc).__name__}
        db.execute('INSERT INTO runs(epoch,status,snapshot,payload) VALUES(?,?,?,?)',
                   (now, result['status'], fingerprint, encoded))
        db.commit()
        return result
    finally:
        db.close()
