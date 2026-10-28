"""Deterministic application replay through cold harness CLI clients, not a model eval."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from agent_harness.project_memory import ProjectMemory  # noqa: E402
from agent_harness.source_scope import resolve_scope, assert_current  # noqa: E402
from agent_harness.vault_sources import SourceVault, initialize  # noqa: E402


def _read_memory(root,project_id,home):
    env={**os.environ,'HOME':str(home),'HARNESS_HOME':str(home/'harness'),
         'PYTHONDONTWRITEBYTECODE':'1'}
    result=subprocess.run([sys.executable,str(ROOT/'bin/harness'),'memory-page',
        '--project-root',str(root),'--project-id',project_id,'--query','port',
        '--allow-sensitivity','private','--allow-scope','task','--layer','project_facts'],
        cwd=home,env=env,capture_output=True,text=True,timeout=15)
    return result.returncode,json.loads(result.stdout) if result.returncode==0 else {}


def _fixture(root):
    root.mkdir();identity=initialize(root)
    return identity,ProjectMemory(root,identity),SourceVault(root,identity)


def _append(root,identity,memory,vault,text,previous=None,claim=None,freshness='current'):
    (root/'policy.txt').write_text(text+'\n')
    source=vault.capture('policy.txt')
    item={'id':'port','project_id':identity,'layer':'project_facts','kind':'fact','scope':'task',
          'text':text if claim is None else claim,'provenance':[{'source':source,'start_line':1,'end_line':1}],
          'confidence':'verified','sensitivity':'private','access_boundary':'local_user',
          'owner':'fixture-owner','freshness':freshness}
    return memory.append(item,expected=previous),source,item


def _mapping(source,identity):
    # The explicit fixture registry is not inferred from source text or a filename.
    identity_bytes=json.dumps({'project_id':source['project_id'],'source':source['source']},sort_keys=True).encode()
    ref={'source_id':hashlib.sha256(identity_bytes).hexdigest(),
         'revision':source['sha256'],'sensitivity':'private'}
    registry={'schema':'harness.scope-registry/v1','mappings':[
        {**ref,'project_id':identity,'declared_scopes':['fixture-project']} ]}
    return ref,registry


def _apply(body,destination):
    assert len(body['hits'])==1,'no unique usable memory claim'
    claim=body['hits'][0]['item']
    assert claim['confidence']=='verified' and claim['freshness']=='current'
    match=re.fullmatch(r'Port: (\d+)',claim['text'])
    assert match,'unexpected application contract'
    destination.write_text(json.dumps({'port':int(match.group(1))}))


def _accept(destination,oracle):
    expected=json.loads(oracle.read_text())
    actual=json.loads(destination.read_text())
    assert actual['port']==expected['required_port'],'configuration violates independent task contract'


def run(lab):
    lab=Path(lab);lab.mkdir(exist_ok=False)
    home=lab/'home';home.mkdir()
    root=lab/'alpha';identity,memory,vault=_fixture(root)
    other=lab/'bravo';other_id,other_memory,other_vault=_fixture(other)
    _append(other,other_id,other_memory,other_vault,'Port: 9000')
    # Acceptance inputs are separate from application outputs and retrieval parsing.
    oracle1=lab/'task-1.json';oracle1.write_text(json.dumps({'required_port':8081}))
    oracle2=lab/'task-2.json';oracle2.write_text(json.dumps({'required_port':8082}))
    cases={};timings=[];packets=[]
    def read():
        start=time.perf_counter();code,body=_read_memory(root,identity,home)
        timings.append((time.perf_counter()-start)*1000)
        packets.append(len(json.dumps(body).encode()))
        return code,body
    first,source,_=_append(root,identity,memory,vault,'Port: 8081')
    ref,registry=_mapping(source,identity)
    readiness=resolve_scope(ref,['fixture-project'],registry,[identity])
    assert readiness['status']=='RESOLVED'
    code,body=read();assert code==0
    _apply(body,lab/'config-1.json');_accept(lab/'config-1.json',oracle1)
    assert '9000' not in json.dumps(body)
    cases['initial_configuration']='PASS'
    retained={str(p.relative_to(root)):p.read_bytes() for folder in (root/'.harness/records',root/'.harness/sources')
              for p in folder.rglob('*') if p.is_file()}
    second,source,item=_append(root,identity,memory,vault,'Port: 8082',first)
    new_ref,new_registry=_mapping(source,identity)
    try:assert_current(readiness,new_ref,['fixture-project'],new_registry,[identity])
    except ValueError:cases['stale_readiness']='REFUSED'
    else:raise AssertionError('old readiness silently survived a source revision')
    readiness=resolve_scope(new_ref,['fixture-project'],new_registry,[identity])
    assert readiness['status']=='RESOLVED'
    code,body=read();assert code==0
    _apply(body,lab/'config-2.json');_accept(lab/'config-2.json',oracle2)
    assert body['hits'][0]['receipt']==second
    cases['explicit_correction']='PASS'
    try:memory.append({**item,'text':'Port: 8083'},expected=first)
    except ValueError:cases['stale_writer']='REFUSED'
    else:raise AssertionError('stale writer succeeded')
    assert memory.read(first,allowed_sensitivities=['private'],historical=True)['item']['text']=='Port: 8081'
    assert all((root/p).read_bytes()==raw for p,raw in retained.items())
    cases['original_evidence']='PRESERVED'
    pending,_,_=_append(root,identity,memory,vault,'Port: 8082',second,claim='Port: 8083')
    code,body=read();assert code==0 and not body['hits']
    assert any(x['reason']=='pending' for x in body['omitted'])
    cases['pending_semantics']='HELD'
    third,source,item=_append(root,identity,memory,vault,'Port: 8082',pending)
    (root/'policy.txt').write_text('Port: 9999\n')
    code,body=read();assert code!=0 and body=={}
    cases['changed_source']='REFUSED'
    # Restore fixture evidence, then explicitly withdraw; no real history is touched.
    _append(root,identity,memory,vault,'Port: 8082',third,freshness='withdrawn')
    code,body=read();assert code==0 and not body['hits']
    assert any(x['reason']=='withdrawn' for x in body['omitted'])
    cases['withdrawn_fact']='HELD'
    denied=resolve_scope(new_ref,['fixture-project'],new_registry,[other_id])
    assert denied['status']=='QUARANTINED' and denied['reason']=='PROJECT_NOT_ALLOWED'
    cases['cross_project']='QUARANTINED'
    ambiguous=copy.deepcopy(new_registry)
    ambiguous['mappings'].append({**ambiguous['mappings'][0],'project_id':other_id})
    result=resolve_scope(new_ref,['fixture-project'],ambiguous,[identity,other_id])
    assert result['status']=='QUARANTINED' and result['reason']=='CONFLICTING_MAPPING'
    cases['ambiguous_mapping']='QUARANTINED'
    return {'status':'SOURCE_TASK_PASS','cases':cases,'cold_processes':len(timings),
            'process_ms':[round(x,3) for x in timings],'response_bytes':packets,
            'native_model_evidence':'NOT_RUN','model_tokens':'NOT_MEASURED','live_migration':False,
            'semantic_scope':'explicit corrections and direct source assertions only; no free-form truth inference'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='memory-task-canary-') as directory:
        report=run(Path(directory)/'lab')
    data=json.dumps(report,indent=2)
    if args.output:
        with args.output.open('x') as f:f.write(data+'\n')
    print(data)
