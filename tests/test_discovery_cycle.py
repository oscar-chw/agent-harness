"""Offline acceptance for candidate model discovery; no runtime settings are changed."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

def cli(tmp_path,*args):
    env=dict(os.environ,HOME=str(tmp_path),HARNESS_HOME=str(tmp_path/'harness'))
    return subprocess.run([sys.executable,str(ROOT/'bin/harness'),*args],env=env,cwd=ROOT,capture_output=True,text=True,timeout=10)

def cache(home):
    p=home/'.codex/models_cache.json';p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps({'models':[{'slug':s,'visibility':'list','supported_reasoning_levels':[{'effort':e} for e in ('low','medium','high')]} for s in ('gpt-6-luna','gpt-6.1-terra','gpt-6.1-sol','gpt-6-astra')]}))

def test_public_registry_reports_exact_pairs_without_writing_config(tmp_path):
    cache(tmp_path)
    r=cli(tmp_path,'model-registry')
    assert r.returncode==0,r.stderr
    x=json.loads(r.stdout)
    assert set(x['families'])=={'luna','terra','sol','astra'}
    assert x['families']['luna']['model']=='gpt-6-luna'
    assert x['families']['luna']['effort']=='low'
    assert all(v['status']=='AVAILABLE_CANDIDATE' for v in x['families'].values())
    assert x['performance']=='NOT_MEASURED'
    assert not (tmp_path/'.codex/config.toml').exists()

def test_missing_family_does_not_fall_back_to_an_unrelated_model(tmp_path):
    r=cli(tmp_path,'model-registry');assert r.returncode==0,r.stderr
    assert all(v['status']=='UNAVAILABLE' for v in json.loads(r.stdout)['families'].values())

def test_schedule_is_an_explicit_inactive_harness_command(tmp_path):
    r=cli(tmp_path,'daily-discovery','--schedule');assert r.returncode==0,r.stderr
    x=json.loads(r.stdout)
    assert x['interval_seconds']==86400 and x['enabled'] is False
    assert x['argv'][-1]=='daily-discovery'
    assert not (tmp_path/'harness/state').exists()

def test_daily_diff_retains_baseline_on_error_and_never_promotes(tmp_path):
    from agent_harness import discovery_cycle as d
    cache(tmp_path); hh=tmp_path/'harness'
    first=d.run(hh,tmp_path,now=100000,fetch=lambda url:b'official v1')
    assert first['status']=='PROPOSED' and first['activation']=='HELD'
    assert d.run(hh,tmp_path,now=100001,fetch=lambda u:pytest.fail('not due'))['status']=='NOT_DUE'
    same=d.run(hh,tmp_path,now=186400,fetch=lambda url:b'official v1')
    assert same['status']=='UNCHANGED'
    def failed(url):raise OSError('offline')
    assert d.run(hh,tmp_path,now=272800,fetch=failed)['status']=='FETCH_FAILED'
    changed=d.run(hh,tmp_path,now=359200,fetch=lambda url:b'official v2')
    assert changed['status']=='PROPOSED' and changed['previous']==first['snapshot']
    assert changed['snapshot']!=first['snapshot']
    assert not (hh/'routing.toml').exists() and not (hh/'skills').exists()

@pytest.mark.parametrize('value',[b'',b'x'*262145],ids=['empty','oversized'])
def test_empty_or_oversized_sources_do_not_create_a_candidate(tmp_path,value):
    from agent_harness import discovery_cycle as d
    assert d.run(tmp_path/'h',tmp_path,now=100,fetch=lambda u:value)['status']=='FETCH_FAILED'

@pytest.mark.parametrize('remaining,requested,reliable,expected',[(12000,100,True,'PAUSE'),(13000,4000,True,'PAUSE'),(13000,2000,True,'ALLOW_BOUNDED'),(None,100,False,'UNKNOWN'),(8,100,False,'UNKNOWN')])
def test_reserve_uses_only_reliable_token_counts(remaining,requested,reliable,expected):
    from agent_harness.discovery_cycle import reserve_decision
    assert reserve_decision(remaining,requested,reliable=reliable)==expected

def test_unsupported_effort_is_not_silently_substituted(tmp_path):
    cache(tmp_path);p=tmp_path/'.codex/models_cache.json';x=json.loads(p.read_text())
    x['models'][0]['supported_reasoning_levels']=[{'effort':'high'}];p.write_text(json.dumps(x))
    r=cli(tmp_path,'model-registry');assert r.returncode==0,r.stderr
    assert json.loads(r.stdout)['families']['luna']['status']=='PAIR_UNSUPPORTED'

def test_official_fetch_refuses_unapproved_urls_before_access():
    from agent_harness.discovery_cycle import fetch_official
    with pytest.raises(ValueError):fetch_official('https://example.com/model')

def test_registry_candidate_integrates_with_existing_resolver(tmp_path):
    from agent_harness import discovery_cycle as d, routing
    cache(tmp_path)
    profile=d.routing_candidate(tmp_path)
    resolved=routing.resolve(ROOT/'content',tmp_path,profile)
    assert [resolved[t]['codex']['model'] for t in ('quick','standard','deep','review')]==['gpt-6-luna','gpt-6.1-terra','gpt-6.1-sol','gpt-6-astra']
    assert profile['routing']['progression']['enabled'] is False
    assert not (tmp_path/'harness/routing.toml').exists()

def test_candidate_refuses_incomplete_family_registry(tmp_path):
    from agent_harness import discovery_cycle as d
    with pytest.raises(ValueError):d.routing_candidate(tmp_path)

def test_audit_cap_holds_without_deleting_history(tmp_path,monkeypatch):
    from agent_harness import discovery_cycle as d
    monkeypatch.setattr(d,'MAX_RUNS',2)
    monkeypatch.setattr(d,'MAX_ARCHIVE_BYTES',1)
    for now in (0,86400):assert d.run(tmp_path/'h',tmp_path,now=now,fetch=lambda u:b'x')['status'] in ('PROPOSED','UNCHANGED')
    db=tmp_path/'h/discovery/audit.sqlite';before=db.read_bytes()
    result=d.run(tmp_path/'h',tmp_path,now=172800,fetch=lambda u:pytest.fail('cap must hold before network'))
    assert result['status']=='RETENTION_HOLD' and db.read_bytes()==before

def test_concurrent_cycle_does_not_fetch_again(tmp_path):
    from agent_harness import discovery_cycle as d
    import sqlite3
    seen=[]
    def fetch(url):
        if not seen:
            with pytest.raises(sqlite3.OperationalError):
                d.run(tmp_path/'h',tmp_path,now=100,fetch=lambda u:pytest.fail('duplicate fetch'))
        seen.append(url)
        return b'valid'
    assert d.run(tmp_path/'h',tmp_path,now=100,fetch=fetch)['status']=='PROPOSED'
    assert seen==list(d.SOURCES)

@pytest.mark.parametrize('damage',['null_levels','list_slug'])
def test_malformed_cache_is_controlled(tmp_path,damage):
    cache(tmp_path);p=tmp_path/'.codex/models_cache.json';x=json.loads(p.read_text())
    if damage=='null_levels':x['models'][0]['supported_reasoning_levels']=None
    else:x['models'][0]['slug']=['invalid']
    p.write_text(json.dumps(x))
    r=cli(tmp_path,'model-registry')
    assert r.returncode==0 and 'Traceback' not in r.stderr
    assert json.loads(r.stdout)['families']['luna']['status']!='AVAILABLE_CANDIDATE'

def test_fetch_wall_deadline_terminates_a_stalling_child(monkeypatch):
    from agent_harness import discovery_cycle as d
    import time
    monkeypatch.setattr(d,'FETCH_WORKER','import time; time.sleep(30)',raising=False)
    monkeypatch.setattr(d,'FETCH_SECONDS',0.15,raising=False)
    started=time.monotonic()
    with pytest.raises(OSError,match='deadline'):
        d.fetch_official(d.SOURCES[0])
    assert time.monotonic()-started<3

def test_history_is_read_only_and_does_not_emit_source_bodies(tmp_path):
    from agent_harness import discovery_cycle as d
    hh=tmp_path/'h'
    assert d.history(hh)==[] and not hh.exists()
    d.run(hh,tmp_path,now=1,fetch=lambda u:b'not instructions: private fixture body')
    db=hh/'discovery/audit.sqlite';before=db.read_bytes()
    rows=d.history(hh)
    assert len(rows)==1 and rows[0]['status']=='PROPOSED'
    assert 'private fixture body' not in json.dumps(rows)
    assert db.read_bytes()==before

def test_rotation_keeps_every_receipt_and_successful_baseline(tmp_path,monkeypatch):
    from agent_harness import discovery_cycle as d
    import gzip,sqlite3
    monkeypatch.setattr(d,'MAX_RUNS',3)
    hh=tmp_path/'h';snap=None
    for n in range(8):
        r=d.run(hh,tmp_path,now=n*86400,fetch=lambda u:b'unchanged official data')
        assert r['status'] in ('PROPOSED','UNCHANGED')
        if snap:assert r['snapshot']==snap
        snap=r['snapshot']
    con=sqlite3.connect(hh/'discovery/audit.sqlite')
    rows=con.execute('SELECT id,epoch,status,snapshot,payload FROM runs').fetchall()
    archives=con.execute('SELECT digest,path FROM archives').fetchall();con.close()
    assert archives
    for digest,path in archives:
        raw=gzip.decompress(Path(path).read_bytes())
        import hashlib
        assert hashlib.sha256(raw).hexdigest()==digest
        rows.extend(json.loads(raw))
    assert len(rows)==8 and sorted(row[0] for row in rows)==list(range(1,9))
    env=dict(os.environ,HOME=str(tmp_path),HARNESS_HOME=str(hh))
    result=subprocess.run([sys.executable,str(ROOT/'bin/harness'),'daily-discovery','--history'],env=env,capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
    exposed=json.loads(result.stdout)['archives']
    assert {a['sha256'] for a in exposed}=={a[0] for a in archives}


def test_archive_capacity_hold_preserves_unarchived_rows(tmp_path,monkeypatch):
    from agent_harness import discovery_cycle as d
    monkeypatch.setattr(d,'MAX_RUNS',3);monkeypatch.setattr(d,'MAX_ARCHIVE_BYTES',1,raising=False)
    hh=tmp_path/'h'
    for n in range(3):d.run(hh,tmp_path,now=n*86400,fetch=lambda u:b'content')
    before=d.history(hh)
    r=d.run(hh,tmp_path,now=3*86400,fetch=lambda u:pytest.fail('capacity hold must precede fetch'))
    assert r['status']=='RETENTION_HOLD' and d.history(hh)==before

def test_corrupt_archive_never_replaces_hot_evidence(tmp_path,monkeypatch):
    from agent_harness import discovery_cycle as d
    import gzip,hashlib,sqlite3
    monkeypatch.setattr(d,'MAX_RUNS',3)
    hh=tmp_path/'h'
    for n in range(3):d.run(hh,tmp_path,now=n*86400,fetch=lambda u:b'official')
    before=d.history(hh)
    con=sqlite3.connect(hh/'discovery/audit.sqlite');rows=con.execute('SELECT id,epoch,status,snapshot,payload FROM runs ORDER BY id').fetchall();con.close()
    raw=json.dumps(rows[:-1],ensure_ascii=False,separators=(',',':')).encode()
    archives=hh/'discovery/archives';archives.mkdir()
    (archives/(hashlib.sha256(raw).hexdigest()+'.json.gz')).write_bytes(gzip.compress(b'wrong receipts'))
    with pytest.raises(ValueError,match='archive verification'):
        d.run(hh,tmp_path,now=3*86400,fetch=lambda u:pytest.fail('corruption must stop before fetch'))
    assert d.history(hh)==before
