"""Controller execution contracts; fake native invocations are not efficacy proof."""
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path

import pytest

from agent_harness import procedures


@pytest.fixture
def controller():
    assert importlib.util.find_spec('agent_harness.procedure_execution') is not None, 'controller-owned procedure execution is required'
    return importlib.import_module('agent_harness.procedure_execution')


@pytest.fixture
def lab(tmp_path):
    project=tmp_path/'project';project.mkdir();(project/'.git').mkdir()
    home=tmp_path/'home';oracle=project/'trials'/'fixture-oracle';oracle.mkdir(parents=True)
    episodes=[];cases=[]
    for n in range(4):
        task=project/f'task-{n}.json'
        task.write_text(json.dumps({'instruction':'Return the status from the supplied evidence.', 'evidence':f'Status: case-{n}.'}))
        answer=oracle/f'answer-{n}.json';answer.write_text(json.dumps({'status':f'case-{n}'}))
        case={'task_id':f'task-{n}','class':'status-extraction','split':'development' if n<2 else 'heldout',
              'task_path':task.relative_to(project).as_posix(),'answer_path':answer.relative_to(oracle).as_posix()}
        cases.append(case)
        if n<2:
            source=project/f'episode-{n}.md';source.write_text(f'Operator observation for distinct task {n}; not trusted as a score.')
            episodes.append({'task_id':case['task_id'],'path':source.name,'task_path':task.name})
    c=procedures.prepare(str(project),{'schema':1,'title':'Read exact status','trigger':'status extraction',
        'steps':['Use the current evidence, not an earlier status.'],'exceptions':['Do not infer an absent status.'],'episodes':episodes})
    proposal=procedures.draft(home,str(project),c)
    suite=oracle/'suite.json';suite.write_text(json.dumps({'schema':1,'cases':cases,'model':'fixture-model','effort':'high','timeout_seconds':5}))
    return home,project,oracle,proposal,suite


def prepare(controller,lab):
    home,project,oracle,proposal,suite=lab
    return controller.prepare(home,str(project),proposal['id'],oracle,suite)


def test_freeze_hashes_real_sources_without_executing_or_promoting(controller,lab,monkeypatch):
    monkeypatch.setattr(controller,'_invoke',lambda *a,**k:pytest.fail('freeze must not invoke a model'))
    frozen=prepare(controller,lab)
    assert frozen['status']=='PREPARED' and frozen['calls_max']==6
    assert frozen['promotion']=='NOT_GRANTED'
    data=json.loads(Path(frozen['freeze_path']).read_text())
    assert len(data['cases'])==4 and all(c['task_sha256'] and c['answer_sha256'] for c in data['cases'])
    assert procedures.inspect(lab[0],str(lab[1]),lab[3]['id'])['status']=='proposed'


def test_combined_procedure_prompt_is_checked_before_freeze_or_native_calls(controller,lab,monkeypatch):
    home,project,oracle,proposal,suite=lab
    candidate={**proposal['candidate'],'steps':['Use the current evidence. ' * 180]}
    replacement=procedures.correct(home,str(project),proposal['id'],candidate)
    monkeypatch.setattr(controller,'_invoke',lambda *a,**k:pytest.fail('oversized prompt must not call a model'))
    with pytest.raises(ValueError,match='prompt|task|bounded'):
        controller.prepare(home,str(project),replacement['id'],oracle,suite)
    assert not list(oracle.glob('run-*/freeze.json'))


@pytest.mark.parametrize('fault',['renamed-input','missing-answer','outside-answer','foreign-development'])
def test_invalid_or_overlapping_cases_cannot_be_frozen(controller,lab,fault):
    home,project,oracle,proposal,suite=lab
    data=json.loads(suite.read_text())
    if fault=='renamed-input':
        (project/'task-2.json').write_bytes((project/'task-0.json').read_bytes())
    elif fault=='missing-answer':(oracle/'answer-2.json').unlink()
    elif fault=='outside-answer':data['cases'][2]['answer_path']='../answer.json'
    else:data['cases'][0]['task_id']='invented-development'
    suite.write_text(json.dumps(data))
    with pytest.raises((ValueError,OSError)):prepare(controller,lab)
    assert not list(oracle.glob('run-*/freeze.json'))


def fake_invoke(actor,request,oracle,*,model,effort,timeout):
    """Host-side protocol fixture. Production accepts no runner/score parameter."""
    assert oracle.is_dir() and model=='fixture-model' and effort=='high' and timeout==5
    source=(actor/'evidence.md').read_text().strip()
    value=source.removeprefix('Status: ').removesuffix('.')
    answer=json.dumps({'status':value,'source_ids':['task-evidence']})
    return {'native_completion':'COMPLETED_UNGRADED','usage_scope':'fresh_thread_total',
        'usage_status':'PROVIDER_REPORTED','usage_report_count':1,
        'usage':{'input_tokens':9,'cached_input_tokens':0,'output_tokens':1},
        'permission_boundary':'observed_parent_file_and_command_control',
        'evaluation_boundary':{'status':'OBSERVED_PARENT_FILE_AND_COMMAND_CONTROL','mcp_surface':'OBSERVED_EMPTY',
            'resolved':{'model':model,'reasoningEffort':effort,'modelProvider':'openai','approvalPolicy':'never'},
            'usage_boundary':'native_total_after_terminal_read_barrier'},
        'runtime_events':{'items':[{'item_type':'agent_message'}],'omitted_items':0},
        'answer':answer,'answer_sha256':hashlib.sha256(answer.encode()).hexdigest(),
        'request_sha256':procedures.digest(request)}


def test_executor_grades_actual_artifacts_counts_development_and_remains_held(controller,lab,monkeypatch):
    calls=[]
    def invoke(*args,**kwargs):calls.append(args[0]);return fake_invoke(*args,**kwargs)
    monkeypatch.setattr(controller,'_invoke',invoke)
    frozen=prepare(controller,lab)
    result=controller.execute(lab[0],str(lab[1]),frozen['run_id'])
    assert result['status']=='GRADED_HELD' and result['promotion']=='NOT_GRANTED'
    assert len(calls)==6 and result['observed_calls']==6
    assert result['known_candidate_tokens_lower_bound']==40
    assert result['known_baseline_tokens']==20
    assert result['usage_complete'] is False and 'preparation' in ' '.join(result['holds'])
    assert all(row['correct'] is True for row in result['observations'])
    # Completed actors move under the denied oracle before another actor starts.
    assert not any(p.exists() for p in calls)
    assert procedures.inspect(lab[0],str(lab[1]),lab[3]['id'])['status']=='proposed'
    with pytest.raises(ValueError,match='consumed|already'):
        controller.execute(lab[0],str(lab[1]),frozen['run_id'])


@pytest.mark.parametrize('fault',['oracle','task','candidate','runtime','freeze'])
def test_changed_inputs_fail_before_any_invocation(controller,lab,monkeypatch,fault):
    frozen=prepare(controller,lab)
    if fault=='oracle':(lab[2]/'answer-2.json').write_text('{"changed":true}')
    elif fault=='task':(lab[1]/'task-2.json').write_text('{"changed":true}')
    elif fault=='candidate':(lab[1]/'episode-0.md').write_text('Changed candidate evidence')
    elif fault=='runtime':
        original=controller._runtime
        monkeypatch.setattr(controller,'_runtime',lambda:{**original(),'procedure_execution.py':'0'*64})
    else:
        doc=json.loads(Path(frozen['freeze_path']).read_text());doc['runtime']['procedure_execution.py']='0'*64
        Path(frozen['freeze_path']).write_text(json.dumps(doc))
    monkeypatch.setattr(controller,'_invoke',lambda *a,**k:pytest.fail('changed freeze must not launch'))
    with pytest.raises((ValueError,OSError)):
        controller.execute(lab[0],str(lab[1]),frozen['run_id'])


@pytest.mark.parametrize('fault',['partial-usage','wrong-model','tools-used','wrong-answer','crash'])
def test_failed_native_or_grade_is_consumed_not_hidden_or_retried(controller,lab,monkeypatch,fault):
    calls=[]
    def invoke(*args,**kwargs):
        calls.append(1)
        if fault=='crash':raise RuntimeError('native execution failed')
        value=fake_invoke(*args,**kwargs)
        if fault=='partial-usage':value['usage_status']='PARTIAL_OR_UNKNOWN'
        elif fault=='wrong-model':value['evaluation_boundary']['resolved']['model']='other'
        elif fault=='tools-used':value['runtime_events']['items']=[{'item_type':'command_execution'}]
        else:
            value['answer']='{"status":"wrong","source_ids":["task-evidence"]}'
            value['answer_sha256']=hashlib.sha256(value['answer'].encode()).hexdigest()
        return value
    monkeypatch.setattr(controller,'_invoke',invoke)
    frozen=prepare(controller,lab);result=controller.execute(lab[0],str(lab[1]),frozen['run_id'])
    assert result['status']=='FAILED' and result['promotion']=='NOT_GRANTED'
    assert len(calls)==1 and result['usage_complete'] is False
    assert result['failures']
    with pytest.raises(ValueError,match='consumed|already'):
        controller.execute(lab[0],str(lab[1]),frozen['run_id'])


def test_receipt_with_foreign_request_identity_is_consumed_ungraded_and_retained(controller,lab,monkeypatch):
    def invoke(*args,**kwargs):
        value=fake_invoke(*args,**kwargs);value['request_sha256']='ff'*32;return value
    monkeypatch.setattr(controller,'_invoke',invoke)
    frozen=prepare(controller,lab)
    result=controller.execute(lab[0],str(lab[1]),frozen['run_id'])
    assert result['status']=='FAILED' and result['observed_calls']==1 and result['observations']==[]
    assert 'request identity' in result['failures'][0]['error']
    attempt=result['execution_attempts'][0]
    assert attempt['consumed'] is True and attempt['native_sha256']
    with pytest.raises(ValueError,match='consumed|already'):
        controller.execute(lab[0],str(lab[1]),frozen['run_id'])


def test_native_seam_uses_the_actual_launch_contract(controller,lab,monkeypatch):
    from agent_harness import launch
    actor=lab[2].parent/'native-seam-actor';actor.mkdir()
    request=controller._actor(actor,{'instruction':'Read status.','evidence':'Status: fixture.'},None)
    seen=[]
    def native(root,request_path,receipt_path,**kwargs):
        # The real preparer rejects nonexistent modes; this previously failed.
        packet=launch.prepare(root,request_path,method_policy=kwargs['method_policy'])
        seen.append(packet['method_policy'])
        assert kwargs['eval_enforce_boundary'] and kwargs['eval_parent_boundary']
        return fake_invoke(root,request,kwargs['eval_deny_root'],model=kwargs['native_model'],
                           effort=kwargs['native_effort'],timeout=kwargs['timeout'])
    monkeypatch.setattr(launch,'execute',native)
    monkeypatch.setattr(launch,'read_answer',lambda root,r:r['answer'])
    result=controller._invoke(actor,request,lab[2],model='fixture-model',effort='high',timeout=5)
    assert result['native_completion']=='COMPLETED_UNGRADED' and seen==['existing']


def test_controller_does_not_swallow_interrupt_or_release_consumed_attempt(controller,lab,monkeypatch):
    def interrupt(*a,**k):raise KeyboardInterrupt()
    monkeypatch.setattr(controller,'_invoke',interrupt)
    frozen=prepare(controller,lab)
    with pytest.raises(KeyboardInterrupt):controller.execute(lab[0],str(lab[1]),frozen['run_id'])
    result=json.loads((Path(frozen['freeze_path']).parent/'result.json').read_text())
    assert result['status']=='INTERRUPTED' and result['usage_complete'] is False
    with pytest.raises(ValueError,match='consumed|already'):
        controller.execute(lab[0],str(lab[1]),frozen['run_id'])


def test_archive_budget_stops_without_deleting_retained_data(controller,lab,monkeypatch):
    frozen=prepare(controller,lab);path=Path(frozen['freeze_path'])
    old=path.read_bytes()
    monkeypatch.setattr(controller,'MAX_RUN_BYTES',len(old)-1)
    monkeypatch.setattr(controller,'_invoke',lambda *a,**k:pytest.fail('storage hold cannot launch'))
    result=controller.execute(lab[0],str(lab[1]),frozen['run_id'])
    assert result['status']=='FAILED' and result['observed_calls']==0
    assert path.read_bytes()==old and 'storage' in result['failures'][0]['error']


def test_final_call_storage_overrun_is_visible_and_retained(controller,lab,monkeypatch):
    frozen=prepare(controller,lab)
    monkeypatch.setattr(controller,'MAX_RUN_BYTES',1024*1024)
    calls=[]
    def invoke(actor,*args,**kwargs):
        calls.append(1)
        if len(calls)==6:(actor/'retained-extra').write_bytes(b'x'*(1024*1024))
        return fake_invoke(actor,*args,**kwargs)
    monkeypatch.setattr(controller,'_invoke',invoke)
    result=controller.execute(lab[0],str(lab[1]),frozen['run_id'])
    assert result['status']=='FAILED' and result['observed_calls']==6
    assert 'storage' in result['failures'][0]['error']
    assert len(list(Path(frozen['freeze_path']).parent.rglob('retained-extra')))==1


def test_preexisting_actor_folder_is_never_moved_or_overwritten(controller,lab,monkeypatch):
    frozen=prepare(controller,lab)
    actor=lab[2].parent/('trial-'+frozen['run_id']+'-0-candidate');actor.mkdir()
    (actor/'user-file').write_text('Preserve this preexisting folder.')
    monkeypatch.setattr(controller,'_invoke',lambda *a,**k:pytest.fail('preexisting actor must refuse'))
    result=controller.execute(lab[0],str(lab[1]),frozen['run_id'])
    assert result['status']=='FAILED' and result['observed_calls']==0
    assert (actor/'user-file').read_text()=='Preserve this preexisting folder.'


def test_duplicate_heldout_inputs_are_rejected_even_with_distinct_names(controller,lab):
    (lab[1]/'task-3.json').write_bytes((lab[1]/'task-2.json').read_bytes())
    with pytest.raises(ValueError,match='repeat'):
        prepare(controller,lab)


def test_nonfinite_grader_answer_is_refused_before_freezing_or_native_calls(controller,lab):
    (lab[2]/'answer-2.json').write_text('{"status":NaN}')
    with pytest.raises(ValueError):prepare(controller,lab)
    assert not list(lab[2].glob('run-*/freeze.json'))


def test_candidate_correction_during_trial_invalidates_it_before_more_calls(controller,lab,monkeypatch):
    frozen=prepare(controller,lab);calls=[]
    def invoke(*args,**kwargs):
        calls.append(1)
        candidate={**lab[3]['candidate'],'title':'Corrected status method'}
        procedures.correct(lab[0],str(lab[1]),lab[3]['id'],candidate)
        return fake_invoke(*args,**kwargs)
    monkeypatch.setattr(controller,'_invoke',invoke)
    result=controller.execute(lab[0],str(lab[1]),frozen['run_id'])
    assert result['status']=='FAILED' and len(calls)==1
    assert procedures.inspect(lab[0],str(lab[1]),lab[3]['id'])['status']=='rolled_back'


def test_heldout_wrong_answer_is_diagnosed_without_hiding_its_tokens(controller,lab,monkeypatch):
    calls=[]
    def invoke(actor,request,oracle,**kwargs):
        calls.append(1);r=fake_invoke(actor,request,oracle,**kwargs)
        if 'Procedure candidate' in request['task'] and 'case-3' in (actor/'evidence.md').read_text():
            r['answer']='{"status":"wrong","source_ids":["task-evidence"]}'
            r['answer_sha256']=hashlib.sha256(r['answer'].encode()).hexdigest()
        return r
    monkeypatch.setattr(controller,'_invoke',invoke);frozen=prepare(controller,lab)
    r=controller.execute(lab[0],str(lab[1]),frozen['run_id'])
    assert len(calls)==6 and r['known_candidate_tokens_lower_bound']==40
    assert any('task-3' in h and 'held-out' in h for h in r['holds'])
    assert all(o['class']=='status-extraction' for o in r['observations'])
    assert r['promotion']=='NOT_GRANTED'
