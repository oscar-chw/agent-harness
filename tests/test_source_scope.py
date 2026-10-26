"""Declarations propose a scope; only an explicit revision-bound registry resolves it."""
import copy
import pytest


def fixture():
    source={'source_id':'a'*64,'revision':'b'*64,'sensitivity':'private'}
    row={**source,'project_id':'project-a','declared_scopes':['old-root','new-root']}
    return source,{'schema':'harness.scope-registry/v1','mappings':[row]}


def api():
    from agent_harness.source_scope import resolve_scope
    return resolve_scope


def test_explicit_aliases_resolve_without_granting_activation_or_fact_authority():
    source,registry=fixture()
    result=api()(source,['new-root','old-root'],registry,['project-a'])
    assert result['status']=='RESOLVED' and result['project_id']=='project-a'
    assert result['activation_allowed'] is False and result['current_fact_authority'] is False
    assert 'new-root' not in str(result)


@pytest.mark.parametrize('case,reason',[
    ('empty','MISSING_DECLARATION'),('unknown','UNMAPPED_SOURCE'),('revision','STALE_MAPPING'),
    ('declaration','DECLARATION_MISMATCH'),('denied','PROJECT_NOT_ALLOWED'),('privacy','PRIVACY_CHANGE')])
def test_ambiguous_or_unapproved_mapping_is_quarantined(case,reason):
    source,registry=fixture();observed=['old-root','new-root'];allowed=['project-a']
    if case=='empty':observed=[]
    elif case=='unknown':registry['mappings']=[]
    elif case=='revision':source['revision']='c'*64
    elif case=='declaration':observed=['other-root']
    elif case=='denied':allowed=[]
    elif case=='privacy':registry['mappings'][0]['sensitivity']='public'
    result=api()(source,observed,registry,allowed)
    assert result['status']=='QUARANTINED' and result['reason']==reason
    assert 'project_id' not in result


def test_two_matching_projects_are_not_resolved_by_registry_order():
    source,registry=fixture()
    other=copy.deepcopy(registry['mappings'][0]);other['project_id']='project-b'
    registry['mappings'].append(other)
    for rows in (registry['mappings'],list(reversed(registry['mappings']))):
        result=api()(source,['old-root','new-root'],{**registry,'mappings':rows},['project-a','project-b'])
        assert result['status']=='QUARANTINED' and result['reason']=='CONFLICTING_MAPPING'


def test_policy_and_revision_changes_invalidate_saved_readiness():
    from agent_harness.source_scope import assert_current
    source,registry=fixture();observed=['old-root','new-root'];allowed=['project-a']
    decision=api()(source,observed,registry,allowed)
    assert_current(decision,source,observed,registry,allowed)
    source['revision']='c'*64
    with pytest.raises(ValueError):assert_current(decision,source,observed,registry,allowed)
    source['revision']='b'*64
    registry['mappings'][0]['declared_scopes'].append('extra-root')
    with pytest.raises(ValueError):assert_current(decision,source,observed,registry,allowed)


def test_invalid_schema_cannot_become_an_implicit_global_grant():
    source,registry=fixture()
    registry['schema']='unknown'
    with pytest.raises(ValueError):api()(source,['old-root'],registry,['project-a'])


def test_archive_alias_resolution_requires_exact_source_revision_and_registry(tmp_path):
    import hashlib,json
    from agent_harness.archive_sources import extract_copy
    source=tmp_path/'history.jsonl'
    source.write_text(''.join(json.dumps({'type':'user','cwd':scope,'message':{'content':'Historical note'}})+'\n' for scope in ('old-root','new-root')))
    mapping={'source_id':hashlib.sha256(str(source).encode()).hexdigest(),
        'revision':hashlib.sha256(source.read_bytes()).hexdigest(),'sensitivity':'private',
        'project_id':'logical-project','declared_scopes':['old-root','new-root']}
    registry={'schema':'harness.scope-registry/v1','mappings':[mapping]}
    destination=tmp_path/'copy.json'
    result=extract_copy(source,tmp_path,'logical-project',destination,
                        scope_registry=registry,allowed_projects=['logical-project'])
    assert result['status']=='STAGED_COPY'
    packet=json.loads(destination.read_text())
    assert packet['project_id']=='logical-project'
    assert packet['scope_decision']['status']=='RESOLVED'
    assert packet['activation_allowed'] is False
    assert all(not r['current_fact'] for r in packet['records'])
    source.write_text(source.read_text().replace('Historical','Different'))
    result=extract_copy(source,tmp_path,'logical-project',tmp_path/'stale.json',
                        scope_registry=registry,allowed_projects=['logical-project'])
    assert result['status']=='SCOPE_UNRESOLVED'
    assert result['scope_reason']=='STALE_MAPPING'
    assert not (tmp_path/'stale.json').exists()
