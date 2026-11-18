"""Controls for frozen semantic-review quality replay."""
import hashlib
import json

import pytest

from agent_harness.dream_candidates import propose, review_packet


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def review_lab(tmp_path):
    source_text = '# Backups\nRestore test evidence is required.\n'
    alternatives = [
        ('support', 'A restore drill compared each recovered checksum against the manifest.'),
        ('support', 'An independent integrity report records every recovered checksum.'),
        ('restatement', 'Restore test evidence is required.'),
        ('stale_or_conflicting', 'The retired policy accepted a successful export without a restore.'),
        ('topic_only', 'Backup storage is assigned its own volume.'),
        ('insufficient', 'Someone mentioned a restore might have worked later.'),
        ('ambiguous', 'The audit recorded the expected result but does not define its scope.'),
    ]
    (tmp_path / 'source.md').write_text(source_text)
    labels = []
    responses = []
    for index, (label, passage) in enumerate(alternatives):
        target = f'target-{index}.md'
        (tmp_path / target).write_text(f'# Restore control\n{passage}\n')
        identity = propose(tmp_path, 'source.md', target, origin='synthetic-review-control')['id']
        labels.append({'id': identity, 'label': label, 'lexical_selected': index < 5})
        decision = 'accept' if label == 'support' else 'abstain' if label == 'ambiguous' else 'reject'
        row = {'id': identity, 'decision': decision}
        if decision == 'accept':
            row.update(source_quote=source_text.splitlines()[1], target_quote=passage)
        responses.append(row)
    frozen = tmp_path / 'labels.json'
    frozen.write_text(json.dumps({'schema': 'harness.dream-review-labels/v1', 'cases': labels}))
    results = {
        'standalone': [
            {'candidate_ids': [row['id']], 'packet_sha256': digest(review_packet(tmp_path, [row['id']])),
             'decisions': [dict(row)]}
            for row in responses
        ],
        'batched': [{'candidate_ids': [row['id'] for row in responses], 'packet_sha256': digest(review_packet(tmp_path, [row['id'] for row in responses])),
                     'decisions': responses}],
    }
    return tmp_path, frozen, digest(frozen.read_bytes()), results


def test_frozen_control_and_exact_packet_replay(review_lab):
    from eval.dream_review_grade import replay

    report = replay(*review_lab)
    assert report['quality_gate'] == 'PASS'
    assert report['promotion'] == 'NOT_GRANTED'
    assert report['usage'] == 'NOT_ASSESSED'
    assert report['lexical'] == {'tp': 2, 'fp': 3, 'fn': 0, 'precision': 0.4, 'recall': 1.0}
    assert report['batched'] == {'tp': 2, 'fp': 0, 'fn': 0, 'precision': 1.0, 'recall': 1.0}
    assert len(report['ambiguous_ids']) == 1
    assert report['affected_decisions'] == []


@pytest.mark.parametrize(('mutation', 'error'), [
    ('omitted', 'candidate coverage'),
    ('duplicate', 'candidate coverage'),
    ('binding', 'packet hash'),
    ('quote', 'exact source and target quotations'),
    ('drift', 'source changed'),
    ('labels', 'label freeze hash'),
])
def test_replay_refuses_incomplete_or_unbound_evidence(review_lab, mutation, error):
    from eval.dream_review_grade import replay

    corpus, frozen, _, results = review_lab
    batched = results['batched'][0]
    if mutation == 'omitted':
        batched['decisions'].pop()
    elif mutation == 'duplicate':
        batched['decisions'].append(dict(batched['decisions'][0]))
    elif mutation == 'binding':
        batched['packet_sha256'] = '0' * 64
    elif mutation == 'quote':
        batched['decisions'][0]['target_quote'] = 'Source text from the wrong document.'
    elif mutation == 'drift':
        (corpus / 'target-0.md').write_text('# Edited\nChanged after review.\n')
    else:
        frozen.write_text(frozen.read_text() + '\n')
    with pytest.raises(ValueError, match=error):
        replay(*review_lab)


def test_correct_aggregate_can_hide_wrong_decision(review_lab):
    from eval.dream_review_grade import replay

    _, _, _, results = review_lab
    batch = results['batched'][0]['decisions']
    results['standalone'][0]['decisions'][0] = {'id': batch[0]['id'], 'decision': 'reject'}
    batch[1] = {'id': batch[1]['id'], 'decision': 'reject'}
    report = replay(*review_lab)
    assert report['batched'] == report['standalone']
    assert report['batched']['precision'] == 1 and report['batched']['recall'] == 0.5
    assert report['quality_gate'] == 'HOLD'
    assert report['affected_decisions'] == [batch[1]['id']]
    assert 'standalone_case_regression' in report['reasons']


def test_accepting_ambiguous_case_holds_for_adjudication(review_lab):
    from eval.dream_review_grade import replay

    _, _, _, results = review_lab
    row = results['batched'][0]['decisions'][-1]
    row.update(decision='accept', source_quote='Restore test evidence is required.',
               target_quote='The audit recorded the expected result but does not define its scope.')
    report = replay(*review_lab)
    assert report['batched']['precision'] == 1
    assert report['quality_gate'] == 'HOLD'
    assert report['accepted_ambiguous_ids'] == [row['id']]


@pytest.mark.parametrize(('mutation', 'reason'), [
    ('extra_false_positive', 'precision_below_threshold'),
    ('perfect_lexical_control', 'precision_below_threshold'),
    ('all_false_negatives', 'recall_below_threshold'),
])
def test_threshold_holds_without_any_standalone_regression(review_lab, mutation, reason):
    from eval.dream_review_grade import replay

    corpus, frozen, original_hash, results = review_lab
    batch = results['batched'][0]['decisions']
    if mutation == 'extra_false_positive':
        batch[2].update(decision='accept', source_quote='Restore test evidence is required.',
                        target_quote='Restore test evidence is required.')
        results['standalone'][2]['decisions'] = [dict(batch[2])]
    elif mutation == 'perfect_lexical_control':
        manifest = json.loads(frozen.read_text())
        for row in manifest['cases']:
            row['lexical_selected'] = row['label'] == 'support'
        frozen.write_text(json.dumps(manifest))
        original_hash = digest(frozen.read_bytes())
    else:
        for index, row in enumerate(batch[:2]):
            batch[index] = {'id': row['id'], 'decision': 'abstain'}
            results['standalone'][index]['decisions'] = [dict(batch[index])]
    report = replay(corpus, frozen, original_hash, results)
    assert report['quality_gate'] == 'HOLD'
    assert report['affected_decisions'] == []
    assert reason in report['reasons']


def test_cli_checks_quality_and_invalid_evidence_separately(review_lab):
    import os
    from pathlib import Path
    import subprocess
    import sys

    corpus, frozen, expected_hash, results = review_lab
    root = Path(__file__).resolve().parents[1]
    response_file = corpus / 'responses.json'
    response_file.write_text(json.dumps(results))
    command = [sys.executable, '-m', 'eval.dream_review_grade', str(corpus), str(frozen),
               str(response_file), '--freeze-sha256', expected_hash]
    env = dict(os.environ, PYTHONPATH=str(root / 'src'))
    good = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=15)
    assert good.returncode == 0 and json.loads(good.stdout)['quality_gate'] == 'PASS'
    results['batched'][0]['decisions'][1] = {'id': results['batched'][0]['candidate_ids'][1], 'decision': 'reject'}
    response_file.write_text(json.dumps(results))
    held = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=15)
    assert held.returncode == 1 and json.loads(held.stdout)['quality_gate'] == 'HOLD'
    response_file.write_text('{}')
    invalid = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=15)
    assert invalid.returncode == 2 and not invalid.stdout and 'both review arms' in invalid.stderr


@pytest.mark.parametrize(('hits', 'status', 'minimum'), [
    (10, 'PRECISION_CEILING', 1.1),
    (9, 'WITHIN_PRECISION_RANGE', 1.0),
    (7, 'WITHIN_PRECISION_RANGE', 0.8),
])
def test_precision_preflight_refuses_only_impossible_precision(tmp_path, hits, status, minimum):
    from eval.dream_review_grade import precision_preflight

    freeze = tmp_path / 'labels.json'
    # Ten selected pairs and another known negative ensure a valid label universe.
    keep = [{'id': f'pair-{index}', 'label': 'support' if index < hits else 'topic_only',
             'lexical_selected': index < 10} for index in range(11)]
    freeze.write_text(json.dumps({'schema': 'harness.dream-review-labels/v1', 'cases': keep}))
    report = precision_preflight(freeze, digest(freeze.read_bytes()))
    assert report['status'] == status
    assert report['required_precision'] == minimum
    assert report['promotion'] == 'NOT_GRANTED'
    assert report['lexical_precision'] == hits / 10


def test_precision_preflight_rejects_a_mutated_label_freeze(review_lab):
    from eval.dream_review_grade import precision_preflight

    _, freeze, expected, _ = review_lab
    freeze.write_text(freeze.read_text() + '\n')
    with pytest.raises(ValueError, match='label freeze hash'):
        precision_preflight(freeze, expected)


def test_cli_preflight_needs_only_the_bound_freeze_and_refuses_an_impossible_run(tmp_path):
    import os
    from pathlib import Path
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    freeze = tmp_path / 'labels.json'
    labels = [
        {'id': 'support', 'label': 'support', 'lexical_selected': True},
        {'id': 'negative', 'label': 'topic_only', 'lexical_selected': False},
    ]

    def write_freeze():
        raw = json.dumps({'schema': 'harness.dream-review-labels/v1', 'cases': labels})
        freeze.write_text(raw)
        return digest(freeze.read_bytes())

    def preflight(expected, *extra):
        return subprocess.run([sys.executable, '-m', 'eval.dream_review_grade',
                               '--preflight-labels', str(freeze), '--freeze-sha256', expected, *extra],
                              cwd=root, env=dict(os.environ, PYTHONPATH=str(root / 'src')),
                              capture_output=True, text=True, timeout=15)

    expected = write_freeze()
    held = preflight(expected)
    assert held.returncode == 1, held.stderr
    ceiling = json.loads(held.stdout)
    assert ceiling['status'] == 'PRECISION_CEILING'
    assert ceiling['required_precision'] == 1.1 and ceiling['promotion'] == 'NOT_GRANTED'

    labels[1]['lexical_selected'] = True
    new_hash = write_freeze()
    invalid = preflight(expected)
    assert invalid.returncode == 2 and not invalid.stdout and 'freeze hash' in invalid.stderr

    feasible = preflight(new_hash)
    assert feasible.returncode == 0, feasible.stderr
    report = json.loads(feasible.stdout)
    assert report['status'] == 'WITHIN_PRECISION_RANGE' and report['promotion'] == 'NOT_GRANTED'
    assert report['required_precision'] == 0.8 and report['label_freeze_sha256'] == new_hash

    ambiguous = preflight(new_hash, str(tmp_path), str(freeze), str(tmp_path / 'results.json'))
    assert ambiguous.returncode == 2 and not ambiguous.stdout and 'cannot be combined' in ambiguous.stderr
