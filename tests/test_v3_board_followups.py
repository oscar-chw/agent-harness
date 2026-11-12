"""Checkpoint coalescing retains independent writer continuations."""
from agent_harness.operational_state import OperationalState
from agent_harness.operational_state import Conflict
from agent_harness.shared_board import SharedBoard
from agent_harness.board_hooks import participate
import pytest


def test_prior_summary_can_be_published_after_original_writer_advances(tmp_path):
    project = tmp_path / 'project'
    (project / '.git').mkdir(parents=True)
    home = tmp_path / 'home'
    first, second = SharedBoard(home, project), SharedBoard(home, project)
    first.publish('Gate pending')
    second.publish('Gate pending')
    first.publish('Gate failed; repair pending')
    second.publish('Gate pending')
    # The duplicate suppression of an unchanged connection is intentional.
    third = SharedBoard(home, project)
    third.publish('Gate pending')
    rows = OperationalState(home, project).snapshot()['tasks']
    assert {row['value']['summary'] for row in rows} == {'Gate pending', 'Gate failed; repair pending'}
    assert len(rows) == 2


def test_coalesced_writer_does_not_take_over_the_original_checkpoint(tmp_path):
    project = tmp_path / 'project'
    (project / '.git').mkdir(parents=True)
    home = tmp_path / 'home'
    first, second = SharedBoard(home, project), SharedBoard(home, project)
    first.publish('Review pending')
    second.publish('Review pending')
    second.publish('Client-specific validation pending')
    first.publish('Review complete; deployment pending')
    rows = OperationalState(home, project).snapshot()['tasks']
    assert len(rows) == 2
    assert {row['value']['summary'] for row in rows} == {
        'Client-specific validation pending', 'Review complete; deployment pending'}


def test_writer_can_return_to_an_earlier_summary_after_a_changed_observation(tmp_path):
    project = tmp_path / 'project'
    (project / '.git').mkdir(parents=True)
    home = tmp_path / 'home'
    writer = SharedBoard(home, project)
    for summary in ('Gate pending', 'Gate failed', 'Gate pending'):
        writer.publish(summary)
    rows = OperationalState(home, project).snapshot()['tasks']
    assert len(rows) == 1 and rows[0]['value']['summary'] == 'Gate pending'
    assert rows[0]['version'] == 3


def test_hook_keeps_stop_suffix_when_direct_task_summary_exceeds_display_budget(tmp_path, monkeypatch):
    project = tmp_path / 'project'
    (project / '.git').mkdir(parents=True)
    home = tmp_path / 'home'
    monkeypatch.setenv('HARNESS_HOME', str(home))
    monkeypatch.delenv('HARNESS_DISABLE', raising=False)
    store = OperationalState(home, project)
    store.put('direct', {'goal': 'Inspect the current task',
                        'summary': 'A' * 900 + ' STOP: preserve original evidence'},
              expected=0, request_id='direct-summary')
    text = participate({'cwd': str(project), 'session_id': 'suffix-reader'}, 'startup')
    assert 'STOP: preserve original evidence' in text
    assert len(text.encode()) <= 1000


@pytest.mark.parametrize('withdraw', [False, True])
def test_coalescing_never_bypasses_target_version_or_withdrawal(tmp_path, withdraw):
    project = tmp_path / 'project'
    (project / '.git').mkdir(parents=True)
    store = OperationalState(tmp_path / 'home', project)
    store.put('existing', {'summary': 'Old observation'}, expected=0, request_id='existing')
    store.put('other', {'summary': 'New observation'}, expected=0, request_id='other')
    if withdraw:
        store.withdraw('existing', expected=1, request_id='withdraw')
    with pytest.raises(Conflict):
        store.put('existing', {'summary': 'New observation'}, expected=0,
                  request_id='coalesce', coalesce=True)
