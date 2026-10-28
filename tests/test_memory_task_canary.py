"""Task-level replay uses real cold CLI processes and independent output acceptance."""
import importlib.util
from pathlib import Path
import pytest


def load():
    path=Path(__file__).resolve().parents[1]/'eval/memory_task_canary.py'
    spec=importlib.util.spec_from_file_location('memory_tasks',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_source_tasks_recover_corrected_state_and_hold_uncertainty(tmp_path):
    result=load().run(tmp_path/'lab')
    assert result['status']=='SOURCE_TASK_PASS'
    assert result['native_model_evidence']=='NOT_RUN'
    assert result['cases']=={
        'initial_configuration':'PASS','explicit_correction':'PASS','stale_writer':'REFUSED',
        'pending_semantics':'HELD','changed_source':'REFUSED','withdrawn_fact':'HELD',
        'cross_project':'QUARANTINED','ambiguous_mapping':'QUARANTINED',
        'stale_readiness':'REFUSED','original_evidence':'PRESERVED'}
    assert result['cold_processes']>=5


def test_task_oracle_rejects_a_stale_or_wrong_retrieval(tmp_path,monkeypatch):
    module=load()
    original=module._read_memory
    def wrong(*args,**kwargs):
        code,body=original(*args,**kwargs)
        if code==0 and body.get('hits'):
            body['hits'][0]['item']['text']='Port: 9999'
        return code,body
    monkeypatch.setattr(module,'_read_memory',wrong)
    with pytest.raises(AssertionError):module.run(tmp_path/'lab')


def test_source_identity_includes_project_not_only_filename():
    module=load()
    a={'source':'policy.txt','sha256':'a'*64,'project_id':'project-a'}
    b={**a,'project_id':'project-b'}
    first,_=module._mapping(a,'project-a');second,_=module._mapping(b,'project-b')
    assert first['source_id']!=second['source_id']
