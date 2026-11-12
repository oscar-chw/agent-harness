"""Freeze a learning campaign before collecting controller-observed experiences.

The bounded controller collects development, drafts from its own observations,
then runs paired trials. Surrounding/native usage is not promotion-qualified.
The OS owner/controller is trusted, as in procedure_execution.
"""
from pathlib import Path
import json
import re
import uuid

from . import procedure_execution as C, procedures as P
from .redact import redact


def _runtime():
    return {**C._runtime(), 'procedure_campaign.py': C._sha(Path(__file__).read_bytes())}


def _table(con):
    if P._READ_ONLY.get():
        con.execute('SELECT 1 FROM procedure_campaign_runs LIMIT 0')
        con.execute('SELECT 1 FROM procedure_campaign_stages LIMIT 0')
        return
    con.execute('CREATE TABLE IF NOT EXISTS procedure_campaign_runs '
                '(campaign_id TEXT PRIMARY KEY,project TEXT,state TEXT,freeze_path TEXT,'
                'freeze_sha256 TEXT,journal TEXT,result TEXT)')
    con.execute('CREATE TABLE IF NOT EXISTS procedure_campaign_stages '
                '(campaign_id TEXT,stage TEXT,payload TEXT,PRIMARY KEY(campaign_id,stage))')


def _inputs(project, oracle, suite, *, raw=None):
    from .launch import _json as strict_json
    spec = strict_json(raw) if raw is not None else C._json(suite)
    if (not isinstance(spec, dict)
            or set(spec) != {'schema', 'cases', 'model', 'effort', 'timeout_seconds'}
            or type(spec['schema']) is not int or spec['schema'] != 1
            or not isinstance(spec['model'], str)
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', spec['model'])
            or spec['effort'] not in ('low', 'medium', 'high', 'xhigh')
            or type(spec['timeout_seconds']) is not int or not 1 <= spec['timeout_seconds'] <= 120
            or not isinstance(spec['cases'], list) or not 4 <= len(spec['cases']) <= C.MAX_CASES):
        raise ValueError('campaign requires a bounded explicit suite, pinned model and effort')
    selected, ids, inputs, normalized = [], set(), set(), set()
    for c in spec['cases']:
        if (not isinstance(c, dict)
                or set(c) != {'task_id', 'class', 'split', 'task_path', 'answer_path'}
                or any(not isinstance(c[k], str) or not c[k].strip() or len(c[k]) > 128
                       for k in ('task_id', 'class'))
                or c['task_id'] in ids or c['split'] not in ('development', 'heldout')):
            raise ValueError('campaign cases must have distinct bounded identities and explicit splits')
        task_path = C._file(project, c['task_path'])
        if oracle in task_path.parents:
            raise ValueError('task evidence must be outside the denied answer directory')
        raw = C._source_read(project, c['task_path'])
        answer_raw = C._source_read(oracle, c['answer_path'])
        task, answer = strict_json(raw), strict_json(answer_raw)
        if (not isinstance(task, dict) or set(task) != {'instruction', 'evidence'}
                or any(not isinstance(v, str) or not v.strip() for v in task.values())
                or len(task['instruction'].encode()) > 4096 or len(task['evidence'].encode()) > 8192
                or redact(raw.decode()) != raw.decode()
                or not isinstance(answer, dict) or not answer or 'source_ids' in answer):
            raise ValueError('campaign supports bounded instruction/evidence and exact object answers only')
        C._prompt(task, None)
        P.encoded(answer)
        task_sha = C._sha(raw)
        task_identity = P.digest(task)
        if task_sha in inputs or task_identity in normalized:
            raise ValueError('campaign inputs overlap even when renamed or reformatted')
        ids.add(c['task_id']); inputs.add(task_sha); normalized.add(task_identity)
        selected.append({**c, 'task_sha256': task_sha, 'task_identity_sha256': task_identity,
                         'answer_sha256': C._sha(answer_raw)})
    if any(sum(c['split'] == split for c in selected) < 2 for split in ('development', 'heldout')):
        raise ValueError('campaign requires two distinct development and two unseen held-out tasks')
    return spec, selected


def prepare(home, project, oracle, suite, *, require_complete_usage=False):
    """Freeze all cases before any model call; caller scores/episodes aren't accepted."""
    if type(require_complete_usage) is not bool:
        raise ValueError('complete usage requires an explicit observer boolean')
    project = Path(P._scope(project))
    oracle = Path(oracle)
    if (not oracle.is_absolute() or oracle.is_symlink() or not oracle.is_dir()
            or project not in oracle.resolve().parents
            or not (oracle.name == 'oracle' or oracle.name.endswith('-oracle'))):
        raise ValueError('campaign requires an explicit project-local denied oracle directory')
    oracle = oracle.resolve(strict=True)
    suite = Path(suite)
    if suite.is_symlink() or oracle not in suite.resolve(strict=True).parents:
        raise ValueError('campaign suite must be inside the denied oracle')
    suite = C._file(oracle, suite.resolve().relative_to(oracle).as_posix())
    raw = C._source_read(oracle, suite.relative_to(oracle).as_posix())
    spec, selected = _inputs(project, oracle, suite, raw=raw)
    # The existing preparer has an 8192-byte evidence cap. Admit it before
    # paying for development that could never enter the next stage.
    _material({'project': str(project), 'oracle': str(oracle), 'cases': selected})
    identity = uuid.uuid4().hex
    frozen = {'schema': 1, 'campaign_id': identity, 'project': str(project),
              'oracle': str(oracle), 'suite_path': str(suite),
              'suite_sha256': C._sha(raw), 'cases': selected,
              'model': spec['model'], 'effort': spec['effort'],
              'timeout_seconds': spec['timeout_seconds'], 'runtime': _runtime(),
              'model_calls_max': 2 * len(selected) + 1, 'controller_retries': 0,
              'require_complete_usage': require_complete_usage,
              'required_dimensions': list(C.QUALITY_DIMENSIONS),
              'scope': 'exact structured output; not general coding/research or efficacy proof'}
    with P._db(home) as con:
        _table(con)
        if con.execute('SELECT count(*) FROM procedure_campaign_runs').fetchone()[0] >= C.MAX_RUNS:
            raise ValueError('campaign storage full; retain evidence deliberately')
        C._storage(oracle)
        path = oracle / ('campaign-' + identity)
        path.mkdir(mode=0o700)
        C._save(path / 'freeze.json', frozen)
        con.execute('INSERT INTO procedure_campaign_runs VALUES (?,?,?,?,?,?,NULL)',
            (identity, str(project), 'PREPARED', str(path / 'freeze.json'),
             C._sha(C._read(path / 'freeze.json')), '[]'))
    return {'campaign_id': identity, 'status': 'PREPARED', 'freeze_path': str(path / 'freeze.json'),
            'model_calls_max': frozen['model_calls_max'], 'promotion': 'NOT_GRANTED'}


def _current(frozen):
    if frozen['runtime'] != _runtime():
        raise ValueError('campaign runtime changed after freeze')
    suite = Path(frozen['suite_path'])
    raw = C._bound(Path(frozen['oracle']), suite.relative_to(frozen['oracle']).as_posix(),
                   frozen['suite_sha256'])
    for c in frozen['cases']:
        for root, name, key in ((Path(frozen['project']), c['task_path'], 'task_sha256'),
                                (Path(frozen['oracle']), c['answer_path'], 'answer_sha256')):
            C._bound(root, name, c[key])
    spec, cases = _inputs(Path(frozen['project']), Path(frozen['oracle']), suite, raw=raw)
    if cases != frozen['cases'] or any(spec[k] != frozen[k] for k in ('model', 'effort', 'timeout_seconds')):
        raise ValueError('campaign input or answer changed after freeze')


def _checkpoint(home, project, identity, journal):
    with P._db(home) as con:
        _table(con)
        row = con.execute('SELECT state FROM procedure_campaign_runs WHERE campaign_id=? AND project=?',
                          (identity, project)).fetchone()
        if row is None or row['state'] != 'DEVELOPMENT_CONSUMED':
            raise ValueError('campaign state changed during development')
        con.execute('UPDATE procedure_campaign_runs SET journal=? WHERE campaign_id=?',
                    (P.encoded(journal).decode(), identity))


def collect_development(home, project, campaign_id):
    """Own two or more fresh baseline experiences; fail/interrupt consumes the stage."""
    project = P._scope(project)
    with P._db(home) as con:
        _table(con)
        row = con.execute('SELECT * FROM procedure_campaign_runs WHERE campaign_id=? AND project=?',
                          (campaign_id, project)).fetchone()
        if row is None or row['state'] != 'PREPARED':
            raise ValueError('campaign state is missing, foreign or already consumed')
        path = Path(row['freeze_path'])
        from .launch import _json as strict_json
        f = strict_json(C._bound(path.parent, path.name, row['freeze_sha256']))
        _current(f)
        con.execute("UPDATE procedure_campaign_runs SET state='DEVELOPMENT_CONSUMED' WHERE campaign_id=?",
                    (campaign_id,))
    journal, experiences, failures = [], [], []
    interrupted = None
    tokens = 0
    for index, c in enumerate(x for x in f['cases'] if x['split'] == 'development'):
        actor = Path(f['oracle']).parent / ('campaign-actor-' + campaign_id + '-' + str(index))
        created = False
        try:
            _current(f)
            C._storage(path.parent)
            actor.mkdir(mode=0o700); created = True
            task_raw = _bound(f, c)
            from .launch import _json as strict_json
            request = C._actor(actor, strict_json(task_raw), None)
            attempt = {'task_id': c['task_id'], 'role': 'development-baseline', 'consumed': True,
                       'request_sha256': P.digest(request)}
            C._save(path.parent / ('development-attempt-' + str(index) + '.json'), attempt)
            journal.append(attempt)
            _checkpoint(home, project, campaign_id, journal)
            native = C._call(actor, request, f)
            observed = path.parent / ('development-native-' + str(index) + '.json')
            C._save(observed, native)
            attempt['native_sha256'] = C._sha(C._read(observed))
            _checkpoint(home, project, campaign_id, journal)
            # Preserve observed counts even when a later grade/source check fails.
            count = P._native_tokens(native)
            attempt['observed_native_tokens'] = count; tokens += count
            _checkpoint(home, project, campaign_id, journal)
            C._request(actor, attempt['request_sha256'], native, f)
            _current(f)
            answer_raw = _bound(f, c, answer=True)
            expected = strict_json(answer_raw)
            grade = C._observe(native, f, expected)
            if not grade['correct']:
                raise ValueError('development did not pass its original frozen answer')
            experience = {'task_id': c['task_id'], 'task_path': c['task_path'],
                'task_sha256': c['task_sha256'], 'correct': True,
                'native_sha256': attempt['native_sha256'], 'artifact_sha256': grade['answer_sha256']}
            C._save(path.parent / ('development-experience-' + str(index) + '.json'), experience)
            experiences.append(experience)
        except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
            failures.append({'task_id': c['task_id'], 'error': redact(str(error))[:512]})
        except (KeyboardInterrupt, SystemExit) as error:
            interrupted = error
            failures.append({'task_id': c['task_id'], 'error': type(error).__name__})
        finally:
            if created and actor.exists():
                actor.rename(path.parent / actor.name)
            try:
                C._storage(path.parent)
            except (ValueError, OSError) as error:
                failures.append({'task_id': c['task_id'], 'error': redact(str(error))[:512]})
        if failures:
            break
    status = 'INTERRUPTED' if interrupted is not None else 'FAILED' if failures else 'DEVELOPMENT_PASSED'
    result = {'campaign_id': campaign_id, 'status': status, 'consumed_calls': len(journal),
              'experiences': experiences, 'attempts': journal, 'failures': failures,
              'observed_native_tokens': tokens, 'unknown_usage_attempts': [a['task_id'] for a in journal
                  if 'observed_native_tokens' not in a], 'usage_complete': False,
              'usage_scope': 'native development counts only; full provider/campaign cost unqualified',
              'promotion': 'NOT_GRANTED'}
    C._save(path.parent / 'development.json', result)
    with P._db(home) as con:
        _table(con)
        con.execute('UPDATE procedure_campaign_runs SET state=?,result=? WHERE campaign_id=? AND project=?',
                    (status, P.encoded(result).decode(), campaign_id, project))
        con.execute('INSERT INTO procedure_campaign_stages VALUES (?,?,?)',
                    (campaign_id, 'development', P.encoded(result).decode()))
    if interrupted is not None:
        raise interrupted
    return result


def _bound(f, case, *, answer=False):
    key, sha, root = (('answer_path', 'answer_sha256', f['oracle']) if answer else
                      ('task_path', 'task_sha256', f['project']))
    return C._bound(Path(root), case[key], case[sha], label='answer' if answer else 'task')


def _load(home, project, identity, state=None):
    project = P._scope(project)
    with P._db(home) as con:
        _table(con)
        row = con.execute('SELECT * FROM procedure_campaign_runs WHERE campaign_id=? AND project=?',
                          (identity, project)).fetchone()
        if row is None or state is not None and row['state'] != state:
            raise ValueError('campaign state is missing, foreign or already consumed')
        row = dict(row)
    path = Path(row['freeze_path'])
    from .launch import _json as strict_json
    f = strict_json(C._bound(path.parent, path.name, row['freeze_sha256']))
    _current(f)
    return row, f, path.parent


def _phase(home, identity, stage):
    from .launch import _json as strict_json
    with P._db(home) as con:
        _table(con)
        row = con.execute('SELECT payload FROM procedure_campaign_stages WHERE campaign_id=? AND stage=?',
                          (identity, stage)).fetchone()
    if row is None:
        raise ValueError('controller-owned campaign stage evidence is missing')
    return strict_json(row['payload'].encode())


def _development(home, row, f, path):
    """Replay grades and exact artifacts; a stored `correct` flag is insufficient."""
    from .launch import _json as strict_json
    result = _phase(home, f['campaign_id'], 'development')
    if (result['status'] != 'DEVELOPMENT_PASSED' or result['failures']
            or P.encoded(C._json(path / 'development.json')) != P.encoded(result)
            or strict_json(row['journal'].encode()) != result['attempts']):
        raise ValueError('controller-bound development evidence changed or did not pass')
    cases = [c for c in f['cases'] if c['split'] == 'development']
    if len(result['attempts']) != len(cases) or result['consumed_calls'] != len(cases):
        raise ValueError('development experience coverage is incomplete')
    observations, experiences, tokens = [], [], 0
    for index, (case, attempt) in enumerate(zip(cases, result['attempts'])):
        native_path = path / ('development-native-' + str(index) + '.json')
        native = strict_json(C._bound(path, native_path.name, attempt.get('native_sha256')))
        actor = path / ('campaign-actor-' + f['campaign_id'] + '-' + str(index))
        request = C._request(actor, attempt['request_sha256'], native, f)
        C._replay_task(actor, attempt, native, f, case, None)
        if C._json(path / ('development-attempt-' + str(index) + '.json')) != {
                k: attempt[k] for k in ('task_id', 'role', 'consumed', 'request_sha256')}:
            raise ValueError('development attempt journal changed')
        if (attempt['task_id'] != case['task_id'] or attempt.get('consumed') is not True
                or P.digest(request) != attempt['request_sha256']
                or native.get('request_sha256') != attempt['request_sha256']):
            raise ValueError('development request evidence changed')
        grade = C._observe(native, f, strict_json(_bound(f, case, answer=True)))
        if not grade['correct']:
            raise ValueError('development experience did not pass replay')
        expected = {'task_id': case['task_id'], 'task_path': case['task_path'],
            'task_sha256': case['task_sha256'], 'correct': True,
            'native_sha256': attempt['native_sha256'], 'artifact_sha256': grade['answer_sha256']}
        if C._json(path / ('development-experience-' + str(index) + '.json')) != expected:
            raise ValueError('development experience artifact changed')
        experiences.append(expected); tokens += grade['tokens']
        observations.append({'task_id': case['task_id'], 'answer': strict_json(native['answer'].encode()),
                             'native_sha256': attempt['native_sha256'],
                             'request_sha256': attempt['request_sha256']})
    if result['experiences'] != experiences or result['observed_native_tokens'] != tokens:
        raise ValueError('development experience or usage summary changed')
    return observations, tokens


def _material(f, observations=None):
    """Exact preparer input; the preflight projection is never saved as experience."""
    from .launch import _json as strict_json
    items = []
    by_id = {x['task_id']: x for x in observations} if observations is not None else None
    for c in (x for x in f['cases'] if x['split'] == 'development'):
        source = by_id[c['task_id']] if by_id is not None else {
            'answer': {**strict_json(_bound(f, c, answer=True)), 'source_ids': ['task-evidence']},
            'native_sha256': '0' * 64, 'request_sha256': '0' * 64}
        body = {'schema': 1, 'kind': 'controller-graded-development', 'task_id': c['task_id'],
                'task_sha256': c['task_sha256'], 'answer': source['answer'],
                'native_sha256': source['native_sha256'], 'request_sha256': source['request_sha256']}
        items.append({'task_id': c['task_id'], 'task': _bound(f, c).decode(),
                      'observation': P.encoded(body).decode()})
    text = json.dumps(items, ensure_ascii=False)
    if len(text.encode()) > 8192 or redact(text) != text:
        raise ValueError('campaign preparation evidence exceeds its 8192-byte budget or contains secrets')
    return items


def _episodes(f, material):
    directory = Path(f['oracle']).parent / ('campaign-sources-' + f['campaign_id'])
    cases = {c['task_id']: c for c in f['cases'] if c['split'] == 'development'}
    return directory, [{'task_id': item['task_id'],
        'path': (directory / ('episode-' + str(i) + '.json')).relative_to(f['project']).as_posix(),
        'sha256': C._sha(item['observation'].encode()),
        'task_path': cases[item['task_id']]['task_path'], 'task_sha256': cases[item['task_id']]['task_sha256']}
        for i, item in enumerate(material)]


def _claim(home, row, f, stage, state):
    with P._db(home) as con:
        _table(con)
        live = con.execute('SELECT * FROM procedure_campaign_runs WHERE campaign_id=? AND project=?',
                           (f['campaign_id'], f['project'])).fetchone()
        if live is None or dict(live) != row:
            raise ValueError('campaign state changed or was already consumed')
        _current(f)
        payload = {'status': state, 'child_run_id': None}
        con.execute('INSERT INTO procedure_campaign_stages VALUES (?,?,?)',
                    (f['campaign_id'], stage, P.encoded(payload).decode()))
        con.execute('UPDATE procedure_campaign_runs SET state=? WHERE campaign_id=?',
                    (state, f['campaign_id']))
    return payload


def _child(home, f, stage, state, payload, child):
    payload['child_run_id'] = child['run_id']
    with P._db(home) as con:
        live = con.execute('SELECT state FROM procedure_campaign_runs WHERE campaign_id=? AND project=?',
                           (f['campaign_id'], f['project'])).fetchone()
        if live is None or live['state'] != state:
            raise ValueError('campaign child identity cannot be pinned after a state change')
        con.execute('UPDATE procedure_campaign_stages SET payload=? WHERE campaign_id=? AND stage=?',
                    (P.encoded(payload).decode(), f['campaign_id'], stage))


def _child_context(child, f):
    frozen = C._json(Path(child['freeze_path']))
    if any(frozen.get(k) != f[k] for k in ('project', 'oracle', 'model', 'effort', 'timeout_seconds')):
        raise ValueError('campaign child context differs from its parent freeze')
    return frozen


def _finish(home, f, path, stage, state, payload, result):
    payload.update(status=result['status'], result=result)
    C._save(path / (stage + '.json'), payload)
    with P._db(home) as con:
        live = con.execute('SELECT state FROM procedure_campaign_runs WHERE campaign_id=? AND project=?',
                           (f['campaign_id'], f['project'])).fetchone()
        if live is None or live['state'] != state:
            raise ValueError('campaign stage changed while running')
        con.execute('UPDATE procedure_campaign_stages SET payload=? WHERE campaign_id=? AND stage=?',
                    (P.encoded(payload).decode(), f['campaign_id'], stage))
        con.execute('UPDATE procedure_campaign_runs SET state=?,result=? WHERE campaign_id=?',
                    (result['status'], P.encoded(result).decode(), f['campaign_id']))
    return result


def _preparation(home, f, path, observations):
    from . import procedure_preparation as S
    stage = _phase(home, f['campaign_id'], 'preparation')
    if stage['status'] != 'DRAFTED_HELD' or C._json(path / 'preparation.json') != stage:
        raise ValueError('controller preparation evidence changed or did not pass')
    result = stage['result']
    with P._db(home) as con:
        payload = P._proposal(con, f['project'], result['procedure_id'])
    observed = S.observed(home, f['project'], stage['child_run_id'], payload)
    _, episodes = _episodes(f, _material(f, observations))
    if (payload['candidate']['episodes'] != episodes
            or observed['native_receipt_sha256'] != result['preparation_native_sha256']):
        raise ValueError('preparation is not derived from the controller-owned development experiences')
    return result, observed


def draft(home, project, campaign_id):
    """Draft from replayed successful experiences; no caller-authored episode input."""
    from . import procedure_preparation as S
    row, f, path = _load(home, project, campaign_id, 'DEVELOPMENT_PASSED')
    observations, tokens = _development(home, row, f, path)
    material = _material(f, observations)
    directory, episodes = _episodes(f, material)
    state = 'PREPARATION_CONSUMED'
    stage = _claim(home, row, f, 'preparation', state)
    interrupted = None
    result = {'campaign_id': campaign_id, 'status': 'FAILED', 'usage_complete': False, 'promotion': 'NOT_GRANTED'}
    try:
        directory.mkdir(mode=0o700)
        for episode, item in zip(episodes, material):
            C._save(Path(f['project']) / episode['path'], json.loads(item['observation']))
        spec = {'schema': 1, 'episodes': [{k: e[k] for k in ('task_id', 'path', 'task_path')} for e in episodes],
                'model': f['model'], 'effort': f['effort'], 'timeout_seconds': f['timeout_seconds']}
        spec_path = path / 'preparation-spec.json'; C._save(spec_path, spec)
        observer = {'require_complete_usage': True} if f.get('require_complete_usage') else {}
        child = S.prepare(home, f['project'], Path(f['oracle']), spec_path, **observer)
        _child(home, f, 'preparation', state, stage, child)
        child_frozen = _child_context(child, f)
        if (child_frozen['episodes'] != episodes
                or child_frozen['specification_sha256'] != P.digest(spec)):
            raise ValueError('preparation episode copy changed before invocation')
        child_result = S.execute(home, f['project'], child['run_id'])
        result.update(preparation_run_id=child['run_id'], observed_role_tokens={'development': tokens,
                      'preparation': child_result['observed_tokens']})
        if child_result['status'] != 'DRAFTED_HELD':
            raise ValueError('native preparation did not produce a valid held draft')
        _current(f); _development(home, row, f, path)
        with P._db(home) as con:
            proposal = P._proposal(con, f['project'], child_result['procedure_id'])
        observed = S.observed(home, f['project'], child['run_id'], proposal)
        if proposal['candidate']['episodes'] != episodes:
            raise ValueError('generated procedure episode binding changed')
        result.update(status='DRAFTED_HELD', procedure_id=proposal['id'],
                      preparation_native_sha256=observed['native_receipt_sha256'])
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
        result['error'] = redact(str(error))[:512]
    except (KeyboardInterrupt, SystemExit) as error:
        interrupted = error; result.update(status='INTERRUPTED', error=type(error).__name__)
    result = _finish(home, f, path, 'preparation', state, stage, result)
    if interrupted is not None:
        raise interrupted
    return result


def evaluate(home, project, campaign_id):
    """Run the frozen pairs after native preparation; complete usage stays held."""
    row, f, path = _load(home, project, campaign_id, 'DRAFTED_HELD')
    observations, development_tokens = _development(home, row, f, path)
    prepared, _ = _preparation(home, f, path, observations)
    state = 'TRIAL_CONSUMED'
    stage = _claim(home, row, f, 'trial', state)
    interrupted = None
    result = {'campaign_id': campaign_id, 'status': 'FAILED', 'usage_complete': False, 'promotion': 'NOT_GRANTED',
              'preparation_run_id': prepared['preparation_run_id'], 'procedure_id': prepared['procedure_id']}
    try:
        observer = {'require_complete_usage': True} if f.get('require_complete_usage') else {}
        child = C.prepare(home, f['project'], prepared['procedure_id'], Path(f['oracle']), Path(f['suite_path']),
                          preparation_run_id=prepared['preparation_run_id'], **observer)
        _child(home, f, 'trial', state, stage, child)
        child_frozen = _child_context(child, f)
        if (child_frozen['cases'] != f['cases'] or child_frozen['suite_sha256'] != f['suite_sha256']
                or child_frozen['procedure_id'] != prepared['procedure_id']):
            raise ValueError('campaign child cases or procedure differ from the parent freeze')
        child_result = C.execute(home, f['project'], child['run_id'])
        result.update(trial_run_id=child['run_id'], status=child_result['status'],
                      observations=child_result['observations'], failures=child_result['failures'],
                      holds=child_result['holds'],
                      observed_role_tokens={'development': development_tokens,
                        'preparation': prepared['observed_role_tokens']['preparation'],
                        'trial_base': child_result['execution_usage']['known_current_baseline_tokens'],
                        'trial_candidate': child_result['execution_usage']['known_current_candidate_tokens']})
        _current(f); _development(home, row, f, path); _preparation(home, f, path, observations)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
        result.update(status='FAILED', error=redact(str(error))[:512])
    except (KeyboardInterrupt, SystemExit) as error:
        interrupted = error; result.update(status='INTERRUPTED', error=type(error).__name__)
    result = _finish(home, f, path, 'trial', state, stage, result)
    if interrupted is not None:
        raise interrupted
    return result


def run(home, project, campaign_id):
    """One bounded state machine, never a repeat-until-green or auto-promotion loop."""
    operations = {'PREPARED': collect_development, 'DEVELOPMENT_PASSED': draft, 'DRAFTED_HELD': evaluate}
    row, _, _ = _load(home, project, campaign_id)
    if row['state'] not in operations:
        raise ValueError('campaign state is already consumed or terminal')
    for _ in range(3):
        result = operations[row['state']](home, project, campaign_id)
        if result['status'] not in operations:
            return result
        row, _, _ = _load(home, project, campaign_id)
    raise ValueError('campaign exceeded its three bounded stages')


def _records(con, project):
    tables = ('procedure_campaign_runs', 'procedure_preparation_runs', 'procedure_execution_runs', 'procedures')
    present = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    records = {name: [dict(r) for r in con.execute('SELECT * FROM ' + name + ' WHERE project=? ORDER BY rowid',
                                                  (project,))] for name in tables if name in present}
    records['stages'] = [dict(r) for r in con.execute(
        'SELECT s.* FROM procedure_campaign_stages s JOIN procedure_campaign_runs c '
        'ON c.campaign_id=s.campaign_id WHERE c.project=? ORDER BY s.rowid', (project,))]
    return records


def _files(records, frozen, payload):
    """Witness the bounded saved evidence across replay and the activation transaction."""
    paths = {}
    for table in ('procedure_campaign_runs', 'procedure_preparation_runs', 'procedure_execution_runs'):
        for row in records.get(table, []):
            root = Path(row['freeze_path']).parent
            C._storage(root)
            for p in root.rglob('*'):
                if p.is_file():
                    paths[p] = (root, p.relative_to(root).as_posix())
    suite = Path(frozen['suite_path'])
    paths[suite] = (Path(frozen['oracle']), suite.relative_to(frozen['oracle']).as_posix())
    for case in frozen['cases']:
        paths[C._file(Path(frozen['project']), case['task_path'])] = (Path(frozen['project']), case['task_path'])
    for episode in payload['candidate']['episodes']:
        paths[C._file(Path(frozen['project']), episode['path'])] = (Path(frozen['project']), episode['path'])
    return {str(p): C._sha(C._source_read(*paths[p])) for p in sorted(paths)}


def _history(records, frozen, run_id):
    """Account all consumed calls sharing canonical development tasks, including failures.

    Deterministic orchestration adds no model calls. Only this controller-owned
    scope can be complete; surrounding chats and general model work are excluded.
    A missing terminal upstream observation leaves the history unknown.
    """
    from .launch import _json as strict_json
    series = sorted(c['task_identity_sha256'] for c in frozen['cases'] if c['split'] == 'development')
    totals = {'base': 0, 'candidate': 0}
    identities, requests, threads, responses = [], set(), set(), set()

    def consume(identity, actor, attempt, native_path, sha, context, *, baseline=False):
        if attempt.get('consumed') is not True or not isinstance(sha, str):
            raise ValueError('history native receipt is missing or changed; usage unknown')
        try:
            native = strict_json(C._bound(native_path.parent, native_path.name, sha))
        except OSError as error:
            raise ValueError('history native receipt is unavailable; usage unknown') from error
        C._request(actor, attempt['request_sha256'], native, context)
        tokens = C._complete_tokens(native, context)
        response_ids = set(native['evaluation_boundary']['provider_usage']['response_id_sha256'])
        if (attempt['request_sha256'] in requests or native['thread_id'] in threads
                or response_ids & responses):
            raise ValueError('history repeats a request, thread or upstream receipt')
        requests.add(attempt['request_sha256'])
        threads.add(native['thread_id'])
        responses.update(response_ids)
        identities.append(identity)
        totals['base' if baseline else 'candidate'] += tokens

    for table in ('procedure_campaign_runs', 'procedure_preparation_runs', 'procedure_execution_runs'):
        for row in records.get(table, []):
            path = Path(row['freeze_path'])
            context = strict_json(C._bound(path.parent, path.name, row['freeze_sha256']))
            development = (context['episodes'] if table == 'procedure_preparation_runs' else
                           [c for c in context['cases'] if c['split'] == 'development'])
            # Derive old receipt identities from their hash-bound source bytes.
            # Formatting changes cannot reset selection-cost history.
            tasks = sorted(P.digest(strict_json(C._bound(Path(context['project']),
                           c['task_path'], c['task_sha256']))) for c in development)
            if tasks != series or row['state'] == 'PREPARED':
                continue
            if row['state'] in ('CONSUMED', 'DEVELOPMENT_CONSUMED', 'PREPARATION_CONSUMED', 'TRIAL_CONSUMED'):
                raise ValueError('relevant history is in progress; terminal complete usage is unknown')
            if table == 'procedure_campaign_runs':
                attempts = strict_json(row['journal'])
                if row['state'] == 'DEVELOPMENT_CONSUMED' and not attempts:
                    raise ValueError('consumed development history has unknown usage')
                for index, attempt in enumerate(attempts):
                    consume((row['campaign_id'], 'development', index),
                        path.parent / ('campaign-actor-' + row['campaign_id'] + '-' + str(index)), attempt,
                        path.parent / ('development-native-' + str(index) + '.json'),
                        attempt.get('native_sha256'), context)
            elif table == 'procedure_preparation_runs':
                if not row['result']:
                    raise ValueError('consumed preparation history has unknown usage')
                result = strict_json(row['result'])
                if C._json(path.parent / 'result.json') != result:
                    raise ValueError('preparation history result changed')
                if result['observed_calls'] == 0:
                    continue
                if result['observed_calls'] != 1:
                    raise ValueError('preparation history call coverage is invalid')
                attempt = C._json(path.parent / 'attempt.json')
                consume((row['run_id'], 'preparation', 0), path.parent / 'actor', attempt,
                        path.parent / 'observed.json', result.get('observed_sha256'), context)
            else:
                if not row['result']:
                    raise ValueError('consumed trial history has unknown usage')
                result = strict_json(row['result'])
                if row['state'] != 'CONSUMED' and C._json(path.parent / 'result.json') != result:
                    raise ValueError('trial history result changed')
                attempts = result.get('execution_attempts')
                if attempts is None or row['state'] == 'CONSUMED' and not attempts:
                    raise ValueError('consumed trial history has unknown usage')
                by_id = {c['task_id']: (i, c) for i, c in enumerate(context['cases'])}
                for ordinal, attempt in enumerate(attempts, 1):
                    index, case = by_id[attempt['case']]
                    actor = path.parent / ('trial-' + row['run_id'] + '-' + str(index) + '-' + attempt['arm'])
                    consume((row['run_id'], 'trial', ordinal), actor, attempt,
                        path.parent / ('native-' + str(ordinal) + '.json'), attempt.get('native_sha256'), context,
                        baseline=(row['run_id'] == run_id and attempt['arm'] == 'base'
                                  and case['split'] == 'heldout'))
    return {**totals, 'attempts': identities, 'usage_complete': True,
            'scope': 'controller-owned campaign history for canonical development tasks only'}


def _admission_inputs(home, project, campaign_id, run_id):
    """Share identical evidence replay between inspection and activation."""
    project = P._scope(project)
    row, frozen, path = _load(home, project, campaign_id, 'GRADED_HELD')
    if not frozen.get('require_complete_usage'):
        raise ValueError('campaign complete usage observer was not frozen')
    if frozen.get('required_dimensions') != list(C.QUALITY_DIMENSIONS):
        raise ValueError('campaign required quality dimensions are missing')
    trial = _phase(home, campaign_id, 'trial')
    if (trial['status'] != 'GRADED_HELD' or trial['child_run_id'] != run_id
            or C._json(path / 'trial.json') != trial
            or P.encoded(trial['result']).decode() != row['result']):
        raise ValueError('trial is missing or belongs to another campaign')
    with P._db(home) as con:
        records = _records(con, project)
        payload = P._proposal(con, project, trial['result']['procedure_id'])
    files = _files(records, frozen, payload)
    observations, _ = _development(home, row, frozen, path)
    prepared, _ = _preparation(home, frozen, path, observations)
    if prepared['procedure_id'] != payload['id']:
        raise ValueError('campaign preparation candidate changed')
    child, pairs = C.replay(home, project, run_id, payload)
    if (any(child.get(k) != frozen[k] for k in
            ('project', 'oracle', 'model', 'effort', 'timeout_seconds', 'cases', 'suite_sha256',
             'require_complete_usage', 'required_dimensions'))
            or child['candidate_preparation_usage']['run_id'] != prepared['preparation_run_id']):
        raise ValueError('trial differs from the frozen campaign or preparation')
    history = _history(records, frozen, run_id)
    pair_tokens = sum(p['cand']['tokens'] for p in pairs)
    context = {'model': frozen['model'], 'effort': frozen['effort'], 'tools_sha256': P.digest('no-tools'),
               'benchmark_sha256': frozen['suite_sha256'], 'budget': frozen['model_calls_max']}
    comparison = {'schema': 1, 'project': project, 'candidate_sha256': payload['sha256'],
                  'comparison': 'without-procedure', 'usage_complete': history['usage_complete'],
                  'context': context, 'base_context': context, 'grader_sha256': P.digest(frozen['runtime']),
                  'pairs': pairs, 'overhead_tokens': history['candidate'] - pair_tokens}
    return {'project': project, 'frozen': frozen, 'payload': payload, 'records': records,
            'files': files, 'comparison': comparison, 'history': history}


def assess(home, project, campaign_id, *, run_id):
    """Replay measured economics without another native call or activation.

    Break-even applies only to the consumed campaign. It is no forecast that
    repetition, a different task distribution or another model will save tokens.
    """
    with P.read_only():
        replay = _admission_inputs(home, project, campaign_id, run_id)
        comparison, history = replay['comparison'], replay['history']
        report = {'campaign_id': campaign_id, 'run_id': run_id,
                  'base_tokens': history['base'], 'candidate_tokens': history['candidate'],
                  'overhead_tokens': comparison['overhead_tokens'],
                  'token_deficit': max(0, history['candidate'] - history['base']),
                  'heldout_pairs': len(comparison['pairs']), 'usage_complete': history['usage_complete'],
                  'scope': history['scope'], 'promotion': 'NOT_GRANTED', 'native_calls_added': 0}
        try:
            P.evaluate(replay['payload'], comparison)
        except ValueError as error:
            report.update(status='HELD', reason=str(error))
        else:
            report['status'] = 'QUALIFIED_UNADOPTED'
        with P._db(home) as con:
            if (_records(con, replay['project']) != replay['records']
                    or _files(replay['records'], replay['frozen'], replay['payload']) != replay['files']):
                raise ValueError('campaign evidence changed during assessment')
            _current(replay['frozen'])
        return report


def adopt(home, project, campaign_id, *, run_id):
    """Replay controller-owned evidence and activate once in a serialized commit."""
    replay = _admission_inputs(home, project, campaign_id, run_id)
    project, frozen, payload = replay['project'], replay['frozen'], replay['payload']
    records, files = replay['records'], replay['files']
    comparison, history = replay['comparison'], replay['history']
    evidence = {**P.evaluate(payload, comparison), 'campaign_id': campaign_id, 'run_id': run_id,
                'comparison': comparison, 'history': history}
    with P._db(home) as con:
        if _records(con, project) != records or _files(records, frozen, payload) != files:
            raise ValueError('campaign evidence changed during adoption')
        _current(frozen)
        P._activate(con, project, payload, evidence)
        con.execute("UPDATE procedure_campaign_runs SET state='ADOPTED' WHERE campaign_id=? AND project=?",
                    (campaign_id, project))
    return {'id': payload['id'], 'status': 'active', 'campaign_id': campaign_id, 'run_id': run_id,
            'usage_complete': True, 'base_tokens': evidence['base_tokens'],
            'candidate_tokens': evidence['candidate_tokens'], 'evidence_sha256': P.digest(evidence)}
