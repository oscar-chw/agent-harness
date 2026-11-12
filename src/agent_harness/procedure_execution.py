"""Bounded controller-owned read-only procedure trials; never a promotion receipt.

Only exact structured-output tasks are supported here. Native calls, original
inputs and output grades are recorded; declared episode files aren't treated
as successful experiences. Unmeasured preparation/maintenance remains a HOLD.
The OS owner/controller is trusted; this isn't cryptographic host attestation.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import uuid

from . import procedures as P
from .redact import redact

MAX_CASES = 20
MAX_RUNS = 16
MAX_RUN_BYTES = 8 * 1024 * 1024
MODULES = ('procedure_execution.py', 'procedure_preparation.py', 'procedures.py', 'cli.py',
           'launch.py', 'eval_boundary.py', 'eval_parent.py', 'procedure_campaign.py')
QUALITY_DIMENSIONS = ('correctness', 'citation_integrity', 'no_tools')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read(path):
    raw = P._read_regular(path)
    if not raw or len(raw) > P.MAX_BYTES:
        raise ValueError('execution input is empty or exceeds 64 KiB')
    return raw


def _json(path):
    from .launch import _json as strict_json
    return strict_json(_read(path))


def _storage(root):
    total = 0
    for count, p in enumerate(root.rglob('*')):
        if count >= 4000 or p.is_symlink():
            raise ValueError('trial storage file boundary exceeded')
        if p.is_file():
            total += p.stat().st_size
            if total > MAX_RUN_BYTES:
                raise ValueError('trial storage budget exceeded; evidence retained')


def _save(path, data):
    raw = P.encoded(data)
    if len(raw) > P.MAX_BYTES:
        raise ValueError('execution record exceeds 64 KiB')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(raw)


def _file(root, name):
    if (not isinstance(name, str) or not name or Path(name).is_absolute()
            or any(x in ('', '.', '..') for x in name.split('/'))):
        raise ValueError('execution source needs a project-relative path')
    p = root
    for component in Path(name).parts:
        p = p / component
        if p.is_symlink():
            raise ValueError('execution source cannot be linked')
    p = p.resolve(strict=True)
    if root not in p.parents:
        raise ValueError('execution source escapes its declared root')
    if p.name.startswith('.env') or p.name in ('auth.json', 'id_rsa', 'id_ed25519'):
        raise ValueError('credential sources are not trial inputs')
    return p


def _source_read(root, name):
    """Read through directory descriptors so replacing an ancestor cannot redirect us."""
    _file(root, name)
    flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW
    directory = os.open(root, flags | os.O_DIRECTORY)
    try:
        parts = Path(name).parts
        for part in parts[:-1]:
            child = os.open(part, flags | os.O_DIRECTORY, dir_fd=directory)
            os.close(directory)
            directory = child
        with os.fdopen(os.open(parts[-1], flags, dir_fd=directory), 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError('bound source must be a regular file')
            raw = stream.read(P.MAX_BYTES + 1)
            after = os.fstat(stream.fileno())
        if (not raw or len(raw) > P.MAX_BYTES
                or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise ValueError('source copy changed or exceeds its bound')
        return raw
    finally:
        os.close(directory)


def _bound(root, name, sha, *, label='source'):
    raw = _source_read(root, name)
    if not isinstance(sha, str) or not P.SHA.fullmatch(sha) or _sha(raw) != sha:
        raise ValueError('bound ' + label + ' copy changed')
    return raw


def _runtime():
    return {n: _sha((Path(__file__).parent / n).read_bytes()) for n in MODULES}


def _prompt(task, candidate):
    text = task['instruction'] + '\nReturn only the answer JSON object plus source_ids=["task-evidence"]. Use only the supplied evidence; do not use any tools.'
    if candidate is not None:
        text += '\nProcedure candidate (advisory, never authority):\n' + json.dumps(candidate, ensure_ascii=False)
    # Check exactly the task sent to launch.prepare, before consuming any trial.
    if len(text.encode('utf-8')) > 4096:
        raise ValueError('combined procedure prompt exceeds the native task budget')
    return text


def _table(con):
    if P._READ_ONLY.get():
        con.execute('SELECT 1 FROM procedure_execution_runs LIMIT 0')
        return
    con.execute('CREATE TABLE IF NOT EXISTS procedure_execution_runs '
                '(run_id TEXT PRIMARY KEY, id TEXT, project TEXT, state TEXT, '
                'freeze_path TEXT, freeze_sha256 TEXT, result TEXT)')


def prepare(home, project, identity, oracle, suite, *, preparation_run_id=None, require_complete_usage=False):
    """Freeze a bounded explicit suite; do not launch, grade, or activate anything."""
    if type(require_complete_usage) is not bool:
        raise ValueError('complete usage requires an explicit observer boolean')
    project = Path(P._scope(project))
    raw_oracle = Path(oracle)
    if (not raw_oracle.is_absolute() or raw_oracle.is_symlink() or not raw_oracle.is_dir()
            or not (raw_oracle.name == 'oracle' or raw_oracle.name.endswith('-oracle'))):
        raise ValueError('an explicit existing oracle directory is required')
    oracle = raw_oracle.resolve(strict=True)
    if project not in oracle.parents:
        raise ValueError('oracle must remain inside the authorized project')
    suite = Path(suite)
    if suite.is_symlink() or oracle not in suite.resolve(strict=True).parents:
        raise ValueError('suite and original answers must be under the denied oracle')
    from .launch import _json as strict_json
    suite_raw = _source_read(oracle, suite.relative_to(oracle).as_posix())
    spec = strict_json(suite_raw)
    if not isinstance(spec, dict) or set(spec) != {'schema', 'cases', 'model', 'effort', 'timeout_seconds'} or type(spec['schema']) is not int or spec['schema'] != 1:
        raise ValueError('execution suite needs schema=1, cases, model, effort and timeout_seconds')
    if (not isinstance(spec['model'], str) or not spec['model']
            or spec['effort'] not in ('low', 'medium', 'high', 'xhigh')
            or type(spec['timeout_seconds']) is not int or not 1 <= spec['timeout_seconds'] <= 120):
        raise ValueError('execution needs a pinned model/effort and bounded timeout')
    cases = spec['cases']
    if not isinstance(cases, list) or not 4 <= len(cases) <= MAX_CASES:
        raise ValueError('execution requires 4–20 explicit development/held-out cases')
    with P._db(home) as con:
        _table(con)
        payload = P._proposal(con, str(project), identity)
        P._episodes(payload['candidate'], str(project))
        if con.execute('SELECT count(*) FROM procedure_execution_runs').fetchone()[0] >= MAX_RUNS:
            raise ValueError('trial storage is full; retain evidence and archive deliberately')
    dev = {e['task_id']: e['task_sha256'] for e in payload['candidate']['episodes']}
    selected, ids, inputs, dev_seen, normalized = [], set(), set(), set(), set()
    for c in cases:
        if (not isinstance(c, dict) or set(c) != {'task_id', 'class', 'split', 'task_path', 'answer_path'}
                or not isinstance(c['task_id'], str) or not c['task_id'] or len(c['task_id']) > 128
                or c['task_id'] in ids or not isinstance(c['class'], str) or not c['class']
                or c['split'] not in ('development', 'heldout')):
            raise ValueError('invalid or duplicate execution case')
        task_raw = _source_read(project, c['task_path'])
        answer_raw = _source_read(oracle, c['answer_path'])
        task, answer = strict_json(task_raw), strict_json(answer_raw)
        if (not isinstance(task, dict) or set(task) != {'instruction', 'evidence'}
                or any(not isinstance(v, str) or not v.strip() for v in task.values())
                or len(task['instruction'].encode()) > 4096 or len(task['evidence'].encode()) > 8192
                or redact(task_raw.decode()) != task_raw.decode()
                or not isinstance(answer, dict) or not answer or 'source_ids' in answer):
            raise ValueError('only bounded explicit instruction/evidence and object-answer tasks are supported')
        P.encoded(answer)  # NaN/Infinity cannot be a frozen exact-JSON oracle.
        _prompt(task, {k: payload['candidate'][k] for k in ('title', 'steps', 'exceptions')})
        fingerprint = _sha(task_raw)
        task_identity = P.digest(task)
        if fingerprint in inputs or task_identity in normalized:
            raise ValueError('task inputs repeat, even if renamed or reformatted')
        if c['split'] == 'development':
            if dev.get(c['task_id']) != fingerprint:
                raise ValueError('development case does not match a candidate episode input')
            dev_seen.add(c['task_id'])
        elif c['task_id'] in dev or fingerprint in dev.values():
            raise ValueError('held-out task overlaps development')
        ids.add(c['task_id']); inputs.add(fingerprint); normalized.add(task_identity)
        selected.append({**c, 'task_sha256': fingerprint, 'task_identity_sha256': task_identity,
                         'answer_sha256': _sha(answer_raw)})
    if dev_seen != set(dev) or sum(c['split'] == 'heldout' for c in selected) < 2:
        raise ValueError('all development episodes and at least two unseen cases are required')
    preparation = 'UNKNOWN'
    if preparation_run_id is not None:
        from .procedure_preparation import observed
        preparation = observed(home, str(project), preparation_run_id, payload)
    run_id = uuid.uuid4().hex
    frozen = {'schema': 1, 'run_id': run_id, 'project': str(project), 'procedure_id': identity,
              'candidate_sha256': payload['sha256'], 'oracle': str(oracle), 'cases': selected,
              'suite_path': str(suite.resolve()), 'suite_sha256': _sha(suite_raw),
              'model': spec['model'], 'effort': spec['effort'], 'timeout_seconds': spec['timeout_seconds'],
              'runtime': _runtime(), 'grader': 'exact-json-and-scoped-citation-v1',
              'calls_max': sum(1 if c['split'] == 'development' else 2 for c in selected),
              'automatic_retries': 0, 'candidate_preparation_usage': preparation,
              'require_complete_usage': require_complete_usage,
              'required_dimensions': list(QUALITY_DIMENSIONS),
              'scope': 'read-only structured output, no model tools; not general coding or research quality'}
    path = oracle / ('run-' + run_id)
    with P._db(home) as con:
        _table(con)
        P._proposal(con, str(project), identity)
        if con.execute('SELECT count(*) FROM procedure_execution_runs').fetchone()[0] >= MAX_RUNS:
            raise ValueError('trial storage is full')
        path.mkdir(mode=0o700)
        _save(path / 'freeze.json', frozen)
        con.execute('INSERT INTO procedure_execution_runs VALUES (?,?,?,?,?,?,NULL)',
                    (run_id, identity, str(project), 'PREPARED', str(path / 'freeze.json'),
                     _sha(_read(path / 'freeze.json'))))
    return {'run_id': run_id, 'status': 'PREPARED', 'freeze_path': str(path / 'freeze.json'),
            'calls_max': frozen['calls_max'], 'promotion': 'NOT_GRANTED'}


def _current(project, payload, f, home=None):
    P._episodes(payload['candidate'], project)
    if f['candidate_sha256'] != payload['sha256'] or f['runtime'] != _runtime():
        raise ValueError('candidate or runtime changed after freezing')
    preparation = f.get('candidate_preparation_usage', 'UNKNOWN')
    if preparation != 'UNKNOWN':
        from .procedure_preparation import observed
        if home is None or observed(home, project, preparation['run_id'], payload) != preparation:
            raise ValueError('observed preparation changed after freezing')
    _bound(Path(f['oracle']), Path(f['suite_path']).relative_to(f['oracle']).as_posix(), f['suite_sha256'])
    for c in f['cases']:
        for root, path, key in ((Path(project), c['task_path'], 'task_sha256'),
                                (Path(f['oracle']), c['answer_path'], 'answer_sha256')):
            _bound(root, path, c[key])


def _proposal_current(home, project, payload):
    with P._db(home) as con:
        live = P._proposal(con, project, payload['id'])
        if live != payload:
            raise ValueError('procedure changed during execution')


def _actor(root, task, candidate):
    from .project_memory import ProjectMemory
    from .vault_sources import SourceVault, initialize
    project_id = initialize(root)
    (root / 'evidence.md').write_text(task['evidence'])
    source = SourceVault(root, project_id).capture('evidence.md')
    ref = ProjectMemory(root, project_id).append({'id': 'task-evidence', 'project_id': project_id,
        'layer': 'project_facts', 'kind': 'fact', 'scope': 'trial', 'text': task['evidence'],
        'provenance': [{'source': source, 'start_line': 1, 'end_line': len(task['evidence'].splitlines())}],
        'confidence': 'verified', 'sensitivity': 'internal', 'access_boundary': 'local_user',
        'owner': 'frozen-procedure-trial', 'freshness': 'current'}, expected=None)
    request = {'schema': 'harness.launch/v1', 'project_id': project_id, 'task': _prompt(task, candidate),
               'references': [ref], 'scope': {'allowed_sensitivities': ['internal'],
                  'allowed_scopes': ['trial'], 'layers': ['project_facts']}, 'max_context_bytes': 16384}
    _save(root / 'request.json', request)
    return request


def _invoke(actor, request, oracle, *, model, effort, timeout, require_complete_usage=False):
    # There is no caller-supplied runner, score or grader command in this API.
    from .launch import execute as native_execute, read_answer
    observer = {'eval_provider_usage': True} if require_complete_usage else {}
    r = native_execute(actor, 'request.json', 'native.json', timeout=timeout,
        native_model=model, native_effort=effort, eval_deny_root=oracle,
        eval_enforce_boundary=True, eval_parent_boundary=True, method_policy='existing', **observer)
    r['answer'] = read_answer(actor, r)
    return r


def _call(actor, request, frozen):
    observer = {'require_complete_usage': True} if frozen.get('require_complete_usage') else {}
    return _invoke(actor, request, Path(frozen['oracle']), model=frozen['model'],
                   effort=frozen['effort'], timeout=frozen['timeout_seconds'], **observer)


def _request(actor, request_sha256, native, frozen):
    raw = _bound(actor, 'request.json', request_sha256)
    from .launch import _json as strict_json, prepare as prepare_launch
    request = strict_json(raw)
    if native.get('request_sha256') != request_sha256:
        raise ValueError('native receipt request identity changed')
    if frozen.get('require_complete_usage'):
        prepared = prepare_launch(actor, 'request.json', method_policy='existing')
        if any(native.get(k) != prepared[k] for k in
               ('request_sha256', 'prompt_sha256', 'context_sha256', 'memory_receipts')):
            raise ValueError('native request prompt or context binding changed')
        if native.get('eval_deny_root_sha256') != _sha(frozen['oracle'].encode()):
            raise ValueError('native oracle boundary binding changed')
        _complete_tokens(native, frozen)
    return request


def _complete_tokens(native, frozen):
    """Require terminal upstream observations in addition to native aggregate counts."""
    if not frozen.get('require_complete_usage'):
        raise ValueError('complete upstream usage observer was not frozen')
    tokens = _observed_tokens(native, frozen)
    usage = native['evaluation_boundary'].get('provider_usage', {})
    if not isinstance(usage, dict):
        raise ValueError('upstream usage observation must be an object')
    ids = usage.get('response_id_sha256')
    if (usage.get('status') != 'OBSERVED_UPSTREAM_COMPLETIONS'
            or type(usage.get('responses')) is not int or not 1 <= usage['responses'] <= 64
            or not isinstance(ids, list) or len(ids) != usage['responses']
            or any(not isinstance(i, str) or not P.SHA.fullmatch(i) for i in ids)
            or len(set(ids)) != len(ids)
            or usage.get('scope') != 'fresh native thread upstream completions; not whole-workflow cost'
            or type(native.get('usage_report_count')) is not int or native.get('resumed_from') is not None
            or not isinstance(native.get('thread_id'), str) or not native['thread_id']):
        raise ValueError('complete bound upstream usage observations missing')
    for key in ('input_tokens', 'cached_input_tokens', 'output_tokens'):
        if type(usage.get(key)) is not int or usage[key] != native['usage'][key]:
            raise ValueError('upstream completion counts differ from the terminal receipt')
    for key, limit in (('cache_write_input_tokens', usage['input_tokens'] - usage['cached_input_tokens']),
                       ('reasoning_output_tokens', usage['output_tokens'])):
        if type(usage.get(key)) is not int or not 0 <= usage[key] <= limit:
            raise ValueError('upstream completion subset counts are invalid')
    return tokens


def _observed_tokens(r, f):
    tokens = P._native_tokens(r)
    b = r.get('evaluation_boundary', {})
    if not isinstance(b, dict):
        raise ValueError('native evaluation boundary must be an object')
    ctx = b.get('resolved', {})
    events = r.get('runtime_events', {})
    if not isinstance(ctx, dict) or not isinstance(events, dict):
        raise ValueError('native context and runtime observations must be objects')
    if (r.get('permission_boundary') != 'observed_parent_file_and_command_control'
            or b.get('status') != 'OBSERVED_PARENT_FILE_AND_COMMAND_CONTROL'
            or b.get('mcp_surface') != 'OBSERVED_EMPTY'
            or b.get('usage_boundary') != ('native_upstream_completions_after_terminal_read_barrier'
                if f.get('require_complete_usage') else 'native_total_after_terminal_read_barrier')
            or ctx.get('model') != f['model'] or ctx.get('reasoningEffort') != f['effort']
            or ctx.get('modelProvider') != 'openai' or ctx.get('approvalPolicy') != 'never'
            or events.get('omitted_items') != 0 or not isinstance(events.get('items'), list)
            or any(not isinstance(e, dict) or e.get('item_type') not in
                   ('user_message', 'reasoning', 'agent_message') for e in events['items'])):
        raise ValueError('trial boundary, model, usage or no-tool scope not observed completely')
    answer = r.get('answer')
    if not isinstance(answer, str) or _sha(answer.encode()) != r.get('answer_sha256'):
        raise ValueError('native answer identity is incomplete')
    return tokens


def _native_output(r, f):
    tokens = _observed_tokens(r, f)
    from .launch import _json as strict_json
    output = strict_json(r['answer'])
    if not isinstance(output, dict):
        raise ValueError('native answer must be an object')
    return output, tokens


def _observe(r, f, expected):
    output, tokens = _native_output(r, f)
    wanted = {**expected, 'source_ids': ['task-evidence']}
    return {'correct': P.encoded(output) == P.encoded(wanted), 'tokens': tokens,
            'answer_sha256': r['answer_sha256'], 'native_receipt_sha256': P.digest(r)}


def _replay_task(actor, attempt, native, frozen, case, candidate):
    from .launch import _json as strict_json
    request = _request(actor, attempt['request_sha256'], native, frozen)
    task = strict_json(_bound(Path(frozen['project']), case['task_path'], case['task_sha256']))
    _bound(actor, 'evidence.md', _sha(task['evidence'].encode()))
    if request['task'] != _prompt(task, candidate):
        raise ValueError('saved actual request differs from the frozen task and candidate')
    return request


def replay(home, project, run_id, payload):
    """Reconstruct every actual trial and its grades from controller-owned artifacts."""
    with P._db(home) as con:
        row = con.execute('SELECT * FROM procedure_execution_runs WHERE run_id=? AND project=?',
                          (run_id, project)).fetchone()
    if row is None or row['state'] != 'GRADED_HELD' or row['id'] != payload['id']:
        raise ValueError('complete controller-owned trial is missing')
    path = Path(row['freeze_path'])
    from .launch import _json as strict_json
    frozen = strict_json(_bound(path.parent, path.name, row['freeze_sha256']))
    _current(project, payload, frozen, home)
    result = _json(path.parent / 'result.json')
    if P.encoded(result).decode() != row['result'] or result['failures']:
        raise ValueError('trial results changed or failed')
    expected = []
    for index, case in enumerate(frozen['cases']):
        arms = ['candidate'] if case['split'] == 'development' else (
            ['base', 'candidate'] if index % 2 == 0 else ['candidate', 'base'])
        expected.extend((index, case, arm) for arm in arms)
    attempts = result['execution_attempts']
    if len(attempts) != len(expected) or result['observed_calls'] != len(expected):
        raise ValueError('trial omitted frozen cases or arms')
    observations, pairs = [], {}
    for ordinal, ((index, case, arm), attempt) in enumerate(zip(expected, attempts), 1):
        original = _json(path.parent / ('attempt-' + str(ordinal) + '.json'))
        if (original != {k: attempt[k] for k in ('case', 'arm', 'consumed', 'request_sha256')}
                or attempt['case'] != case['task_id'] or attempt['arm'] != arm
                or attempt['consumed'] is not True):
            raise ValueError('trial attempt does not match the frozen case and arm')
        native_path = path.parent / ('native-' + str(ordinal) + '.json')
        native = strict_json(_bound(path.parent, native_path.name, attempt['native_sha256']))
        actor = path.parent / ('trial-' + run_id + '-' + str(index) + '-' + arm)
        candidate = ({k: payload['candidate'][k] for k in ('title', 'steps', 'exceptions')}
                     if arm == 'candidate' else None)
        _replay_task(actor, attempt, native, frozen, case, candidate)
        answer = strict_json(_bound(Path(frozen['oracle']), case['answer_path'], case['answer_sha256']))
        grade = {**_observe(native, frozen, answer), 'task_id': case['task_id'], 'class': case['class'],
                 'split': case['split'], 'arm': arm}
        if _json(path.parent / ('observed-' + str(ordinal) + '.json')) != {'native': native, 'grade': grade}:
            raise ValueError('saved independent grade changed')
        observations.append(grade)
        if case['split'] == 'development':
            if not grade['correct']:
                raise ValueError('development experience failed replay')
            continue
        output, _ = _native_output(native, frozen)
        if arm == 'candidate' and not grade['correct']:
            raise ValueError('held-out candidate failed required quality dimensions')
        pair = pairs.setdefault(case['task_id'], {k: case[k] for k in
            ('task_id', 'class', 'split', 'task_path', 'task_sha256')})
        pair['base' if arm == 'base' else 'cand'] = {
            'quality': {'correctness': int(P.encoded({k: v for k, v in output.items() if k != 'source_ids'})
                                           == P.encoded(answer)),
                        'citation_integrity': int(output.get('source_ids') == ['task-evidence']), 'no_tools': 1},
            'tokens': _complete_tokens(native, frozen)}
    if observations != result['observations']:
        raise ValueError('trial observation coverage or grades changed')
    return frozen, list(pairs.values())


def _checkpoint(home, project, run_id, attempts):
    # Commit before invocation, then again before any grading/current-source check.
    # A crash must leave either a pinned received receipt or an explicit unknown.
    with P._db(home) as con:
        changed = con.execute("UPDATE procedure_execution_runs SET result=? "
                              "WHERE run_id=? AND project=? AND state='CONSUMED'",
                              (P.encoded({'execution_attempts': attempts}).decode(), run_id, project))
        if changed.rowcount != 1:
            raise ValueError('execution journal lost its consumed run')


def _series(frozen):
    # Changing candidate text, case IDs, suite paths or models cannot erase debt.
    return sorted(c['task_sha256'] for c in frozen['cases'] if c['split'] == 'development')


def _account(home, project, frozen):
    with P._db(home) as con:
        records = con.execute('SELECT * FROM procedure_execution_runs WHERE project=? ORDER BY rowid',
                              (project,)).fetchall()
    if len(records) > MAX_RUNS:
        raise ValueError('execution attempt ledger exceeds its bound')
    current = {'base': 0, 'candidate': 0}
    prior, ids, unknown = 0, [], []
    for record in records:
        path = Path(record['freeze_path'])
        from .launch import _json as strict_json
        other = strict_json(_bound(path.parent, path.name, record['freeze_sha256']))
        if record['state'] == 'PREPARED' or _series(other) != _series(frozen):
            continue
        identity = record['run_id']
        ids.append(identity)
        if not record['result']:
            unknown.append({'run_id': identity, 'call': None})
            continue
        result = strict_json(record['result'])
        if record['state'] != 'CONSUMED' and P.encoded(_json(path.parent / 'result.json')) != P.encoded(result):
            raise ValueError('execution attempt result changed')
        attempts = result.get('execution_attempts')
        if attempts is None:
            # Retained pre-journal runs: only original, DB-bound observed grades
            # can establish known usage. Missing ungraded responses stay unknown.
            attempts = []
            for ordinal in range(1, result['observed_calls'] + 1):
                attempt = _json(path.parent / ('attempt-' + str(ordinal) + '.json'))
                grades = [o for o in result['observations']
                          if (o['task_id'], o['arm']) == (attempt['case'], attempt['arm'])]
                if len(grades) == 1:
                    observed = _json(path.parent / ('observed-' + str(ordinal) + '.json'))
                    if observed['grade'] != grades[0] or P.digest(observed['native']) != grades[0]['native_receipt_sha256']:
                        raise ValueError('prior execution native receipt changed')
                    attempt['legacy_native'] = observed['native']
                attempts.append(attempt)
        if not isinstance(attempts, list) or len(attempts) > other['calls_max']:
            raise ValueError('invalid execution attempt journal')
        for ordinal, attempt in enumerate(attempts, 1):
            if attempt.get('consumed') is not True or attempt.get('arm') not in current:
                raise ValueError('invalid consumed execution attempt')
            native = attempt.get('legacy_native')
            if 'native_sha256' in attempt:
                raw = _bound(path.parent, 'native-' + str(ordinal) + '.json', attempt['native_sha256'])
                native = strict_json(raw)
            try:
                tokens = P._native_tokens(native)
            except (ValueError, TypeError, KeyError):
                unknown.append({'run_id': identity, 'call': ordinal})
                continue
            if identity == frozen['run_id']:
                current[attempt['arm']] += tokens
            else:
                # All earlier experimental arms are selection/retry overhead;
                # they must not inflate this run's paired baseline allowance.
                prior += tokens
    return {'attempt_ids': ids, 'known_prior_tokens': prior,
            'known_current_candidate_tokens': current['candidate'],
            'known_current_baseline_tokens': current['base'], 'unknown_attempts': unknown,
            'scope': 'same canonical development inputs; prior arms charged as candidate selection overhead'}


def execute(home, project, run_id):
    """Consume one frozen suite; record independently computed grades, always HOLD.

    Successful trials aren't accepting learning: the candidate's preparation
    and wider maintenance costs/provenance have not been independently captured.
    """
    project = P._scope(project)
    with P._db(home) as con:
        _table(con)
        row = con.execute('SELECT * FROM procedure_execution_runs WHERE run_id=? AND project=?',
                          (run_id, project)).fetchone()
        if not row or row['state'] != 'PREPARED':
            raise ValueError('execution is missing, already consumed, or belongs to another project')
        path = Path(row['freeze_path'])
        from .launch import _json as strict_json
        f = strict_json(_bound(path.parent, path.name, row['freeze_sha256']))
        payload = P._proposal(con, project, row['id'])
        _current(project, payload, f, home)
        con.execute("UPDATE procedure_execution_runs SET state='CONSUMED',result=? WHERE run_id=?",
                    (P.encoded({'execution_attempts': []}).decode(), run_id))
    _account(home, project, f)  # Reject changed prior evidence before another native call.
    observations, failures, observed_calls = [], [], 0
    attempts = []
    interrupted = None
    preparation = f.get('candidate_preparation_usage', 'UNKNOWN')
    preparation_tokens = preparation['tokens'] if isinstance(preparation, dict) else 0
    for index, c in enumerate(f['cases']):
        arms = ['candidate'] if c['split'] == 'development' else (
            ['base', 'candidate'] if index % 2 == 0 else ['candidate', 'base'])
        for arm in arms:
            actor = Path(f['oracle']).parent / ('trial-' + run_id + '-' + str(index) + '-' + arm)
            created_actor = False
            try:
                _proposal_current(home, project, payload)
                _current(project, payload, f, home)
                _storage(path.parent)
                actor.mkdir(mode=0o700)
                created_actor = True
                from .launch import _json as strict_json
                task = strict_json(_bound(Path(project), c['task_path'], c['task_sha256']))
                candidate = ({k: payload['candidate'][k] for k in ('title', 'steps', 'exceptions')}
                             if arm == 'candidate' else None)
                request = _actor(actor, task, candidate)
                observed_calls += 1
                attempt = {'case': c['task_id'], 'arm': arm, 'consumed': True,
                           'request_sha256': P.digest(request)}
                _save(path.parent / ('attempt-' + str(observed_calls) + '.json'), attempt)
                attempts.append(attempt)
                _checkpoint(home, project, run_id, attempts)
                r = _call(actor, request, f)
                native_path = path.parent / ('native-' + str(observed_calls) + '.json')
                _save(native_path, r)
                attempt['native_sha256'] = _sha(_read(native_path))
                _checkpoint(home, project, run_id, attempts)
                _request(actor, attempt['request_sha256'], r, f)
                _proposal_current(home, project, payload)
                _current(project, payload, f, home)
                expected = strict_json(_bound(Path(f['oracle']), c['answer_path'], c['answer_sha256']))
                observation = {**_observe(r, f, expected), 'task_id': c['task_id'], 'class': c['class'],
                               'split': c['split'], 'arm': arm}
                observations.append(observation)
                _save(path.parent / ('observed-' + str(observed_calls) + '.json'), {'native': r, 'grade': observation})
                if c['split'] == 'development' and not observation['correct']:
                    raise ValueError('development experience did not pass its frozen grader')
            except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
                failures.append({'task_id': c['task_id'], 'arm': arm,
                                 'error': redact(str(error))[:512], 'usage': 'UNKNOWN_UNLESS_OBSERVED'})
            except (KeyboardInterrupt, SystemExit) as error:
                interrupted = error
                failures.append({'task_id': c['task_id'], 'arm': arm,
                                 'error': type(error).__name__, 'usage': 'UNKNOWN_UNLESS_OBSERVED'})
            finally:
                # Keep finished answers away from the next actor; retain, don't delete.
                if created_actor and actor.exists():
                    actor.rename(path.parent / actor.name)
                try:
                    _storage(path.parent)
                except (ValueError, OSError) as error:
                    failures.append({'task_id': c['task_id'], 'arm': arm,
                                     'error': redact(str(error))[:512], 'usage': 'UNKNOWN_UNLESS_OBSERVED'})
            if failures:
                break
        if failures:
            break
    holds = [('wider orchestration, review and maintenance usage/provenance unverified'
              if isinstance(preparation, dict) else
              'candidate preparation and wider maintenance usage/provenance unverified')]
    if isinstance(preparation, dict) and preparation['unknown_attempts']:
        holds.append('preparation attempts have unknown usage; known tokens are only a lower bound')
    execution_usage = _account(home, project, f)
    if execution_usage['unknown_attempts']:
        holds.append('execution attempts have unknown usage; known tokens are only a lower bound')
    holds.extend('held-out ' + o['task_id'] + ' did not pass the frozen grader'
                 for o in observations if o['split'] == 'heldout' and o['arm'] == 'candidate' and not o['correct'])
    result = {'run_id': run_id, 'status': 'INTERRUPTED' if interrupted else 'FAILED' if failures else 'GRADED_HELD',
              'observed_calls': observed_calls, 'observations': observations, 'failures': failures,
              'execution_attempts': attempts, 'execution_usage': execution_usage,
              'known_candidate_tokens_lower_bound': (preparation_tokens + execution_usage['known_prior_tokens']
                                                    + execution_usage['known_current_candidate_tokens']),
              'known_preparation_tokens': preparation_tokens if isinstance(preparation, dict) else 'UNKNOWN',
              'known_baseline_tokens': execution_usage['known_current_baseline_tokens'], 'usage_complete': False,
              'holds': holds,
              'promotion': 'NOT_GRANTED', 'scope': f['scope']}
    _save(path.parent / 'result.json', result)
    with P._db(home) as con:
        _table(con)
        con.execute('UPDATE procedure_execution_runs SET state=?,result=? WHERE run_id=? AND project=?',
                    (result['status'], P.encoded(result).decode(), run_id, project))
    if interrupted is not None:
        raise interrupted
    return result
