"""Bounded advisory board delivery per MCP connection, shared by every adapter."""
import hashlib
import json
import uuid

from .mcp import checks
from .operational_state import OperationalState
from .redact import redact


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

    def publish(self, summary):
        if checks.disabled('op_state'):
            return
        clean = redact(summary)
        digest = hashlib.sha256(clean.encode()).hexdigest()
        if digest == self.last_summary:
            return
        preview = clean if len(clean) <= 300 else clean[:175] + ' ... [preview] ... ' + clean[-100:]
        value = {'stage': 'checkpoint_saved', 'summary': preview,
                 'resource': 'full_text_sha256=' + digest,
                 'next': 'Read the saved source checkpoint and verify current gate evidence'}
        result = self.store.put(self.identity, value, expected=self.version,
                                request_id=self.identity + '-' + str(self.sequence),
                                coalesce=self.version == 0)
        self.sequence += 1
        if not result.get('coalesced'):
            self.version = result['version']
        self.last_summary = digest
