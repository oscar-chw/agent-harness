"""H6b backflow guard: a tombstoned fact must not silently flow back in.

H5 (memory_forget) made a fact provably ABSENT under a hash-chained tombstone
ledger; its verdict recorded backflow as detected-not-prevented. This module is
the write-time complement: an admission guard whose blocklist is DERIVED from
that same ledger (single source of truth — an entry exists iff the page is
currently tombstoned, so a relearn reopens admission by construction, never by
a second bookkeeping step).

Match legs (pre-registered in plan/v3-h6b-backflow-guard.md):
  L1 exact-bytes       sha256(candidate) == tombstone page_sha256
  L2 normalized-body   frontmatter stripped (mc._body), whitespace collapsed —
                       catches a near-verbatim re-add under fresh frontmatter
  L3 unique-literal    candidate carries >=1 literal (mc._literals) whose
                       document frequency over reference texts + the escrowed
                       body is exactly 1 — the contracted paraphrase leg
  L4 distinctive-token >= min_shared_tokens tokens shared with the escrowed
                       body in the df band [2, mc._distinctive_df_cap(n)] —
                       SUPPLEMENTARY: reported in every verdict ('signals'),
                       blocks only with l4_blocks=True (the E4 sweep decides
                       the shipped default; topical neighbours share tokens
                       without being the same fact)

Refusal contract: check() never raises for content reasons and returns a
content-free verdict; on a match it receipts a 'backflow_refused' record into
the SAME ledger (memory_forget.append_refusal — identity, hashes, leg names,
never content). Fail-closed: a ledger that exists but fails verify_ledger (or
cannot be parsed) refuses ALL admissions — the receipt is returned, NOT chained
onto a broken ledger. No ledger at all => the guard is inactive (whether
unlearning ever happened is certification's question, not the guard's). A
missing or tampered escrow degrades loudly: L1 still refuses via the recorded
page_sha256, L2-L4 go dark, and every verdict carries degraded=True.

Stdlib only (Python 3.9-safe), model-free, no network. The guard never deletes,
moves or edits the content it refuses — admission control, not file policy.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from agent_harness import memory_consolidate as mc
from agent_harness import memory_forget as mf

LEG_EXACT = 'exact_bytes'
LEG_BODY = 'normalized_body'
LEG_LITERAL = 'unique_literal'
LEG_TOKENS = 'distinctive_tokens'
LEG_INTEGRITY = 'ledger_integrity'

STATE_INACTIVE = 'inactive'
STATE_OK = 'ok'
STATE_CORRUPT = 'corrupt'

MIN_SHARED_TOKENS = 4


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _norm_body(text: str) -> str:
    """Frontmatter out, whitespace collapsed: the shape-insensitive content form."""
    return re.sub(r'\s+', ' ', mc._body(text)).strip()


class Guard:
    """Write-time admission guard derived from a tombstone ledger.

    ledger_root: a directory holding mf.LEDGER_REL (a corpus root, or any store
      root that keeps its tombstones there).
    escrow_dir: the H5 escrow (page bytes by sha256); without it the guard runs
      degraded (exact-bytes leg only).
    reference_texts: the live corpus the df statistics are computed against
      (should exclude the tombstoned page's live copy — post-unlearn state).
    l4_blocks: whether the supplementary distinctive-token leg refuses
      (default False — advisory; see the module docstring).
    append_receipts: False turns check() into a pure probe (audit_store uses
      this internally; wiring should leave it True).
    """

    def __init__(self, ledger_root, escrow_dir=None, reference_texts: Sequence[str] = (),
                 *, min_shared_tokens: int = MIN_SHARED_TOKENS, l4_blocks: bool = False,
                 append_receipts: bool = True):
        self.ledger_root = Path(ledger_root)
        self.escrow_dir = Path(escrow_dir) if escrow_dir is not None else None
        self.reference_texts = list(reference_texts)
        self.min_shared_tokens = int(min_shared_tokens)
        self.l4_blocks = bool(l4_blocks)
        self.append_receipts = bool(append_receipts)
        # Reference texts are constructor constants: their tokenization is cached.
        # The ledger and escrow are re-read on every check — relearns and tampers
        # between admissions take effect immediately.
        self._ref_token_sets = [set(mc._tokens(t)) for t in self.reference_texts]
        self.state = STATE_INACTIVE
        self.problems: List[str] = []
        self.warnings: List[str] = []
        self.entries: List[dict] = []
        self._rebuild()

    # ------------------------------------------------------------ blocklist
    def _rebuild(self) -> None:
        """Reload + reverify the ledger and rebuild entries. Called on every
        check: the ledger is the source of truth, and a relearn (or a tamper)
        between admissions must take effect immediately."""
        self.problems, self.warnings, self.entries = [], [], []
        lp = mf.ledger_path(self.ledger_root)
        if not lp.is_file():
            self.state = STATE_INACTIVE
            return
        try:
            records = mf.load_ledger(self.ledger_root)
        except (OSError, ValueError) as exc:
            self.state = STATE_CORRUPT
            self.problems = ['ledger unreadable: %r' % exc]
            return
        problems = mf.verify_ledger(records)
        if problems:
            self.state = STATE_CORRUPT
            self.problems = problems
            return
        self.state = STATE_OK
        states = mf.page_states(records)
        tombstones: Dict[str, dict] = {}
        for rec in records:
            if rec.get('kind') == 'tombstone':
                tombstones[rec['page']] = rec
            elif rec.get('kind') == 'relearn':
                tombstones.pop(rec['page'], None)
        live = [tombstones[p] for p, st in states.items()
                if st == 'tombstoned' and p in tombstones]

        bodies: Dict[str, Optional[str]] = {}
        esc_bodies: List[str] = []
        for tomb in live:
            body = None
            if self.escrow_dir is not None:
                esc = self.escrow_dir / ('%s.md' % tomb['page_sha256'])
                if esc.is_file():
                    raw = esc.read_bytes()
                    if hashlib.sha256(raw).hexdigest() == tomb['page_sha256']:
                        body = mc._body(raw.decode('utf-8', 'replace'))
                    else:
                        self.warnings.append('escrow hash mismatch for %s — degraded'
                                             % tomb['page'])
                else:
                    self.warnings.append('escrow missing for %s — degraded' % tomb['page'])
            else:
                self.warnings.append('no escrow dir — degraded (exact-bytes leg only)')
            bodies[tomb['page']] = body
            if body is not None:
                esc_bodies.append(body)

        token_df: Dict[str, int] = {}
        for ts in self._ref_token_sets + [set(mc._tokens(b)) for b in esc_bodies]:
            for t in ts:
                token_df[t] = token_df.get(t, 0) + 1
        n_docs = len(self.reference_texts) + len(esc_bodies)
        cap = mc._distinctive_df_cap(n_docs) if n_docs else 2

        for tomb in live:
            body = bodies[tomb['page']]
            entry = {'page': tomb['page'], 'page_sha256': tomb['page_sha256'],
                     'tombstone': tomb['record_hash'], 'authority': tomb['authority'],
                     'degraded': body is None,
                     'body_sha256': None, 'literals': set(), 'tokens': set()}
            if body is not None:
                entry['body_sha256'] = _sha256_text(_norm_body(body))
                entry['literals'] = {
                    lit for lit in mc._literals(body)
                    if sum(1 for rt in self.reference_texts if lit in rt)
                    + sum(1 for b in esc_bodies if lit in b) == 1}
                entry['tokens'] = {t for t in set(mc._tokens(body))
                                   if 2 <= token_df.get(t, 0) <= cap}
            self.entries.append(entry)

    # ------------------------------------------------------------ admission
    def check(self, text: str, *, path: str) -> dict:
        """Admission verdict for candidate content at the named seam.

        Never raises for content reasons; never carries content in the verdict.
        Refusals are receipted into the same ledger (deduped: a repeated refusal
        of the same candidate at the same seam is not re-chained)."""
        self._rebuild()
        verdict = {'admit': True, 'state': self.state, 'path': path,
                   'degraded': any(e['degraded'] for e in self.entries),
                   'signals': [], 'refused': None, 'receipt': None}
        if self.warnings:
            verdict['warnings'] = list(self.warnings)
        if self.state == STATE_INACTIVE:
            return verdict
        if self.state == STATE_CORRUPT:
            # Fail closed — and do NOT chain a receipt onto a ledger whose
            # integrity already failed; the returned verdict IS the receipt.
            verdict.update(admit=False, problems=list(self.problems),
                           refused={'page': None, 'tombstone': None, 'authority': None,
                                    'legs': [LEG_INTEGRITY], 'path': path,
                                    'degraded': verdict['degraded']})
            return verdict
        if not isinstance(text, str) or not text:
            return verdict

        cand_sha = _sha256_text(text)
        cand_body_sha = _sha256_text(_norm_body(text))
        cand_tokens = set(mc._tokens(text))
        for entry in self.entries:
            legs = []
            if cand_sha == entry['page_sha256']:
                legs.append(LEG_EXACT)
            if entry['body_sha256'] is not None and cand_body_sha == entry['body_sha256']:
                legs.append(LEG_BODY)
            if any(lit in text for lit in entry['literals']):
                legs.append(LEG_LITERAL)
            shared = cand_tokens & entry['tokens']
            if len(shared) >= self.min_shared_tokens:
                (legs if self.l4_blocks else verdict['signals']).append(LEG_TOKENS)
            if not legs:
                continue
            refused = {'page': entry['page'], 'tombstone': entry['tombstone'],
                       'authority': entry['authority'], 'legs': sorted(legs),
                       'path': path, 'degraded': entry['degraded']}
            verdict.update(admit=False, refused=refused)
            if self.append_receipts:
                rec = mf.append_refusal(
                    self.ledger_root, page=entry['page'], candidate_sha256=cand_sha,
                    tombstone_record_hash=entry['tombstone'], legs=legs, path=path,
                    degraded=entry['degraded'], authority=entry['authority'])
                verdict['receipt'] = {'seq': rec['seq'], 'record_hash': rec['record_hash']}
            return verdict
        return verdict

    # ------------------------------------------------------------ audit side
    def audit_store(self, texts: Sequence[str], *, path: str = 'audit') -> dict:
        """Scan EXISTING content against the blocklist: catches pre-existing
        backflow and guard bypass alike. Content-free findings; never receipts."""
        self._rebuild()
        out = {'state': self.state, 'findings': []}
        if self.problems:
            out['problems'] = list(self.problems)
        if self.state != STATE_OK:
            return out
        probe = Guard(self.ledger_root, self.escrow_dir, self.reference_texts,
                      min_shared_tokens=self.min_shared_tokens,
                      l4_blocks=True, append_receipts=False)
        for text in texts:
            v = probe.check(text, path=path)
            legs = list(v['refused']['legs']) if v['refused'] else []
            legs += [s for s in v['signals'] if s not in legs]
            if legs:
                out['findings'].append(
                    {'candidate_sha256': _sha256_text(text),
                     'page': v['refused']['page'] if v['refused'] else None,
                     'tombstone': v['refused']['tombstone'] if v['refused'] else None,
                     'legs': sorted(legs), 'path': path})
        return out
