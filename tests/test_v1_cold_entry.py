"""Cold-entry memory correction must reach the packet and the real plan gate."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agent_harness.project_memory import ProjectMemory  # noqa: E402
from agent_harness.vault_sources import SourceVault, initialize  # noqa: E402

ENGINE = ROOT / "src/agent_harness/workgraph/plan.py"
CLI = ROOT / "bin/harness"


@pytest.fixture
def case(tmp_path):
    project = tmp_path / "alpha"
    sibling = tmp_path / "bravo"
    for path in (project, sibling):
        path.mkdir()
        (path / ".git").mkdir()
    pid = initialize(project)
    sibling_id = initialize(sibling)
    (project / "decision.md").write_text("Current limit: 3. Never export.\n")
    source = SourceVault(project, pid).capture("decision.md")
    item = {"id": "limit", "project_id": pid, "layer": "authority", "kind": "authority",
            "scope": "project", "text": (project / "decision.md").read_text(),
            "provenance": [{"source": source, "start_line": 1, "end_line": 1}],
            "confidence": "user_stated", "sensitivity": "private",
            "access_boundary": "local_user", "owner": "fixture-user", "freshness": "current"}
    old = ProjectMemory(project, pid).append(item, expected=None)
    (project / "plan").mkdir()
    (project / "plan/work.md").write_text(
        "## goal: use the current decision\n## versions: v1\n\n"
        "- [ ] 1. Answer from decision | inputs: decision.md | outputs: answer.txt | "
        "ctx: answer.txt | gate: python3 check.py\n")
    (project / "check.py").write_text(
        "from pathlib import Path\n"
        "Path('gate-ran').write_text('yes')\n"
        "assert Path('answer.txt').read_text() == Path('decision.md').read_text()\n")
    request = {"schema": "harness.launch/v1", "project_id": pid,
               "task": "Write the current decision to answer.txt, preserving the exception.",
               "references": [old], "scope": {
                   "allowed_sensitivities": ["private"], "allowed_scopes": ["project"],
                   "layers": ["authority"]},
               "max_context_bytes": 8192, "plan_node": {"slug": "work", "id": 1}}
    (project / "request.json").write_text(json.dumps(request))
    return project, sibling, sibling_id, item, old, source


def prepare(root):
    result = subprocess.run(
        [sys.executable, str(CLI), "launch", "--project-root", str(root),
         "--request", "request.json"],
        cwd=root, capture_output=True, text=True, timeout=15)
    return result, json.loads(result.stdout) if result.stdout else None


def plan(root, *args):
    env = {**os.environ, "HOME": str(root.parent / "test-home"), "PLAN_QUIET": "1"}
    return subprocess.run([sys.executable, str(ENGINE), *args], cwd=root, env=env,
                          capture_output=True, text=True, timeout=15)


def test_cold_entry_rebuilds_corrected_source_and_scoped_context(case):
    root, _, _, item, old, old_source = case
    first_run, first = prepare(root)
    assert first_run.returncode == 0, first_run.stderr
    assert "Current limit: 3" in first["prompt"]
    assert old_source["source_id"] in first["prompt"]
    (root / "decision.md").write_text("Current limit: 5. Never export.\n")
    new_source = SourceVault(root, item["project_id"]).capture("decision.md")
    item["text"] = (root / "decision.md").read_text()
    item["provenance"][0]["source"] = new_source
    current = ProjectMemory(root, item["project_id"]).append(item, expected=old)
    second_run, second = prepare(root)  # a fresh CLI process, as after compaction
    assert second_run.returncode == 0, second_run.stderr
    assert second["memory_receipts"] == [current]
    assert second["context_sha256"] != first["context_sha256"]
    assert "Current limit: 5" in second["prompt"]
    assert "Current limit: 3" not in second["prompt"]
    assert new_source["source_id"] in second["prompt"]
    assert old_source["source_id"] not in second["prompt"]
    assert "Never export" in second["prompt"]


def test_stale_worker_cannot_settle_after_memory_source_correction(case):
    root, _, _, item, old, _ = case
    claim = plan(root, "claim", "work", "--id", "1", "--owner", "fixture-worker")
    assert claim.returncode == 0, claim.stdout + claim.stderr
    (root / "answer.txt").write_text("Current limit: 3. Never export.\n")
    (root / "decision.md").write_text("Current limit: 5. Never export.\n")
    item["text"] = (root / "decision.md").read_text()
    item["provenance"][0]["source"] = SourceVault(root, item["project_id"]).capture("decision.md")
    ProjectMemory(root, item["project_id"]).append(item, expected=old)
    stale = plan(root, "gate", "work", "1", "--owner", "fixture-worker")
    assert stale.returncode != 0 and "NOT_RUN" in stale.stdout + stale.stderr
    assert not (root / "gate-ran").exists()
    assert "- [ ] 1." in (root / "plan/work.md").read_text()
    (root / "answer.txt").write_text("Current limit: 5. Never export.\n")
    fresh = plan(root, "gate", "work", "1")
    assert fresh.returncode == 0, fresh.stdout + fresh.stderr
    assert (root / "gate-ran").read_text() == "yes"
    assert "- [x] 1." in (root / "plan/work.md").read_text()


def test_sibling_project_memory_cannot_be_prepared_as_this_plan(case):
    root, _, sibling_id, _, _, _ = case
    request_path = root / "request.json"
    request = json.loads(request_path.read_text())
    request["project_id"] = sibling_id
    request_path.write_text(json.dumps(request))
    result, _ = prepare(root)
    assert result.returncode == 2 and result.stdout == ""
    assert "project" in result.stderr.lower()
    assert not (root / "answer.txt").exists()


def test_cold_entry_refuses_memory_outside_declared_scope(case):
    root, _, _, _, _, _ = case
    request_path = root / "request.json"
    request = json.loads(request_path.read_text())
    request["scope"]["allowed_scopes"] = ["another-project-scope"]
    request_path.write_text(json.dumps(request))
    result, _ = prepare(root)
    assert result.returncode == 2 and result.stdout == ""
    assert "scope" in result.stderr.lower()
    assert not (root / "answer.txt").exists()
