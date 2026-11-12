"""Judge the submitted query's consequences, rather than a known-good demo query."""
import copy
import json

import pytest

from agent_harness.sql_outcome import evaluate_query


def cases():
    return [
        {'id': 'fanout', 'tables': {
            'orders': {'columns': ['id', 'total'], 'rows': [[1, 100], [2, 50]]},
            'items': {'columns': ['order_id'], 'rows': [[1], [1], [2]]}},
         'expected': [[150]], 'ordered': False},
        {'id': 'equal_values', 'tables': {
            'orders': {'columns': ['id', 'total'], 'rows': [[4, 100], [8, 100], [9, 25]]},
            'items': {'columns': ['order_id'], 'rows': [[4], [4], [8], [9]]}},
         'expected': [[225]], 'ordered': False},
    ]


def test_valid_alternative_queries_pass_without_changing_frozen_cases():
    pack = cases()
    before = copy.deepcopy(pack)
    for sql in ['SELECT SUM(total) FROM orders',
                'SELECT SUM(value) FROM (SELECT id, MAX(total) AS value FROM orders GROUP BY id)']:
        result = evaluate_query(sql, pack)
        assert result['status'] == 'PASS'
        assert result['scope'] == 'bounded_fixture_outcomes_only'
        assert [c['observed'] for c in result['cases']] == [[[150]], [[225]]]
        assert result['native_quality'] == 'NOT_RUN'
        assert len(result['query_sha256']) == len(result['fixtures_sha256']) == 64
    assert pack == before


@pytest.mark.parametrize('query', [
    'SELECT SUM(total) FROM orders JOIN items ON id=order_id',
    'SELECT SUM(DISTINCT total) FROM orders',
    'SELECT 150',
])
def test_plausible_shortcuts_fail_the_actual_consequence_check(query):
    result = evaluate_query(query, cases())
    assert result['status'] == 'FAIL'
    assert any(not c['passed'] for c in result['cases'])
    assert all(c['execution'] == 'EXECUTED' for c in result['cases'])


def test_changed_metric_changes_the_required_result():
    pack = cases()
    pack[0]['expected'] = [[3]]
    pack[1]['expected'] = [[4]]
    assert evaluate_query('SELECT COUNT(*) FROM items', pack)['status'] == 'PASS'
    assert evaluate_query('SELECT SUM(total) FROM orders', pack)['status'] == 'FAIL'


def test_known_population_and_duplicate_values_keep_their_metric_unit():
    pack = []
    for size in range(16):
        orders = [[i, (i % 3 + 1) * 10] for i in range(size)]
        items = [[i] for i in range(size) for _ in range(i % 3)]
        pack.append({'id': 'population' + str(size), 'tables': {
            'orders': {'columns': ['id', 'total'], 'rows': orders},
            'items': {'columns': ['order_id'], 'rows': items}},
            'expected': [[sum(row[1] for row in orders) if orders else None]], 'ordered': False})
    assert evaluate_query('SELECT SUM(total) FROM orders', pack)['status'] == 'PASS'
    assert evaluate_query('SELECT SUM(DISTINCT total) FROM orders', pack)['status'] == 'FAIL'
    assert evaluate_query('SELECT SUM(total) FROM orders JOIN items ON id=order_id', pack)['status'] == 'FAIL'


@pytest.mark.parametrize('query', ['DELETE FROM orders', 'DROP TABLE orders',
                                 'PRAGMA database_list', 'SELECT * FROM sqlite_master',
                                 "SELECT load_extension('missing-extension')"])
def test_non_fixture_reads_and_writes_are_rejected(query):
    result = evaluate_query(query, cases())
    assert result['status'] == 'FAIL'
    assert all(c['execution'] == 'ERROR' and c['error'] for c in result['cases'])


def test_attach_cannot_create_an_external_file(tmp_path):
    target = tmp_path / 'should-not-exist.sqlite'
    result = evaluate_query("ATTACH DATABASE '" + str(target) + "' AS outside", cases())
    assert result['status'] == 'FAIL'
    assert not target.exists()


def test_nonterminating_query_stops_at_the_vm_budget():
    query = 'WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n) SELECT SUM(x) FROM n'
    result = evaluate_query(query, cases())
    assert result['status'] == 'FAIL'
    assert all('interrupted' in c['error'].lower() for c in result['cases'])


def test_sql_syntax_error_is_a_failed_outcome_not_an_empty_pass():
    result = evaluate_query('not valid SQL', cases())
    assert result['status'] == 'FAIL'
    assert all(c['execution'] == 'ERROR' for c in result['cases'])


def test_result_row_limit_is_enforced():
    pack = cases()[:1]
    result = evaluate_query('SELECT a.id FROM orders a, orders b, orders c, orders d, '
                            'orders e, orders f, orders g, orders h, orders i', pack)
    assert result['status'] == 'FAIL'
    assert 'row limit' in result['cases'][0]['error']


def test_irrelevant_extra_fixture_and_ordering_are_explicit():
    pack = cases()[:1]
    pack[0]['expected'] = [[100], [50]]
    assert evaluate_query('SELECT total FROM orders ORDER BY total', pack)['status'] == 'PASS'
    pack[0]['ordered'] = True
    assert evaluate_query('SELECT total FROM orders ORDER BY total', pack)['status'] == 'FAIL'


@pytest.mark.parametrize('change', ['empty', 'duplicate', 'bad_table', 'bad_column',
                                  'ragged', 'missing_expected', 'infinite', 'too_large'])
def test_malformed_or_missing_cases_never_produce_a_pass(change):
    pack = cases()
    if change == 'empty':
        pack = []
    elif change == 'duplicate':
        pack[1]['id'] = pack[0]['id']
    elif change == 'bad_table':
        pack[0]['tables']['orders; DROP TABLE items'] = pack[0]['tables'].pop('orders')
    elif change == 'bad_column':
        pack[0]['tables']['orders']['columns'][0] = 'id); --'
    elif change == 'ragged':
        pack[0]['tables']['orders']['rows'][0] = [1]
    elif change == 'missing_expected':
        del pack[0]['expected']
    elif change == 'infinite':
        pack[0]['expected'] = [[float('inf')]]
    elif change == 'too_large':
        pack[0]['tables']['orders']['rows'] = [[i, 'x' * 4000] for i in range(100)]
    with pytest.raises(ValueError):
        evaluate_query('SELECT SUM(total) FROM orders', pack)


def test_bindings_change_when_the_problem_or_the_submitted_query_changes():
    pack = cases()
    first = evaluate_query('SELECT SUM(total) FROM orders', pack)
    other_query = evaluate_query('SELECT COUNT(*) FROM orders', pack)
    assert first['query_sha256'] != other_query['query_sha256']
    assert first['fixtures_sha256'] == other_query['fixtures_sha256']
    pack[0]['expected'] = [[999]]
    changed = evaluate_query('SELECT SUM(total) FROM orders', pack)
    assert changed['fixtures_sha256'] != first['fixtures_sha256']
    assert changed['status'] == 'FAIL'
    json.dumps(changed, allow_nan=False)
