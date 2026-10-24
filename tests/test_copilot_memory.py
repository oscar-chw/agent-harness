"""A Copilot-only install shares skills and memory with other MCP clients."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agent_harness.adapters.copilot_vscode import vscode_user_dirs  # noqa: E402
from agent_harness.adapters.base import Ctx  # noqa: E402
from agent_harness.mcp.memory import Memory  # noqa: E402


@pytest.fixture
def installed(tmp_path):
    home = tmp_path / "home"
    project = tmp_path / "project"
    home.mkdir()
    project.mkdir()
    (project / ".git").mkdir()
    # Editor CLIs can target the logged-in desktop even with HOME overridden.
    # Expose only Python: the fixture must never invoke code/cursor or install extensions.
    tools = tmp_path / "bin"
    tools.mkdir()
    (tools / "python3").symlink_to(sys.executable)
    env = {k: v for k, v in os.environ.items() if not k.startswith("HARNESS_")}
    env.update(HOME=str(home), HARNESS_HOME=str(home / ".agent-harness"), PATH=str(tools))
    result = subprocess.run([sys.executable, str(ROOT / "bin/harness"), "--home", str(home),
                             "install", "--yes", "--tools", "copilot-vscode"],
                            env=env, text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    return home, project, env


def test_copilot_only_install_copies_every_shared_skill(installed):
    home, _, _ = installed
    sources = list((ROOT / "content/skills").glob("*/SKILL.md"))
    assert sources
    for source in sources:
        copied = home / ".agents/skills" / source.parent.name / "SKILL.md"
        assert copied.is_file(), source.parent.name
        assert copied.read_bytes() == source.read_bytes()


def invoke(entry, project, env, calls):
    requests = [{"jsonrpc": "2.0", "id": i, "method": "tools/call",
                 "params": {"name": name, "arguments": args}}
                for i, (name, args) in enumerate(calls)]
    result = subprocess.run([entry["command"], *entry.get("args", [])], cwd=project,
                            env=env, input="".join(json.dumps(r) + "\n" for r in requests),
                            text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    responses = [json.loads(line)["result"] for line in result.stdout.splitlines()]
    assert len(responses) == len(calls)
    assert all(not r["isError"] for r in responses), responses
    return [json.loads(r["content"][0]["text"]) for r in responses]


@pytest.mark.parametrize("portable", [False, True])
def test_generated_copilot_configuration_launches_shared_memory_after_restart(installed, portable):
    home, project, env = installed
    if portable:
        config, key = home / ".copilot/mcp-config.json", "mcpServers"
    else:
        ctx = Ctx(home, home / ".agent-harness", ROOT / "content", {}, "", [])
        config, key = vscode_user_dirs(ctx)[0] / "mcp.json", "servers"
    entry = json.loads(config.read_text())[key]["harness"]
    assert entry["type"] == "stdio"
    memory = Memory(home=home / ".agent-harness", project=project)
    try:
        identity = memory.mem_add("The release color is turquoise.", scope="project")["id"]
    finally:
        memory.close()
    found = invoke(entry, project, env, [("mem_search", {"query": "release color"})])[0]
    assert [r["id"] for r in found] == [identity]
    assert found[0]["project"] == str(project.resolve())
    added = invoke(entry, project, env, [("mem_add", {"text": "The test marker is amber.",
                                                    "scope": "project", "project": str(project)})])[0]
    # A new non-Copilot reader sees the same store; no vendor-specific copy.
    memory = Memory(home=home / ".agent-harness", project=project)
    try:
        assert memory.mem_search("test marker")[0]["id"] == added["id"]
    finally:
        memory.close()
    other = project.parent / "other"
    other.mkdir()
    assert invoke(entry, other, env, [("mem_search", {"query": "release color"})])[0] == []


def test_copilot_rules_do_not_treat_empty_fact_search_as_absent_history(installed):
    home, _, _ = installed
    rules = (home / ".copilot/instructions/harness.instructions.md").read_text()
    assert "Empty means none" not in rules
    assert "session_search" in rules
    assert "project" in rules
