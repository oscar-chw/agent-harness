"""Opt-in, user-scoped macOS discovery timer. Never installs a model or a skill."""
from __future__ import annotations

import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import sys
import time

from . import installer as I
from .discovery_cycle import DAY

LABEL = 'com.agent-harness.official-discovery'


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _paths(hh, home):
    return hh / 'discovery/schedule.json', home / 'Library/LaunchAgents' / (LABEL + '.plist')


def _ctl(runner, *args):
    return runner(['/bin/launchctl', *args], capture_output=True, text=True, timeout=10,
                  env=dict(os.environ, LC_ALL='C'))


def _loaded(runner, target):
    probe = _ctl(runner, 'print', target)
    if probe.returncode == 0:
        return True
    if probe.returncode == 113 and ('Could not find service "' + LABEL + '"') in probe.stderr:
        return False
    raise OSError('launchctl readback unavailable; service absence is not established')


def _domain(uid):
    return 'gui/' + str(os.getuid() if uid is None else uid)


def _save(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(tmp, path)


def status(hh, home, *, runner=subprocess.run, platform=sys.platform, uid=None):
    receipt, plist = _paths(hh, home)
    if not receipt.is_file():
        return {'enabled': False, 'status': 'NOT_INSTALLED', 'plist': str(plist)}
    data = json.loads(receipt.read_text())
    if platform != 'darwin':
        return {**data, 'enabled': False, 'status': 'UNSUPPORTED_HOST'}
    loaded = _loaded(runner, _domain(uid) + '/' + LABEL)
    if data.get('status') == 'DISABLED' and not plist.exists() and not loaded:
        return {**data, 'enabled': False, 'status': 'DISABLED'}
    present = plist.is_file() and _digest(plist) == data['plist_sha256']
    return {**data, 'enabled': loaded and present,
            'status': 'LOADED' if loaded and present else 'NOT_LOADED_OR_CHANGED'}


def enable(hh, home, *, runner=subprocess.run, platform=sys.platform, uid=None):
    if platform != 'darwin':
        raise ValueError('native discovery scheduling currently supports macOS only')
    receipt, plist = _paths(hh, home)
    if plist.exists() or plist.is_symlink():
        raise ValueError('existing discovery plist must be reviewed and disabled first')
    if _loaded(runner, _domain(uid) + '/' + LABEL):
        raise ValueError('a discovery job is already loaded')
    root = hh / 'discovery'
    root.mkdir(parents=True, exist_ok=True)
    bundle = root / ('runner-' + str(time.time_ns()))
    package = bundle / 'lib/agent_harness'
    shutil.copytree(I.PKG_DIR, package, ignore=I.IGNORE)
    shutil.copytree(I.REPO_ROOT / 'content', package / 'content', dirs_exist_ok=True, ignore=I.IGNORE)
    hashes = {str(p.relative_to(bundle)): _digest(p) for p in (bundle / 'lib').rglob('*') if p.is_file()}
    (bundle / 'manifest.json').write_text(json.dumps(hashes, sort_keys=True))
    # Freeze code independently of a working checkout. A changed bundle refuses
    # rather than silently running newly edited code on tomorrow's invocation.
    script = bundle / 'run.py'
    script.write_text('''import hashlib,json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parent
expected={k:v for k,v in json.loads((root/'manifest.json').read_text()).items() if k.startswith('lib/')}
actual={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'lib').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
if actual != expected: raise SystemExit('discovery runner changed; re-qualify before enabling')
sys.path.insert(0,str(root/'lib'))
from agent_harness.discovery_cycle import run
result=run(Path(os.environ['HARNESS_HOME']),Path.home())
print(json.dumps(result),flush=True)
raise SystemExit(1 if result['status'] in ('FETCH_FAILED','RETENTION_HOLD') else 0)
''')
    hashes['run.py'] = _digest(script)
    (bundle / 'manifest.json').write_text(json.dumps(hashes, sort_keys=True))
    # The bootstrapped command pins both the manifest and runner, outside the
    # mutable bundle. This detects drift, not a hostile same-user launchctl edit.
    bootstrap = """import hashlib,json,runpy,sys
from pathlib import Path
root=Path(sys.argv[1]); raw=(root/'manifest.json').read_bytes()
if hashlib.sha256(raw).hexdigest()!=sys.argv[2]: raise SystemExit('discovery manifest changed')
expected=json.loads(raw)
for name,want in expected.items():
 if hashlib.sha256((root/name).read_bytes()).hexdigest()!=want: raise SystemExit('discovery runner changed')
runpy.run_path(str(root/'run.py'),run_name='__main__')
"""
    spec = {'Label': LABEL, 'ProgramArguments': [sys.executable, '-c', bootstrap, str(bundle), _digest(bundle / 'manifest.json')],
            'RunAtLoad': True, 'StartInterval': DAY, 'ProcessType': 'Background',
            'EnvironmentVariables': {'HOME': str(home), 'HARNESS_HOME': str(hh), 'PYTHONDONTWRITEBYTECODE': '1'},
            'StandardOutPath': str(root / 'daily.out.log'), 'StandardErrorPath': str(root / 'daily.err.log')}
    plist.parent.mkdir(parents=True, exist_ok=True)
    with plist.open('xb') as stream:
        plistlib.dump(spec, stream)
    data = {'schema': 1, 'enabled': False, 'plist': str(plist), 'bundle': str(bundle),
            'plist_sha256': _digest(plist), 'interval_seconds': DAY,
            'scope': 'official-source discovery only; no model calls, installs or promotion'}
    _save(receipt, data)
    loaded = _ctl(runner, 'bootstrap', _domain(uid), str(plist))
    if loaded.returncode:
        plist.rename(root / ('bootstrap-failed-' + str(time.time_ns()) + '.plist'))
        raise OSError('launchctl bootstrap failed; bundle and receipt retained; job not claimed enabled')
    result = status(hh, home, runner=runner, platform=platform, uid=uid)
    if not result['enabled']:
        raise OSError('scheduler readback failed; inspect before retrying')
    _save(receipt, result)
    return result


def disable(hh, home, *, runner=subprocess.run, platform=sys.platform, uid=None):
    if platform != 'darwin':
        raise ValueError('native discovery scheduling currently supports macOS only')
    receipt, plist = _paths(hh, home)
    data = json.loads(receipt.read_text())
    if not plist.is_file() or _digest(plist) != data['plist_sha256']:
        raise ValueError('discovery plist changed or missing; refuse to affect unknown configuration')
    target = _domain(uid) + '/' + LABEL
    if _loaded(runner, target):
        stopped = _ctl(runner, 'bootout', target)
        if stopped.returncode:
            raise OSError('launchctl bootout failed; job not claimed disabled')
    if _loaded(runner, target):
        raise OSError('discovery job remains loaded')
    archived = hh / 'discovery' / ('disabled-' + str(time.time_ns()) + '.plist')
    plist.rename(archived)
    data.update(enabled=False, status='DISABLED', archived_plist=str(archived))
    _save(receipt, data)
    return data
