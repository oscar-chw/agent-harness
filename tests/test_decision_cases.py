"""Visible development-case calibration does not imply native decision quality."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest
from agent_harness.mcp.kb import KB

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('decision_case_check', ROOT / 'docs/v2/check_decision_cases.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def pack():
    return json.loads(checker.PACK.read_text())


def test_all_visible_family_contrasts_and_sql_controls_are_exercised():
    result = checker.validate(pack())
    assert result['families'] == 6 and result['variants'] == 19
    assert result['sql_query_controls'] == 6
    assert result['native_decision_quality'] == result['comparative_quality_total_usage'] == 'NOT_RUN'


def test_each_fluent_but_wrong_consequence_is_rejected(capsys):
    assert checker.negative_controls(pack()) == 7
    output = capsys.readouterr().out
    assert 'accept-fanout' in output and 'ignore-accessibility' in output


@pytest.mark.parametrize('change', ['no_outcomes', 'changed_facts', 'missing_contrast', 'pretend_execution'])
def test_incomplete_or_invented_case_qualification_fails(change):
    value = pack()
    v = value['families'][0]['variants'][0]
    if change == 'no_outcomes':
        v['expected_observable_distinctions'] = {}
    elif change == 'changed_facts':
        v['effective_facts']['new_deployable_budget'] = 5
    elif change == 'missing_contrast':
        value['families'][0]['variants'].pop()
    elif change == 'pretend_execution':
        v['execution_status'] = 'PASS'
    with pytest.raises(ValueError):
        checker.validate(value)


def test_boolean_claim_cannot_be_replaced_by_a_number():
    value = pack()
    value['families'][1]['variants'][0]['expected_observable_distinctions']['distinct_K2_can_create_second_job'] = 1
    with pytest.raises(ValueError):
        checker.validate(value)


@pytest.mark.parametrize('family,variant,remaining', [
    (2, 1, {'deadline_ms': 500}),
    (1, 1, {'duplicate_effect_guarantee': 'not established'}),
])
def test_losing_only_the_decisive_claim_still_fails(family, variant, remaining):
    value = pack()
    value['families'][family]['variants'][variant]['expected_observable_distinctions'] = remaining
    with pytest.raises(ValueError, match='required consequence'):
        checker.validate(value)


def test_nonmaterial_label_cannot_hide_a_changed_budget():
    value = pack()
    v = value['families'][0]['variants'][2]
    v['fact_overrides']['new_deployable_budget'] = 5
    v['effective_facts']['new_deployable_budget'] = 5
    v['expected_observable_distinctions']['new_deployables_max'] = 5
    with pytest.raises(ValueError, match='nonmaterial'):
        checker.validate(value)


def test_material_label_needs_a_discriminating_change():
    value = pack()
    f = value['families'][2]
    v = f['variants'][1]
    v['fact_overrides'] = {}
    v['effective_facts'] = copy.deepcopy(f['supplied_facts'])
    v['expected_observable_distinctions'] = {'max_total_rpc_attempts': 2, 'extra_attempts': 1}
    with pytest.raises(ValueError, match='material contrast'):
        checker.validate(value)


def test_evaluation_does_not_rewrite_the_case_pack():
    value = pack()
    before = copy.deepcopy(value)
    checker.validate(value)
    assert value == before


def test_everyday_choice_rechecks_feasibility_instead_of_copying_the_old_answer():
    value = pack()['families'][5]
    facts = copy.deepcopy(value['supplied_facts'])
    facts['walking_feasible'] = False
    observed = checker.consequences(value['family'], facts)
    assert observed['preferred_option'] == 'take_shuttle' and observed['arrival'] == '08:55'
    facts['shuttle_departure'] = '09:01'
    with pytest.raises(ValueError, match='no feasible'):
        checker.consequences(value['family'], facts)


def test_existing_kb_reads_only_the_relevant_case_section(tmp_path):
    index = ROOT / 'docs/v2/decision-cases.md'
    kb = KB(home=tmp_path, paths=[index], fts=False)
    try:
        selected = kb.get('decision-cases.md#sql-metric-semantics', max_bytes=1800)
        assert not selected['truncated']
        assert 'DC-04' in selected['text'] and 'received cash' in selected['text']
        assert 'DC-02' not in selected['text'] and 'DC-06' not in selected['text']
        with pytest.raises(KeyError):
            kb.get('decision-cases.md#unavailable-case')
    finally:
        kb.close()
