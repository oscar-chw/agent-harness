"""Personal-v1 authority supersedes the historical +15% and noise allowances."""
import json

import pytest

from agent_harness import improve


def comparison(bp=4, cp=5, bt=100, ct=100):
    return {'base': {'pass': bp, 'n': 6, 'tokens': bt},
            'cand': {'pass': cp, 'n': 6, 'tokens': ct}}


def test_old_keep_rule_cannot_admit_more_tokens():
    assert not improve.keep_rule(comparison(ct=101))[0]
    assert improve.keep_rule(comparison())[0]


def test_equal_quality_and_fewer_tokens_is_a_measurable_gain():
    assert improve.keep_rule(comparison(cp=4, ct=99))[0]
    assert not improve.keep_rule(comparison(cp=4))[0]
    assert not improve.keep_rule(comparison(cp=3, ct=50))[0]


@pytest.mark.parametrize('passes,tokens', [(53, 100), (54, 101)])
def test_old_release_trend_cannot_relax_personal_v1(passes, tokens):
    base = {'version': 'a', 'n': 54, 'pass': 54, 'tokens': 100}
    cand = {'version': 'b', 'n': 54, 'pass': passes, 'tokens': tokens}
    assert not improve._judge(cand, [base])[0]
    assert improve._judge(dict(cand, **{'pass': 54, 'tokens': 100}), [base])[0]


def test_captured_error_is_not_automatically_a_procedure(tmp_path):
    proposals = tmp_path / 'proposals'
    proposals.mkdir()
    prop = {'id': 'legacy', 'status': 'proposed', 'summary': 'test failed',
            'evidence': 'exit code 1', 'count': 2}
    path = proposals / 'legacy.json'
    path.write_text(json.dumps(prop))
    receipt = tmp_path / 'comparison.json'
    receipt.write_text(json.dumps({'proposal': 'legacy', **comparison()}))
    code, message = improve.apply(tmp_path, 'legacy', str(receipt))
    assert code != 0 and 'procedure' in message and 'draft' in message
    assert json.loads(path.read_text()) == prop
    assert not (tmp_path / 'lessons.jsonl').exists()
