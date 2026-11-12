"""Real CLI scheduling checks with a disposable local worker, never a model."""
import json
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "src/agent_harness/workgraph/plan.py"


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "plan").mkdir()
    stub = tmp_path / "stub"
    stub.mkdir()
    worker = stub / "claude"
    worker.write_text(f"#!{sys.executable}\n" + '''import json, re, sys
from pathlib import Path
prompt = sys.argv[sys.argv.index('-p') + 1]
n = re.search(r'^NODE (\\d+):', prompt, re.M).group(1)
with Path('calls').open('a') as f: f.write(n + '\\n')
Path('out-' + n).touch()
print(json.dumps({'is_error': False, 'subtype': 'success', 'result': 'fixture complete'}))
''')
    worker.chmod(0o700)
    monkeypatch.setenv("PATH", str(stub) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("HARNESS_HOME", str(tmp_path / "home/.agent-harness"))
    monkeypatch.setenv("PLAN_RUNNER", "claude")
    monkeypatch.setenv("PLAN_GUARD", "off")
    monkeypatch.setenv("PLAN_QUIET", "1")
    monkeypatch.delenv("PLAN_DIR", raising=False)
    return tmp_path


def graph(root, writes):
    text = "## goal: scheduling contract\n"
    for n, declaration in enumerate(writes, 1):
        field = "" if declaration is None else f" | write_scope: {json.dumps(declaration)}"
        text += f"- [ ] {n}. node {n}{field} | gate: test -f out-{n}\n"
    (root / "plan/g.md").write_text(text)


def run(root, *args):
    return subprocess.run([sys.executable, "-B", str(ENGINE), *args], cwd=root,
                          capture_output=True, text=True, timeout=30)


def test_shared_mode_serializes_undeclared_writes(project):
    graph(project, [None, None])
    result = run(project, "run", "g", "--shared-capacity", "2", "--workers", "2")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "round 2: dispatching 1 node(s)" in result.stdout
    assert (project / "calls").read_text().splitlines() == ["1", "2"]


def test_disjoint_declared_writes_share_a_frontier_and_release(project):
    graph(project, [["out-1"], ["out-2"]])
    result = run(project, "run", "g", "--shared-capacity", "2", "--workers", "2")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "round 1: dispatching 2 node(s)" in result.stdout
    status = run(project, "admission", "--capacity", "2")
    assert status.returncode == 0, status.stderr
    assert json.loads(status.stdout)["reservations"] == []


def test_invalid_writes_do_not_start_worker_or_gate(project):
    graph(project, [["../outside"]])
    result = run(project, "run", "g", "--shared-capacity", "2")
    assert result.returncode != 0
    assert "write" in (result.stdout + result.stderr).lower()
    assert not (project / "calls").exists() and not (project / "out-1").exists()
    assert "exit 1" not in (project / "plan/g.md").read_text()


def test_dry_run_leaves_no_capacity_reservation(project):
    graph(project, [None])
    result = run(project, "run", "g", "--shared-capacity", "1", "--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (project / "calls").exists()
    status = run(project, "admission", "--capacity", "1")
    assert json.loads(status.stdout)["reservations"] == []


def test_legacy_mode_does_not_create_a_shared_store(project):
    graph(project, [None, None])
    result = run(project, "run", "g", "--workers", "2")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "dispatching 2 node(s)" in result.stdout
    assert not (project / "home/.agent-harness/admission").exists()


def test_invalid_capacity_does_not_dispatch(project):
    graph(project, [None])
    result = run(project, "run", "g", "--shared-capacity", "0")
    assert result.returncode != 0
    assert not (project / "calls").exists()


def loaded_engine():
    spec = importlib.util.spec_from_file_location("admission_engine_fixture", ENGINE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_uncertain_dispatch_keeps_reservation_but_normal_failure_releases(project, monkeypatch):
    from agent_harness.workgraph.admission import Admission
    graph(project, [None])
    monkeypatch.chdir(project)
    module = loaded_engine()
    broker = Admission(project / "broker", 1)
    token = broker.acquire(project, None, "fixture", "g/1")["reservation"]
    monkeypatch.setattr(module, "_dispatch", lambda *a, **k: {
        "id": 1, "quota": False, "dispatch_failed": True,
        "execution_unknown": True, "why": "worker timed out"})
    result = module._work_one("g", 1, 1, None, "fixture", admission=broker, reservation=token)
    assert result["dispatch_failed"]
    assert [r["id"] for r in broker.inspect()] == [token]
    assert "exit 1" not in (project / "plan/g.md").read_text()
    assert broker.release(token)
    token = broker.acquire(project, None, "fixture", "g/1")["reservation"]
    monkeypatch.setattr(module, "_dispatch", lambda *a, **k: {"id": 1, "quota": False})
    assert module._work_one("g", 1, 1, None, "fixture", admission=broker,
                            reservation=token)["gate_rc"] == 1
    assert broker.inspect() == []


def test_foreign_capacity_wait_is_not_gate_failure_or_round_cap(project):
    from agent_harness.workgraph.admission import Admission
    graph(project, [None])
    broker = Admission(project / "home/.agent-harness", 1)
    token = broker.acquire(project, None, "other", "other/1")["reservation"]
    result = run(project, "run", "g", "--shared-capacity", "1")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "ADMISSION" in result.stdout and "gates failed 0" in result.stdout
    assert "round cap" not in result.stdout
    assert not (project / "calls").exists()
    assert "exit 1" not in (project / "plan/g.md").read_text()
    assert broker.release(token)
    retry = run(project, "run", "g", "--shared-capacity", "1")
    assert retry.returncode == 0, retry.stdout + retry.stderr
    assert (project / "calls").read_text().splitlines() == ["1"]


def test_real_worker_timeout_keeps_unknown_reservation(project):
    graph(project, [None])
    worker = project / "stub/claude"
    worker.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(3)\n")
    result = run(project, "run", "g", "--shared-capacity", "1", "--timeout", "1", "--max-rounds", "1")
    assert result.returncode == 1, result.stdout + result.stderr
    status = run(project, "admission", "--capacity", "1")
    assert len(json.loads(status.stdout)["reservations"]) == 1
    assert "exit 1" not in (project / "plan/g.md").read_text()


def test_same_graph_has_one_coordinator_while_its_workers_can_be_parallel(project):
    graph(project, [["out-1"], ["out-2"]])
    worker = project / "stub/claude"
    worker.write_text(worker.read_text().replace("Path('out-' + n).touch()", """if n == '1':
    import time
    Path('started').touch()
    while not Path('release').exists(): time.sleep(0.02)
Path('out-' + n).touch()"""))
    first = subprocess.Popen([sys.executable, "-B", str(ENGINE), "run", "g",
                              "--shared-capacity", "2", "--workers", "1", "--max-rounds", "1"],
                             cwd=project, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        until = time.monotonic() + 8
        while not (project / "started").exists() and time.monotonic() < until:
            time.sleep(0.02)
        assert (project / "started").exists(), "fixture worker did not reach its barrier"
        second = run(project, "run", "g", "--shared-capacity", "2", "--workers", "1", "--max-rounds", "1")
        assert second.returncode == 1, second.stdout + second.stderr
        assert (project / "calls").read_text().splitlines() == ["1"]
        assert "coordinator" in second.stdout.lower()
    finally:
        (project / "release").touch()
        out, err = first.communicate(timeout=12)
    assert first.returncode == 1, out + err
    text = (project / "plan/g.md").read_text()
    assert "- [x] 1." in text and "- [ ] 2." in text
    assert "TAMPERED" not in out


def test_failure_before_dispatch_rolls_back_only_unstarted_reservations(project, monkeypatch):
    from agent_harness.workgraph.admission import Admission
    graph(project, [None])
    monkeypatch.chdir(project)
    module = loaded_engine()
    def fail(*_args):
        raise OSError("fixture record unavailable before dispatch")
    monkeypatch.setattr(module, "ensure_record", fail)
    args = type("A", (), {"slug": "g", "workers": 1, "max_rounds": 1, "timeout": 1,
                           "model": None, "dry_run": False, "shared_capacity": 1})()
    with pytest.raises(OSError, match="fixture record unavailable"):
        module.cmd_run(args)
    assert Admission(project / "home/.agent-harness", 1).inspect() == []
    assert not (project / "calls").exists()
