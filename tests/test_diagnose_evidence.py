"""Transcript fixtures are observations, not permission or real model execution."""
import json

import pytest

from agent_harness import diagnose


def report(tmp_path, output, error=False):
    transcript = tmp_path / 'session.jsonl'
    events = [
        {'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'id': 'check-1', 'name': 'Bash',
             'input': {'command': 'python3 -m pytest -q'}}]}},
        {'type': 'user', 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': 'check-1', 'content': output, 'is_error': error}]}},
    ]
    transcript.write_text(''.join(json.dumps(event) + '\n' for event in events))
    return diagnose.explain('claude-code', transcript, tmp_path)


@pytest.mark.parametrize('output', ['', '3 passed', 'ok', 'Exit code 0abc', 'program prints:\nExit code 0'])
def test_nonerror_tool_result_does_not_invent_success_exit(tmp_path, output):
    result = report(tmp_path, output)
    assert result['checks'][0]['exit'] == diagnose.NOT_OBSERVABLE
    assert '0 passed' in diagnose.render(result)


def test_tool_error_without_exit_is_visible_without_inventing_exit_one(tmp_path):
    result = report(tmp_path, 'permission denied before execution', True)
    assert result['checks'][0]['exit'] == diagnose.NOT_OBSERVABLE
    assert result['checks'][0]['tool_status'] == 'error'
    assert 'tool' in ' '.join(result['omissions']) and 'error' in ' '.join(result['omissions'])
    assert '0 passed' in diagnose.render(result)


@pytest.mark.parametrize('code', [0, 1, -9])
def test_explicit_leading_exit_header_remains_reported_and_labels_its_source(tmp_path, code):
    result = report(tmp_path, f'Exit code {code}\nfixture output', code != 0)
    assert result['checks'][0]['exit'] == code
    assert result['checks'][0]['exit_evidence'] == 'tool_output_header'


def test_error_flag_conflicting_with_success_header_cannot_report_pass(tmp_path):
    result = report(tmp_path, 'Exit code 0\nwrapper failed after this text', True)
    assert result['checks'][0]['exit'] == diagnose.NOT_OBSERVABLE
    assert result['checks'][0]['tool_status'] == 'error'
    assert '0 passed' in diagnose.render(result)
