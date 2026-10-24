"""Source-process integration, not a claim of native Claude/Codex loading."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agent_harness.project_memory import ProjectMemory  # noqa: E402
from agent_harness.vault_sources import SourceVault, initialize  # noqa: E402

ENGINE = ROOT / "src/agent_harness/workgraph/plan.py"


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    identity = initialize(root)
    (root / "plan").mkdir()
    (root / "independent.txt").write_text("independent result")
    (root / "check.py").write_text(
        "import json,sys\nfrom pathlib import Path\n"
        f"sys.path.insert(0, {str(ROOT / 'src')!r})\n"
        "from agent_harness.project_memory import ProjectMemory\n"
        "node=sys.argv[1]\nPath('ran-'+node).write_text('executed')\n"
        "if node == '3':\n"
        " assert Path('c.txt').read_text() == Path('independent.txt').read_text()\n"
        "else:\n"
        " ref=json.loads(Path('memory-receipt.json').read_text())\n"
        " item=ProjectMemory(Path.cwd(),ref['project_id']).read(ref,allowed_sensitivities=['public'])['item']\n"
        " decision=json.loads(Path('decision.json').read_text())\n"
        " assert item['text'] == 'Port: '+str(decision['chosen'])\n"
        " output='a.txt' if node=='1' else 'b.txt'\n"
        " assert Path(output).read_text() == item['text']\n"
    )
    (root / "plan/g.md").write_text(
        "## goal: source-bound decision and workflow integration\n## versions: v1\n\n"
        "- [ ] 1. apply decision | inputs: decision.json,memory-receipt.json | checks: check.py"
        " | outputs: a.txt | ctx: a.txt | owner: fixture-owner | write_scope: a.txt"
        " | budget: 60s | retry: 2 | escalation: stop-and-replan"
        " | evidence: plan/g | gate: python3 check.py 1\n"
        "- [ ] 2. integrate | needs: 1 | inputs: a.txt,decision.json,memory-receipt.json"
        " | checks: check.py | outputs: b.txt | ctx: b.txt | gate: python3 check.py 2\n"
        "- [ ] 3. independent | inputs: independent.txt | checks: check.py"
        " | outputs: c.txt | ctx: c.txt | gate: python3 check.py 3\n"
    )
    home = tmp_path / "home"
    home.mkdir()
    return root, identity, home


def environment(home):
    result = {**os.environ, "HOME": str(home), "HARNESS_HOME": str(home / ".agent-harness"),
              "PYTHONDONTWRITEBYTECODE": "1", "PLAN_QUIET": "1", "PLAN_OWNER": "fixture-owner"}
    result.pop("PLAN_DIR", None)
    return result


def save_decision(project, port, previous=None, freshness="current"):
    root, identity, _ = project
    decision = {
        "question": "Which local port does this synthetic task require?",
        "evidence": "Fixture requirement supplied independently of the task output.",
        "alternatives": [8081, 8082],
        "chosen": port,
        "rationale": "Match the current fixture requirement.",
        "assumptions": ["Loopback-only example; no service is started."],
        "reversal_trigger": "A later recorded correction changes the chosen port.",
        "downstream": ["a.txt", "b.txt"],
    }
    (root / "decision.json").write_text(json.dumps(decision))
    source = SourceVault(root, identity).capture("decision.json")
    item = {
        "id": "port", "project_id": identity, "layer": "project_facts", "kind": "fact",
        "scope": "task", "text": f"Port: {port}",
        "provenance": [{"source": source, "start_line": 1, "end_line": 1}],
        "confidence": "verified", "sensitivity": "public", "access_boundary": "local_user",
        "owner": "fixture-owner", "freshness": freshness,
    }
    receipt = ProjectMemory(root, identity).append(item, expected=previous)
    (root / "memory-receipt.json").write_text(json.dumps(receipt))
    return receipt


def plan(project, *args):
    root, _, home = project
    return subprocess.run([sys.executable, str(ENGINE), *args], cwd=root, env=environment(home),
                          capture_output=True, text=True, timeout=15, check=False)


def states(project):
    result = plan(project, "versions", "g")
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["nodes"]


def consume(project, cwd):
    root, identity, home = project
    cwd.mkdir()
    result = subprocess.run([
        sys.executable, str(ROOT / "bin/harness"), "memory-page",
        "--project-root", str(root), "--project-id", identity, "--query", "Port",
        "--allow-sensitivity", "public", "--allow-scope", "task", "--layer", "project_facts",
    ], cwd=cwd, env=environment(home), capture_output=True, text=True, timeout=15, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["hits"]


def finish(project, node, text):
    (project[0] / {1: "a.txt", 2: "b.txt", 3: "c.txt"}[node]).write_text(text)
    result = plan(project, "gate", "g", str(node))
    assert result.returncode == 0, result.stdout + result.stderr


def test_fresh_consumer_correction_reopens_chain_and_preserves_history(project, tmp_path):
    first = save_decision(project, 8081)
    hits = consume(project, tmp_path / "consumer-a")
    assert [hit["receipt"] for hit in hits] == [first]
    assert hits[0]["item"]["provenance"]
    for node in (1, 2):
        finish(project, node, hits[0]["item"]["text"])
    finish(project, 3, "independent result")
    accepted = states(project)
    root, identity, _ = project
    retained = {str(p.relative_to(root)): p.read_bytes()
                for directory in (root / ".harness/records", root / "plan/g.versions")
                for p in directory.glob("*.json")}
    second = save_decision(project, 8082, first)
    corrected = consume(project, tmp_path / "consumer-b")
    assert [hit["receipt"] for hit in corrected] == [second]
    assert corrected[0]["item"]["text"] == "Port: 8082"
    changed = states(project)
    assert [changed[str(i)]["state"] for i in (1, 2, 3)] == ["stale", "stale", "current"]
    assert changed["3"]["receipt"] == accepted["3"]["receipt"]
    assert all((root / name).read_bytes() == raw for name, raw in retained.items())
    assert ProjectMemory(root, identity).read(
        first, historical=True, allowed_sensitivities=["public"]
    )["item"]["text"] == "Port: 8081"
    finish(project, 1, corrected[0]["item"]["text"])
    wrong = plan(project, "gate", "g", "2")
    assert wrong.returncode != 0 and "FAIL 2" in wrong.stdout
    finish(project, 2, corrected[0]["item"]["text"])
    final = states(project)
    assert all(row["state"] == "current" for row in final.values())
    assert final["2"]["receipt"] != accepted["2"]["receipt"]


def test_changed_claim_does_not_execute_against_new_decision(project):
    first = save_decision(project, 8081)
    claimed = plan(project, "claim", "g", "--id", "1")
    assert claimed.returncode == 0, claimed.stderr
    save_decision(project, 8082, first)
    (project[0] / "a.txt").write_text("Port: 8082")
    result = plan(project, "gate", "g", "1")
    assert result.returncode != 0
    assert "NOT_RUN" in result.stdout
    assert not (project[0] / "ran-1").exists()


def test_wrong_output_does_not_pass_a_valid_citation(project):
    save_decision(project, 8081)
    (project[0] / "a.txt").write_text("Port: 9999")
    result = plan(project, "gate", "g", "1")
    assert result.returncode != 0 and "FAIL 1" in result.stdout
    assert (project[0] / "ran-1").exists()


def test_expired_memory_cannot_be_reaccepted_by_an_exit_zero_assumption(project):
    first = save_decision(project, 8081)
    finish(project, 1, "Port: 8081")
    save_decision(project, 8081, first, freshness="expired")
    result = plan(project, "gate", "g", "1")
    assert result.returncode != 0 and "FAIL 1" in result.stdout
    records = "".join(path.read_text() for path in (project[0] / "plan/g").glob("01-*.md"))
    assert "expired" in records


def test_worker_context_carries_declared_contract_without_claiming_enforcement(project):
    save_decision(project, 8081)
    result = plan(project, "context", "g", "1")
    assert result.returncode == 0
    for text in ("inputs: decision.json,memory-receipt.json", "outputs: a.txt",
                 "checks: check.py", "write_scope: a.txt", "budget: 60s",
                 "retry: 2", "escalation: stop-and-replan", "evidence: plan/g"):
        assert text in result.stdout
    assert "advisory" in result.stdout.lower()
