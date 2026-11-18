"""Candidate lessons, captured at the end of every turn by the Stop hook, without the model having to remember.

Only two signals count, because a lesson is only as good as the signal it came from (Reflexion got WORSE on
MBPP when 16% of its "passing" tests were false positives):
  gate  a check that failed and then passed in the same turn: run_checks, `plan gate`, or a test command
  user  an explicit correction or teaching cue from the user ("no, ...", "please remember that ...")
They are kept apart (source), redacted, deduplicated with a count, and written to
~/.agent-harness/candidates.jsonl, never straight into lessons. A repeated observation is evidence for a
separate, source-bound procedure draft; promotion needs an independent comparison. The store is capped by
agent_harness.storage.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import List, Optional

from .redact import redact
from .native_evidence import NativeEvidence as NativeEvidence
from .mcp.memory import _store_lock

STORE = "candidates.jsonl"
PENDING = "capture-pending.json"
PROMPT_QUEUE = Path("capture-inbox/observations.json")
PROMPT_QUEUE_LIMIT = 64
PROMPT_QUEUE_BYTES = 256 * 1024
# A check is a command whose PROGRAM is a test runner or linter, in any step of the command line: `grep -rn
# pytest docs/` names pytest and is not one. Parsed with shlex, so text in quotes or a heredoc is never a step;
# wrappers are skipped (VAR=1, env, time, timeout N, nice, sudo -u X, xvfb-run, uv/poetry/pdm/hatch run, npx,
# any python[3[.x]] -m, a venv's or /usr/bin's python); --version/--help is not a check run.
WRAPPERS = {"time", "nohup", "xvfb-run", "npx", "command", "exec"}
# Wrappers whose own options come before the wrapped command: {name: options that take a value}.
OPT_WRAPPERS = {"env": {"-u", "--unset", "-C", "--chdir"}, "nice": {"-n"}, "timeout": {"-s", "-k", "--signal", "--kill-after"}, "sudo": {"-u", "-g"},
                "ionice": {"-c", "-n"}}
RUNNERS = {"pytest", "py.test", "unittest", "mypy", "tsc", "phase-check", "phase-check.py"}
RUFF_SUBCOMMANDS = {"format", "version", "rule", "config", "linter", "clean", "server", "analyze", "help"}
HEREDOC_BODY = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?\n\s*\1\s*(\n|$)", re.S)


def _steps(cmd: str) -> List[List[str]]:
    import shlex
    cmd = HEREDOC_BODY.sub("\n", cmd)
    lex = shlex.shlex(cmd.replace("\n", " ; "), posix=True, punctuation_chars=";&|()")
    lex.whitespace_split = True
    try:
        toks = list(lex)
    except ValueError:
        return []
    out, cur = [], []
    for t in toks:
        if t and set(t) <= set(";&|()"):        # a subshell's parentheses separate steps like ; does
            out.append(cur)
            cur = []
        else:
            cur.append(t)
    out.append(cur)
    return [x for x in out if x]


def _skip_opts(w: List[str], i: int, valued) -> int:
    while i < len(w) and w[i].startswith("-"):
        i += 2 if w[i] in valued else 1
    return i


def _is_check_step(w: List[str]) -> bool:
    i = 0
    while i < len(w):
        t = w[i]
        b = t.rsplit("/", 1)[-1]
        if re.match(r"^[A-Za-z_]\w*=", t) or b in WRAPPERS:
            i += 1
        elif b in OPT_WRAPPERS:
            i = _skip_opts(w, i + 1, OPT_WRAPPERS[b])
            if b == "timeout" and i < len(w):
                i += 1                                   # the duration
        elif b in ("uv", "poetry", "pdm", "hatch") and i + 1 < len(w) and w[i + 1] == "run":
            i = _skip_opts(w, i + 2, {"--with", "--python", "-p", "--project", "--directory", "--env-file"})
        elif re.match(r"^python[\d.]*$", b):
            j = i + 1                                    # python's own flags (-u, -X dev, ...) before -m
            while j < len(w) and w[j].startswith("-") and w[j] != "-m":
                j += 2 if w[j] in ("-X", "-W") else 1
            if j + 1 < len(w) and w[j] == "-m":
                w, i = [w[j + 1]] + w[j + 2:], 0
            else:
                return False                             # python <script>: not a known check
        else:
            break
    if i >= len(w):
        return False
    prog, rest = w[i].rsplit("/", 1)[-1], w[i + 1:]
    if any(a in ("--version", "--help", "-h", "-V", "--collect-only", "--co", "-n", "--dry-run") for a in rest):
        return False                                     # a listing or a dry run is not a check run
    if prog in RUNNERS:
        return True
    if prog == "ruff":
        return not rest or rest[0] == "check" or (rest[0] not in RUFF_SUBCOMMANDS)   # `ruff src/` is a check
    if prog in ("go", "cargo"):
        return bool(rest) and rest[0] == "test"
    if prog in ("npm", "yarn", "pnpm"):
        script = rest[1] if rest[:1] == ["run"] and len(rest) > 1 else (rest[0] if rest else "")
        return script == "test" or script.startswith("test:")      # not `npm install test`
    if prog == "make":
        return any(t in ("test", "check") for t in rest)
    if prog in ("plan", "plan.py"):
        return bool(rest) and rest[0] == "gate"
    return False


def is_check(cmd: str) -> bool:
    return any(_is_check_step(step) for step in _steps(cmd))


# Only a leading tool status counts: the same words later in output are not the command's exit status.
EXIT_LINE = re.compile(r"\A\s*(?:Exit code|Command failed with exit code):?\s*(-?\d+)")

# Strict on purpose: "Stop the server" is an instruction, not a correction.
CORRECTION = re.compile(r"^\s*(no[,.!]|nope\b|don'?t\b|do not\b|wrong\b|that'?s (wrong|not)|not like that)"
                        r"|\b(instead of|use \S+ (instead|not))\b", re.I)
TEACH = re.compile(r"^\s*(?:please\s+)?remember\s+(?:that\b|to\b|for this project\b)|^\s*from now on\b", re.I)
FAIL_LINE = re.compile(r"(FAILED|ERROR|Error|Traceback|assert|FAIL\b|failed)")
MAX_TEXT = 300


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
    return ""


TAIL_BYTES = 4 * 1024 * 1024


def _replace_capture(path, data):
    temporary = path.with_name(path.name + '.capture-tmp')
    if path.is_symlink() or path.parent.is_symlink() or temporary.is_symlink():
        raise ValueError('capture storage is redirected')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary.touch(mode=0o600, exist_ok=True)
    if path.exists():
        temporary.chmod(path.stat().st_mode & 0o777)
    temporary.write_bytes(data)
    temporary.replace(path)


def _recover_capture(home):
    """Complete the pending writer before another cooperating writer changes its bytes."""
    pending = home / PENDING
    if pending.is_symlink():
        raise ValueError('capture recovery record is redirected')
    if not pending.exists():
        return
    value = json.loads(pending.read_text(encoding='utf-8'))
    fields = {'schema', 'before', 'data', 'marker', 'state', 'sha256'}
    if (not isinstance(value, dict) or set(value) != fields or type(value['schema']) is not int
            or value['schema'] != 1 or not isinstance(value['data'], str)
            or (value['before'] is not None and (not isinstance(value['before'], str)
                or not re.fullmatch(r'[a-f0-9]{64}', value['before'])))
            or not isinstance(value['marker'], str)
            or not re.fullmatch(r'capture-[\w.-]+', value['marker'])
            or not isinstance(value['state'], dict) or set(value['state']) != {'turn', 'keys'}
            or not isinstance(value['state']['turn'], str)
            or not isinstance(value['state']['keys'], list)
            or any(not isinstance(key, str) for key in value['state']['keys'])):
        raise ValueError('invalid capture recovery record')
    bound = {key: item for key, item in value.items() if key != 'sha256'}
    if hashlib.sha256(json.dumps(bound, sort_keys=True).encode()).hexdigest() != value['sha256']:
        raise ValueError('capture recovery record changed')
    path, marker = home / STORE, home / 'state' / value['marker']
    if path.is_symlink() or marker.is_symlink() or marker.parent.is_symlink():
        raise ValueError('capture recovery target is redirected')
    current = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    data = value['data'].encode('utf-8')
    after = hashlib.sha256(data).hexdigest()
    if current == value['before']:
        _replace_capture(path, data)
    elif current != after:
        raise ValueError('capture data changed during recovery; retain the pending record')
    _replace_capture(marker, json.dumps(value['state']).encode('utf-8'))
    pending.unlink()


def _last_turn(path: str) -> list:
    return _last_turn_info(path)[0]


def _jsonl_tail(path: str) -> list:
    with open(path, "rb") as fb:
        size = fb.seek(0, 2)
        fb.seek(max(0, size - TAIL_BYTES))
        if size > TAIL_BYTES:
            fb.readline()                         # a partial first line
        return fb.read().decode("utf-8", "replace").splitlines()


def _last_turn_info(path: str):
    """(events of the last user turn, whether its start is in view). Only the file's tail is read: a long
    session's transcript runs to tens of megabytes, and this runs at the end of every turn. A turn longer than
    the window has no plain user message in it; the caller must then not treat it as a new turn. Known limit:
    a NEW turn whose start is also out of the window is then taken for the old one, so a repeat inside it can
    be missed (an undercount; it can never make one occurrence look like two)."""
    events, started = [], False
    for line in _jsonl_tail(path):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        content = (e.get("message") or {}).get("content")
        plain = e.get("type") == "user" and (isinstance(content, str) or any(
            isinstance(c, dict) and c.get("type") == "text" for c in content or []))
        if plain:
            events, started = [], True
        events.append(e)
    return events, started


def _last_kimi_turn_info(path: str):
    """Translate the latest main-agent wire turn into the existing capture event contract."""
    events, started = [], False
    for line in _jsonl_tail(path):
        try:
            wrapper = json.loads(line)
        except ValueError:
            continue
        if wrapper.get("type") == "turn.prompt":
            turn = str(wrapper.get("turnId") if wrapper.get("turnId") is not None else "")
            events = [{"type": "user", "uuid": wrapper.get("promptId") or turn,
                       "message": {"content": [{"type": "text", "text": _text(wrapper.get("input"))}]}}]
            started = True
            continue
        if not started or wrapper.get("type") != "context.append_loop_event":
            continue
        event = wrapper.get("event") or {}
        if event.get("type") == "tool.call":
            args = event.get("args") or {}
            if not isinstance(args, dict):
                continue
            uid = event.get("toolCallId") or event.get("uuid") or "call-%d" % len(events)
            converted = {"type": "tool_use", "id": uid, "name": str(event.get("name", "")), "input": args}
            events.append({"type": "assistant", "message": {"content": [converted]}})
        elif event.get("type") == "tool.result":
            uid = event.get("toolCallId")
            if not uid:
                continue
            result = event.get("result") or {}
            output = result.get("output", "") if isinstance(result, dict) else str(result)
            converted = {"type": "tool_result", "tool_use_id": uid, "content": output}
            events.append({"type": "user", "message": {"content": [converted]}})
    return events, started


def capture_kimi_turn(hh: Path, transcript: str, session: str, project=None) -> List[dict]:
    events, started = _last_kimi_turn_info(str(transcript))
    return capture_turn(hh, str(transcript), session, project=project, events=events, started=started)


def _pending_prompts(path: Path) -> List[dict]:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError('deferred prompt storage is redirected or invalid')
    if not path.exists():
        return []
    with path.open('rb') as stream:
        raw = stream.read(PROMPT_QUEUE_BYTES + 1)
    if len(raw) > PROMPT_QUEUE_BYTES:
        raise ValueError('deferred prompt storage exceeds its byte limit')
    rows = json.loads(raw)
    hashes = {'key': 16, 'source_sha256': 64, 'source_event_sha256': 64, 'project_sha256': 64}
    fields = {*hashes, 'source', 'summary', 'evidence'}
    if (not isinstance(rows, list) or len(rows) > PROMPT_QUEUE_LIMIT
            or any(not isinstance(row, dict) or set(row) != fields or row['source'] != 'user'
                   or not isinstance(row['summary'], str) or len(row['summary']) > MAX_TEXT
                   or row['summary'] != row['evidence']
                   or any(not isinstance(row[key], str)
                          or not re.fullmatch(r'[a-f0-9]{%d}' % length, row[key])
                          for key, length in hashes.items()) for row in rows)):
        raise ValueError('invalid deferred prompt observations')
    return rows


def _prompt_queue_lock(path: Path):
    if path.parent.is_symlink():
        raise ValueError('deferred prompt storage is redirected')
    return _store_lock(path.parent, timeout=0.05)


def _defer_prompt(path: Path, observation: dict) -> None:
    with _prompt_queue_lock(path):
        rows = _pending_prompts(path)
        if any((row['key'], row['source_event_sha256']) ==
               (observation['key'], observation['source_event_sha256']) for row in rows):
            return
        data = json.dumps([*rows, observation], ensure_ascii=False).encode('utf-8')
        if len(rows) >= PROMPT_QUEUE_LIMIT or len(data) > PROMPT_QUEUE_BYTES:
            raise ValueError('deferred prompt storage is full')
        _replace_capture(path, data)


def _merge_prompt_observations(home: Path, path: Path, observed: List[dict]) -> List[dict]:
    if not path.exists() and not path.is_symlink():
        return _record(home, observed)
    with _prompt_queue_lock(path):
        rows = _record(home, _pending_prompts(path) + observed)
        # On process loss before this acknowledgement, event hashes deduplicate the replay.
        path.unlink(missing_ok=True)
        return rows


def capture_prompt(home: Path, payload: dict) -> Optional[List[dict]]:
    """Observe a Codex prompt without inferring authority. None means durably deferred."""
    if (payload.get('hook_event_name') != 'UserPromptSubmit'
            or any(not isinstance(payload.get(key), str) or not payload[key]
                   for key in ('session_id', 'turn_id', 'cwd', 'prompt'))):
        return []
    project = Path(payload['cwd'])
    if not project.is_absolute() or not project.is_dir():
        return []
    session = hashlib.sha256(payload['session_id'].encode()).hexdigest()
    event = {'type': 'user', 'uuid': payload['turn_id'], 'capture_origin': 'codex-prompt',
             'session_sha256': session, 'message': {'content': payload['prompt']}}
    observed = candidates('', events=[event], project=project)
    queue = home / PROMPT_QUEUE
    pending = home / PENDING
    if not observed and not any(p.exists() or p.is_symlink() for p in (queue, pending)):
        return []
    try:
        with _store_lock(home, timeout=0.2):
            _recover_capture(home)
            rows = _merge_prompt_observations(home, queue, observed)
    except TimeoutError:
        if not observed:
            raise
        _defer_prompt(queue, observed[0])
        return None
    _prune_capture(home, 0.2)
    return rows


def _checks(events) -> List[dict]:
    """[(command, exit, output)] for each check-like tool call in order, matched to its result."""
    calls, out = {}, []
    for e in events:
        for c in (e.get("message") or {}).get("content") or []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                name, inp = str(c.get("name", "")), c.get("input") or {}
                if name.endswith("run_checks"):
                    calls[c.get("id")] = "run_checks"
                elif name.endswith("__plan") and str(inp.get("args", "")).startswith("gate"):
                    calls[c.get("id")] = "plan " + str(inp.get("args"))
                elif name == "Bash" and is_check(str(inp.get("command", ""))):
                    calls[c.get("id")] = str(inp.get("command"))   # whole: it is redacted before any cut
            elif c.get("type") == "tool_result" and c.get("tool_use_id") in calls:
                text = _text(c.get("content"))
                code = None
                try:
                    code = int(json.loads(text).get("exit"))
                except (ValueError, TypeError, AttributeError):
                    m = EXIT_LINE.match(text)
                    code = int(m.group(1)) if m else (1 if c.get("is_error") else 0)
                out.append({"cmd": calls[c["tool_use_id"]], "exit": code, "text": text})
    return out


def _key(source: str, text: str) -> str:
    norm = re.sub(r"[0-9]+", "#", re.sub(r"\s+", " ", text.lower())).strip()
    return hashlib.sha1((source + ":" + norm).encode()).hexdigest()[:16]


def _norm(cmd: str) -> str:
    return re.sub(r"\s+", " ", cmd).strip()


def candidates(transcript: str, events: Optional[list] = None, project=None) -> List[dict]:
    events = _last_turn(transcript) if events is None else events
    project_sha = None
    if project is not None:
        from .mcp.state import project_root
        root = project_root(project)
        if not root.is_dir():
            raise ValueError("candidate project is not a directory")
        project_sha = hashlib.sha256(str(root).encode("utf-8")).hexdigest()
    found = []
    first = events[0] if events else {}
    prompt = _text((first.get("message") or {}).get("content")) if first.get("type") == "user" else ""
    if prompt and (CORRECTION.search(prompt) or TEACH.search(prompt)):
        clean = redact(prompt.strip())
        t = clean[:MAX_TEXT]
        key = _key("user", project_sha + ":" + t if project_sha else t)
        if first.get('capture_origin') == 'codex-prompt':
            # Literal preferences can differ by number, case or text past the preview.
            # Native collection is new; keep legacy transcript identities readable.
            key = hashlib.sha1(('codex-user:' + (project_sha or '') + ':' + clean).encode()).hexdigest()[:16]
        found.append({"source": "user", "summary": t, "evidence": t,
                      "key": key,
                      # A retained transcript event can be matched later; neither hash
                      # authenticates the speaker or promotes the text to a method.
                      "source_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                      "source_event_sha256": hashlib.sha256(json.dumps(first, sort_keys=True,
                                                                         ensure_ascii=False).encode()).hexdigest()})
        if project_sha:
            found[-1]["project_sha256"] = project_sha
    checks = _checks(events)
    for i, c in enumerate(checks):
        if c["exit"] == 0:
            continue
        fixed = next((d for d in checks[i + 1:] if _norm(d["cmd"]) == _norm(c["cmd"]) and d["exit"] == 0), None)
        if fixed is None:
            continue
        text = redact(c["text"].replace("\\n", "\n"))   # whole text first: a key cut in half escapes the pattern
        lines = [x for x in text.splitlines() if FAIL_LINE.search(x)][:3]
        ev = ("\n".join(lines) or text)[:MAX_TEXT]
        cmd = redact(c["cmd"])[:MAX_TEXT]
        found.append({"source": "gate", "summary": "`%s` failed, then passed after a change" % cmd,
                      "evidence": ev, "key": _key("gate", (project_sha + ":" if project_sha else "")
                                                   + c["cmd"] + "|" + (lines[0] if lines else ""))})
        if project_sha:
            found[-1]["project_sha256"] = project_sha
        break                                    # one lesson per turn: the first thing that was wrong
    return found


def capture_turn(hh: Path, transcript: str, session: str, project=None, *,
                 events: Optional[list] = None, started: Optional[bool] = None,
                 lock_timeout: float = 30) -> List[dict]:
    """The Stop hook's entry point. A turn can end in more than one Stop (after the harness's own block, the
    model works on and stops again), so the marker names the turn and the lessons already recorded for it, and
    a later Stop of the same turn records only what is new: one fail-then-pass must count once, or a single
    occurrence would pass the "has recurred" rule harness improve depends on."""
    if events is None:
        events, started = _last_turn_info(transcript)
    elif started is None:
        started = True
    # The marker and candidate count form one read-modify-write operation.
    # Serializing only the JSONL replace still counts simultaneous Stops twice.
    with _store_lock(hh, timeout=lock_timeout):
        _recover_capture(hh)
        rows = _capture_turn(hh, transcript, session, project, events, started)
    _prune_capture(hh, lock_timeout)
    return rows


def _prune_capture(hh, lock_timeout):
    try:
        from . import storage
        storage.prune(hh, lock_timeout=lock_timeout)
    except Exception:
        pass


def _capture_turn(hh, transcript, session, project, events, started):
    first = events[0] if events else {}
    turn = "%s:%s" % (transcript, first.get("uuid") or hashlib.sha1(
        json.dumps(first, sort_keys=True).encode()).hexdigest())
    mark = hh / "state" / ("capture-%s" % re.sub(r"[^\w.-]", "_", session or "x"))
    seen = []
    try:
        m = json.loads(mark.read_text(encoding="utf-8"))
        if not started and str(m.get("turn", "")).startswith(transcript + ":"):
            turn = m["turn"]          # the turn's start scrolled out of the window: it is the same turn
        seen = m.get("keys", []) if m.get("turn") == turn else []
    except (OSError, ValueError, AttributeError, KeyError):
        pass
    new = [f for f in candidates(transcript, events, project=project) if f["key"] not in seen]
    state = {"turn": turn, "keys": seen + [f["key"] for f in new]}
    if new:
        return _record(hh, new, checkpoint=(mark.name, state))
    _replace_capture(mark, json.dumps(state).encode('utf-8'))
    return []


def record(hh: Path, found: List[dict], now: Optional[str] = None) -> List[dict]:
    """Merge into the store: a repeat raises the count of the entry it repeats."""
    if not found:
        return []
    with _store_lock(hh):
        _recover_capture(hh)
        return _record(hh, found, now)


def _record(hh, found, now=None, checkpoint=None):
    if not found:
        return []
    now = now or time.strftime("%Y-%m-%dT%H:%M:%S")
    path = hh / STORE
    if path.is_symlink():
        raise ValueError('capture store is redirected')
    original = path.read_bytes() if path.exists() else None
    rows = []
    if original is not None:
        for line in original.decode('utf-8').splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if not isinstance(row, dict):
                raise ValueError('capture candidate row must be an object')
            rows.append(row)
    by_key = {r.get("key"): r for r in rows if r.get("key")}
    for f in found:
        r = by_key.get(f["key"])
        event = f.get("source_event_sha256")
        if r and event and event in r.get("source_events", []):
            continue  # a replayed transcript event is not a second episode
        if r and event and len(r.get("source_events", [])) >= 20:
            continue  # bounded provenance: more repeats need deliberate curation
        if r:
            r["count"] = int(r.get("count", 1)) + 1
            r["last"] = now
            if event:
                r.setdefault("source_events", []).append(event)
            rows.remove(r)
            rows.append(r)                       # most recent last, so pruning drops the stalest first
        else:
            r = dict(f, id=f["key"][:12], count=1, first=now, last=now)
            if event:
                r["source_events"] = [event]
            rows.append(r)
            by_key[f["key"]] = r
    hh.mkdir(parents=True, exist_ok=True)
    data = "".join(json.dumps(r) + "\n" for r in rows)
    if checkpoint is None:
        _replace_capture(path, data.encode('utf-8'))
    else:
        marker, state = checkpoint
        pending = {'schema': 1, 'before': hashlib.sha256(original).hexdigest() if original is not None else None,
                   'data': data, 'marker': marker, 'state': state}
        pending['sha256'] = hashlib.sha256(json.dumps(pending, sort_keys=True).encode()).hexdigest()
        _replace_capture(hh / PENDING, json.dumps(pending).encode('utf-8'))
        _recover_capture(hh)
    return rows
