"""Project recall across the real stdio MCP boundary; no native model calls."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
from agent_harness.mcp.memory import Memory  # noqa: E402

SERVER = SRC / "agent_harness/mcp/server.py"


@pytest.fixture
def lab(tmp_path):
    home = tmp_path / "home"
    projects = [tmp_path / name for name in ("launcher", "alpha", "bravo")]
    home.mkdir()
    for path in projects:
        path.mkdir()
        (path / ".git").mkdir()
    return home, projects


def exchange(lab, calls):
    home, projects = lab
    env = dict(os.environ, HOME=str(home), HARNESS_HOME=str(home / "harness"),
               HARNESS_PROJECT=str(projects[0]), HARNESS_ENABLE="", HARNESS_DISABLE="")
    requests = [{"jsonrpc": "2.0", "id": i, "method": "tools/call",
                 "params": {"name": name, "arguments": args}}
                for i, (name, args) in enumerate(calls)]
    result = subprocess.run([sys.executable, str(SERVER)], cwd=projects[0], env=env,
                            input="".join(json.dumps(r) + "\n" for r in requests),
                            text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    responses = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(responses) == len(calls)
    assert not result.stderr, result.stderr
    return [r["result"] for r in responses]


def value(response):
    assert response["isError"] is False, response
    return json.loads(response["content"][0]["text"])


def seed(lab, project, text, scope="project"):
    memory = Memory(home=lab[0] / "harness", project=project)
    try:
        return memory.mem_add(text, scope=scope)["id"]
    finally:
        memory.close()


def test_explicit_project_recalls_library_written_fact_in_fresh_server(lab):
    project = lab[1][1]
    identity = seed(lab, project, "Release cutoff is 10:00 UTC.")
    found = value(exchange(lab, [("mem_search", {
        "query": "Release cutoff", "project": str(project)})])[0])
    assert [r["id"] for r in found] == [identity]
    assert found[0]["scope"] == "project"
    assert found[0]["project"] == str(project.resolve())


def test_explicit_write_uses_requested_project_not_launcher(lab):
    project = lab[1][1]
    added = value(exchange(lab, [("mem_add", {
        "text": "Alpha uses a Tuesday cutoff.", "scope": "project", "project": str(project)})])[0])
    memory = Memory(home=lab[0] / "harness", project=project)
    try:
        assert [r["id"] for r in memory.mem_search("Tuesday cutoff")] == [added["id"]]
    finally:
        memory.close()


def test_one_server_does_not_keep_previous_calls_project(lab):
    alpha, bravo = lab[1][1:]
    a = seed(lab, alpha, "Alpha release uses Tuesday.")
    b = seed(lab, bravo, "Bravo release uses Friday.")
    user = seed(lab, alpha, "Release summaries use plain text.", scope="user")
    result = exchange(lab, [("mem_search", {"query": "release", "project": str(p)})
                            for p in (alpha, bravo, alpha)])
    assert [{r["id"] for r in value(res)} for res in result] == [{a, user}, {b, user}, {a, user}]
    default = value(exchange(lab, [("mem_search", {"query": "release"})])[0])
    assert {r["id"] for r in default} == {user}


def test_forget_cannot_archive_a_different_projects_fact(lab):
    alpha, bravo = lab[1][1:]
    identity = seed(lab, alpha, "Release cutoff is 10:00 UTC.")
    denied = value(exchange(lab, [("mem_forget", {"id": identity, "project": str(bravo)})])[0])
    assert denied["ok"] is False
    recovered = value(exchange(lab, [("mem_search", {"query": "Release cutoff", "project": str(alpha)})])[0])
    assert recovered[0]["id"] == identity


def test_explicit_correction_survives_server_restart_and_archives_original(lab):
    project = str(lab[1][1])
    old = seed(lab, project, "Release cutoff is 10:00 UTC.")
    responses = exchange(lab, [
        ("mem_forget", {"id": old, "project": project}),
        ("mem_add", {"text": "Release cutoff is 11:00 UTC.", "scope": "project", "project": project})])
    assert value(responses[0])["ok"] is True
    new = value(responses[1])["id"]
    recovered = value(exchange(lab, [("mem_search", {"query": "Release cutoff", "project": project})])[0])
    assert [r["id"] for r in recovered] == [new]
    assert "11:00" in recovered[0]["text"]
    assert recovered[0]["project"] == project
    assert (lab[0] / "harness/memory/project/archive" / (old + ".json")).exists()


@pytest.mark.parametrize("project", ["relative/project", "/missing-project-fixture", 7, [], None, ""])
def test_invalid_explicit_project_is_refused_not_silently_replaced(lab, project):
    res = exchange(lab, [("mem_add", {"text": "Never store this fallback.",
                                     "scope": "project", "project": project})])[0]
    assert res["isError"] is True
    assert "project" in res["content"][0]["text"].lower()
    assert not list((lab[0] / "harness/memory/project").glob("*.json"))


def test_explicit_subdirectory_resolves_to_repo_without_exposing_sibling(lab):
    alpha, bravo = lab[1][1:]
    sub = alpha / "src"
    sub.mkdir()
    identity = seed(lab, alpha, "Alpha documentation uses teal headings.")
    seed(lab, bravo, "Bravo documentation uses teal headings.")
    recovered = value(exchange(lab, [("mem_search", {"query": "teal headings", "project": str(sub)})])[0])
    assert [r["id"] for r in recovered] == [identity]


def test_unrelated_query_stays_empty(lab):
    project = lab[1][1]
    seed(lab, project, "Release cutoff is 10:00 UTC.")
    assert value(exchange(lab, [("mem_search", {"query": "oceanography", "project": str(project)})])[0]) == []


def test_mcp_schema_exposes_explicit_project_to_real_clients(lab):
    home, projects = lab
    env = dict(os.environ, HOME=str(home), HARNESS_HOME=str(home / "harness"), HARNESS_DISABLE="")
    result = subprocess.run([sys.executable, str(SERVER)], cwd=projects[0], env=env,
                            input=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n",
                            text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    schemas = {t["name"]: t["inputSchema"] for t in json.loads(result.stdout)["result"]["tools"]}
    for name in ("mem_add", "mem_search", "mem_forget"):
        assert schemas[name]["properties"]["project"]["type"] == "string"
