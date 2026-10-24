"""Personal, project-scoped procedure candidates, promotion and rollback.

SQLite is the source of truth for this lifecycle; memory search reads active
rows rather than copying them into a second store. Receipts bind a comparison
to a candidate, not to an authenticated evaluator. The caller must supply an
independent evaluator's measurements. This is not proof of model learning,
tenant isolation, or protection against the same OS user rewriting the DB.
"""
import hashlib
import json
import math
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .mcp.state import project_root
from .redact import redact

MAX_BYTES = 65536
MAX_RECORDS = 128
SHA = re.compile(r"[0-9a-f]{64}\Z")


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def read_json(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("procedure input exceeds 64 KiB")
    return json.loads(raw)


def _scope(project):
    if not project or not Path(project).is_absolute() or not Path(project).is_dir():
        raise ValueError("an existing absolute project directory is required")
    return str(project_root(project))


@contextmanager
def _db(home):
    root = Path(home)
    root.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(root / "procedures.sqlite"), timeout=10)
    con.row_factory = sqlite3.Row
    try:
        con.execute("CREATE TABLE IF NOT EXISTS procedures "
                    "(id TEXT PRIMARY KEY, project TEXT, status TEXT, payload TEXT, evidence TEXT)")
        con.execute("CREATE TABLE IF NOT EXISTS procedure_events "
                    "(sequence INTEGER PRIMARY KEY, id TEXT, action TEXT, evidence_sha256 TEXT, at REAL)")
        con.execute("BEGIN IMMEDIATE")
        yield con
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()


def _bound_file(project, name, sha):
    if (not isinstance(name, str) or not name or Path(name).is_absolute()
            or not isinstance(sha, str) or not SHA.fullmatch(sha)):
        raise ValueError("source needs a relative path and SHA-256")
    path = (Path(project) / name).resolve(strict=True)
    if Path(project) not in path.parents:
        raise ValueError("source escapes its project")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES or hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError("source changed or exceeds its bound")


def _episodes(candidate, project):
    episodes = candidate.get("episodes")
    if not isinstance(episodes, list) or not 2 <= len(episodes) <= 20:
        raise ValueError("at least two bounded development episodes are required")
    ids, fingerprints = set(), set()
    for episode in episodes:
        if not isinstance(episode, dict) or set(episode) != {
                "task_id", "path", "sha256", "task_path", "task_sha256"}:
            raise ValueError("episode needs both evidence and canonical task-input file bindings")
        identity, name, sha = (episode[k] for k in ("task_id", "path", "sha256"))
        if (not isinstance(identity, str) or not identity or identity in ids
                or not isinstance(name, str) or Path(name).is_absolute()
                or not isinstance(sha, str) or not SHA.fullmatch(sha)):
            raise ValueError("invalid or duplicate episode identity")
        ids.add(identity)
        _bound_file(project, name, sha)
        _bound_file(project, episode["task_path"], episode["task_sha256"])
        if episode["task_sha256"] in fingerprints:
            raise ValueError("development episodes repeat the same task inputs")
        fingerprints.add(episode["task_sha256"])
    return ids, fingerprints


def draft(home, project, candidate):
    project = _scope(project)
    fields = {"schema", "title", "trigger", "steps", "exceptions", "episodes"}
    if (not isinstance(candidate, dict) or set(candidate) != fields
            or type(candidate["schema"]) is not int or candidate["schema"] != 1):
        raise ValueError("invalid procedure candidate schema")
    for key in ("title", "trigger"):
        if not isinstance(candidate[key], str) or not candidate[key].strip():
            raise ValueError(key + " is required")
    for key in ("steps", "exceptions"):
        if (not isinstance(candidate[key], list) or not 1 <= len(candidate[key]) <= 20
                or any(not isinstance(s, str) or not s.strip() for s in candidate[key])):
            raise ValueError(key + " must name concrete steps or exclusions")
    raw = encoded(candidate)
    if len(raw) > 8000 or redact(raw.decode()) != raw.decode():
        raise ValueError("candidate is too large or contains credential-shaped text")
    _episodes(candidate, project)
    sha = digest({"project": project, "candidate": candidate})
    identity = "pr-" + sha[:24]
    payload = {"id": identity, "project": project, "sha256": sha, "candidate": candidate}
    with _db(home) as con:
        row = con.execute("SELECT * FROM procedures WHERE id=?", (identity,)).fetchone()
        if row:
            return {**json.loads(row["payload"]), "status": row["status"]}
        if con.execute("SELECT count(*) FROM procedures").fetchone()[0] >= MAX_RECORDS:
            raise ValueError("procedure storage is full; archive deliberately, not silently")
        con.execute("INSERT INTO procedures VALUES (?,?,?,?,?)",
                    (identity, project, "proposed", encoded(payload).decode(), None))
        con.execute("INSERT INTO procedure_events(id,action,at) VALUES (?,?,?)",
                    (identity, "proposed", time.time()))
    return {**payload, "status": "proposed"}


def _number(value, *, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError("measurements must be finite nonnegative numbers")
    return value


def evaluate(payload, result):
    """Strict per-case/dimension non-regression AND total tokens <= baseline.

    Whole-campaign overhead includes adaptation, retrieval, review, retries and
    maintenance. Cached input remains part of tokens. Unknown usage is refused.
    Matching metadata cannot certify that an external evaluator actually ran.
    """
    if (not isinstance(result, dict) or type(result.get("schema")) is not int or result.get("schema") != 1
            or result.get("candidate_sha256") != payload["sha256"]
            or result.get("project") != payload["project"]
            or result.get("usage_complete") is not True
            or result.get("comparison") != "without-procedure"):
        raise ValueError("comparison is stale, unscoped or has incomplete usage")
    context = result.get("context")
    if (not isinstance(context, dict)
            or set(context) != {"model", "effort", "tools_sha256", "budget", "benchmark_sha256"}
            or context != result.get("base_context")
            or not all(isinstance(context[k], str) and context[k] for k in ("model", "effort"))):
        raise ValueError("comparison must match model, effort, tools, benchmark and budget")
    _number(context["budget"], positive=True)
    for value in (context["tools_sha256"], context["benchmark_sha256"], result.get("grader_sha256")):
        if not isinstance(value, str) or not SHA.fullmatch(value):
            raise ValueError("comparison requires pinned benchmark, tools and independent grader")
    development, development_inputs = _episodes(payload["candidate"], payload["project"])
    pairs = result.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("no unseen task pairs")
    baseline, candidate = 0, _number(result.get("overhead_tokens"))
    seen, seen_inputs, improvement = set(), set(), False
    for pair in pairs:
        if not isinstance(pair, dict):
            raise ValueError("each comparison pair must be an object")
        identity = pair.get("task_id")
        if (not isinstance(identity, str) or not identity or identity in seen or identity in development
                or pair.get("split") != "heldout" or not isinstance(pair.get("class"), str)
                or not pair["class"]):
            raise ValueError("held-out task identities must be unique and unseen")
        seen.add(identity)
        _bound_file(payload["project"], pair.get("task_path"), pair.get("task_sha256"))
        fingerprint = pair["task_sha256"]
        if fingerprint in development_inputs or fingerprint in seen_inputs:
            raise ValueError("held-out inputs overlap development or another pair, even if renamed")
        seen_inputs.add(fingerprint)
        b, c = pair["base"], pair["cand"]
        bq, cq = b["quality"], c["quality"]
        if not isinstance(bq, dict) or not bq or not isinstance(cq, dict) or bq.keys() != cq.keys():
            raise ValueError("quality dimensions must match")
        for dimension in bq:
            bv, cv = _number(bq[dimension]), _number(cq[dimension])
            if cv < bv:
                raise ValueError("quality regression on " + identity + ":" + dimension)
            improvement |= cv > bv
        baseline += _number(b["tokens"], positive=True)
        candidate += _number(c["tokens"], positive=True)
    _number(baseline, positive=True)
    _number(candidate, positive=True)
    if candidate > baseline:
        raise ValueError("aggregate tokens exceed the baseline")
    if not improvement and candidate >= baseline:
        raise ValueError("no measured quality or token gain")
    return {"pairs": len(pairs), "base_tokens": baseline, "candidate_tokens": candidate,
            "receipt_sha256": digest(result)}


def change(home, project, identity, result=None, *, rollback=False):
    project = _scope(project)
    with _db(home) as con:
        row = con.execute("SELECT * FROM procedures WHERE id=? AND project=?", (identity, project)).fetchone()
        if not row:
            raise ValueError("no procedure in this project")
        payload = json.loads(row["payload"])
        if rollback:
            if row["status"] != "active":
                raise ValueError("only an active procedure can be rolled back")
            status, receipt, evidence = "rolled_back", None, row["evidence"]
        else:
            if row["status"] != "proposed":
                raise ValueError("procedure is already " + row["status"])
            receipt = evaluate(payload, result)
            status, evidence = "active", encoded(result).decode()
        con.execute("UPDATE procedures SET status=?,evidence=? WHERE id=?", (status, evidence, identity))
        con.execute("INSERT INTO procedure_events(id,action,evidence_sha256,at) VALUES (?,?,?,?)",
                    (identity, status, receipt["receipt_sha256"] if receipt else None, time.time()))
    return {"id": identity, "status": status, "evidence": receipt}


def _active(home, project):
    path = Path(home) / "procedures.sqlite"
    if not path.is_file():
        return []
    con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        records = [json.loads(r[0]) for r in con.execute(
            "SELECT payload FROM procedures WHERE project=? AND status='active'", (str(project),))]
    finally:
        con.close()
    return records


def _item(record):
    method = record["candidate"]
    fix = "Advisory procedure %s: %s Exceptions: %s" % (
        record["id"], " ".join(method["steps"]), " ".join(method["exceptions"]))
    return {"id": record["id"], "trigger": method["trigger"], "fix": fix,
            "mistake": "See source episodes in the bound procedure candidate.", "uses": 0,
            "project": record["project"], "sha256": record["sha256"]}


def recover(home, project, ids):
    return {r["id"]: _item(r) for r in _active(home, project) if r["id"] in ids}


def matches(home, project, query, min_score=0.2):
    """Active project procedures only; uses the existing lexical relevance model."""
    from .mcp import kb
    terms = kb.query_terms(query)
    if not terms:
        return []
    out = []
    for record in _active(home, project):
        method = record["candidate"]
        tokens = kb.tokens(method["title"] + " " + method["trigger"])
        score = kb.relevance(terms, tokens, 1, len(tokens), {t: 1 for t in set(tokens)}, doc_coverage=True)
        if score < min_score:
            continue
        out.append((score, _item(record)))
    return sorted(out, key=lambda match: -match[0])


def withdrawn(home, project, recalled_ids):
    """Tell an existing session that previously supplied advice was revoked."""
    path = Path(home) / "procedures.sqlite"
    if not path.is_file():
        return []
    con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        return [r[0] for r in con.execute(
            "SELECT id FROM procedures WHERE project=? AND status='rolled_back'", (str(project),))
                if r[0] in recalled_ids]
    finally:
        con.close()
