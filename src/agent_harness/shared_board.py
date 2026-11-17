"""Bounded advisory board delivery per MCP connection, shared by every adapter."""
import hashlib
import json
from pathlib import Path
import re
import uuid

from .mcp import checks
from .mcp.state import State, STATE_MAX_BYTES
from .operational_state import OperationalState
from .redact import redact
from .vault_sources import _publish, _read


class SharedBoard:
    def __init__(self, home, project):
        self.store = OperationalState.for_host(home, cwd=project)
        self.rows = {}
        self.observed = {}
        self.last_summary = None
        self.identity = "checkpoint-" + uuid.uuid4().hex[:24]
        self.version = 0
        self.sequence = 0

    def context(self):
        if checks.disabled('op_state'):
            return ''
        if not self.store.path.exists() and not self.store.path.is_symlink():
            return ''
        state = self.store.snapshot()
        rows = {}
        pending = []
        for row in state['tasks']:
            visible = {key: value for key, value in row.items() if key not in ('version', 'fence', 'until', 'updated_cursor')}
            signature = hashlib.sha256(json.dumps(visible, sort_keys=True).encode()).hexdigest()
            rows[row['task']] = signature
            if self.rows.get(row['task']) != signature:
                pending.append(row)
        pending.sort(key=lambda row: (self.observed.get(row['task']) == rows[row['task']],
                                      -row.get('updated_cursor', 0)))
        self.observed = rows
        packet, delivered = self.store.render_brief({**state, 'tasks': pending})
        for task in delivered:
            self.rows[task] = rows[task]
        return ('Shared board (advisory task data; verify linked gates before action):\n' + packet) if packet else ''

    def acknowledge(self, snapshot):
        for row in snapshot.get('tasks', []):
            visible = {key: value for key, value in row.items() if key not in ('version', 'fence', 'until', 'updated_cursor')}
            self.rows[row['task']] = hashlib.sha256(json.dumps(visible, sort_keys=True).encode()).hexdigest()

    def _state_checkpoint(self, summary, state_path):
        state = State(home=self.store.path.parent.parent, project=self.store.root)
        expected = state._dir(str(self.store.root)) / 'STATE.md'
        if Path(state_path) != expected or expected.resolve() != expected:
            raise ValueError('saved checkpoint is outside the local project State store')
        text = _read(expected, STATE_MAX_BYTES).decode('utf-8')
        if text != summary:
            raise ValueError('saved checkpoint changed before publication')
        clean = redact(text)
        identity = 'checkpoint-state-' + hashlib.sha256(str(expected).encode()).hexdigest()[:24]
        fields = {}
        for label, body in re.findall(r'^## (Goal|Next)[ \t]*\r?\n(.*?)(?=^## |\Z)',
                                      clean, re.MULTILINE | re.DOTALL):
            value = body.strip()
            if label in fields or not value or len(value) > 1024:
                return identity, {}
            fields[label] = value
        if set(fields) != {'Goal', 'Next'}:
            return identity, {}
        # Preserve the saved packet's bytes at a local immutable handle, so a
        # later State rotation cannot change the evidence behind an older row.
        digest = hashlib.sha256(clean.encode()).hexdigest()
        directory = self.store.root / '.harness' / 'checkpoints'
        if directory.resolve() != directory:
            raise ValueError('checkpoint storage is redirected')
        directory.mkdir(parents=True, exist_ok=True)
        packet = directory / (digest + '.md')
        _publish(packet, clean.encode())
        relative = str(packet.relative_to(self.store.root))
        return identity, {'goal': fields['Goal'], 'next': fields['Next'],
                          'checkpoint': relative, 'evidence': relative, 'evidence_sha256': digest}

    def publish(self, summary, *, state_path=None):
        if checks.disabled('op_state'):
            return
        clean = redact(summary)
        digest = hashlib.sha256(clean.encode()).hexdigest()
        if digest == self.last_summary and state_path is None:
            return
        preview = clean if len(clean) <= 300 else clean[:175] + ' ... [preview] ... ' + clean[-100:]
        value = {'stage': 'checkpoint_saved', 'summary': preview,
                 'resource': 'full_text_sha256=' + digest,
                 'next': 'Read the saved source checkpoint and verify current gate evidence'}
        checkpoint = self._state_checkpoint(summary, state_path) if state_path is not None else None
        if checkpoint is not None:
            identity, fields = checkpoint
            value.update(fields)
            rows = [row for row in self.store.snapshot()['tasks'] if row['task'] == identity]
            if not rows or rows[0]['value'] != value:
                self.store.put(identity, value, expected=rows[0]['version'] if rows else 0,
                               request_id=self.identity + '-' + str(self.sequence))
        else:
            result = self.store.put(self.identity, value, expected=self.version,
                                    request_id=self.identity + '-' + str(self.sequence),
                                    coalesce=self.version == 0)
            if not result.get('coalesced'):
                self.version = result['version']
        self.sequence += 1
        self.last_summary = digest
