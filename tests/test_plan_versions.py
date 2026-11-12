"""Versioned graph acceptance uses actual gates and fresh subprocesses, not worker claims."""
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "src/agent_harness/workgraph/plan.py"


@pytest.fixture
def graph(tmp_path):
    (tmp_path / "plan").mkdir()
    (tmp_path / "home").mkdir()
    (tmp_path / "req.txt").write_text("approved-local-v1")
    (tmp_path / "other.txt").write_text("independent-v1")
    (tmp_path / "check.py").write_text('''from pathlib import Path
import sys, time
node = sys.argv[1]
Path("ran-" + node).write_text("called")
while Path("wait").exists():
    time.sleep(.02)
if Path("change-input").exists():
    Path("req.txt").write_text("revoked-v2")
expected = {"1": lambda: Path("req.txt").read_text(),
            "2": lambda: Path("a.txt").read_text() if Path("a.txt").exists() else "missing",
            "3": lambda: Path("other.txt").read_text()}
path = {"1": "a.txt", "2": "b.txt", "3": "c.txt"}[node]
assert Path(path).read_text() == expected[node]()
''')
    (tmp_path / "plan/g.md").write_text(
        "## goal: synthetic input/result bindings\n## versions: v1\n\n"
        "- [ ] 1. first | inputs: req.txt | outputs: a.txt | ctx: a.txt | gate: python3 check.py 1\n"
        "- [ ] 2. dependent | needs: 1 | inputs: a.txt | outputs: b.txt | ctx: b.txt | gate: python3 check.py 2\n"
        "- [ ] 3. independent | inputs: other.txt | outputs: c.txt | ctx: c.txt | gate: python3 check.py 3\n")
    return tmp_path


def env(root, **extra):
    result = {**os.environ, "HOME": str(root / "home"), "PLAN_QUIET": "1", "PLAN_OWNER": "test-owner"}
    result.pop("PLAN_DIR", None)
    result.update(extra)
    return result


def run(root, *args, **extra):
    return subprocess.run([sys.executable, str(ENGINE), *args], cwd=root, env=env(root, **extra),
                          capture_output=True, text=True, timeout=15)


def versions(root):
    result = run(root, "versions", "g")
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["nodes"]


def finish(root, node):
    source, output = {1: ("req.txt", "a.txt"), 2: ("a.txt", "b.txt"), 3: ("other.txt", "c.txt")}[node]
    (root / output).write_bytes((root / source).read_bytes())
    result = run(root, "gate", "g", str(node))
    assert result.returncode == 0, result.stdout + result.stderr


def accepted(root):
    for node in (1, 2, 3):
        finish(root, node)


def mark(root, node):
    line = next(x for x in (root / "plan/g.md").read_text().splitlines() if x.startswith("- [") and f"] {node}." in x)
    return line[3]


def test_real_gate_receipt_binds_inputs_outputs_and_parent_result(graph):
    accepted(graph)
    rows = versions(graph)
    assert all(r["state"] == "current" for r in rows.values())
    receipt = json.loads((graph / "plan/g.versions" / (rows["2"]["receipt"] + ".json")).read_text())
    assert receipt["binding"]["parents"] == {"1": rows["1"]["receipt"]}
    assert receipt["binding"]["inputs"]["a.txt"]["sha256"] == hashlib.sha256(b"approved-local-v1").hexdigest()
    assert receipt["outputs"]["b.txt"]["sha256"] == hashlib.sha256(b"approved-local-v1").hexdigest()
    assert receipt["exit_code"] == 0


def test_change_reopens_only_affected_dependency_closure_and_preserves_sources(graph):
    accepted(graph)
    old = versions(graph)
    retained = {p.name: p.read_bytes() for p in (graph / "plan/g.versions").glob("*.json")}
    (graph / "req.txt").write_text("revoked-v2")
    rows = versions(graph)
    assert rows["1"]["state"] == rows["2"]["state"] == "stale"
    assert rows["3"]["state"] == "current"
    ready = run(graph, "ready", "g")
    assert "READY 1." in ready.stdout and "READY 2." not in ready.stdout and "ALL DONE" not in ready.stdout
    assert run(graph, "refresh", "g").returncode == 0
    assert [mark(graph, n) for n in (1, 2, 3)] == [" ", " ", "x"]
    assert (graph / "req.txt").read_text() == "revoked-v2"
    assert {p.name: p.read_bytes() for p in (graph / "plan/g.versions").glob("*.json")} == retained
    assert versions(graph)["3"]["receipt"] == old["3"]["receipt"]


def test_restoring_old_file_does_not_undo_persisted_invalidation(graph):
    accepted(graph)
    (graph / "req.txt").write_text("revoked-v2")
    assert run(graph, "refresh", "g").returncode == 0
    (graph / "req.txt").write_text("approved-local-v1")
    assert mark(graph, 1) == mark(graph, 2) == " "
    assert "ALL DONE" not in run(graph, "ready", "g").stdout
    finish(graph, 1)
    assert "READY 2." in run(graph, "ready", "g").stdout


def test_stale_dependency_is_refused_before_gate_runs(graph):
    accepted(graph)
    (graph / "ran-2").unlink()
    (graph / "req.txt").write_text("new")
    result = run(graph, "gate", "g", "2")
    assert result.returncode != 0 and "PASS 2" not in result.stdout
    assert not (graph / "ran-2").exists()


def test_reverification_uses_new_receipts_and_old_history_remains(graph):
    accepted(graph)
    old = versions(graph)
    (graph / "req.txt").write_text("corrected-v2")
    finish(graph, 1)
    assert versions(graph)["2"]["state"] == "stale"
    finish(graph, 2)
    new = versions(graph)
    assert new["1"]["receipt"] != old["1"]["receipt"]
    assert new["2"]["receipt"] != old["2"]["receipt"]
    assert new["3"] == old["3"]
    assert (graph / "plan/g.versions" / (old["1"]["receipt"] + ".json")).is_file()


def test_output_bytes_and_executable_bit_are_bound(graph):
    accepted(graph)
    (graph / "a.txt").chmod(0o755)
    assert versions(graph)["1"]["state"] == "stale"
    (graph / "a.txt").chmod(0o644)
    (graph / "b.txt").write_text("unverified rewrite")
    assert versions(graph)["2"]["state"] == "stale"
    assert versions(graph)["3"]["state"] == "current"


def test_claim_pins_input_before_worker_can_edit_it(graph):
    assert run(graph, "claim", "g", "--id", "1", "--owner", "worker").returncode == 0
    (graph / "req.txt").write_text("changed-after-dispatch")
    (graph / "a.txt").write_text("changed-after-dispatch")
    result = run(graph, "gate", "g", "1", "--owner", "worker")
    assert result.returncode != 0
    assert not (graph / "ran-1").exists()
    assert "NOT_RUN" in result.stdout + result.stderr
    assert mark(graph, 1) == " "


def test_gate_changes_input_then_exit_zero_is_not_accepted(graph):
    (graph / "a.txt").write_text("revoked-v2")
    (graph / "change-input").touch()
    result = run(graph, "gate", "g", "1")
    assert result.returncode != 0 and "PASS 1" not in result.stdout
    assert mark(graph, 1) == " "
    assert (graph / "req.txt").read_text() == "revoked-v2"


def test_missing_declared_output_cannot_pass_an_exit_zero_gate(graph):
    plan = graph / "plan/g.md"
    plan.write_text(plan.read_text().replace("python3 check.py 1", "true"))
    result = run(graph, "gate", "g", "1")
    assert result.returncode != 0 and mark(graph, 1) == " "


@pytest.mark.parametrize("damage", ["delete", "corrupt"])
def test_missing_or_corrupt_receipt_is_held_not_silently_reaccepted(graph, damage):
    accepted(graph)
    receipt = graph / "plan/g.versions" / (versions(graph)["1"]["receipt"] + ".json")
    if damage == "delete":
        receipt.unlink()
    else:
        receipt.write_text("{}")
    rows = versions(graph)
    assert rows["1"]["state"] == "held"
    assert rows["2"]["state"] != "current"
    (graph / "ran-1").unlink()
    assert run(graph, "gate", "g", "1").returncode != 0
    assert not (graph / "ran-1").exists()


def test_refresh_does_not_steal_live_worker_lease(graph):
    accepted(graph)
    assert run(graph, "mark", "g", "2", "pending").returncode == 0
    assert run(graph, "claim", "g", "--id", "2", "--owner", "other-worker").returncode == 0
    (graph / "req.txt").write_text("changed")
    assert run(graph, "refresh", "g").returncode == 0
    assert mark(graph, 2) == ">"
    text = (graph / "plan/g.md").read_text()
    assert "owner: other-worker" in text
    assert run(graph, "claim", "g", "--id", "2", "--owner", "intruder").returncode != 0


def test_gate_or_requirement_prose_change_invalidates_results(graph):
    accepted(graph)
    p = graph / "plan/g.md"
    p.write_text(p.read_text().replace("python3 check.py 1", "python3 check.py 1 && true"))
    assert versions(graph)["1"]["state"] == "stale"
    assert versions(graph)["3"]["state"] == "current"
    p.write_text(p.read_text() + "\nCurrent authority: publication is revoked.\n")
    assert versions(graph)["3"]["state"] == "stale"


def test_cannot_bypass_gate_by_mark_done_or_remove_version_marker(graph):
    assert run(graph, "mark", "g", "1", "done", "--force").returncode != 0
    accepted(graph)
    p = graph / "plan/g.md"
    p.write_text(p.read_text().replace("## versions: v1\n", ""))
    result = run(graph, "ready", "g")
    assert result.returncode != 0 and "ALL DONE" not in result.stdout


@pytest.mark.parametrize("path", ["../outside.txt", "/tmp/outside.txt", "plan/g.md"])
def test_invalid_input_boundaries_are_not_read_or_executed(graph, path):
    p = graph / "plan/g.md"
    p.write_text(p.read_text().replace("inputs: req.txt", "inputs: " + path))
    assert run(graph, "gate", "g", "1").returncode != 0
    assert not (graph / "ran-1").exists()


def test_unrelated_work_remains_ready_when_an_input_is_missing(graph):
    (graph / "req.txt").unlink()
    result = run(graph, "ready", "g")
    assert "READY 3." in result.stdout and "READY 1." not in result.stdout
    finish(graph, 3)
    assert versions(graph)["3"]["state"] == "current"


def test_independent_gate_still_rejects_wrong_output_when_other_input_is_missing(graph):
    (graph / "req.txt").unlink()
    (graph / "c.txt").write_text("wrong independent result")
    result = run(graph, "gate", "g", "3")
    assert result.returncode != 0 and "PASS 3" not in result.stdout
    assert mark(graph, 3) == " "
    assert (graph / "ran-3").is_file()


def test_interrupted_gate_cannot_leave_old_success_and_can_resume(graph):
    accepted(graph)
    (graph / "ran-1").unlink()
    (graph / "wait").touch()
    proc = subprocess.Popen([sys.executable, str(ENGINE), "gate", "g", "1"], cwd=graph,
                            env=env(graph), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    try:
        deadline = time.monotonic() + 5
        while not (graph / "ran-1").exists() and time.monotonic() < deadline:
            time.sleep(.02)
        assert (graph / "ran-1").exists()
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)
    assert mark(graph, 1) == ">"
    assert "ALL DONE" not in run(graph, "ready", "g").stdout
    (graph / "wait").unlink()
    assert run(graph, "claim", "g", "--id", "1", PLAN_LEASE_HOURS="0").returncode == 0
    finish(graph, 1)
    assert versions(graph)["2"]["state"] == "stale"


def test_legacy_plan_does_not_gain_new_files_or_change_gate_semantics(graph):
    p = graph / "plan/g.md"
    p.write_text(p.read_text().replace("## versions: v1\n", ""))
    accepted(graph)
    (graph / "req.txt").write_text("later")
    assert "ALL DONE" in run(graph, "ready", "g").stdout
    assert not (graph / "plan/g.versions").exists()


def stub_worker(root, change_decision=False):
    directory = root / "stub-bin"
    directory.mkdir()
    stub = directory / "codex"
    stub.write_text(f'''#!{sys.executable}
from pathlib import Path
import json, re, sys
node = re.search(r"^NODE (\\d+):", sys.argv[-1], re.M).group(1)
source, output = {{"1": ("req.txt", "a.txt"), "2": ("a.txt", "b.txt"), "3": ("other.txt", "c.txt")}}[node]
if {change_decision!r} and node == "1":
    Path("decision.md").write_text("corrected-v2")
Path(output).write_bytes(Path(source).read_bytes())
print(json.dumps({{"type":"item.completed","item":{{"type":"agent_message","text":"synthetic worker produced output"}}}}))
''')
    stub.chmod(0o755)
    return {"PLAN_RUNNER": "codex", "PATH": str(directory) + os.pathsep + os.environ.get("PATH", "")}


def test_run_uses_real_gates_after_parallel_stub_workers_and_preserves_notes(graph):
    result = run(graph, "run", "g", "--workers", "2", "--max-rounds", "3", **stub_worker(graph))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "TAMPERED" not in result.stdout + result.stderr
    assert all(row["state"] == "current" for row in versions(graph).values())
    assert all((graph / f"ran-{i}").exists() for i in (1, 2, 3))


def test_run_refuses_changed_declared_input_even_if_worker_reports_success(graph):
    (graph / "decision.md").write_text("decision-v1")
    p = graph / "plan/g.md"
    p.write_text(p.read_text().replace("inputs: req.txt", "inputs: req.txt,decision.md"))
    result = run(graph, "run", "g", "--workers", "1", "--max-rounds", "1", **stub_worker(graph, True))
    assert result.returncode != 0
    assert "NOT_RUN" in result.stdout + result.stderr
    assert not (graph / "ran-1").exists()
    assert mark(graph, 1) == " " and versions(graph)["1"]["state"] != "current"
    assert (graph / "decision.md").read_text() == "corrected-v2"


def test_declared_check_source_is_bound_not_only_the_shell_command(graph):
    p = graph / "plan/g.md"
    p.write_text(p.read_text().replace("inputs: req.txt", "checks: check.py | inputs: req.txt"))
    finish(graph, 1)
    (graph / "check.py").write_text((graph / "check.py").read_text() + "\n# different check revision\n")
    assert versions(graph)["1"]["state"] == "stale"


def test_check_change_after_claim_prevents_execution(graph):
    p = graph / "plan/g.md"
    p.write_text(p.read_text().replace("inputs: req.txt", "checks: check.py | inputs: req.txt"))
    assert run(graph, "claim", "g", "--id", "1").returncode == 0
    (graph / "check.py").write_text((graph / "check.py").read_text() + "\n# different check revision\n")
    (graph / "a.txt").write_text("approved-local-v1")
    assert run(graph, "gate", "g", "1").returncode != 0
    assert not (graph / "ran-1").exists()


def test_join_waits_for_both_current_parent_results(graph):
    p = graph / "plan/g.md"
    p.write_text(p.read_text().replace("needs: 1 |", "needs: 1,3 |"))
    finish(graph, 1)
    assert "READY 2." not in run(graph, "ready", "g").stdout
    finish(graph, 3)
    assert "READY 2." in run(graph, "ready", "g").stdout
    finish(graph, 2)
    old = versions(graph)
    (graph / "other.txt").write_text("corrected-independent-v2")
    rows = versions(graph)
    assert rows["1"] == old["1"]
    assert rows["2"]["state"] == rows["3"]["state"] == "stale"
    (graph / "ran-2").unlink()
    assert run(graph, "gate", "g", "2").returncode != 0
    assert not (graph / "ran-2").exists()


def test_inspection_never_rewrites_graph_sources_or_receipts(graph):
    accepted(graph)
    (graph / "req.txt").write_text("revoked-by-user")
    before = {p.relative_to(graph).as_posix(): p.read_bytes() for p in graph.rglob("*") if p.is_file()}
    assert versions(graph)["1"]["state"] == "stale"
    run(graph, "ready", "g")
    run(graph, "status", "g")
    after = {p.relative_to(graph).as_posix(): p.read_bytes() for p in graph.rglob("*") if p.is_file()}
    assert before == after


@pytest.mark.parametrize("kind", ["symlink", "fifo", "oversize"])
def test_non_regular_or_oversized_inputs_hold_before_execution(graph, kind):
    path = graph / "req.txt"
    path.unlink()
    if kind == "symlink":
        path.symlink_to(graph / "other.txt")
    elif kind == "fifo":
        os.mkfifo(path)
    else:
        with path.open("wb") as stream:
            stream.truncate(16 * 1024 * 1024 + 1)
    assert versions(graph)["1"]["state"] == "held"
    assert run(graph, "gate", "g", "1").returncode != 0
    assert not (graph / "ran-1").exists()


def test_full_receipt_store_refuses_publication_without_deleting_history(graph):
    directory = graph / "plan/g.versions"
    directory.mkdir()
    retained = directory / "retained-history.bin"
    with retained.open("wb") as stream:
        stream.truncate(64 * 1024 * 1024)
    (graph / "a.txt").write_text("approved-local-v1")
    result = run(graph, "gate", "g", "1")
    assert result.returncode != 0 and mark(graph, 1) == " "
    assert retained.stat().st_size == 64 * 1024 * 1024
    assert not list(directory.glob("*.json"))


def test_long_reverse_order_dependency_chain_and_cycles_do_not_recurse(tmp_path):
    # Synthetic accepted-receipt fixtures exercise resolution depth, not model quality.
    spec = importlib.util.spec_from_file_location("version_fixture", ENGINE.with_name("versions.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = tmp_path / "plan/g.md"
    path.parent.mkdir()
    nodes, lines = {}, ["## versions: v1"]
    for nid in range(1, 601):
        fields = {"gate": "true"}
        if nid < 600:
            fields["needs"] = str(nid + 1)
        nodes[nid] = {"id": nid, "title": str(nid), "mark": " ", "fields": fields,
                      "line": nid, "notes": [], "note_lines": []}
        lines.append(f"- [ ] {nid}. synthetic")
    state = module.Versions(path, lines, nodes)
    for nid in reversed(nodes):
        receipt = state.publish(nid, state.capture(nid), "2026-01-01T00:00:00Z", module.nonce())
        nodes[nid]["mark"] = "x"
        nodes[nid]["notes"] = [f"2026-01-01T00:00:00Z exit 0 in 0s — synthetic @version={receipt}"]
    fresh = module.Versions(path, lines, nodes)
    fresh.annotate()
    assert all(n["_version_state"]["state"] == "current" for n in nodes.values())
    nodes[600]["fields"]["needs"] = "1"
    cyclic = module.Versions(path, lines, nodes)
    cyclic.annotate()
    assert all(n["_version_state"]["state"] != "current" for n in nodes.values())


def test_new_irreversible_hold_before_claim_is_honoured(graph, monkeypatch):
    spec = importlib.util.spec_from_file_location("race_engine", ENGINE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.chdir(graph)
    monkeypatch.setenv("HOME", str(graph / "home"))
    monkeypatch.delenv("PLAN_DIR", raising=False)
    original = module.Lock
    changed = False

    class EditBeforeLock(original):
        def __enter__(self):
            nonlocal changed
            if not changed:
                p = graph / "plan/g.md"
                p.write_text(p.read_text().replace("inputs: req.txt", "risk: irreversible | inputs: req.txt"))
                changed = True
            return super().__enter__()

    monkeypatch.setattr(module, "Lock", EditBeforeLock)
    (graph / "a.txt").write_text("approved-local-v1")
    with pytest.raises(SystemExit) as error:
        module.cmd_gate(SimpleNamespace(slug="g", id=1, attended=False, owner="test-owner", force=False))
    assert error.value.code == 3
    assert not (graph / "ran-1").exists()


def test_same_owner_overlapping_gates_only_publish_the_latest_run(graph):
    (graph / "a.txt").write_text("approved-local-v1")
    (graph / "wait").touch()
    children = []
    try:
        for _ in range(2):
            (graph / "ran-1").unlink(missing_ok=True)
            children.append(subprocess.Popen([sys.executable, str(ENGINE), "gate", "g", "1"], cwd=graph,
                                             env=env(graph), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                             text=True, start_new_session=True))
            deadline = time.monotonic() + 5
            while not (graph / "ran-1").exists() and time.monotonic() < deadline:
                time.sleep(.02)
            assert (graph / "ran-1").exists()
        (graph / "wait").unlink()
        for child in children:
            child.communicate(timeout=5)
        assert sorted(child.returncode for child in children) == [0, 5]
        assert versions(graph)["1"]["state"] == "current"
        assert len(list((graph / "plan/g.versions").glob("*.json"))) == 1
    finally:
        for child in children:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
