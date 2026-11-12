"""Development case/oracle calibration; no native reasoning or efficacy verdict."""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from agent_harness.sql_outcome import evaluate_query  # noqa: E402

PACK = ROOT / 'docs/v2/philosophy/decision-contract-20261103.json'
# Independently retained acceptance fields for this frozen development pack.
# Deriving these from the object being checked would let a subset erase its judge.
REQUIRED_CLAIMS = {
    'DC-01.control': 'approval_stale_version unauthorised_reviewer new_deployables_max',
    'DC-01.isolation': 'renderer_fault new_deployables_max approval_invariant',
    'DC-01.renamed': 'new_deployables_max approval_invariant',
    'DC-02.control': 'same_intent_successful_replays_effects distinct_K2_can_create_second_job changed_payload_same_id',
    'DC-02.no_contract': 'automatic_creates_after_timeout visible_state duplicate_effect_guarantee',
    'DC-02.key_spelling': 'same_intent_successful_replays_effects visible_confirmation_requires',
    'DC-03.control': 'max_total_rpc_attempts valid_cache_age_seconds deadline_ms',
    'DC-03.systemwide': 'max_total_rpc_attempts extra_attempts',
    'DC-03.instance_rename': 'max_total_rpc_attempts deadline_ms',
    'DC-04.control': 'rows raw_join_bad_total sum_distinct_bad_total',
    'DC-04.received_payments': 'rows metric',
    'DC-04.label_change': 'rows',
    'DC-05.control': 'answer_days source_revision project',
    'DC-05.correction': 'answer_days source_revision derived_summary_state r1_history',
    'DC-05.distractor': 'answer_days source_revision project',
    'DC-05.missing_current_bytes': 'current_value gap old_value_status',
    'DC-06.control': 'walk_arrival shuttle_arrival preferred_option',
    'DC-06.accessibility': 'preferred_option arrival',
    'DC-06.title_only': 'preferred_option arrival',
}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sql_fixture(facts, expected):
    tables = {}
    for name in ('customers', 'invoices', 'invoice_lines', 'payments'):
        records = facts[name]
        columns = list(records[0])
        # Names are irrelevant to the metric but retained to exercise changed labels.
        tables[name] = {'columns': columns, 'rows': [[r[c] for c in columns] for r in records]}
    return {'id': 'metric', 'tables': tables, 'expected': [[r['customer_id'], r['value']] for r in expected],
            'ordered': False}


INVOICE_QUERY = ('SELECT c.customer_id, COALESCE(SUM(i.amount),0) FROM customers c '
                 'LEFT JOIN invoices i ON c.customer_id=i.customer_id GROUP BY c.customer_id')
PAYMENT_QUERY = ('SELECT c.customer_id, COALESCE(SUM(p.amount),0) FROM customers c '
                 'LEFT JOIN invoices i ON c.customer_id=i.customer_id '
                 'LEFT JOIN payments p ON i.invoice_id=p.invoice_id GROUP BY c.customer_id')
ALTERNATIVE_QUERY = ('SELECT c.customer_id, COALESCE((SELECT SUM(i.amount) FROM invoices i '
                     'WHERE i.customer_id=c.customer_id),0) FROM customers c')
BAD_JOIN = ('SELECT c.customer_id, SUM(i.amount) FROM customers c JOIN invoices i '
            'ON c.customer_id=i.customer_id JOIN invoice_lines l ON i.invoice_id=l.invoice_id '
            'JOIN payments p ON i.invoice_id=p.invoice_id GROUP BY c.customer_id')
BAD_DISTINCT = ('SELECT c.customer_id, COALESCE(SUM(DISTINCT i.amount),0) FROM customers c '
                'LEFT JOIN invoices i ON c.customer_id=i.customer_id GROUP BY c.customer_id')


def _clock(value):
    h, m = map(int, value.split(':'))
    require(0 <= h < 24 and 0 <= m < 60, 'invalid same-day clock')
    return h * 60 + m


def _time(value):
    return f'{value // 60:02d}:{value % 60:02d}'


def consequences(family, facts):
    """Independently derive finite supplied-model constraints, not actor judgments."""
    if family == 'module_isolation':
        result = {'approval_stale_version': 'rejected', 'unauthorised_reviewer': 'rejected',
                  'new_deployables_max': facts['new_deployable_budget'], 'approval_invariant': 'unchanged'}
        if facts['required_renderer_failure_isolation']:
            require(facts['new_deployable_budget'] >= 1, 'isolation needs an admitted boundary')
            result['renderer_fault'] = 'must not stop edits'
        return result
    if family == 'api_replay_unknown_outcome':
        contract = facts['server_contract']
        safe = (contract['caller_request_id'] and contract['atomic_effect_and_id_record'] and
                facts['seconds_since_first_send'] < facts['retention_seconds'])
        if not safe:
            return {'automatic_creates_after_timeout': 0, 'visible_state': 'unknown',
                    'duplicate_effect_guarantee': 'not established'}
        return {'same_intent_successful_replays_effects': 1, 'distinct_K2_can_create_second_job': True,
                'changed_payload_same_id': 'rejected', 'visible_confirmation_requires': 'authoritative result'}
    if family == 'overload_retry_budget':
        cache = facts['valid_cached_report']
        require(cache['available'] and cache['age_seconds'] <= cache['max_age_seconds'], 'no valid cached alternative')
        can_retry = (facts['replay_safe'] and facts['verified_alternate_capacity'] and
                     facts['elapsed_ms'] + facts['healthy_alternate_response_ms'] <= facts['deadline_ms'] and
                     not facts['other_layers_retry'])
        return {'max_total_rpc_attempts': 1 + (facts['max_extra_attempts'] if can_retry else 0),
                'extra_attempts': facts['max_extra_attempts'] if can_retry else 0,
                'valid_cache_age_seconds': cache['age_seconds'], 'deadline_ms': facts['deadline_ms']}
    if family == 'sql_metric_semantics':
        metric = facts['requested_metric']
        require(metric in ('invoice_revenue', 'received_payments'), 'unknown metric')
        invoice_customer = {i['invoice_id']: i['customer_id'] for i in facts['invoices']}
        require(len(invoice_customer) == len(facts['invoices']), 'duplicate source invoice identity')
        values = {c['customer_id']: 0 for c in facts['customers']}
        for row in facts['invoices'] if metric == 'invoice_revenue' else facts['payments']:
            customer = row['customer_id'] if metric == 'invoice_revenue' else invoice_customer[row['invoice_id']]
            values[customer] += row['amount']
        return {'rows': [{'customer_id': k, 'value': v} for k, v in sorted(values.items())], 'metric': metric,
                'raw_join_bad_total': sum(i['amount'] for i in facts['invoices']
                    for line in facts['invoice_lines'] if line['invoice_id'] == i['invoice_id']
                    for payment in facts['payments'] if payment['invoice_id'] == i['invoice_id']),
                'sum_distinct_bad_total': sum({i['amount'] for i in facts['invoices']})}
    if family == 'scoped_evidence_correction':
        current = [r for r in facts['records'] if r['project'] in facts['authorised_projects'] and r['status'] == 'current']
        require(len(current) == 1, 'current evidence absent or conflicting')
        row = current[0]
        if not row['bytes_available']:
            return {'current_value': 'UNKNOWN', 'gap': 'current r2 source bytes unavailable', 'old_value_status': 'historical_only'}
        return {'answer_days': row['value_days'], 'source_revision': row['revision'], 'project': row['project'],
                'derived_summary_state': 'stale_or_refreshed', 'r1_history': 'retained'}
    if family == 'everyday_proportional_choice':
        walk = _clock(facts['now']) + facts['walk_minutes']
        shuttle = _clock(facts['shuttle_departure']) + facts['shuttle_minutes']
        feasible = {'take_shuttle': shuttle}
        if facts['walking_feasible']:
            feasible['walk_now'] = walk
        feasible = {k: v for k, v in feasible.items() if v <= _clock(facts['meeting_deadline'])}
        require(bool(feasible), 'no feasible option supplied')
        choice = min(feasible, key=feasible.get)
        return {'walk_arrival': _time(walk), 'shuttle_arrival': _time(shuttle),
                'preferred_option': choice, 'arrival': _time(feasible[choice])}
    raise ValueError('unsupported decision family')


def validate(pack):
    require(pack['classification'] == 'AUTHORED_INFERENCE_NOT_EMPIRICAL_RESULT', 'authorship classification changed')
    families = pack['families']
    require(len(families) == 6 and len({f['id'] for f in families}) == 6, 'six distinct families required')
    require({v['variant_id'] for f in families for v in f['variants']} == set(REQUIRED_CLAIMS),
            'frozen contrast omitted or replaced')
    count, sql_controls = 0, 0
    for family in families:
        variants = family['variants']
        roles = {v['role'] for v in variants}
        require({'control', 'changed_constraints', 'nonmaterial_change'} <= roles, 'missing transfer contrast')
        require(len({v['variant_id'] for v in variants}) == len(variants), 'duplicate variant identity')
        baseline = consequences(family['family'], family['supplied_facts'])
        for variant in variants:
            expected_facts = {**family['supplied_facts'], **variant['fact_overrides']}
            require(expected_facts == variant['effective_facts'], 'effective facts do not follow declared change')
            require(variant['execution_status'] == 'NOT_RUN', 'case authoring is not execution')
            require(bool(variant['permissible_decisions']) and bool(variant['unacceptable_consequences']), 'empty acceptance contrast')
            actual = consequences(family['family'], expected_facts)
            if variant['role'] == 'nonmaterial_change':
                require(actual == baseline, 'nonmaterial label changed a required consequence')
            elif variant['role'] == 'changed_constraints':
                require(actual != baseline, 'material contrast does not discriminate consequences')
            wanted = variant['expected_observable_distinctions']
            require(isinstance(wanted, dict) and bool(wanted), 'missing consequence checks')
            require(set(REQUIRED_CLAIMS[variant['variant_id']].split()) <= set(wanted),
                    'required consequence claims are missing')
            for key, value in wanted.items():
                # Python considers True equal to 1; those are different evidence claims.
                require(key in actual and json.dumps(actual[key], sort_keys=True) == json.dumps(value, sort_keys=True),
                        variant['variant_id'] + ': consequence mismatch ' + key)
            if family['family'] == 'sql_metric_semantics':
                fixture = sql_fixture(expected_facts, actual['rows'])
                good = INVOICE_QUERY if expected_facts['requested_metric'] == 'invoice_revenue' else PAYMENT_QUERY
                require(evaluate_query(good, [fixture])['status'] == 'PASS', 'valid SQL consequence rejected')
                if expected_facts['requested_metric'] == 'invoice_revenue':
                    for query, wanted in [(ALTERNATIVE_QUERY, 'PASS'), (BAD_JOIN, 'FAIL'), (BAD_DISTINCT, 'FAIL')]:
                        require(evaluate_query(query, [fixture])['status'] == wanted, 'SQL consequence control failed')
                        sql_controls += 1
            count += 1
    return {'status': 'PASS_CASE_CONTRACT_AND_FINITE_CONSTRAINTS', 'families': 6, 'variants': count,
            'sql_query_controls': sql_controls, 'native_decision_quality': 'NOT_RUN',
            'comparative_quality_total_usage': 'NOT_RUN',
            'scope': 'case consistency and bounded SQL oracle calibration; no actor reasoning or implementation proof'}


def negative_controls(pack):
    def changed(family, variant, key, value):
        mutant = copy.deepcopy(pack)
        mutant['families'][family]['variants'][variant]['expected_observable_distinctions'][key] = value
        return mutant
    mutants = {
        'accept-fanout': changed(3, 0, 'rows', [{'customer_id': 1, 'value': 500}, {'customer_id': 2, 'value': 0}]),
        'carry-old-metric': changed(3, 1, 'rows', [{'customer_id': 1, 'value': 200}, {'customer_id': 2, 'value': 0}]),
        'invent-confirmed-outcome': changed(1, 1, 'visible_state', 'confirmed'),
        'retry-systemic-overload': changed(2, 1, 'extra_attempts', 1),
        'use-forbidden-project': changed(4, 2, 'answer_days', 1),
        'guess-missing-evidence': changed(4, 3, 'current_value', 30),
        'ignore-accessibility': changed(5, 1, 'preferred_option', 'walk_now'),
    }
    for name, mutant in mutants.items():
        try:
            validate(mutant)
        except ValueError:
            print('REJECTED:', name)
        else:
            raise AssertionError('decision control survived: ' + name)
    return len(mutants)


def main():
    raw = PACK.read_bytes()
    pack = json.loads(raw)
    result = validate(pack)
    result['pack_sha256'] = hashlib.sha256(raw).hexdigest()
    if '--controls' in sys.argv:
        result['countercontrols_rejected'] = negative_controls(pack)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
