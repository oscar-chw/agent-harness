"""Opt-in whole-client evaluator protection; native state is a write exception.

The controller/grader stays outside this process tree. This is not tenant,
credential, remote-tool or network-domain isolation. Native bookkeeping is
intentionally writable. The launch protocol observes both command and direct
file controls before generation; constructing these arguments is not evidence.
"""
import base64
import binascii
import hashlib
import json
from pathlib import Path


def parent_command(native, actor, oracle, state):
    paths = [Path(p) for p in (actor, oracle, state)]
    if any(not p.is_absolute() or p.is_symlink() or not p.is_dir() for p in paths):
        raise ValueError('parent actor, evaluator and native state must be existing absolute directories')
    actor, oracle, state = [p.resolve(strict=True) for p in paths]
    for a, b in ((actor, oracle), (actor, state), (oracle, state)):
        if a == b or a in b.parents or b in a.parents:
            raise ValueError('actor, evaluator and native state must be separate without overlap')
    name = 'harness_controller_' + hashlib.sha256(str(oracle).encode()).hexdigest()[:12]
    rules = {str(state): 'write', str(oracle): 'deny',
             **{str(state / p): 'read' for p in ('config.toml', 'AGENTS.md', 'AGENTS.override.md',
                                                'agents', 'rules', 'hooks', 'skills')}}
    value = '{' + ','.join(json.dumps(k) + '=' + json.dumps(v) for k, v in rules.items()) + '}'
    return [str(native), 'sandbox', '--include-managed-config', '-P', name, '-C', str(actor),
            '-c', f'permissions.{name}.extends=":read-only"',
            '-c', f'permissions.{name}.filesystem={value}',
            '-c', f'permissions.{name}.network.enabled=true', '--']


def file_control(stage, packet):
    if packet.get('id') != stage or 'method' in packet:
        raise ValueError('parent file control received an unexpected native response')
    if stage == 9:
        try:
            result = packet.get('result')
            data = base64.b64decode(result['dataBase64'], validate=True)
        except (TypeError, KeyError, ValueError, binascii.Error) as error:
            raise ValueError('parent task read control failed') from error
        if 'error' in packet or data != b'harness-boundary-control':
            raise ValueError('parent task read control failed')
    else:
        error = packet.get('error')
        if (not isinstance(error, dict) or error.get('code') != -32603 or 'result' in packet
                or not any(x in str(error.get('message', '')).lower() for x in
                           ('operation not permitted', 'permission denied', 'access is denied'))):
            raise ValueError('parent evaluator file control did not prove denial')
