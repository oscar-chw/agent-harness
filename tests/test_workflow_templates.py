"""Exercise shipped templates through existing public interfaces, offline."""
import json
import os
from pathlib import Path
import subprocess
import sys

from agent_harness.installer import copy_harness

ROOT = Path(__file__).resolve().parents[1]


def test_templates_are_installed_without_replacing_memory(tmp_path):
    hh = tmp_path / 'harness'
    memory = hh / 'memory' / 'retained.json'
    memory.parent.mkdir(parents=True)
    memory.write_text('{"fact":"keep this existing evidence"}')
    before = memory.read_bytes()
    copy_harness(hh, ROOT, None)
    expected = {'task.md', 'worker.md', 'handoff.md', 'source.json', 'procedure.json', 'learning-review.md'}
    assert expected <= {p.name for p in (hh / 'content/templates').iterdir()}
    assert memory.read_bytes() == before


def test_procedure_template_runs_through_prepare_draft_and_inspect(tmp_path):
    template = ROOT / 'content/templates/procedure.json'
    assert template.is_file(), 'The user needs a shipped executable candidate example'
    spec = json.loads(template.read_text())
    project = tmp_path / 'project'
    project.mkdir()
    subprocess.run(['git', 'init', '-q', str(project)], check=True)
    for n, episode in enumerate(spec['episodes']):
        for key in ('path', 'task_path'):
            path = project / episode[key]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f'Synthetic independent {key} record {n}')
    spec_file = project / 'method.json'
    spec_file.write_text(json.dumps(spec))
    env = dict(os.environ, HOME=str(tmp_path / 'home'), HARNESS_HOME=str(tmp_path / 'store'),
               PYTHONPATH=str(ROOT / 'src'))
    def call(*args):
        r = subprocess.run([sys.executable, str(ROOT / 'bin/harness'), 'improve',
                            '--project', str(project), *args], cwd=project, env=env,
                           capture_output=True, text=True, timeout=20)
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout)
    candidate = call('--prepare-procedure', str(spec_file))
    bound = project / 'bound.json'
    bound.write_text(json.dumps(candidate))
    draft = call('--draft-procedure', str(bound))
    assert draft['status'] == 'proposed'
    assert call('--inspect-procedure', draft['id'])['candidate'] == candidate


def test_workgraph_remains_the_completion_authority(tmp_path):
    project = tmp_path / 'project'
    project.mkdir()
    subprocess.run(['git', 'init', '-q', str(project)], check=True)
    tool = ROOT / 'src/agent_harness/workgraph/plan.py'
    r = subprocess.run([sys.executable, str(tool), 'new', 'sample', 'Prove the output', '--autonomous'],
                       cwd=project, capture_output=True, text=True, timeout=10)
    assert r.returncode == 0, r.stderr
    plan = project / 'plan/sample.md'
    with plan.open('a') as f:
        f.write('\n- [ ] 5. Actual check | gate: false\n')
    r = subprocess.run([sys.executable, str(tool), 'gate', 'sample', '5'],
                       cwd=project, capture_output=True, text=True, timeout=10)
    assert r.returncode != 0
    assert '- [ ] 5.' in plan.read_text() and '- [x] 5.' not in plan.read_text()
