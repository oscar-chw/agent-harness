"""Frozen matched continuation trials with controller-owned receipts and stops.

Reported fresh-turn inference is measurable. Whole preparation cost, other
providers and general learning efficacy remain outside this experiment.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval"))
import reasoning_iteration as R  # noqa: E402
from agent_harness import installer, procedures as P  # noqa: E402
from agent_harness.mcp.server import Server  # noqa: E402

CASES = [
    {"goal": "Restore invoice rounding checks.", "next": "Inspect the retained decimal integration checks.", "done": False},
    {"goal": "Continue shipment audit.", "next": "Read the checksum mismatch evidence before changing the importer.", "done": False},
]
PROMPT = (
    "Resume the saved task from the shared harness MCP. Read only. Do not edit, "
    "execute the task, send messages or change trust/configuration. Use harness MCP "
    "for task status. Never use shell commands or filesystem reads as a fallback. "
    "If MCP has no saved task, report unavailable. Return JSON with string goal, "
    "string next and boolean done. Whole-goal completion requires verified evidence."
)
CANDIDATE = (
    " Start with op_state status. If it supplies the goal, next step and completion "
    "evidence needed to answer, continue from that packet. Retrieve state_load or "
    "another status only for missing detail or an actual intervening change."
)


class PrelaunchRefused(ValueError):
    """No model process has been started for this reserved attempt."""


def _settings(actor, servers):
    settings = {'model_provider': 'openai', 'service_tier': 'default', 'features.apps': False,
        'model_reasoning_effort': 'high', 'mcp_servers.harness.command': sys.executable,
        'mcp_servers.harness.args': installer.mcp_cmd(actor / 'store')[1:],
        'mcp_servers.harness.enabled_tools': ['state_load', 'op_state']}
    settings.update({'mcp_servers.' + json.dumps(name): {
                         'enabled': False, 'command': sys.executable, 'args': ['-c', 'pass']}
                     for name in servers if name != 'harness'})
    return settings


def _environment():
    excluded = {'HARNESS_PROJECT', 'CODEX_APP_TOOLS_PIPE_PATH', 'OPENAI_BASE_URL'}
    return {key: value for key, value in os.environ.items()
            if key not in excluded and not key.endswith('API_KEY')}


def _native_context(executable, actor, model='gpt-6.1-sol'):
    """Read account mode and available surfaces without logging identity or credentials."""
    command = [executable, 'app-server', '--stdio', '-c', 'model_provider="openai"',
               '-c', 'model=' + json.dumps(model), '-c', 'model_reasoning_effort="high"', '--disable', 'apps']
    child = subprocess.Popen(command, cwd=actor / 'project', env=_environment(),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        bufsize=0, start_new_session=True)
    deadline = time.monotonic() + 60
    try:
        def request(identity, method, params):
            child.stdin.write((json.dumps({'id': identity, 'method': method, 'params': params}) + '\n').encode())
            child.stdin.flush()
            with selectors.DefaultSelector() as selector:
                selector.register(child.stdout, selectors.EVENT_READ)
                while time.monotonic() < deadline:
                    if not selector.select(max(0, deadline - time.monotonic())):
                        break
                    line = child.stdout.readline(1024 * 1024)
                    if not line:
                        raise PrelaunchRefused('native context process closed at ' + method)
                    if not line.endswith(b'\n'):
                        raise PrelaunchRefused('native context response exceeded 1 MiB at ' + method)
                    packet = json.loads(line)
                    if packet.get('id') == identity:
                        if 'error' in packet or not isinstance(packet.get('result'), dict):
                            raise PrelaunchRefused('native context request refused')
                        return packet['result']
            raise PrelaunchRefused('native context read timed out at ' + method + '; process=' + str(child.poll()))
        request(1, 'initialize', {'clientInfo': {'name': 'harness_continuation_probe', 'version': '1'},
                                'capabilities': {'experimentalApi': True}})
        child.stdin.write(b'{"method":"initialized","params":{}}\n')
        child.stdin.flush()
        account = request(2, 'account/read', {'refreshToken': False})
        limits = request(3, 'account/rateLimits/read', {}).get('rateLimits')
        thread = request(4, 'thread/start', {'cwd': str(actor / 'project'), 'model': model,
            'approvalPolicy': 'never', 'permissions': ':read-only', 'ephemeral': True, 'serviceTier': 'default'})
        if thread.get('modelProvider') != 'openai' or thread.get('model') != model:
            raise PrelaunchRefused('native resolved model context differs')
        inventory = request(5, 'mcpServerStatus/list', {'limit': 100, 'detail': 'toolsAndAuthOnly',
            'threadId': thread['thread']['id']})
        safe = {'auth_mode': account.get('account', {}).get('type') if isinstance(account.get('account'), dict) else None,
            'limits_type': type(limits).__name__, 'limit_keys': list(limits) if isinstance(limits, dict) else [],
            'credits_type': type(limits.get('credits')).__name__ if isinstance(limits, dict) else None,
            'has_credits': limits['credits'].get('hasCredits') if isinstance(limits, dict) and isinstance(limits.get('credits'), dict) else None}
        (actor / 'admission-metadata.json').write_text(json.dumps(safe, indent=2) + '\n')
        return _admit_context(actor, account, limits, inventory)
    finally:
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()


def _admit_context(actor, account, limits, inventory):
    if not isinstance(account.get('account'), dict) or account['account'].get('type') != 'chatgpt':
        raise PrelaunchRefused('included native ChatGPT login is required')
    if (not isinstance(limits, dict) or not isinstance(limits.get('credits'), dict)
            or type(limits['credits'].get('hasCredits')) is not bool):
        raise PrelaunchRefused('included account usage metadata is unavailable')
    windows = [limits[name] for name in ('primary', 'secondary') if isinstance(limits.get(name), dict)]
    if (limits.get('rateLimitReachedType') is not None or limits.get('spendControlReached') is True
            or not windows or any(type(w.get('usedPercent')) not in (int, float)
                          or not 0 <= w['usedPercent'] < 100 for w in windows)):
        raise PrelaunchRefused('included quota headroom is unavailable')
    servers = inventory.get('data')
    if (inventory.get('nextCursor') is not None or not isinstance(servers, list)
            or any(not isinstance(s, dict) or not isinstance(s.get('name'), str)
                   or not s['name'] for s in servers)):
        raise PrelaunchRefused('native MCP surface cannot be bounded by this study')
    return {'auth_mode': 'chatgpt', 'paid_credits_available': limits['credits']['hasCredits'],
            'included_window_open': True,
            'quota_used_percent': [w['usedPercent'] for w in windows],
            'surface_names_sha256': P.digest(sorted(s['name'] for s in servers)),
            'surface_control': 'per-invocation disable requests; extra actions independently rejected',
            'settings': _settings(actor, [s['name'] for s in servers])}


def _sources():
    files = sorted((ROOT / "src/agent_harness").rglob("*.py"))
    files += [Path(__file__), ROOT / "eval/reasoning_iteration.py"]
    return {str(p.relative_to(ROOT)): R.C._sha(p.read_bytes()) for p in files}


def prepare(out, *, mode="native", model="gpt-6.1-sol", max_tokens=350000, timeout_seconds=120):
    if (mode not in ("native", "simulation") or type(max_tokens) is not int
            or not 1 <= max_tokens <= 350000 or type(timeout_seconds) is not int
            or not 1 <= timeout_seconds <= 120):
        raise ValueError("invalid continuation study bounds")
    out = Path(out).absolute()
    out.mkdir(parents=True, exist_ok=False)
    (out / "oracle").mkdir()
    executable = shutil.which("codex") if mode == "native" else "simulation"
    if not executable:
        raise ValueError("native Codex executable is unavailable")
    version = subprocess.check_output([executable, "--version"], text=True).strip() if mode == "native" else "fixture"
    for index, case in enumerate(CASES, 1):
        for arm in ("base", "cand"):
            actor = out / str(index) / arm
            project = actor / "project"
            project.mkdir(parents=True)
            (project / ".git").mkdir()
            home = actor / "store"
            installer.copy_harness(home, ROOT, None)
            previous = Path.cwd()
            try:
                os.chdir(project)
                response = Server(home=home).handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                    "params": {"name": "state_save", "arguments": {"text": (
                    "## Goal\n" + case["goal"] + "\n## Done\nImplementation pending.\n## Next\n" + case["next"] + "\n"),
                    "project": str(project)}}})
                if "error" in response or response.get("result", {}).get("isError"):
                    raise ValueError("fixture state save did not succeed")
            finally:
                os.chdir(previous)
            _preflight(actor, case)
    frozen = {"schema": "continuation-iteration/v1", "mode": mode, "model": model, "effort": "high",
        "max_calls": 4, "max_tokens": max_tokens, "timeout_seconds": timeout_seconds,
        "executable": executable, "native_version": version, "cases": CASES,
        "prompt": PROMPT, "candidate": CANDIDATE, "sources": _sources(),
        "orders": [["base", "cand"], ["cand", "base"]], "preparation_native_calls": 0,
        "acceptance": "all paired answers correct, MCP evidence, no extra actions, candidate inference tokens strictly fewer",
        "scope": "two authored continuation cases; total fresh-turn input plus output, cached subsets counted once; preparation/selection history and general transfer unmeasured"}
    ref = R._immutable(out / "oracle/freeze.json", frozen)
    R._append(out, "FROZEN", ref)
    return {"status": "FROZEN_NOT_RUN", "freeze_sha256": ref["sha256"], "mode": mode,
            "max_calls": 4, "max_tokens": max_tokens, "promotion": "NOT_GRANTED"}


def _usage(record):
    events = record.get("events", [])
    turns = [event for event in events if event.get("type") == "turn.completed"]
    if len(turns) != 1:
        raise ValueError("native usage is missing or duplicated")
    usage = turns[0].get("usage", {})
    receipt = {"native_completion": "COMPLETED_UNGRADED", "usage_scope": "fresh_thread_total",
        "usage_status": "PROVIDER_REPORTED", "usage_report_count": 1, "usage": usage}
    try:
        tokens = P._native_tokens(receipt)
        write = usage.get("cache_write_input_tokens", 0)
        reasoning = usage.get("reasoning_output_tokens", 0)
        if (type(write) is not int or type(reasoning) is not int or write < 0 or reasoning < 0
                or usage["cached_input_tokens"] + write > usage["input_tokens"]
                or reasoning > usage["output_tokens"]):
            raise ValueError("native usage subsets exceed their totals")
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError("invalid or incomplete native usage") from error
    return tokens, usage


def assess(record, expected):
    tokens, usage = _usage(record)
    events = record["events"]
    if (record.get("exit_code") != 0
            or any(event.get("type") in ("error", "turn.failed") for event in events)):
        raise ValueError("native terminal completion is missing")
    reads, messages, pending = [], [], set()
    for event in events:
        phase = event.get("type")
        if phase not in ("item.started", "item.updated", "item.completed"):
            continue
        item = event.get("item", {})
        kind = item.get("type")
        if kind in ("agent_message", "reasoning"):
            if kind == "agent_message" and phase == 'item.completed':
                messages.append(item.get("text", ""))
            continue
        if (kind != "mcp_tool_call" or item.get("server") != "harness"
                or item.get("tool") not in ("state_load", "op_state")
                or (item["tool"] == "op_state" and item.get("arguments", {}).get("action") != "status")):
            raise ValueError("extra native action invalidates the trial")
        if phase != 'item.completed':
            if not isinstance(item.get('id'), str):
                raise ValueError('native action identity is missing')
            pending.add(item['id'])
            continue
        pending.discard(item.get('id'))
        if item.get("status") != "completed" or item.get("error"):
            raise ValueError("failed native action invalidates the trial")
        if not isinstance(item.get('result'), dict) or item['result'].get('isError'):
            raise ValueError('native action returned error evidence')
        reads.append(item)
    if pending:
        raise ValueError('native action lifecycle is incomplete')
    try:
        answer = json.loads(messages[-1])
    except (ValueError, IndexError):
        answer = None
    source_ok = any(_source_matches(item, expected) for item in reads)
    return {"correct": P.encoded(answer) == P.encoded(expected) and source_ok,
        "tokens": tokens, "usage": usage, "mcp_reads": len(reads),
        "tool_order": [item["tool"] for item in reads], "answer": answer}


def _source_matches(item, expected):
    content = item['result'].get('content')
    if not isinstance(content, list) or not content or not isinstance(content[0].get('text'), str):
        return False
    text = content[0]['text']
    if item['tool'] == 'state_load':
        fields = dict(re.findall(r'^## (Goal|Next)[ \t]*\r?\n(.*?)(?=^## |\Z)', text, re.M | re.S))
        return fields.get('Goal', '').strip() == expected['goal'] and fields.get('Next', '').strip() == expected['next']
    try:
        packet = json.loads(text)
    except ValueError:
        return False
    return isinstance(packet, dict) and any(
        isinstance(task, dict) and isinstance(task.get('value'), dict)
        and all(task['value'].get(key) == expected[key] for key in ('goal', 'next'))
        for task in packet.get('tasks', []))


def _preflight(actor, expected):
    env = dict(os.environ, HOME=str(actor / "preflight-home"))
    for name in ("HARNESS_HOME", "HARNESS_PROJECT", "PYTHONPATH"):
        env.pop(name, None)
    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": "op_state", "arguments": {"action": "status"}}}
    result = subprocess.run([sys.executable, *installer.mcp_cmd(actor / "store")[1:]],
        cwd=actor / "project", env=env, input=json.dumps(request) + "\n", text=True,
        capture_output=True, timeout=15)
    if result.returncode or not all(expected[key] in result.stdout for key in ("goal", "next")):
        raise ValueError("cold fixture board does not expose the saved task")


def _invoke(actor, prompt, frozen, expected):
    try:
        _preflight(actor, expected)
        if subprocess.check_output([frozen["executable"], "--version"], text=True, timeout=10).strip() != frozen["native_version"]:
            raise PrelaunchRefused("native executable version changed")
        context = _native_context(frozen['executable'], actor, frozen['model'])
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise PrelaunchRefused(str(error)) from error
    options = []
    for key, value in context['settings'].items():
        options += ['-c', key + '=' + installer._toml_val(value)]
    validation = subprocess.run([frozen['executable'], *options, 'app-server', '--print-startup-config'],
        env=_environment(), cwd=actor / 'project', capture_output=True, timeout=20)
    if validation.returncode:
        raise PrelaunchRefused('native startup configuration validation failed')
    context['startup_configuration_validated'] = True
    R._immutable(actor / 'context.json', context)
    command = [frozen["executable"], *options, "exec", "--json", "-m", frozen["model"],
        "-s", "read-only", "-C", str(actor / "project"), prompt]
    started = time.monotonic()
    with (actor / "events.jsonl").open("x") as output, (actor / "stderr.log").open("x") as error:
        try:
            child = subprocess.Popen(command, stdout=output, stderr=error, env=_environment(), start_new_session=True)
        except OSError as error:
            raise PrelaunchRefused('native model process did not start') from error
        try:
            code = child.wait(timeout=frozen["timeout_seconds"])
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            code = child.returncode
    raw = (actor / "events.jsonl").read_bytes()
    return {"exit_code": code, "seconds": time.monotonic() - started,
        "events_sha256": R.C._sha(raw), "events": [json.loads(line) for line in raw.splitlines() if line]}


def execute(out, *, authorized_execute, invoke=None):
    out = Path(out).resolve(strict=True)
    with (out / "oracle/execute.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _execute(out, authorized_execute, invoke)


def _execute(out, authorized_execute, invoke):
    journal = R.journal(out)
    if len(journal) != 1 or journal[0]["kind"] != "FROZEN":
        raise ValueError("continuation run was already consumed")
    ref = journal[0]["data"]
    frozen = R._bound(out / "oracle", ref)
    if authorized_execute != ref["sha256"] or frozen["sources"] != _sources():
        raise ValueError("frozen artifact or source changed")
    if frozen["mode"] == "simulation" and invoke is None:
        raise ValueError("simulation requires an explicit fixture transport")
    if frozen["mode"] == "native" and invoke is not None:
        raise ValueError("native mode uses only its controller transport")
    invoke = invoke or _invoke
    result = {"status": "INCOMPLETE", "mode": frozen["mode"], "calls": 0, "tokens_observed": 0,
        "tokens": {"base": 0, "cand": 0}, "observations": [], "promotion": "NOT_GRANTED",
        "complete_learning_cost": "UNMEASURED", "preparation_native_calls": 0, "unknown_usage_calls": 0,
        "prelaunch_failures": 0}
    for index, case in enumerate(frozen["cases"], 1):
        for arm in frozen["orders"][index - 1]:
            if result["tokens_observed"] >= frozen["max_tokens"]:
                result["status"] = "CEILING_REACHED"
                return _finish(out, result)
            actor = out / str(index) / arm
            prompt = frozen["prompt"] + (frozen["candidate"] if arm == "cand" else "")
            R._append(out, "CONSUMED", {"case": index, "arm": arm, "prompt_sha256": R.C._sha(prompt.encode())})
            known_usage = False
            launched = False
            try:
                record = invoke(actor, prompt, frozen, case)
                launched = True
                result["calls"] += 1
                tokens, _ = _usage(record)
                result["tokens_observed"] += tokens
                result["tokens"][arm] += tokens
                known_usage = True
                raw_ref = R._immutable(out / "oracle" / ("native-" + str(result["calls"]) + ".json"), record)
                grade = assess(record, case)
            except PrelaunchRefused as error:
                result.update(status='PRELAUNCH_REFUSED', failure=str(error))
                result['prelaunch_failures'] += 1
                return _finish(out, result)
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                if not launched:
                    result['calls'] += 1
                result.update(status="INVALID_OBSERVATION", failure=str(error))
                result["unknown_usage_calls"] += int(not known_usage)
                return _finish(out, result)
            observed = {"case": index, "arm": arm, "raw": raw_ref, **grade}
            result["observations"].append(observed)
            R._append(out, "OBSERVED", observed)
            print(json.dumps({"case": index, "arm": arm, "correct": grade["correct"],
                              "tokens": grade["tokens"], "mcp_reads": grade["mcp_reads"]}), flush=True)
            if not grade["correct"]:
                result["status"] = "QUALITY_FAILURE"
                return _finish(out, result)
    result["paired_quality_equal"] = all(row["correct"] for row in result["observations"])
    saves = result["tokens"]["cand"] < result["tokens"]["base"]
    result["status"] = "NATIVE_SCOPED_INFERENCE_GAIN" if saves else "NO_INFERENCE_GAIN"
    if frozen["mode"] == "simulation":
        result["status"] = "SIMULATION_ONLY"
    return _finish(out, result)


def _finish(out, result):
    ref = R._immutable(out / "oracle/result.json", result)
    R._append(out, "RESULT", ref)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "execute"))
    parser.add_argument("out", type=Path)
    parser.add_argument("--authorized-execute")
    args = parser.parse_args()
    result = prepare(args.out) if args.action == "prepare" else execute(args.out, authorized_execute=args.authorized_execute)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
