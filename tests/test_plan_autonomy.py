"""A reversible new work graph must not invent a human approval hold."""
from pathlib import Path
import subprocess
import sys


PLAN = Path(__file__).resolve().parents[1] / "src/agent_harness/workgraph/plan.py"


def call(root, *args):
    return subprocess.run([sys.executable, str(PLAN), *args], cwd=root,
                          capture_output=True, text=True, timeout=10)


def test_authorized_graph_can_opt_into_verifiable_autonomous_front_half(tmp_path):
    (tmp_path / ".git").mkdir()
    result = call(tmp_path, "new", "--autonomous", "research", "Write a source-backed document")
    assert result.returncode == 0, result.stderr
    text = (tmp_path / "plan/research.md").read_text()
    assert text.count("- [ ] ") == 3
    assert "phase-check research analysis" in text
    assert "phase-check research research" in text
    assert "phase-check research plan" in text
    assert "grep -q '^APPROVED'" not in text
    assert "needs: 3" in text


def test_default_graph_retains_explicit_human_gate(tmp_path):
    (tmp_path / ".git").mkdir()
    result = call(tmp_path, "new", "release", "Deploy after owner approval")
    assert result.returncode == 0, result.stderr
    text = (tmp_path / "plan/release.md").read_text()
    assert text.count("- [ ] ") == 4
    assert "gate: grep -q '^APPROVED' plan/release.md" in text
    assert "needs: 4" in text
