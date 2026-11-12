"""Frozen source-correction pickup comparison using the real native observer.

Only disposable project stores are touched. This evaluates model-free factual
memory updates, separately from generated-procedure learning. Neither human nor
competitor superiority follows from these authored cases.
"""
import argparse
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from agent_harness import procedure_execution as C, procedures as P  # noqa: E402
from agent_harness.project_memory import ProjectMemory  # noqa: E402
from agent_harness.vault_sources import SourceVault, initialize  # noqa: E402

CASES = [('portal', 'port', '8443'), ('reports', 'retention_days', '31'),
         ('queue', 'retry_limit', '4'), ('search', 'batch_size', '128')]


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def prepare(out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    project = out / 'project'
    project.mkdir()
    (project / '.git').mkdir()
    oracle = project / 'qualification-oracle'
    oracle.mkdir()
    cases = []
    started = time.monotonic()
    for name, key, value in CASES:
        memory_root = project / ('store-' + name)
        memory_root.mkdir()
        identity = initialize(memory_root)
        vault, memory = SourceVault(memory_root, identity), ProjectMemory(memory_root, identity)
        previous, history = None, []
        for revision in range(6):
            text = key + ': ' + (value if revision == 5 else str(100 + revision))
            (memory_root / 'config.txt').write_text(text + '\n')
            source = vault.capture('config.txt')
            previous = memory.append({'id': 'config', 'project_id': identity,
                'layer': 'project_facts', 'kind': 'fact', 'scope': 'task', 'text': text,
                'provenance': [{'source': source, 'start_line': 1, 'end_line': 1}],
                'confidence': 'verified', 'sensitivity': 'internal', 'access_boundary': 'local_user',
                'owner': 'authored-source-update', 'freshness': 'current'}, expected=previous)
            history.append(memory.read(previous, allowed_sensitivities=['internal']))
        current = memory.latest('config', allowed_sensitivities=['internal'])
        assert current['item']['text'] == key + ': ' + value
        packets = {'history': json.dumps({'historical_revisions': history, 'current': current}),
                   'current': json.dumps({'current': current})}
        instruction = ('Read the current source-bound configuration for ' + name + '. '
                       'Earlier records are historical. Return the exact field as a JSON string: ' + key)
        tasks = {}
        for arm, evidence in packets.items():
            task = {'instruction': instruction, 'evidence': evidence}
            task_path = out / (name + '-' + arm + '.json')
            save(task_path, task)
            tasks[arm] = {'path': task_path.name, 'sha256': C._sha(task_path.read_bytes()),
                          'evidence_bytes': len(evidence.encode())}
        cases.append({'id': name, 'tasks': tasks, 'expected': {key: value},
                      'order': ['history', 'current'] if len(cases) % 2 == 0 else ['current', 'history']})
    frozen = {'schema': 'harness.v3-memory-pickup/v1', 'model': 'gpt-6.1-sol', 'effort': 'high',
              'require_complete_usage': True, 'max_calls': 8, 'max_observed_tokens': 250000,
              'timeout_seconds': 90, 'retries': 0, 'runtime': C._runtime(), 'cases': cases,
              'preparation_model_calls': 0, 'preparation_wall_s': time.monotonic() - started,
              'claim_scope': 'authored source-correction pickup; zero-model memory updates',
              'generated_procedure_learning': 'UNQUALIFIED',
              'whole_project_research_usage': 'UNKNOWN',
              'evaluator_sha256': C._sha(Path(__file__).read_bytes())}
    save(oracle / 'freeze.json', frozen)
    return {'status': 'FROZEN_NOT_RUN', 'calls_max': frozen['max_calls'],
            'token_ceiling': frozen['max_observed_tokens'], 'oracle': str(oracle)}


def run(out):
    out = Path(out).resolve()
    frozen = C._json(out / 'project/qualification-oracle/freeze.json')
    assert frozen['runtime'] == C._runtime(), 'runtime changed after freeze'
    assert frozen['evaluator_sha256'] == C._sha(Path(__file__).read_bytes()), 'evaluator changed after freeze'
    journal = out / 'journal.json'
    assert not journal.exists(), 'consumed campaign cannot be rerun'
    rows, tokens = [], 0
    project = out / 'project'
    oracle = project / 'qualification-oracle'
    for case in frozen['cases']:
        for arm in case['order']:
            bound = case['tasks'][arm]
            task = json.loads(C._bound(out, bound['path'], bound['sha256']))
            actor = project / ('actor-' + case['id'] + '-' + arm)
            actor.mkdir()
            request = C._actor(actor, task, None)
            row = {'case': case['id'], 'arm': arm, 'status': 'CONSUMED',
                   'actor': actor.relative_to(out).as_posix(), 'request_sha256': P.digest(request)}
            rows.append(row)
            save(journal, rows)
            started = time.monotonic()
            native = C._call(actor, request, {**frozen, 'oracle': str(oracle)})
            receipt = oracle / ('native-' + str(len(rows)) + '.json')
            save(receipt, native)
            grade = C._observe(native, frozen, case['expected'])
            count = C._complete_tokens(native, frozen)
            tokens += count
            row.update(status='OBSERVED', receipt=receipt.relative_to(out).as_posix(),
                       receipt_sha256=C._sha(receipt.read_bytes()), tokens=count,
                       correct=grade['correct'], wall_s=time.monotonic() - started)
            save(journal, rows)
            print(json.dumps({k: row[k] for k in ('case', 'arm', 'correct', 'tokens', 'wall_s')}), flush=True)
            if not grade['correct'] or tokens >= frozen['max_observed_tokens']:
                raise ValueError('stop on failed correctness or observed tranche ceiling')
    result = verify(out)
    save(out / 'result.json', result)
    return result


def verify(out):
    out = Path(out).resolve()
    frozen = C._json(out / 'project/qualification-oracle/freeze.json')
    assert frozen['runtime'] == C._runtime(), 'runtime changed after freeze'
    assert frozen['evaluator_sha256'] == C._sha(Path(__file__).read_bytes()), 'evaluator changed after freeze'
    rows = C._json(out / 'journal.json')
    expected_order = [(case['id'], arm) for case in frozen['cases'] for arm in case['order']]
    assert [(row['case'], row['arm']) for row in rows] == expected_order
    assert len(rows) == frozen['max_calls'] and all(row['status'] == 'OBSERVED' for row in rows)
    totals, responses, threads, pairs = {'history': 0, 'current': 0}, set(), set(), {}
    for row in rows:
        case = next(case for case in frozen['cases'] if case['id'] == row['case'])
        task_ref = case['tasks'][row['arm']]
        C._bound(out, task_ref['path'], task_ref['sha256'])
        native = json.loads(C._bound(out, row['receipt'], row['receipt_sha256']))
        C._request(out / row['actor'], row['request_sha256'], native,
                   {**frozen, 'oracle': str(out / 'project/qualification-oracle')})
        grade = C._observe(native, frozen, case['expected'])
        count = C._complete_tokens(native, frozen)
        assert grade['correct'] and row['correct'] and row['tokens'] == count
        assert native['thread_id'] not in threads
        threads.add(native['thread_id'])
        ids = set(native['evaluation_boundary']['provider_usage']['response_id_sha256'])
        assert not ids & responses
        responses.update(ids)
        totals[row['arm']] += count
        pairs.setdefault(row['case'], {})[row['arm']] = count
    differences = [pair['history'] - pair['current'] for pair in pairs.values()]
    return {'status': 'PASS' if totals['current'] < totals['history'] else 'HELD_TOKEN_REGRESSION',
            'native_calls': len(rows), 'correct_pairs': len(pairs), 'tokens': totals,
            'mean_paired_token_saving': statistics.mean(differences),
            'paired_standard_error': statistics.stdev(differences) / len(differences) ** 0.5,
            'observed_usage_complete': True, 'usage_scope': 'these eight controller-owned calls',
            'adaptation_model_calls': frozen['preparation_model_calls'],
            'scope': frozen['claim_scope'], 'generated_procedure_adoption': 'NOT_GRANTED',
            'human_comparison': 'NOT_RUN', 'competitor_comparison': 'NOT_RUN'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'run', 'verify'))
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    result = globals()[args.action](args.directory)
    print(json.dumps(result, indent=2))
    if result.get('status', 'PASS') != 'PASS':
        sys.exit(1)
