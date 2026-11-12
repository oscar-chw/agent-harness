"""Actual unprotected command control, plus malformed native-control refusals.

The rejected whole-client wrapper is archived with its failed SQLite startup.
These tests target the supported tool boundary and do not certify native macOS.
"""
import json
import subprocess
import sys

import pytest

from agent_harness.eval_boundary import CONTROL, PROBE, EvaluationProtocol
from .test_eval_protocol import through_control, response


@pytest.mark.parametrize('control', [{**CONTROL, 'inside_readable': False},
    {**CONTROL, 'oracle_denied': False}, {**CONTROL, 'writes_denied': False},
    {**CONTROL, 'writes_denied': 1}, {}, {**CONTROL, 'extra': True}])
def test_missing_or_ineffective_native_control_never_permits_generation(tmp_path, control):
    p = EvaluationProtocol(tmp_path/'actor', tmp_path/'oracle', 'in', 'out', 'model', 'high', 'task')
    check = through_control(p)
    with pytest.raises(ValueError, match='boundary'):
        p.feed(response(check['id'], {'exitCode': 0, 'stdout': json.dumps(control)}))
    assert not any(r['method'] in ('thread/start', 'turn/start') for r in p.pending)


@pytest.mark.parametrize('code,body', [(2, json.dumps(CONTROL)), (0, 'not json'),
                                     (True, json.dumps(CONTROL))])
def test_command_failure_or_invalid_output_is_not_evidence(tmp_path, code, body):
    p = EvaluationProtocol(tmp_path/'actor', tmp_path/'oracle', 'in', 'out', 'model', 'high', 'task')
    check = through_control(p)
    with pytest.raises(ValueError, match='boundary'):
        p.feed(response(check['id'], {'exitCode': code, 'stdout': body}))
    assert not any(r['method'] == 'turn/start' for r in p.pending)


def test_actual_unprotected_child_fails_the_same_native_control(tmp_path):
    actor, oracle = tmp_path/'actor', tmp_path/'oracle'
    actor.mkdir(); oracle.mkdir()
    inside, outside = actor/'inside', oracle/'outside'
    inside.write_bytes(b'harness-boundary-control'); outside.write_bytes(b'fixture-only')
    observed = subprocess.run([sys.executable, '-B', '-I', '-S', '-c', PROBE, str(inside), str(outside)],
                              capture_output=True, text=True, timeout=3, check=True)
    assert json.loads(observed.stdout) == {'inside_readable': True, 'oracle_denied': False,
                                          'writes_denied': False}
    p = EvaluationProtocol(actor, oracle, str(inside), str(outside), 'model', 'high', 'task')
    check = through_control(p)
    with pytest.raises(ValueError, match='boundary'):
        p.feed(response(check['id'], {'exitCode': observed.returncode, 'stdout': observed.stdout}))
    assert not any(r['method'] in ('thread/start', 'turn/start') for r in p.pending)
