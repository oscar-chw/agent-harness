"""Real concurrent entrypoints must preserve candidate counts and turn identity."""
from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier

from agent_harness import capture


def rows(home):
    return [json.loads(line) for line in (home / capture.STORE).read_text().splitlines()]


def candidate(key):
    return {'key': key, 'source': 'gate', 'summary': 'Verified fixture observation',
            'evidence': 'A fixed failing check followed by a pass'}


def turn():
    return [
        {'type': 'user', 'uuid': 'one-turn', 'message': {'content': 'Fix the failing check'}},
        {'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'id': 'failed', 'name': 'Bash', 'input': {'command': 'pytest -q'}}]}},
        {'type': 'user', 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': 'failed', 'content': 'Exit code 1\nFAILED test_fixture'}]}},
        {'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'id': 'passed', 'name': 'Bash', 'input': {'command': 'pytest -q'}}]}},
        {'type': 'user', 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': 'passed', 'content': 'Exit code 0\n1 passed'}]}},
    ]


def test_parallel_record_keeps_every_independent_candidate(tmp_path):
    home = tmp_path / 'home'
    capture.record(home, [candidate('seed')])
    start = Barrier(8)
    def write(worker):
        for index in range(8):
            start.wait(timeout=10)
            capture.record(home, [candidate(f'worker-{worker}-{index}')])
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, range(8)))
    saved = rows(home)
    assert {row['key'] for row in saved} == {'seed'} | {
        f'worker-{worker}-{index}' for worker in range(8) for index in range(8)}
    assert len(saved) == 65
    assert all(row['count'] == 1 for row in saved)


def test_parallel_stops_of_one_turn_count_one_occurrence(tmp_path):
    home = tmp_path / 'home'
    start = Barrier(8)
    def stop(_):
        start.wait(timeout=10)
        return capture.capture_turn(home, 'one-transcript.jsonl', 'one-session',
                                    events=turn(), started=True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(stop, range(8)))
    assert [row['count'] for row in rows(home)] == [1]


def test_parallel_genuine_turns_keep_their_recurrence_count(tmp_path):
    home = tmp_path / 'home'
    start = Barrier(8)
    def stop(worker):
        events = turn()
        events[0]['uuid'] = f'turn-{worker}'
        start.wait(timeout=10)
        return capture.capture_turn(home, f'transcript-{worker}.jsonl', f'session-{worker}',
                                    events=events, started=True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(stop, range(8)))
    assert [row['count'] for row in rows(home)] == [8]


def test_candidate_pruning_cannot_overwrite_a_parallel_record(tmp_path, monkeypatch):
    from threading import Event, current_thread
    from agent_harness import storage
    home = tmp_path / 'home'
    capture.record(home, [candidate(f'entry-{index}') for index in range(501)])
    snapshot_read, release_prune, writer_started, writer_done = Event(), Event(), Event(), Event()
    original = type(home).read_text
    def read_text(path, *args, **kwargs):
        text = original(path, *args, **kwargs)
        if path == home / capture.STORE and current_thread().name.startswith('pruner'):
            snapshot_read.set()
            assert release_prune.wait(timeout=5)
        return text
    monkeypatch.setattr(type(home), 'read_text', read_text)
    def update():
        writer_started.set()
        try:
            capture.record(home, [candidate('entry-500')])
        finally:
            writer_done.set()
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix='pruner') as pruning:
        prune = pruning.submit(storage.prune, home)
        assert snapshot_read.wait(timeout=5)
        with ThreadPoolExecutor(max_workers=1) as recording:
            pending = recording.submit(update)
            assert writer_started.wait(timeout=5)
            # A correctly serialized writer waits for the prune transaction.
            writer_done.wait(timeout=0.2)
            release_prune.set()
            prune.result(timeout=5)
            pending.result(timeout=5)
    saved = {row['key']: row for row in rows(home)}
    assert len(saved) == 500
    assert saved['entry-500']['count'] == 2


def test_independent_hook_processes_keep_every_session_observation(tmp_path):
    import os
    from pathlib import Path
    import subprocess
    import sys
    project = tmp_path / 'project'
    project.mkdir()
    (project / '.git').mkdir()
    home = tmp_path / 'home'
    env = dict(os.environ, HARNESS_HOME=str(home),
               PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))
    env.pop('HARNESS_PROJECT', None)
    children = []
    for worker in range(6):
        transcript = project / f'transcript-{worker}.jsonl'
        events = turn()
        events[0]['uuid'] = f'process-turn-{worker}'
        transcript.write_text(''.join(json.dumps(event) + '\n' for event in events))
        child = subprocess.Popen([sys.executable, '-m', 'agent_harness.cli', '_hook-capture'],
                                 cwd=project, env=env, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        child.stdin.write(json.dumps({'transcript_path': str(transcript),
                                     'session_id': f'process-{worker}', 'cwd': str(project)}))
        child.stdin.close()
        children.append(child)
    for child in children:
        assert child.wait(timeout=20) == 0
        assert child.stdout.read() == ''
        assert child.stderr.read() == ''
    assert [row['count'] for row in rows(home)] == [6]
