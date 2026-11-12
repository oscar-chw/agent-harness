"""A complete native turn is narrower than a complete learning campaign."""
import json

import pytest

from agent_harness import native_usage as U
from .test_native_usage_window import counts, event, fixture, THREAD

TURN = 'owned-turn'


def boundary(kind, turn=TURN):
    return {'type': 'event_msg', 'payload': {'type': kind, 'turn_id': turn,
                                           'root_turn_id': turn}}


def rows():
    return [event(counts(100, 10), counts(100, 10)), boundary('task_started'),
            event(counts(140, 18, cached=30, reasoning=3), counts(40, 8, cached=30, reasoning=3)),
            {'type': 'response_item', 'payload': {'text': 'PRIVATE_BODY_NOT_TO_RETAIN'}},
            event(counts(165, 22, cached=40, reasoning=4), counts(25, 4, cached=10, reasoning=1)),
            boundary('task_complete')]


def read(tmp_path, records, turn=TURN):
    source, start, end = fixture(tmp_path, records)
    return U.inspect_turn(tmp_path, source, thread_id=THREAD, turn_id=turn,
                          scan_start=start, scan_end=end)


def test_complete_turn_counts_all_requests_and_includes_cached_input(tmp_path):
    result = read(tmp_path, rows())
    assert result['turn_id'] == TURN and result['terminal_observed'] is True
    assert result['delta'] == counts(65, 12, cached=40, reasoning=4)
    assert result['distinct_increments'] == 2
    assert result['whole_workflow_usage_complete'] is False
    assert 'PRIVATE_BODY_NOT_TO_RETAIN' not in json.dumps(result)


@pytest.mark.parametrize('fault', ['active', 'foreign-complete', 'aborted', 'nested',
                                    'duplicate-start', 'duplicate-complete', 'missing-anchor',
                                    'missing-counters', 'root-mismatch'])
def test_incomplete_or_ambiguous_turn_does_not_become_complete_usage(tmp_path, fault):
    records = rows()
    if fault == 'active': records.pop()
    elif fault == 'foreign-complete': records[-1] = boundary('task_complete', 'another-turn')
    elif fault == 'aborted': records.insert(-1, boundary('turn_aborted'))
    elif fault == 'nested': records.insert(2, boundary('task_started', 'another-turn'))
    elif fault == 'duplicate-start': records.insert(2, boundary('task_started'))
    elif fault == 'duplicate-complete': records.append(boundary('task_complete'))
    elif fault == 'missing-anchor': records.pop(0)
    elif fault == 'missing-counters': records = [records[0], records[1], records[-1]]
    else: records[-1]['payload']['root_turn_id'] = 'another-root'
    with pytest.raises(ValueError, match='turn|anchor|counter|boundary'):
        read(tmp_path, records)


def test_nearest_pre_turn_anchor_excludes_prior_requests_and_later_turns(tmp_path):
    records = [event(counts(60, 5), counts(60, 5))] + rows()
    records.extend([boundary('task_started', 'later-turn'),
                    event(counts(195, 25, cached=50, reasoning=5), counts(30, 3, cached=10, reasoning=1)),
                    boundary('task_complete', 'later-turn')])
    result = read(tmp_path, records)
    assert result['delta']['total_tokens'] == 77
    assert result['first_anchor']['total']['input_tokens'] == 100
    assert result['last_anchor']['total']['input_tokens'] == 165


def test_dropped_counter_inside_complete_turn_still_refuses(tmp_path):
    records = rows(); records.pop(2)
    with pytest.raises(ValueError, match='counter|missing|mismatch'):
        read(tmp_path, records)


def test_bounded_scan_and_current_identity_still_apply_to_turns(tmp_path):
    source, start, end = fixture(tmp_path, rows())
    with pytest.raises(ValueError, match='budget|bound|window'):
        U.inspect_turn(tmp_path, source, thread_id=THREAD, turn_id=TURN,
                       scan_start=start, scan_end=end, max_bytes=10)
    with pytest.raises(ValueError, match='thread'):
        U.inspect_turn(tmp_path, source, thread_id='foreign', turn_id=TURN,
                       scan_start=start, scan_end=end)
    with pytest.raises(ValueError, match='record|boundary'):
        U.inspect_turn(tmp_path, source, thread_id=THREAD, turn_id=TURN,
                       scan_start=start+1, scan_end=end)


def test_long_closed_turn_uses_overlapping_bounded_counter_pages(tmp_path):
    records = rows()
    padding = {'type': 'response_item', 'payload': {'text': 'x' * (2*1024*1024+1024)}}
    records.insert(2, padding)
    records.insert(-2, padding)
    source, start, end = fixture(tmp_path, records)
    assert end-start > U.WINDOW_LIMIT
    with pytest.raises(ValueError, match='budget'):
        U.inspect_window(tmp_path, source, thread_id=THREAD, start_offset=start, end_offset=end)
    result = U.inspect_turn(tmp_path, source, thread_id=THREAD, turn_id=TURN,
                            scan_start=start, scan_end=end)
    assert result['delta']['total_tokens'] == 77
    assert len(result['counter_windows']) == 2
    assert all(w['source_span']['end_offset']-w['source_span']['start_offset'] <= U.WINDOW_LIMIT
               for w in result['counter_windows'])
    assert result['counter_windows'][0]['last_anchor'] == result['counter_windows'][1]['first_anchor']
    assert result['whole_workflow_usage_complete'] is False


def test_local_estimate_shaped_frame_cannot_be_treated_as_free_provider_usage(tmp_path):
    records = [event(counts(100, 10), counts(100, 10)), boundary('task_started'),
               event(counts(100, 10, residual=17), counts(0, 0, residual=17)),
               event(counts(140, 18, residual=17), counts(40, 8)), boundary('task_complete')]
    with pytest.raises(ValueError, match='inconsistent'):
        read(tmp_path, records)


def test_counter_pages_must_share_the_exact_same_anchor(tmp_path, monkeypatch):
    import copy
    records = rows()
    padding = {'type':'response_item','payload':{'text':'x'*(2*1024*1024+1024)}}
    records.insert(2,padding);records.insert(-2,padding)
    original = U.inspect_window; calls=[]
    def moved(*args, **kwargs):
        result=original(*args, **kwargs);calls.append(1)
        if len(calls)==2:
            result=copy.deepcopy(result);result['first_anchor']['offset']+=1
        return result
    monkeypatch.setattr(U,'inspect_window',moved)
    with pytest.raises(ValueError,match='changed|pages'):
        read(tmp_path,records)
    assert len(calls)==2


def test_turn_source_change_during_page_read_is_not_silently_accepted(tmp_path, monkeypatch):
    source,start,end=fixture(tmp_path,rows());original=U.inspect_window
    def changed(*args,**kwargs):
        result=original(*args,**kwargs)
        raw=source.read_bytes();source.write_bytes(raw.replace(b'PRIVATE_BODY',b'CHANGED_BODY'))
        return result
    monkeypatch.setattr(U,'inspect_window',changed)
    with pytest.raises(ValueError,match='changed'):
        U.inspect_turn(tmp_path,source,thread_id=THREAD,turn_id=TURN,scan_start=start,scan_end=end)
