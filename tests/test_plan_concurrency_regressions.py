"""Cross-process graph ownership and history regressions with stub workers only."""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


ENGINE = Path(__file__).resolve().parents[1] / "src/agent_harness/workgraph/plan.py"


def setup(tmp_path):
    (tmp_path / "plan").mkdir()
    (tmp_path / "home").mkdir()
    stub = tmp_path / "stub"
    stub.mkdir()
    worker = stub / "claude"
    worker.write_text("#!/bin/sh\nprintf '%s\\n' '" + json.dumps({
        "is_error": False, "subtype": "success", "result": "stub finished",
        "duration_ms": 10, "total_cost_usd": 0, "permission_denials": []}) + "'\n")
    worker.chmod(0o755)
    env = dict(os.environ, HOME=str(tmp_path / "home"),
               PLAN_RUNNER="claude", PLAN_QUIET="1", PLAN_LEASE_HOURS="0.0001",
               PATH=str(stub) + os.pathsep + os.environ.get("PATH", ""))
    return env


def wait_for(path, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.02)
    raise AssertionError("stub gate did not begin")


def codex_tree_stub(tmp_path):
    stub = tmp_path / "stub/codex"
    stub.write_text("#!/usr/bin/env python3\n"
                    "import os,subprocess,sys,time\nfrom pathlib import Path\n"
                    "Path('codex-worker-pid').write_text(str(os.getpid()))\n"
                    "subprocess.Popen([sys.executable,'-c',"
                    "\"import os,time; from pathlib import Path; "
                    "Path('codex-child-pid').write_text(str(os.getpid())); "
                    "time.sleep(12); Path('codex-child-finished').write_text('late')\"])\n"
                    "time.sleep(12)\nPath('codex-worker-finished').write_text('late work')\n")
    stub.chmod(0o755)


def test_expired_gate_conflict_preserves_the_new_owners_live_lease(tmp_path):
    env = setup(tmp_path)
    (tmp_path / "plan/g.md").write_text(
        "## goal: preserve the owner after a delayed gate\n\n"
        "- [ ] 1. work | gate: sh -c 'touch gate-started; "
        "while [ ! -f gate-unblock ]; do sleep 0.05; done; true'\n")
    run = subprocess.Popen([sys.executable, str(ENGINE), "run", "g", "--workers", "1",
                            "--max-rounds", "1"], cwd=tmp_path, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        wait_for(tmp_path / "gate-started")
        deadline = time.monotonic() + 3  # wait for second-granular lease expiry, not gate completion
        while True:
            claimed = subprocess.run([sys.executable, str(ENGINE), "claim", "g", "--owner", "takeover"],
                                     cwd=tmp_path, env=env, capture_output=True, text=True, timeout=3)
            if claimed.returncode == 0:
                break
            assert "NONE READY" in claimed.stderr, claimed.stdout + claimed.stderr
            assert time.monotonic() < deadline, "the short lease never became reclaimable"
            time.sleep(0.1)
        assert "1" in claimed.stdout
        (tmp_path / "gate-unblock").touch()
        out, _ = run.communicate(timeout=5)
    finally:
        (tmp_path / "gate-unblock").touch()
        if run.poll() is None:
            run.kill()
            run.wait(timeout=5)
    line = next(line for line in (tmp_path / "plan/g.md").read_text().splitlines()
                if line.startswith("- ["))
    assert "- [>] 1." in line and "owner: takeover" in line, out
    assert "CONFLICT 1" in out
    assert "gates failed 0" in out  # a stale result was not a task failure


def test_reconcile_restores_rewritten_historical_gate_note(tmp_path):
    env = setup(tmp_path)
    original = "2026-01-01T00:00:00Z exit 1 in 1s [deadbeef] — real failure"
    (tmp_path / "plan/g.md").write_text(
        "## goal: preserve old gate evidence\n\n- [ ] 1. work | gate: false\n"
        "      " + original + "\n")
    stub = tmp_path / "stub/claude"
    stub.write_text("#!/bin/sh\npython3 - <<'PY'\n"
                    "from pathlib import Path\n"
                    "p=Path('plan/g.md')\n"
                    "p.write_text(p.read_text().replace('exit 1 in 1s [deadbeef]', "
                    "'exit 0 in 1s [deadbeef]'))\n"
                    "PY\nprintf '%s\\n' '" + json.dumps({
                        "is_error": False, "subtype": "success", "result": "stub finished",
                        "duration_ms": 10, "total_cost_usd": 0, "permission_denials": []}) + "'\n")
    stub.chmod(0o755)
    run = subprocess.run([sys.executable, str(ENGINE), "run", "g", "--workers", "1",
                          "--max-rounds", "1"], cwd=tmp_path, env=env,
                         capture_output=True, text=True, timeout=10)
    text = (tmp_path / "plan/g.md").read_text()
    assert run.returncode == 2 and "TAMPERED 1" in run.stdout, run.stdout + run.stderr
    assert "      " + original in text
    assert "exit 0 in 1s [deadbeef]" not in text


def test_sighup_stops_a_codex_worker_before_releasing_its_claim(tmp_path):
    env = setup(tmp_path)
    env["PLAN_RUNNER"] = "codex"
    codex_tree_stub(tmp_path)
    (tmp_path / "plan/g.md").write_text("## goal: stop a Codex worker\n\n- [ ] 1. slow | gate: true\n")
    run = subprocess.Popen([sys.executable, str(ENGINE), "run", "g", "--workers", "1",
                            "--max-rounds", "1"], cwd=tmp_path, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    worker_pid = child_pid = None
    try:
        wait_for(tmp_path / "codex-worker-pid")
        wait_for(tmp_path / "codex-child-pid")
        worker_pid = int((tmp_path / "codex-worker-pid").read_text())
        child_pid = int((tmp_path / "codex-child-pid").read_text())
        os.kill(run.pid, signal.SIGHUP)
        out, _ = run.communicate(timeout=3)
        assert run.returncode == 129, out
        for pid in (worker_pid, child_pid):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                pass
            else:
                raise AssertionError("Codex worker process tree survived the orchestrator stop")
        assert not (tmp_path / "codex-worker-finished").exists()
        assert not (tmp_path / "codex-child-finished").exists()
        assert "- [>]" not in (tmp_path / "plan/g.md").read_text()
    finally:
        if run.poll() is None:
            run.kill()
            run.wait(timeout=5)
        for pid in (worker_pid, child_pid):
            if pid is None:
                continue
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_codex_timeout_kills_its_process_tree_without_running_the_gate(tmp_path):
    env = setup(tmp_path)
    env["PLAN_RUNNER"] = "codex"
    codex_tree_stub(tmp_path)
    (tmp_path / "plan/g.md").write_text("## goal: timeout a Codex worker\n\n- [ ] 1. slow | gate: touch GATE-RAN\n")
    worker_pid = child_pid = None
    try:
        run = subprocess.run([sys.executable, str(ENGINE), "run", "g", "--workers", "1",
                              "--max-rounds", "1", "--timeout", "1"], cwd=tmp_path, env=env,
                             capture_output=True, text=True, timeout=5)
        assert run.returncode != 0 and "DISPATCH FAILED" in run.stdout, run.stdout + run.stderr
        assert not (tmp_path / "GATE-RAN").exists()
        worker_pid = int((tmp_path / "codex-worker-pid").read_text())
        child_pid = int((tmp_path / "codex-child-pid").read_text())
        for pid in (worker_pid, child_pid):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                pass
            else:
                raise AssertionError("timed-out Codex process tree is still alive")
    finally:
        for pid in (worker_pid, child_pid):
            if pid is None:
                continue
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_normal_codex_worker_still_reaches_an_independent_gate(tmp_path):
    env = setup(tmp_path)
    env["PLAN_RUNNER"] = "codex"
    events = [
        {"type": "thread.started", "thread_id": "fixture"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "work finished"}},
        {"type": "turn.completed", "usage": {"input_tokens": 5, "output_tokens": 2}},
    ]
    worker = tmp_path / "stub/codex"
    worker.write_text("#!/bin/sh\n" + "\n".join(
        "printf '%s\\n' '" + json.dumps(event) + "'" for event in events) + "\n")
    worker.chmod(0o755)
    (tmp_path / "plan/g.md").write_text("## goal: prove the gate ran\n\n- [ ] 1. work | gate: touch GATE-RAN\n")
    result = subprocess.run([sys.executable, str(ENGINE), "run", "g", "--workers", "1",
                             "--max-rounds", "1"], cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=8)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "GATE-RAN").exists()
    assert "- [x] 1." in (tmp_path / "plan/g.md").read_text()


def test_unversioned_mark_done_cannot_bypass_a_failing_gate(tmp_path):
    env = setup(tmp_path)
    graph = tmp_path / "plan/g.md"
    graph.write_text("## goal: only gate results complete work\n\n- [ ] 1. work | gate: false\n")
    for extra in ([], ["--force"]):
        marked = subprocess.run([sys.executable, str(ENGINE), "mark", "g", "1", "done", *extra],
                                cwd=tmp_path, env=env, capture_output=True, text=True, timeout=5)
        assert marked.returncode == 8, marked.stdout + marked.stderr
        assert "- [ ] 1." in graph.read_text()
    failed_gate = subprocess.run([sys.executable, str(ENGINE), "gate", "g", "1"],
                                 cwd=tmp_path, env=env, capture_output=True, text=True, timeout=5)
    assert failed_gate.returncode != 0 and "- [ ] 1." in graph.read_text()
    graph.write_text("## goal: only gate results complete work\n\n- [ ] 1. work | gate: true\n")
    passed_gate = subprocess.run([sys.executable, str(ENGINE), "gate", "g", "1"],
                                 cwd=tmp_path, env=env, capture_output=True, text=True, timeout=5)
    assert passed_gate.returncode == 0 and "- [x] 1." in graph.read_text()
