"""Status must report event chronology, not the position of nodes in a file."""
import os
from pathlib import Path
import subprocess
import sys

ENGINE = Path(__file__).resolve().parents[1] / 'src/agent_harness/workgraph/plan.py'


def status(tmp_path, rows):
    (tmp_path / 'plan').mkdir()
    (tmp_path / 'plan/lab.md').write_text('## goal: chronological status\n\n' + rows)
    result = subprocess.run([sys.executable, str(ENGINE), 'status', 'lab'], cwd=tmp_path,
        env={**os.environ, 'HOME': str(tmp_path), 'HARNESS_HOME': str(tmp_path / 'hh'),
             'PLAN_DIR': str(tmp_path / 'plan')}, text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def node(identity, *notes):
    return f'- [ ] {identity}. task {identity} | gate: true\n' + ''.join(f'      {n}\n' for n in notes)


def note(when, code=1, tail='failure'):
    return f'{when} exit {code} in 0s [deadbeef] — {tail}'


def test_newest_failure_can_precede_an_older_failed_node_in_file_order(tmp_path):
    output = status(tmp_path, node(4, note('2026-11-03T05:00:00Z', tail='new')) +
                    node(16, note('2026-11-02T05:00:00Z', tail='old')))
    line = next(s for s in output.splitlines() if 'last fail' in s)
    assert '4. exit 1' in line and 'new' in line
    assert '16.' not in line


def test_note_order_cannot_override_timestamps(tmp_path):
    output = status(tmp_path, node(1, note('2026-11-03T05:00:00Z', tail='new'),
                                  note('2026-11-02T05:00:00Z', tail='old')))
    line = next(s for s in output.splitlines() if 'last fail' in s)
    assert 'new' in line and 'old' not in line


def test_success_after_failure_does_not_erase_the_last_failure(tmp_path):
    output = status(tmp_path, node(1, note('2026-11-02T05:00:00Z', tail='retained'),
                                  note('2026-11-03T05:00:00Z', code=0, tail='passed')))
    assert '1. exit 1 — retained' in output
    assert '2 runs' in output and '1 failed' in output


def test_equal_second_failures_are_reported_as_a_tie(tmp_path):
    output = status(tmp_path, node(4, note('2026-11-03T05:00:00Z')) +
                    node(16, note('2026-11-03T05:00:00Z')))
    assert 'last fails' in output and '4, 16' in output and 'tie' in output


def test_invalid_failure_date_does_not_invent_chronology(tmp_path):
    output = status(tmp_path, node(4, note('2026-11-03T05:00:00Z', tail='dated')) +
                    node(16, note('2026-99-03T05:00:00Z', tail='undated')))
    assert 'last dated' in output and '4. exit 1' in output
    assert 'unranked' in output and '1' in output
    assert '2 failed' in output  # malformed chronology is still retained evidence


def test_success_only_has_no_last_failure_or_undated_warning(tmp_path):
    output = status(tmp_path, node(4, note('2026-11-03T05:00:00Z', code=0)))
    assert 'last fail' not in output and 'unranked' not in output
    assert '1 runs' in output and '0 failed' in output
