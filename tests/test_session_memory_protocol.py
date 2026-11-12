"""Two-process handoff mechanics, separate from unmeasured model compliance."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from agent_harness.installer import copy_harness  # noqa: E402


def call(tmp_path, project, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('HARNESS_')}
    return subprocess.run([sys.executable, str(ROOT / 'bin/harness'), '--home',
                           str(tmp_path / 'home'), 'task', *args], cwd=project,
                          env=env, capture_output=True, text=True, timeout=15)


def test_installed_skill_and_template_are_available_without_touching_memory(tmp_path):
    hh = tmp_path / 'store'
    memory = hh / 'memory/retained.json'
    memory.parent.mkdir(parents=True)
    memory.write_text('{"fact":"retained"}')
    copy_harness(hh, ROOT, None)
    assert (hh / 'content/skills/session-memory/SKILL.md').is_file()
    assert (hh / 'content/templates/handoff.md').is_file()
    assert memory.read_text() == '{"fact":"retained"}'


def test_a_fresh_reader_finds_the_checkpoint_without_activating_another_session(tmp_path):
    project = tmp_path / 'project'
    project.mkdir()
    packet = project / 'handoffs/task/session-a.md'
    packet.parent.mkdir(parents=True)
    packet.write_text('Task: task\nState: pending\nNext: reproduce the failure\n')
    saved = call(tmp_path, project, 'checkpoint', 'task', '--goal', 'Fix the parser',
                 '--checkpoint', 'handoffs/task/session-a.md', '--next', 'reproduce the failure', '--json')
    assert saved.returncode == 0, saved.stderr
    before = packet.read_bytes()
    read = call(tmp_path, project, 'status', 'task', '--json')
    assert read.returncode == 0, read.stderr
    row = json.loads(read.stdout)['tasks'][0]
    assert row['value']['checkpoint'] == 'handoffs/task/session-a.md'
    assert row['checkpoint_status'] == 'present'
    assert row['status'] == 'open'  # Publishing a summary never proves completion.
    assert packet.read_bytes() == before
    other = tmp_path / 'other-project'
    other.mkdir()
    isolated = call(tmp_path, other, 'status', '--json')
    assert isolated.returncode == 0 and json.loads(isolated.stdout)['tasks'] == []


def test_absent_handoff_is_refused_and_removed_checkpoint_is_visible(tmp_path):
    project = tmp_path / 'project'
    project.mkdir()
    missing = call(tmp_path, project, 'checkpoint', 'task', '--goal', 'Fix it',
                   '--checkpoint', 'handoffs/missing.md', '--next', 'test', '--json')
    assert missing.returncode != 0
    packet = project / 'handoff.md'
    packet.write_text('An advisory handoff, not an execution receipt.')
    saved = call(tmp_path, project, 'checkpoint', 'task', '--goal', 'Fix it',
                 '--checkpoint', 'handoff.md', '--next', 'test', '--json')
    assert saved.returncode == 0
    packet.unlink()
    read = call(tmp_path, project, 'status', 'task', '--json')
    assert read.returncode == 0
    assert json.loads(read.stdout)['tasks'][0]['checkpoint_status'] != 'present'
