"""Opt-in local command controls; not remote-tool or learning attestation."""
import hashlib
import json
from pathlib import Path
import sys

CONTROL = {'inside_readable': True, 'oracle_denied': True, 'writes_denied': True}


class EvaluationProtocol:
    """Native app-server handshake; never infer actor isolation from CLI flags."""

    def __init__(self, root, oracle, inside, outside, model, effort, prompt, *, parent_state=None,
                 require_provider_usage=False):
        if type(require_provider_usage) is not bool:
            raise ValueError('provider usage requirement must be an explicit boolean')
        self.root, self.oracle = str(Path(root).resolve()), str(Path(oracle).resolve())
        self.profile = 'harness_eval_' + hashlib.sha256(self.oracle.encode()).hexdigest()[:12]
        self.model, self.effort, self.prompt = model, effort, prompt
        self.inside, self.outside = inside, outside
        self.pending = [{'id': 1, 'method': 'initialize', 'params': {
            'clientInfo': {'name': 'harness_evaluation', 'version': '2'},
            'capabilities': {'experimentalApi': True}}}]
        self.events = []
        self.finished = False
        self.receipt = None
        self.expected = 1
        self.thread = self.turn = self.usage = None
        self.completed = False
        self.last_error = None
        self.mcp_disabled = {}
        self.parent_state = parent_state
        self.parent_argv_built = False
        self.parent_files_observed = False
        self.held_turn = None
        self.require_provider_usage = require_provider_usage
        self.provider_responses = {}

    def argv(self, native):
        command = [str(native), 'app-server', '--stdio', '-c',
                f'permissions.{self.profile}.extends=":read-only"', '-c',
                f'permissions.{self.profile}.filesystem={{' + json.dumps(self.oracle) + '="deny"}',
                '-c', 'model_reasoning_effort=' + json.dumps(self.effort),
                '-c', 'mcp_servers={}', '-c', 'web_search="disabled"', '--disable', 'apps', '--disable', 'plugins']
        if self.parent_state is not None:
            from .eval_parent import parent_command
            command = parent_command(native, self.root, self.oracle, self.parent_state) + command
            self.parent_argv_built = True
        return command

    @staticmethod
    def environment(parent):
        # The desktop bridge is a separate tool transport, not a local file
        # permission. Do not attach it to a frozen, tool-scoped evaluation.
        return {k: v for k, v in parent.items() if k != 'CODEX_APP_TOOLS_PIPE_PATH'}

    def _queue(self, identity, method, params):
        if method == 'thread/start' and self.require_provider_usage:
            # The native experimental schema requires this explicit opt-in to
            # deliver rawResponse/completed. Aggregate counters cannot replace it.
            params['experimentalRawEvents'] = True
        if self.parent_state is not None:
            if not self.parent_argv_built:
                raise ValueError('parent evaluation requires the enclosing native command')
            if method == 'command/exec':
                params.pop('permissionProfile', None)
                params['sandboxPolicy'] = {'type': 'externalSandbox', 'networkAccess': 'enabled'}
            elif method == 'thread/start':
                # macOS refuses nested sandbox_apply, including instruction loading.
                # The enclosing read-only process restriction remains enforced.
                params['permissions'] = ':danger-full-access'
            elif method == 'turn/start':
                params['sandboxPolicy'] = {'type': 'externalSandbox', 'networkAccess': 'enabled'}
                if not self.parent_files_observed:
                    self.held_turn = (identity, method, params)
                    identity, method, params = 9, 'fs/readFile', {'path': self.inside}
        self.expected = identity
        self.pending.append({'id': identity, 'method': method, 'params': params})

    def _context_matches(self, result):
        return (result.get('model') == self.model and result.get('reasoningEffort') == self.effort
                and result.get('modelProvider') == 'openai'
                and result.get('approvalPolicy') == 'never'
                and result.get('serviceTier') in (None, 'default', 'standard')
                and (result.get('sandbox') == {'type': 'dangerFullAccess'}
                     if self.parent_state is not None else
                     result.get('activePermissionProfile', {}).get('id') == self.profile
                     and result.get('sandbox') == {'type': 'readOnly', 'networkAccess': False}))

    def drain(self):
        body = b''.join((json.dumps(packet) + '\n').encode() for packet in self.pending)
        self.pending.clear()
        return body

    def _scope(self, params):
        if params.get('threadId') != self.thread:
            raise ValueError('evaluation boundary received a foreign thread')
        turn = params.get('turnId', params.get('turn', {}).get('id'))
        if turn is not None and turn != self.turn:
            raise ValueError('evaluation boundary received a foreign turn')

    def _provider_report(self, params):
        self._scope(params)
        identity, usage = params.get('responseId'), params.get('usage')
        names = ('inputTokens', 'cachedInputTokens', 'outputTokens', 'reasoningOutputTokens', 'totalTokens')
        if (self.finished or not isinstance(self.turn, str) or params.get('turnId') != self.turn
                or not isinstance(identity, str) or not identity or len(identity) > 256
                or not identity.isprintable() or identity in self.provider_responses
                or len(self.provider_responses) >= 64 or not isinstance(usage, dict)
                or any(type(usage.get(k)) is not int or usage[k] < 0 for k in names)):
            raise ValueError('provider response is missing, invalid, replayed or after the terminal barrier')
        write = usage.get('cacheWriteInputTokens', 0)
        if (type(write) is not int or write < 0
                or usage['cachedInputTokens'] + write > usage['inputTokens']
                or usage['reasoningOutputTokens'] > usage['outputTokens']
                or usage['totalTokens'] != usage['inputTokens'] + usage['outputTokens']
                or usage['totalTokens'] <= 0):
            raise ValueError('provider response usage is incomplete or inconsistent')
        # UsageMetadata may contain billing details. Counts and a response-ID
        # fingerprint suffice; never copy that metadata into the evaluation log.
        self.provider_responses[identity] = {**{k: usage[k] for k in names}, 'cacheWriteInputTokens': write}

    def _provider_total(self):
        if not self.provider_responses:
            raise ValueError('provider upstream completion usage was not observed')
        totals = {k: sum(r[k] for r in self.provider_responses.values())
                  for k in next(iter(self.provider_responses.values()))}
        if self.usage and any(totals[k] < self.usage[k] for k in
                              ('inputTokens', 'cachedInputTokens', 'outputTokens', 'reasoningOutputTokens')):
            raise ValueError('provider completions omit usage seen in the native counter')
        self.receipt['provider_usage'] = {
            'status': 'OBSERVED_UPSTREAM_COMPLETIONS', 'responses': len(self.provider_responses),
            'response_id_sha256': [hashlib.sha256(i.encode()).hexdigest() for i in self.provider_responses],
            'input_tokens': totals['inputTokens'], 'cached_input_tokens': totals['cachedInputTokens'],
            'cache_write_input_tokens': totals['cacheWriteInputTokens'], 'output_tokens': totals['outputTokens'],
            'reasoning_output_tokens': totals['reasoningOutputTokens'],
            'scope': 'fresh native thread upstream completions; not whole-workflow cost'}
        return totals

    def feed(self, packet):
        result_events = []
        if not isinstance(packet, dict):
            raise ValueError('evaluation boundary received invalid protocol data')
        if (self.parent_state is not None and self.expected in (9, 10, 11)
                and 'id' in packet):
            from .eval_parent import file_control
            file_control(self.expected, packet)
            if self.expected == 9:
                self._queue(10, 'fs/readFile', {'path': self.outside})
            elif self.expected == 10:
                self._queue(11, 'fs/writeFile', {'path': self.outside, 'dataBase64': 'IQ=='})
            else:
                self.parent_files_observed = True
                self.receipt.update(status='OBSERVED_PARENT_FILE_AND_COMMAND_CONTROL',
                    parent_filesystem='readonly_except_native_state;oracle_denied',
                    network_scope='parent_enabled_for_native_transport_not_domain_containment',
                    native_file_controls='task_read;oracle_read_denied;oracle_write_denied')
                self._queue(*self.held_turn)
                self.held_turn = None
            return []
        if 'id' in packet:
            if packet.get('id') != self.expected or 'method' in packet or 'error' in packet:
                from .redact import redact
                error = packet.get('error')
                self.last_error = ({'code': error.get('code') if type(error.get('code')) is int else None,
                    'message': redact(str(error.get('message', '')))[:512]}
                    if isinstance(error, dict) else {'method': redact(str(packet.get('method', '')))[:128]})
                raise ValueError('evaluation boundary native RPC refused or unexpected request')
            result = packet.get('result')
            if not isinstance(result, dict):
                raise ValueError('evaluation boundary RPC result missing')
            stage = self.expected
            if stage == 1:
                self.pending.append({'method': 'initialized', 'params': {}})
                self._queue(2, 'account/read', {'refreshToken': False})
            elif stage == 2:
                if not isinstance(result.get('account'), dict) or result['account'].get('type') != 'chatgpt':
                    raise ValueError('evaluation boundary requires included native ChatGPT login')
                self._queue(7, 'mcpServerStatus/list', {'limit': 100, 'detail': 'full'})
            elif stage == 7:
                servers = result.get('data')
                if (not isinstance(servers, list) or len(servers) > 100
                        or result.get('nextCursor') is not None
                        or any(not isinstance(s, dict) or not isinstance(s.get('name'), str)
                               or not s['name'] or len(s['name']) > 128 for s in servers)):
                    raise ValueError('evaluation boundary MCP inventory incomplete')
                self.mcp_disabled = {s['name']: {'enabled': False} for s in servers if not s.get('pluginId')}
                self._queue(3, 'command/exec', {'cwd': self.root,
                    'permissionProfile': self.profile,
                    'command': [sys.executable, '-B', '-I', '-S', '-c', PROBE,
                                self.inside, self.outside],
                    'timeoutMs': 10000, 'outputBytesCap': 16384})
            elif stage == 3:
                try:
                    control = json.loads(result.get('stdout', ''))
                except (ValueError, TypeError) as error:
                    raise ValueError('evaluation boundary control output invalid') from error
                if (type(result.get('exitCode')) is not int or result['exitCode'] != 0
                        or not isinstance(control, dict) or set(control) != set(CONTROL)
                        or any(type(v) is not bool or v is not True for v in control.values())):
                    raise ValueError('evaluation boundary local command control failed')
                self._queue(4, 'thread/start', {'cwd': self.root, 'permissions': self.profile,
                    'ephemeral': True, 'approvalPolicy': 'never', 'model': self.model,
                    'serviceTier': 'default', 'config': {'mcp_servers': self.mcp_disabled}})
            elif stage == 4:
                self.rejected_context = {k: result.get(k) for k in (
                    'model', 'reasoningEffort', 'modelProvider', 'approvalPolicy',
                    'activePermissionProfile', 'sandbox', 'serviceTier')}
                if not self._context_matches(result):
                    raise ValueError('evaluation boundary resolved context mismatch')
                self.thread = result.get('thread', {}).get('id')
                if not isinstance(self.thread, str) or not self.thread:
                    raise ValueError('evaluation boundary fresh thread missing')
                self.receipt = {'status': 'OBSERVED_LOCAL_TOOL_CONTROL', 'control': dict(CONTROL),
                    'remote_tools': 'NOT_VERIFIED', 'learning_promotion': 'NOT_GRANTED',
                    'model_identity_scope': 'native_client_resolution_not_backend_weights',
                    'resolved': {k: result.get(k) for k in ('model', 'modelProvider', 'reasoningEffort',
                                                       'approvalPolicy', 'sandbox', 'activePermissionProfile', 'serviceTier')}}
                result_events.append({'type': 'thread.started', 'thread_id': self.thread})
                self._queue(5, 'mcpServerStatus/list', {'threadId': self.thread, 'limit': 100, 'detail': 'full'})
            elif stage == 5:
                servers = result.get('data')
                if (not isinstance(servers, list) or result.get('nextCursor') is not None
                        or any(not isinstance(s, dict) or s.get('runtimeStatus') != 'disabled'
                               or s.get('tools') != {} or s.get('resources') != []
                               or s.get('resourceTemplates') != [] for s in servers)):
                    raise ValueError('evaluation boundary has an unscoped or incomplete MCP surface')
                self.receipt['mcp_surface'] = 'OBSERVED_EMPTY'
                self._queue(6, 'turn/start', {'threadId': self.thread,
                    'input': [{'type': 'text', 'text': self.prompt}]})
            elif stage == 8:
                thread = result.get('thread')
                if (not isinstance(thread, dict) or thread.get('id') != self.thread
                        or thread.get('status') != {'type': 'idle'}
                        or not self.completed or (not self.require_provider_usage and not self.usage)):
                    raise ValueError('evaluation boundary terminal turn or complete usage missing')
                measured = self._provider_total() if self.require_provider_usage else self.usage
                result_events.append({'type': 'turn.completed', 'usage': {
                    'input_tokens': measured['inputTokens'],
                    'cached_input_tokens': measured['cachedInputTokens'],
                    'output_tokens': measured['outputTokens'],
                    'reasoning_output_tokens': measured['reasoningOutputTokens']}})
                self.receipt['usage_boundary'] = ('native_upstream_completions_after_terminal_read_barrier'
                    if self.require_provider_usage else 'native_total_after_terminal_read_barrier')
                self.finished = True
                self.expected = None
            elif stage == 6:
                self.turn = result.get('turn', {}).get('id')
                if not isinstance(self.turn, str) or not self.turn:
                    raise ValueError('evaluation boundary turn missing')
                self.expected = None
            else:
                raise ValueError('evaluation boundary unexpected RPC response')
        else:
            method, params = packet.get('method'), packet.get('params', {})
            if self.require_provider_usage and method == 'rawResponse/completed':
                if not isinstance(params, dict):
                    raise ValueError('provider response parameters are invalid')
                self._provider_report(params)
            elif self.require_provider_usage and method == 'error':
                raise ValueError('provider usage is incomplete after a native error or retry')
            if method in ('item/started', 'item/completed', 'thread/tokenUsage/updated', 'turn/completed'):
                self._scope(params)
                if method.startswith('item/'):
                    item = dict(params.get('item', {}))
                    import re
                    item['type'] = re.sub(r'(?<!^)(?=[A-Z])', '_', str(item.get('type', 'other'))).lower()
                    if 'aggregatedOutput' in item:
                        item['aggregated_output'] = item['aggregatedOutput']
                    if 'exitCode' in item:
                        item['exit_code'] = item['exitCode']
                    result_events.append({'type': method.replace('/', '.'), 'item': item})
                elif method == 'thread/tokenUsage/updated':
                    total = params.get('tokenUsage', {}).get('total', {})
                    names = ('inputTokens', 'cachedInputTokens', 'outputTokens', 'reasoningOutputTokens')
                    if (any(type(total.get(k)) is not int or total[k] < 0 for k in names)
                            or total['cachedInputTokens'] > total['inputTokens']
                            or total['reasoningOutputTokens'] > total['outputTokens']
                            or (not self.require_provider_usage
                                and total.get('totalTokens') != total['inputTokens'] + total['outputTokens'])
                            or (self.usage and any(total[k] < self.usage[k] for k in names))):
                        raise ValueError('evaluation boundary usage incomplete or regressing')
                    self.usage = total
                elif params.get('turn', {}).get('status') == 'completed':
                    if self.completed:
                        raise ValueError('evaluation boundary duplicate terminal event')
                    self.completed = True
                    self._queue(8, 'thread/read', {'threadId': self.thread, 'includeTurns': False})
                else:
                    result_events.append({'type': 'turn.failed'})
                    self.finished = True
        self.events.extend(result_events)
        return result_events

PROBE = '''import json,sys
result={}
with open(sys.argv[1],'rb') as stream:
 result['inside_readable']=stream.read()==b'harness-boundary-control'
try:
 with open(sys.argv[2],'rb') as stream: stream.read(1)
 result['oracle_denied']=False
except PermissionError: result['oracle_denied']=True
try:
 with open(sys.argv[1],'ab') as stream: stream.write(b'!')
 result['writes_denied']=False
except PermissionError: result['writes_denied']=True
print(json.dumps(result))
'''

