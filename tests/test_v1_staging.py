"""Offline wheel -> isolated prefix -> temporary HOME -> real MCP stdio.

Requires an existing Python with pip, setuptools>=61 and wheel. Set
HARNESS_STAGING_PYTHON to use that interpreter when the test runner has an older
build backend. No build dependencies are downloaded and no editor CLI is exposed.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
BUILD_PYTHON = os.environ.get("HARNESS_STAGING_PYTHON", sys.executable)


def run(argv, cwd, env, input=None):
    result = subprocess.run([str(a) for a in argv], cwd=cwd, env=env, input=input,
                            text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def environment(root, prefix):
    home = root / "home"
    home.mkdir()
    # HOME alone is insufficient: an editor CLI can control the real desktop.
    # A fresh venv's bin is the entire PATH; inherit no vendor/plan/Python config.
    return {"HOME": str(home), "HARNESS_HOME": str(home / ".agent-harness"),
            "PATH": str(prefix / "bin"), "PYTHONNOUSERSITE": "1",
            "PIP_CONFIG_FILE": os.devnull, "PIP_NO_INDEX": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_CACHE_DIR": "1",
            "TMPDIR": str(root)}


@pytest.fixture(scope="module")
def wheel(tmp_path_factory):
    root = tmp_path_factory.mktemp("wheel-build")
    source = root / "source"
    source.mkdir()
    # Copy only build inputs, never a checkout's stale build/ or egg-info.
    for name in ("pyproject.toml", "README.md", "LICENSE"):
        shutil.copy2(ROOT / name, source / name)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
    shutil.copytree(ROOT / "src/agent_harness", source / "src/agent_harness", ignore=ignore)
    shutil.copytree(ROOT / "content", source / "content", ignore=ignore)
    package = source / "src/agent_harness"
    expected = {"agent_harness/" + p.relative_to(package).as_posix(): p.read_bytes()
                for p in package.rglob("*.py")}
    for name in ("bin/plan", "bin/phase-check", "tiers/pytest.ini"):
        expected["agent_harness/workgraph/" + name] = (package / "workgraph" / name).read_bytes()
    expected.update({"agent_harness/content/" + p.relative_to(source / "content").as_posix():
                     p.read_bytes() for p in (source / "content").rglob("*") if p.is_file()})
    env = environment(root, root / "unused-prefix")
    run([BUILD_PYTHON, "-I", "-m", "pip", "wheel", "--no-index", "--no-deps",
         "--no-build-isolation", "--no-cache-dir", "--wheel-dir", root / "dist", source],
        root, env)
    wheels = list((root / "dist").glob("*.whl"))
    assert len(wheels) == 1, wheels
    # Subsequent install/runtime checks cannot fall back to the build tree.
    shutil.rmtree(source)
    return wheels[0], expected


@pytest.fixture
def prefix(wheel, tmp_path):
    prefix = tmp_path / "prefix"
    env = environment(tmp_path, prefix)
    # Use the venv's own offline pip. External pip --prefix writes an entrypoint
    # shebang for the external interpreter, which cannot import this venv's wheel.
    run([BUILD_PYTHON, "-I", "-m", "venv", prefix], tmp_path, env)
    run([prefix / "bin/python", "-I", "-m", "pip", "install", "--no-index", "--no-deps",
         "--no-cache-dir", wheel[0]], tmp_path, env)
    python = prefix / "bin/python"
    imported = json.loads(run([python, "-I", "-c",
                               "import agent_harness, json, sys; "
                               "print(json.dumps([agent_harness.__file__, sys.path]))"],
                              tmp_path, env))
    assert Path(imported[0]).is_relative_to(prefix)
    assert all(not Path(p).is_relative_to(ROOT) for p in imported[1] if p)
    for name in ("code", "code-insiders", "cursor", "claude", "codex", "copilot"):
        assert shutil.which(name, path=env["PATH"]) is None
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
    # Execute the wheel's real console script using its isolated prefix Python.
    return {"cli": [python, prefix / "bin/harness"], "env": env,
            "home": Path(env["HOME"]), "project": project}


def cli(stage, *args, input=None):
    return run([*stage["cli"], "--home", stage["home"], *args],
               stage["project"], stage["env"], input=input)


def install(stage):
    cli(stage, "install", "--yes", "--tools", "copilot-vscode")
    config = stage["home"] / ".copilot/mcp-config.json"
    entry = json.loads(config.read_text())["mcpServers"]["harness"]
    assert entry["type"] == "stdio"
    server = stage["home"] / ".agent-harness/lib/agent_harness/mcp/server.py"
    assert entry["args"] == [str(server)]
    stage["entry"] = [entry["command"], *entry["args"]]


def exchange(stage, messages):
    requests = [{"jsonrpc": "2.0", "id": i, "method": method, "params": params}
                for i, (method, params) in enumerate(messages)]
    output = run(stage["entry"], stage["project"], stage["env"],
                 input="".join(json.dumps(r) + "\n" for r in requests))
    responses = [json.loads(line) for line in output.splitlines()]
    assert len(responses) == len(requests), responses
    for request, response in zip(requests, responses):
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == request["id"]
        assert "error" not in response, response
        assert response["result"].get("isError") is not True, response
    return [r["result"] for r in responses]


def call(stage, name, arguments):
    return exchange(stage, [("tools/call", {"name": name, "arguments": arguments})])[0]["content"][0]["text"]


def snapshot(home):
    result = {}
    for path in home.rglob("*"):
        relative = path.relative_to(home)
        if relative.parts[0] == ".agent-harness":
            continue  # Uninstall intentionally retains memory and backups.
        if path.is_symlink():
            result[str(relative)] = ("link", os.readlink(path))
        elif path.is_dir():
            result[str(relative)] = ("directory",)
        else:
            result[str(relative)] = ("file", path.read_bytes())
    return result


def test_clean_wheel_contains_runtime_and_content(wheel):
    artifact, expected = wheel
    with zipfile.ZipFile(artifact) as archive:
        missing = expected.keys() - set(archive.namelist())
        assert not missing, "wheel omitted: " + ", ".join(sorted(missing))
        for name, content in expected.items():
            assert archive.read(name) == content, name


def test_staged_console_script_runs_without_an_interpreter_wrapper(prefix):
    # The package install must leave a CLI users can execute directly.
    script = prefix["cli"][1]
    result = subprocess.run([script, "--help"], cwd=prefix["project"], env=prefix["env"],
                            text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert "harness" in result.stdout


def test_wheel_installs_and_generated_mcp_recalls_memory_and_runs_plan(prefix):
    install(prefix)
    initialized, listed = exchange(prefix, [
        ("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                        "clientInfo": {"name": "staging-test", "version": "1"}}),
        ("tools/list", {})])
    assert initialized["serverInfo"]["name"] == "harness"
    assert initialized["protocolVersion"] == "2024-11-05"
    assert {"mem_add", "mem_search", "plan"} <= {t["name"] for t in listed["tools"]}
    fact = "The staging release color is turquoise."
    added = json.loads(call(prefix, "mem_add", {"text": fact, "scope": "project"}))
    # Every call starts a fresh MCP process; persistence cannot be in-process state.
    recalled = json.loads(call(prefix, "mem_search", {"query": "staging release color"}))
    assert [r["id"] for r in recalled] == [added["id"]]
    assert recalled[0]["text"] == fact
    assert recalled[0]["project"] == str(prefix["project"].resolve())
    assert json.loads(call(prefix, "mem_search", {"query": "oceanography"})) == []
    prompt = json.dumps({"prompt": "What is the staging release color?", "session_id": "wheel",
                         "cwd": str(prefix["project"])})
    assert fact in cli(prefix, "_hook-prompt", input=prompt)
    call(prefix, "plan", {"args": "init . --python --slug staging", "project": str(prefix["project"])})
    assert (prefix["project"] / "plan/staging.md").is_file()
    assert (prefix["project"] / "pytest.ini").read_bytes() == (
        prefix["home"] / ".agent-harness/lib/agent_harness/workgraph/tiers/pytest.ini").read_bytes()
    listing = call(prefix, "plan", {"args": "list", "project": str(prefix["project"])})
    assert "staging" in listing and "0 broken" in listing, listing
    versions = json.loads(call(prefix, "plan", {"args": "versions staging",
                                               "project": str(prefix["project"])}))
    assert versions["mode"] == "legacy" and versions["nodes"], versions


def test_staged_uninstall_restores_user_files_and_keeps_memory(prefix):
    home = prefix["home"]
    (home / ".copilot/instructions").mkdir(parents=True)
    original = b'{"mcpServers": {"other": {"command": "fixture-only"}}}\n'
    (home / ".copilot/mcp-config.json").write_bytes(original)
    (home / ".copilot/instructions/harness.instructions.md").write_bytes(b"My own rules.\r\n")
    before = snapshot(home)
    install(prefix)
    added = json.loads(call(prefix, "mem_add", {"text": "The rollback marker is amber.", "scope": "project"}))
    saved = home / ".agent-harness/memory/project" / (added["id"] + ".json")
    memory = saved.read_bytes()
    assert snapshot(home) != before
    cli(prefix, "uninstall")
    assert snapshot(home) == before
    assert saved.read_bytes() == memory
    assert not (home / ".agent-harness/installed.json").exists()
    assert not (home / ".agent-harness/lib").exists()


def test_missing_staged_workgraph_cannot_fall_back_to_checkout_or_prefix(prefix):
    install(prefix)
    workgraph = prefix["home"] / ".agent-harness/lib/agent_harness/workgraph"
    assert workgraph.is_dir()
    workgraph.rename(prefix["home"] / "removed-workgraph")
    result = subprocess.run(prefix["entry"], cwd=prefix["project"], env=prefix["env"],
                            input=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n",
                            text=True, capture_output=True, timeout=15)
    assert result.returncode != 0
    assert "No module named 'agent_harness.workgraph'" in result.stderr
    assert not result.stdout


def test_staged_explicit_launch_loads_current_memory_then_restores_adapter(prefix):
    """The installed wheel, not this checkout, owns prepare and invoke."""
    before = snapshot(prefix["home"])
    install(prefix)
    _, listed = exchange(prefix, [("initialize", {"protocolVersion": "2024-11-05",
                                    "capabilities": {}, "clientInfo": {"name": "launch-test", "version": "1"}}),
                                  ("tools/list", {})])
    assert "plan" in {tool["name"] for tool in listed["tools"]}
    code = """import json
from pathlib import Path
from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault,initialize
root=Path.cwd(); pid=initialize(root)
(root/'decision.md').write_text('Qualification: NOT_DEPLOYED; limit 7.\\n')
ref=SourceVault(root,pid).capture('decision.md')
item=dict(id='stage',project_id=pid,layer='project_facts',kind='fact',scope='qualification',
          text='Qualification: NOT_DEPLOYED; limit 7.',provenance=[dict(source=ref,start_line=1,end_line=1)],
          confidence='verified',sensitivity='internal',access_boundary='local_user',owner='fixture',freshness='current')
receipt=ProjectMemory(root,pid).append(item,expected=None)
(root/'plan').mkdir()
(root/'plan/work.md').write_text('## goal: fixture\\n\\n- [ ] 1. Check result | gate: true\\n')
request=dict(schema='harness.launch/v1',project_id=pid,task='State current qualification and limit.',
             references=[receipt],scope=dict(allowed_sensitivities=['internal'],
             allowed_scopes=['qualification'],layers=['project_facts']),max_context_bytes=8192,
             plan_node=dict(slug='work',id=1))
(root/'request.json').write_text(json.dumps(request))
"""
    run([prefix["cli"][0], "-I", "-c", code], prefix["project"], prefix["env"])
    prepared = json.loads(cli(prefix, "launch", "--project-root", prefix["project"],
                              "--request", "request.json"))
    assert prepared["native_completion"] == "NOT_RUN"
    assert "NOT_DEPLOYED; limit 7" in prepared["prompt"]
    assert "plan context work 1" in prepared["prompt"]
    assert "plan gate work 1" in prepared["prompt"]
    native = Path(prefix["env"]["PATH"]) / "codex"
    native.write_text(f"#!{prefix['cli'][0]}\n" +
                      "import json,os,sys\n"
                      "assert sys.argv[1:4]==['exec','--json','-s']\n"
                      "assert sys.argv[4]=='read-only'\n"
                      "assert os.environ['PATH'].split(os.pathsep)[0].endswith('agent_harness/workgraph/bin')\n"
                      "assert 'NOT_DEPLOYED; limit 7' in sys.stdin.read()\n"
                      "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'NOT_DEPLOYED; limit 7'}}))\n"
                      "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':5,'cached_input_tokens':0,'output_tokens':2}}))\n")
    native.chmod(0o700)
    result = json.loads(cli(prefix, "launch", "--project-root", prefix["project"],
                            "--request", "request.json", "--execute", "--receipt-out", "launch.json",
                            "--timeout", "5"))
    assert result["native_completion"] == "COMPLETED_UNGRADED"
    assert result["task_evaluation"] == "NOT_RUN"
    assert result["answer"] == "NOT_DEPLOYED; limit 7"
    assert json.loads((prefix["project"] / "launch.json").read_text()) == result
    cli(prefix, "uninstall")
    assert snapshot(prefix["home"]) == before
    assert (prefix["project"] / ".harness/records/00000001.json").is_file()


def test_staged_normal_session_hooks_revalidate_withdrawn_project_memory(prefix):
    """Generated hook commands must work from the wheel, including after a source withdrawal."""
    (prefix["home"] / ".claude").mkdir()
    (prefix["home"] / ".codex").mkdir()
    (prefix["home"] / ".claude/settings.json").write_text('{"model":"user-choice"}\n')
    (prefix["home"] / ".codex/config.toml").write_text('model = "user-choice"\n')
    before = snapshot(prefix["home"])
    cli(prefix, "install", "--yes", "--tools", "claude-code,codex")
    claude = json.loads((prefix["home"] / ".claude/settings.json").read_text())
    codex = json.loads((prefix["home"] / ".codex/hooks.json").read_text())
    claude_commands = [h["command"] for group in claude["hooks"]["SessionStart"] for h in group["hooks"]]
    codex_commands = [h["command"] for group in codex["hooks"]["SessionStart"] for h in group["hooks"]]
    commands = [next(c for c in claude_commands if "_hook-op" in c),
                next(c for c in codex_commands if "_hook-context" in c)]
    setup = '''import json
from pathlib import Path
from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault,initialize
root=Path.cwd(); pid=initialize(root)
(root/'basis.md').write_text('The service is in review.\\n')
ref=SourceVault(root,pid).capture('basis.md')
item=dict(id='basis',project_id=pid,layer='project_facts',kind='fact',scope='project',
 text='The service is in review.',provenance=[dict(source=ref,start_line=1,end_line=1)],
 confidence='verified',sensitivity='private',access_boundary='local_user',owner='fixture',freshness='current')
receipt=ProjectMemory(root,pid).append(item,expected=None)
(root/'memory-fixture.json').write_text(json.dumps(dict(item=item,receipt=receipt)))
'''
    run([prefix["cli"][0], "-I", "-c", setup], prefix["project"], prefix["env"])
    receipt = json.loads((prefix["project"] / "memory-fixture.json").read_text())["receipt"]
    request = {"schema": "harness.launch/v1", "project_id": receipt["project_id"],
               "task": "State the current service review status.", "references": [receipt],
               "scope": {"allowed_sensitivities": ["private"], "allowed_scopes": ["project"],
                         "layers": ["project_facts"]}, "max_context_bytes": 8192}
    (prefix["project"] / "request.json").write_text(json.dumps(request))
    prepared = json.loads(cli(prefix, "launch", "--project-root", prefix["project"],
                              "--request", "request.json"))
    assert "The service is in review." in prepared["prompt"] and prepared["native_completion"] == "NOT_RUN"
    state = json.loads(cli(prefix, "op", "put", input=json.dumps({
        "task": "review", "value": {"stage": "check source"}, "expected": 0,
        "request_id": "staged-create", "memory_receipt": receipt})))
    assert state["cursor"] == 1

    def delivered(source):
        event = {"hook_event_name": "SessionStart", "cwd": str(prefix["project"]),
                 "session_id": "staged-session", "source": source}
        output = []
        for command in commands:
            result = subprocess.run(["/bin/sh", "-c", command], cwd=prefix["project"], env=prefix["env"],
                                    input=json.dumps(event), text=True, capture_output=True, timeout=10)
            assert result.returncode == 0, result.stderr
            output.append(result.stdout)
        return output

    startup_output = delivered("startup")
    for text in startup_output:
        assert '"cursor":1' in text and "review" in text and "check source" in text

    recall_setup = '''from agent_harness.mcp.memory import Memory
from pathlib import Path
m=Memory(project=Path.cwd());m.mem_add('The staging cutover window is 03:00.',scope='project');m.close()
'''
    run([prefix["cli"][0], "-I", "-c", recall_setup], prefix["project"], prefix["env"])
    prompt_commands = [
        next(h["command"] for group in claude["hooks"]["UserPromptSubmit"] for h in group["hooks"]
             if "_hook-prompt" in h["command"]),
        next(h["command"] for group in codex["hooks"]["UserPromptSubmit"] for h in group["hooks"]
             if "_hook-prompt" in h["command"]),
    ]
    prompt_output = []
    for n, command in enumerate(prompt_commands):
        event = {"hook_event_name": "UserPromptSubmit", "cwd": str(prefix["project"]),
                 "session_id": "staged-prompt-" + str(n), "prompt": "What is the staging cutover window?"}
        result = subprocess.run(["/bin/sh", "-c", command], cwd=prefix["project"], env=prefix["env"],
                                input=json.dumps(event), text=True, capture_output=True, timeout=10)
        assert result.returncode == 0, result.stderr
        assert "03:00" in result.stdout
        prompt_output.append(result.stdout)
    withdraw = '''import json
from pathlib import Path
from agent_harness.project_memory import ProjectMemory
root=Path.cwd(); data=json.loads((root/'memory-fixture.json').read_text())
ProjectMemory(root,data['receipt']['project_id']).append(
 dict(data['item'],freshness='withdrawn'),expected=data['receipt'])
'''
    run([prefix["cli"][0], "-I", "-c", withdraw], prefix["project"], prefix["env"])
    resume_output = delivered("resume")
    for text in resume_output:
        assert "review" in text and "stale" in text and "check source" not in text
    failed = subprocess.run([*prefix["cli"], "--home", str(prefix["home"]), "launch",
                             "--project-root", str(prefix["project"]), "--request", "request.json"],
                            cwd=prefix["project"], env=prefix["env"], text=True,
                            capture_output=True, timeout=10)
    assert failed.returncode == 2 and "REFUSE_WITHDRAWN" in failed.stderr
    delta = json.loads(cli(prefix, "op", "changes", "--cursor", "1"))
    assert delta["events"] == [] and delta["memory_invalidations"] == ["review"]
    (prefix["project"] / "candidate-observations.json").write_text(json.dumps({
        "prepared": prepared, "startup_output": startup_output, "prompt_output": prompt_output,
        "resume_output": resume_output, "withdrawn_launch_exit": failed.returncode,
        "withdrawn_launch_error": failed.stderr, "changes": delta}, sort_keys=True))
    cli(prefix, "uninstall")
    assert snapshot(prefix["home"]) == before
    assert not (prefix["home"] / ".agent-harness/installed.json").exists()
    assert not (prefix["home"] / ".agent-harness/lib").exists()
    assert (prefix["project"] / ".harness/records/00000002.json").is_file()
    assert list((prefix["home"] / ".agent-harness/operational").glob("*.sqlite"))
