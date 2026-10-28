"""Schedule lifecycle tests use a fake launchctl; live qualification is separate."""
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

def test_public_scheduler_has_readback_and_disable_actions(tmp_path):
    env=dict(os.environ,HOME=str(tmp_path),HARNESS_HOME=str(tmp_path/'harness'))
    p=subprocess.run([sys.executable,str(ROOT/'bin/harness'),'daily-discovery','--schedule-status'],env=env,capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    assert json.loads(p.stdout)['enabled'] is False

class Launchctl:
    def __init__(self):self.loaded=False;self.calls=[]
    def __call__(self,argv,**kwargs):
        self.calls.append(argv)
        action=argv[1]
        if action=='print':
            error='' if self.loaded else 'Could not find service "com.agent-harness.official-discovery" in domain'
            return subprocess.CompletedProcess(argv,0 if self.loaded else 113,'state = not running\nlast exit code = 0\n',error)
        if action=='bootstrap':self.loaded=True
        if action=='bootout':self.loaded=False
        return subprocess.CompletedProcess(argv,0,'','')

def test_enable_readback_disable_preserves_bundle_and_audit(tmp_path):
    from agent_harness import daily_schedule as d
    home=tmp_path/'home';home.mkdir();hh=tmp_path/'harness';ctl=Launchctl()
    result=d.enable(hh,home,runner=ctl,platform='darwin',uid=501)
    assert result['enabled'] is True
    spec=plistlib.loads(Path(result['plist']).read_bytes())
    assert spec['StartInterval']==86400 and spec['RunAtLoad'] is True
    assert spec['EnvironmentVariables']['HARNESS_HOME']==str(hh)
    bundle=Path(result['bundle']);assert bundle.is_dir()
    state=hh/'discovery/audit.sqlite';state.write_bytes(b'existing audit')
    assert d.status(hh,home,runner=ctl,platform='darwin',uid=501)['enabled'] is True
    result=d.disable(hh,home,runner=ctl,platform='darwin',uid=501)
    assert result['enabled'] is False and bundle.exists() and state.read_bytes()==b'existing audit'
    assert not Path(result['plist']).exists()
    assert d.status(hh,home,runner=ctl,platform='darwin',uid=501)['status']=='DISABLED'

def test_existing_unowned_plist_is_never_replaced(tmp_path):
    from agent_harness import daily_schedule as d
    home=tmp_path/'home';p=home/'Library/LaunchAgents'/f'{d.LABEL}.plist';p.parent.mkdir(parents=True);p.write_text('owner data')
    with pytest.raises(ValueError):d.enable(tmp_path/'h',home,runner=Launchctl(),platform='darwin',uid=501)
    assert p.read_text()=='owner data'

def test_disable_refuses_modified_plist(tmp_path):
    from agent_harness import daily_schedule as d
    home=tmp_path/'home';home.mkdir();hh=tmp_path/'h';ctl=Launchctl()
    r=d.enable(hh,home,runner=ctl,platform='darwin',uid=501)
    p=Path(r['plist']);p.write_bytes(p.read_bytes()+b'\n')
    with pytest.raises(ValueError):d.disable(hh,home,runner=ctl,platform='darwin',uid=501)
    assert ctl.loaded is True

def test_unsupported_host_does_not_claim_enabled(tmp_path):
    from agent_harness import daily_schedule as d
    with pytest.raises(ValueError):d.enable(tmp_path/'h',tmp_path,runner=Launchctl(),platform='win32',uid=501)
    assert not (tmp_path/'h').exists()

@pytest.mark.parametrize('target',['lib/agent_harness/discovery_cycle.py','run.py'])
def test_scheduler_uses_a_frozen_runner_and_refuses_changed_code(tmp_path,target):
    from agent_harness import daily_schedule as d
    home=tmp_path/'home';home.mkdir();hh=tmp_path/'h'
    r=d.enable(hh,home,runner=Launchctl(),platform='darwin',uid=501)
    bundle=Path(r['bundle']);changed=bundle/target
    changed.write_text('raise SystemExit(0)\n' if target=='run.py' else changed.read_text()+'\n# changed after qualification\n')
    env=dict(os.environ,HOME=str(home),HARNESS_HOME=str(hh),PYTHONDONTWRITEBYTECODE='1')
    spec=plistlib.loads(Path(r['plist']).read_bytes())
    result=subprocess.run(spec['ProgramArguments'],env=env,capture_output=True,text=True,timeout=5)
    assert result.returncode!=0 and 'changed' in result.stderr
    assert not (hh/'discovery/audit.sqlite').exists()

def test_bootstrap_failure_is_not_reported_as_active(tmp_path):
    from agent_harness import daily_schedule as d
    ctl=Launchctl()
    def failed(argv,**kwargs):
        if argv[1]=='bootstrap':return subprocess.CompletedProcess(argv,1,'','refused')
        return ctl(argv,**kwargs)
    home=tmp_path/'home';home.mkdir();hh=tmp_path/'h'
    with pytest.raises(OSError,match='bootstrap'):d.enable(hh,home,runner=failed,platform='darwin',uid=501)
    assert not d.status(hh,home,runner=ctl,platform='darwin',uid=501)['enabled']
    assert list((hh/'discovery').glob('bootstrap-failed-*.plist'))

def test_readback_error_cannot_claim_disabled(tmp_path):
    from agent_harness import daily_schedule as d
    home=tmp_path/'home';home.mkdir();hh=tmp_path/'h';ctl=Launchctl()
    r=d.enable(hh,home,runner=ctl,platform='darwin',uid=501)
    p=Path(r['plist']);before=p.read_bytes()
    def unavailable(argv,**kwargs):return subprocess.CompletedProcess(argv,1,'','permission denied')
    with pytest.raises(OSError):d.disable(hh,home,runner=unavailable,platform='darwin',uid=501)
    assert p.read_bytes()==before and ctl.loaded
    with pytest.raises(OSError):d.status(hh,home,runner=unavailable,platform='darwin',uid=501)
