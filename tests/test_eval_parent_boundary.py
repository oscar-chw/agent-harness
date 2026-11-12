"""Whole-process eval protection must not rely on an inner command-only profile."""
import base64
import json

import pytest

from agent_harness.eval_boundary import EvaluationProtocol

from .test_explicit_launch import launch_request as _shared_launch_request


@pytest.fixture
def launch_request(tmp_path):
    return _shared_launch_request.__wrapped__(tmp_path)


def parent(tmp_path):
    actor, oracle, state = (tmp_path / name for name in ('actor', 'oracle', 'native-state'))
    for p in (actor, oracle, state):
        p.mkdir()
    p = EvaluationProtocol(actor, oracle, str(actor / 'inside'), str(oracle / 'outside'),
                           'fixture-model', 'high', 'Read task.', parent_state=state)
    return p, state


def take(p, method):
    q = p.pending.pop(0)
    assert q['method'] == method
    return q


def respond(p, request, result):
    return p.feed({'id': request['id'], 'result': result})


def ready_for_files(p):
    p.argv('/fixture/codex')
    respond(p, take(p, 'initialize'), {})
    take(p, 'initialized')
    respond(p, take(p, 'account/read'), {'account': {'type': 'chatgpt'}})
    respond(p, take(p, 'mcpServerStatus/list'), {'data': [], 'nextCursor': None})
    check = take(p, 'command/exec')
    assert 'permissionProfile' not in check['params']
    assert check['params']['sandboxPolicy'] == {'type': 'externalSandbox', 'networkAccess': 'enabled'}
    respond(p, check, {'exitCode': 0, 'stdout': json.dumps({
        'inside_readable': True, 'oracle_denied': True, 'writes_denied': True})})
    start = take(p, 'thread/start')
    assert start['params']['permissions'] == ':danger-full-access'
    respond(p, start, {'thread': {'id': 'fresh-thread'}, 'model': 'fixture-model',
                       'modelProvider': 'openai', 'reasoningEffort': 'high',
                       'approvalPolicy': 'never', 'sandbox': {'type': 'dangerFullAccess'},
                       'serviceTier': 'default'})
    respond(p, take(p, 'mcpServerStatus/list'), {'data': [], 'nextCursor': None})
    assert not any(q['method'] == 'turn/start' for q in p.pending)


def denied(p, request, message='Operation not permitted (os error 1)', code=-32603):
    return p.feed({'id': request['id'], 'error': {'code': code, 'message': message}})


def test_parent_argv_always_encloses_entire_native_client_and_keeps_managed_rules(tmp_path):
    p, state = parent(tmp_path)
    argv = p.argv('/fixture/codex')
    assert argv[:3] == ['/fixture/codex', 'sandbox', '--include-managed-config']
    split = argv.index('--')
    assert argv[split + 1:split + 4] == ['/fixture/codex', 'app-server', '--stdio']
    policy = ' '.join(argv[:split])
    assert 'extends=":read-only"' in policy
    assert json.dumps(str(state)) + '="write"' in policy
    assert json.dumps(p.oracle) + '="deny"' in policy
    assert json.dumps(str(state / 'config.toml')) + '="read"' in policy


def test_native_direct_file_controls_precede_generation_and_external_mode_is_explicit(tmp_path):
    p, _ = parent(tmp_path)
    ready_for_files(p)
    read = take(p, 'fs/readFile')
    assert read['params']['path'] == p.inside
    respond(p, read, {'dataBase64': base64.b64encode(b'harness-boundary-control').decode()})
    read = take(p, 'fs/readFile')
    assert read['params']['path'] == p.outside
    denied(p, read)
    write = take(p, 'fs/writeFile')
    assert write['params']['path'] == p.outside
    denied(p, write)
    turn = take(p, 'turn/start')
    assert turn['params']['sandboxPolicy'] == {'type': 'externalSandbox', 'networkAccess': 'enabled'}
    assert p.receipt['status'] == 'OBSERVED_PARENT_FILE_AND_COMMAND_CONTROL'
    assert p.receipt['parent_filesystem'] == 'readonly_except_native_state;oracle_denied'
    assert p.receipt['resolved']['sandbox'] == {'type': 'dangerFullAccess'}
    assert p.receipt['network_scope'] == 'parent_enabled_for_native_transport_not_domain_containment'
    assert p.receipt['learning_promotion'] == 'NOT_GRANTED'


@pytest.mark.parametrize('fault', ['read-succeeds', 'write-succeeds', 'method-missing',
                                  'wrong-error-code', 'wrong-task-bytes', 'bad-base64'])
def test_missing_or_false_native_file_controls_cannot_start_a_turn(tmp_path, fault):
    p, _ = parent(tmp_path)
    ready_for_files(p)
    read = take(p, 'fs/readFile')
    with pytest.raises(ValueError):
        if fault in ('wrong-task-bytes', 'bad-base64'):
            data = '???' if fault == 'bad-base64' else base64.b64encode(b'wrong').decode()
            respond(p, read, {'dataBase64': data})
        else:
            respond(p, read, {'dataBase64': base64.b64encode(b'harness-boundary-control').decode()})
            read = take(p, 'fs/readFile')
            if fault == 'read-succeeds':
                respond(p, read, {'dataBase64': 'eA=='})
            elif fault == 'method-missing':
                denied(p, read, 'Method not found', -32601)
            elif fault == 'wrong-error-code':
                denied(p, read, code=-32601)
            else:
                denied(p, read)
                respond(p, take(p, 'fs/writeFile'), {})
    assert not any(q['method'] == 'turn/start' for q in p.pending)


@pytest.mark.parametrize('where', ['actor', 'oracle', 'ancestor'])
def test_native_state_write_exception_cannot_cover_actor_or_grader(tmp_path, where):
    actor, oracle = tmp_path / 'actor', tmp_path / 'oracle'
    actor.mkdir(); oracle.mkdir()
    state = {'actor': actor, 'oracle': oracle, 'ancestor': tmp_path}[where]
    with pytest.raises(ValueError, match='separate|overlap|state'):
        p = EvaluationProtocol(actor, oracle, str(actor / 'inside'), str(oracle / 'outside'),
                               'fixture', 'high', 'Task', parent_state=state)
        p.argv('/fixture/codex')


def test_launcher_requires_complete_enforcement_before_requesting_a_parent(tmp_path):
    from agent_harness.launch import execute
    with pytest.raises(ValueError, match='parent|enforced'):
        execute(tmp_path, 'absent-request.json', 'not-created.json', eval_parent_boundary=True)
    assert not (tmp_path / 'not-created.json').exists()
    with pytest.raises(ValueError, match='boolean'):
        execute(tmp_path, 'absent-request.json', 'not-created.json', eval_parent_boundary='yes')


def test_launcher_routes_parent_policy_and_persists_its_distinct_receipt(launch_request, monkeypatch):
    """Protocol fixture only; actual OS protection is a separate native control."""
    import sys
    from agent_harness.launch import execute
    root, _, _ = launch_request
    oracle = root.with_name(root.name + '-oracle'); oracle.mkdir()
    state = root.with_name(root.name + '-native-state'); state.mkdir()
    native = root / 'codex'
    native.write_text('#!' + sys.executable + '\n' + r'''
import base64,json,sys
from pathlib import Path
assert sys.argv[1:3]==['sandbox','--include-managed-config']
cut=sys.argv.index('--')
assert sys.argv[cut+2:cut+4]==['app-server','--stdio']
Path('outer-arguments.json').write_text(json.dumps(sys.argv[1:]))
def send(x): print(json.dumps(x),flush=True)
for line in sys.stdin:
 r=json.loads(line);m=r['method'];q=r.get('params',{})
 if m=='initialized':continue
 if m=='initialize':v={}
 elif m=='account/read':v={'account':{'type':'chatgpt'}}
 elif m=='mcpServerStatus/list':v={'data':[],'nextCursor':None}
 elif m=='command/exec':
  assert q['sandboxPolicy']['type']=='externalSandbox' and 'permissionProfile' not in q
  v={'exitCode':0,'stdout':json.dumps({'inside_readable':True,'oracle_denied':True,'writes_denied':True})}
 elif m=='thread/start':
  assert q['permissions']==':danger-full-access'
  v={'thread':{'id':'fixture-thread'},'model':'fixture-model','reasoningEffort':'high','modelProvider':'openai','approvalPolicy':'never','sandbox':{'type':'dangerFullAccess'},'serviceTier':None}
 elif m=='fs/readFile' and r['id']==9:v={'dataBase64':base64.b64encode(Path(q['path']).read_bytes()).decode()}
 elif m in ('fs/readFile','fs/writeFile'):
  send({'id':r['id'],'error':{'code':-32603,'message':'Operation not permitted (os error 1)'}});continue
 elif m=='turn/start':
  assert q['sandboxPolicy']=={'type':'externalSandbox','networkAccess':'enabled'}
  v={'turn':{'id':'fixture-turn'}}
 elif m=='thread/read':v={'thread':{'id':'fixture-thread','status':{'type':'idle'}}}
 else:raise AssertionError(m)
 send({'id':r['id'],'result':v})
 if m=='turn/start':
  send({'method':'item/completed','params':{'threadId':'fixture-thread','turnId':'fixture-turn','item':{'id':'message','type':'agentMessage','text':'fixture answer'}}})
  send({'method':'thread/tokenUsage/updated','params':{'threadId':'fixture-thread','turnId':'fixture-turn','tokenUsage':{'total':{'inputTokens':2,'cachedInputTokens':0,'outputTokens':1,'reasoningOutputTokens':0,'totalTokens':3}}}})
  send({'method':'turn/completed','params':{'threadId':'fixture-thread','turn':{'id':'fixture-turn','status':'completed'}}})
''')
    native.chmod(0o755)
    monkeypatch.setenv('PATH', str(root)); monkeypatch.setenv('CODEX_HOME', str(state))
    result = execute(root, 'request.json', 'parent.json', timeout=3, eval_deny_root=oracle,
                     eval_enforce_boundary=True, eval_parent_boundary=True,
                     native_model='fixture-model', native_effort='high')
    assert result['native_completion'] == 'COMPLETED_UNGRADED'
    assert result['permission_boundary'] == 'observed_parent_file_and_command_control'
    assert result['evaluation_boundary']['status'] == 'OBSERVED_PARENT_FILE_AND_COMMAND_CONTROL'
    assert result['usage']['input_tokens'] + result['usage']['output_tokens'] == 3
    assert result['usage_report_count'] == 1
    assert (root / 'outer-arguments.json').is_file()



def test_parent_keeps_global_native_instructions_and_skills_readonly(tmp_path):
    p, state = parent(tmp_path)
    policy = ' '.join(p.argv('/fixture/codex'))
    for name in ('AGENTS.md', 'AGENTS.override.md', 'skills'):
        assert json.dumps(str(state / name)) + '="read"' in policy
