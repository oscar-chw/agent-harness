"""Deterministic advisory source mapping; declarations never grant runtime access."""
import hashlib
import json
import re


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _strings(values):
    if (not isinstance(values,list) or len(values)>1000 or
            any(not isinstance(x,str) or not x or len(x)>4096 for x in values) or len(values)!=len(set(values))):
        raise ValueError('explicit bounded unique string list required')
    return sorted(values)


def _identity(item):
    for key in ('source_id','revision'):
        if not isinstance(item.get(key),str) or not re.fullmatch('[0-9a-f]{64}',item[key]):
            raise ValueError('source and revision digests required')
    if item.get('sensitivity') not in ('public','internal','private'):
        raise ValueError('source sensitivity required')


def resolve_scope(source,observed_scopes,registry,allowed_projects):
    if not isinstance(source,dict) or set(source)!={'source_id','revision','sensitivity'}:
        raise ValueError('invalid source identity')
    _identity(source)
    observed=_strings(observed_scopes);allowed=_strings(allowed_projects)
    if (not isinstance(registry,dict) or set(registry)!={'schema','mappings'} or
            registry['schema']!='harness.scope-registry/v1' or
            not isinstance(registry['mappings'],list) or len(registry['mappings'])>10000):
        raise ValueError('explicit scope registry required')
    normalized=[]
    for row in registry['mappings']:
        if not isinstance(row,dict) or set(row)!={'source_id','revision','sensitivity','project_id','declared_scopes'}:
            raise ValueError('invalid registry mapping')
        _identity(row)
        if not isinstance(row['project_id'],str) or not row['project_id'] or len(row['project_id'])>512:
            raise ValueError('invalid project identity')
        normalized.append({**row,'declared_scopes':_strings(row['declared_scopes'])})
    normalized.sort(key=lambda x:json.dumps(x,sort_keys=True))
    out={'schema':'harness.scope-decision/v1','source_id':source['source_id'],'revision':source['revision'],
         'policy_sha256':_digest(normalized),'observation_sha256':_digest(observed),
         'allowed_projects_sha256':_digest(allowed),'sensitivity':source['sensitivity'],
         'status':'QUARANTINED','activation_allowed':False,'current_fact_authority':False}
    def quarantine(reason):
        return {**out,'reason':reason}
    if not observed:return quarantine('MISSING_DECLARATION')
    matches=[r for r in normalized if r['source_id']==source['source_id']]
    if not matches:return quarantine('UNMAPPED_SOURCE')
    matches=[r for r in matches if r['revision']==source['revision']]
    if not matches:return quarantine('STALE_MAPPING')
    if any(r['declared_scopes']!=observed for r in matches):return quarantine('DECLARATION_MISMATCH')
    if any(r['sensitivity']!=source['sensitivity'] for r in matches):return quarantine('PRIVACY_CHANGE')
    projects={r['project_id'] for r in matches}
    if len(projects)!=1:return quarantine('CONFLICTING_MAPPING')
    project=next(iter(projects))
    if project not in allowed:return quarantine('PROJECT_NOT_ALLOWED')
    return {**out,'status':'RESOLVED','project_id':project,'reason':'EXPLICIT_REVISION_BOUND_MAPPING'}


def assert_current(decision,source,observed_scopes,registry,allowed_projects):
    current=resolve_scope(source,observed_scopes,registry,allowed_projects)
    if current['status']!='RESOLVED' or decision!=current:
        raise ValueError('scope decision is stale, unresolved or outside allowed projects')
