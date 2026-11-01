"""Personal, project-scoped procedure candidates, promotion and rollback.

SQLite is the source of truth for this lifecycle; memory search reads active
rows rather than copying them into a second store. A local binder records
frozen inputs, observed artifacts and provider usage, but holds promotion until
actor isolation and evaluator provenance can be verified. This is not proof of
model learning, tenant isolation, or protection against the same OS user.
"""
import hashlib
import json
import math
import os
import re
import sqlite3
import stat
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


def _read_regular(path):
    # A source may change after preparation/stat. Nonblocking open plus fstat
    # refuses a replacement FIFO instead of waiting indefinitely for a writer.
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("procedure source must be a regular file")
        raw = stream.read(MAX_BYTES + 1)
    return raw


def read_json(path):
    raw = _read_regular(Path(path).resolve(strict=True))
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
        con.execute("CREATE TABLE IF NOT EXISTS procedure_frozen_cases "
                    "(id TEXT, task_id TEXT, task_sha256 TEXT, answer_sha256 TEXT, "
                    "PRIMARY KEY(id,task_id))")
        con.execute("CREATE TABLE IF NOT EXISTS procedure_binder_receipts "
                    "(id TEXT, task_id TEXT, receipt TEXT, PRIMARY KEY(id,task_id))")
        con.execute("CREATE TABLE IF NOT EXISTS procedure_corrections "
                    "(old_id TEXT PRIMARY KEY, new_id TEXT UNIQUE, project TEXT, at REAL)")
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
    raw = _read_regular(path)
    if len(raw) > MAX_BYTES or hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError("source changed or exceeds its bound")


def _episodes(candidate, project):
    episodes = candidate.get("episodes")
    if not isinstance(episodes, list) or not 2 <= len(episodes) <= 20:
        raise ValueError("at least two bounded development episodes are required")
    ids, fingerprints, sources = set(), set(), set()
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
        if sha in sources:
            raise ValueError("development episodes repeat the same source evidence")
        sources.add(sha)
        if episode["task_sha256"] in fingerprints:
            raise ValueError("development episodes repeat the same task inputs")
        fingerprints.add(episode["task_sha256"])
    return ids, fingerprints


def _prepared_candidate(project, candidate):
    fields = {"schema", "title", "trigger", "steps", "exceptions", "episodes"}
    if (not isinstance(candidate, dict) or set(candidate) != fields
            or type(candidate["schema"]) is not int or candidate["schema"] != 1):
        raise ValueError("candidate needs schema=1, title, trigger, steps, exceptions, episodes; "
                         "each episode needs task_id, path, sha256, task_path, task_sha256")
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
    return identity, payload


def prepare(project, specification):
    """Bind explicit episode files without saving or activating any method.

    Hashes show which bytes were supplied, not whether the observations are true
    or independent. Draft revalidates them, so preparation cannot bless a later edit.
    """
    project = _scope(project)
    fields = {"schema", "title", "trigger", "steps", "exceptions", "episodes"}
    if not isinstance(specification, dict) or set(specification) != fields:
        raise ValueError("specification needs schema, title, trigger, steps, exceptions, episodes")
    episodes = specification["episodes"]
    if not isinstance(episodes, list) or not 2 <= len(episodes) <= 20:
        raise ValueError("at least two bounded development episodes are required")
    candidate = {**specification, "episodes": []}
    for episode in episodes:
        if not isinstance(episode, dict) or set(episode) != {"task_id", "path", "task_path"}:
            raise ValueError("unbound episode needs task_id, path, task_path only")
        bound = dict(episode)
        for key, hash_key in (("path", "sha256"), ("task_path", "task_sha256")):
            name = episode[key]
            if not isinstance(name, str) or not name or Path(name).is_absolute():
                raise ValueError("episode source needs a project-relative path")
            path = (Path(project) / name).resolve(strict=True)
            if Path(project) not in path.parents or not path.is_file():
                raise ValueError("episode source must be a regular file inside its project")
            raw = _read_regular(path)
            if not raw or len(raw) > MAX_BYTES:
                raise ValueError("episode source must contain 1..65536 bytes")
            bound[hash_key] = hashlib.sha256(raw).hexdigest()
        candidate["episodes"].append(bound)
    _prepared_candidate(project, candidate)
    return candidate


def draft(home, project, candidate):
    project = _scope(project)
    identity, payload = _prepared_candidate(project, candidate)
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


def correct(home, project, old_id, candidate):
    """Withdraw one named method and draft its replacement in one local commit.

    This is a correction of stored advice, not evidence that the replacement
    has passed independent evaluation. A failed validation leaves the old row
    intact so the caller can explicitly roll it back if the draft is not ready.
    """
    project = _scope(project)
    new_id, payload = _prepared_candidate(project, candidate)
    if new_id == old_id:
        raise ValueError("a correction must change the candidate")
    payload = {**payload, "supersedes": old_id}
    with _db(home) as con:
        old = con.execute("SELECT * FROM procedures WHERE id=? AND project=?", (old_id, project)).fetchone()
        if not old:
            raise ValueError("no procedure in this project")
        link = con.execute("SELECT new_id FROM procedure_corrections WHERE old_id=? AND project=?",
                           (old_id, project)).fetchone()
        if link:
            row = con.execute("SELECT * FROM procedures WHERE id=? AND project=?", (new_id, project)).fetchone()
            if link["new_id"] == new_id and old["status"] == "rolled_back" and row \
                    and row["status"] == "proposed" and json.loads(row["payload"]) == payload:
                return {**payload, "status": "proposed"}
            raise ValueError("correction conflicts with an existing replacement")
        if old["status"] not in ("active", "proposed"):
            raise ValueError("only an active or proposed method can be corrected")
        if con.execute("SELECT 1 FROM procedures WHERE id=?", (new_id,)).fetchone():
            raise ValueError("replacement candidate already exists")
        if con.execute("SELECT count(*) FROM procedures").fetchone()[0] >= MAX_RECORDS:
            raise ValueError("procedure storage is full; archive deliberately, not silently")
        con.execute("INSERT INTO procedures VALUES (?,?,?,?,?)",
                    (new_id, project, "proposed", encoded(payload).decode(), None))
        con.execute("UPDATE procedures SET status='rolled_back' WHERE id=? AND project=?", (old_id, project))
        con.execute("INSERT INTO procedure_corrections VALUES (?,?,?,?)",
                    (old_id, new_id, project, time.time()))
        con.execute("INSERT INTO procedure_events(id,action,at) VALUES (?,?,?)",
                    (old_id, "rolled_back", time.time()))
        con.execute("INSERT INTO procedure_events(id,action,at) VALUES (?,?,?)",
                    (new_id, "proposed", time.time()))
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
            raise ValueError("comparison requires pinned benchmark, tools and grader identifiers")
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


def _bytes(value, name):
    if not isinstance(value, bytes) or not value or len(value) > MAX_BYTES:
        raise ValueError(name + " must be nonempty bytes within 64 KiB")
    return hashlib.sha256(value).hexdigest()


def _proposal(con, project, identity):
    row = con.execute("SELECT * FROM procedures WHERE id=? AND project=?", (identity, project)).fetchone()
    if not row or row["status"] != "proposed":
        raise ValueError("a proposed procedure in this project is required")
    return json.loads(row["payload"])


def freeze_case(home, project, identity, task_id, task, answer):
    """Pin a small local task and answer before any artifact is submitted.

    Only hashes are persisted. This does not establish that the actor could not
    read the answer; that requires a separately observed native deny boundary.
    """
    project = _scope(project)
    if not isinstance(task_id, str) or not task_id or len(task_id) > 128:
        raise ValueError("a bounded task id is required")
    task_sha, answer_sha = _bytes(task, "task"), _bytes(answer, "answer")
    with _db(home) as con:
        payload = _proposal(con, project, identity)
        _, development_inputs = _episodes(payload["candidate"], project)
        if task_sha in development_inputs:
            raise ValueError("frozen task overlaps a development input")
        prior = con.execute("SELECT task_sha256,answer_sha256 FROM procedure_frozen_cases "
                            "WHERE id=? AND task_id=?", (identity, task_id)).fetchone()
        if prior:
            if tuple(prior) == (task_sha, answer_sha):
                return {"task_id": task_id, "task_sha256": task_sha, "answer_sha256": answer_sha}
            raise ValueError("frozen task id conflicts with changed task or answer")
        if con.execute("SELECT 1 FROM procedure_frozen_cases WHERE id=? AND task_sha256=?",
                       (identity, task_sha)).fetchone():
            raise ValueError("frozen task input is already registered")
        con.execute("INSERT INTO procedure_frozen_cases VALUES (?,?,?,?)",
                    (identity, task_id, task_sha, answer_sha))
    return {"task_id": task_id, "task_sha256": task_sha, "answer_sha256": answer_sha}


def _native_tokens(receipt):
    if (not isinstance(receipt, dict)
            or receipt.get("native_completion") != "COMPLETED_UNGRADED"
            or receipt.get("usage_scope") != "fresh_thread_total"
            or receipt.get("usage_status") != "PROVIDER_REPORTED"
            or receipt.get("usage_report_count") != 1):
        raise ValueError("complete single-run provider usage receipt is required")
    usage = receipt.get("usage")
    if not isinstance(usage, dict) or any(type(usage.get(k)) is not int or usage[k] < 0
                                            for k in ("input_tokens", "cached_input_tokens", "output_tokens")):
        raise ValueError("provider usage counts are incomplete")
    if usage["cached_input_tokens"] > usage["input_tokens"]:
        raise ValueError("cached input exceeds total input")
    return _number(usage["input_tokens"] + usage["output_tokens"], positive=True)


def bind_hold(home, project, identity, task_id, task, answer,
              base_artifact, candidate_artifact, base_usage, candidate_usage):
    """Compute a content-bound local receipt; never activate from this receipt.

    Exact-byte correctness is a narrow mechanical grader, not general quality.
    The provided native receipts are checked for completeness and hashed, but
    same-user mutation and actor answer isolation are not established here.
    """
    project = _scope(project)
    task_sha, answer_sha = _bytes(task, "task"), _bytes(answer, "answer")
    base_sha = _bytes(base_artifact, "baseline artifact")
    cand_sha = _bytes(candidate_artifact, "candidate artifact")
    base_tokens, cand_tokens = _native_tokens(base_usage), _native_tokens(candidate_usage)
    with _db(home) as con:
        payload = _proposal(con, project, identity)
        frozen = con.execute("SELECT task_sha256,answer_sha256 FROM procedure_frozen_cases "
                             "WHERE id=? AND task_id=?", (identity, task_id)).fetchone()
        if not frozen or (task_sha, answer_sha) != tuple(frozen):
            raise ValueError("frozen task or answer receipt is missing or changed")
        grader = {"version": "exact-bytes-v1",
                  "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        result = {"schema": 1, "project": project, "procedure_id": identity,
                  "candidate_sha256": payload["sha256"], "task_id": task_id,
                  "task_sha256": task_sha, "answer_sha256": answer_sha,
                  "artifacts": {"base_sha256": base_sha, "candidate_sha256": cand_sha},
                  "grader": grader,
                  "quality": {"base": int(base_artifact == answer),
                              "candidate": int(candidate_artifact == answer)},
                  "usage_receipts": {"base_sha256": digest(base_usage),
                                     "candidate_sha256": digest(candidate_usage)},
                  "tokens": {"base": base_tokens, "candidate": cand_tokens},
                  "decision": "HOLD_UNVERIFIED_BOUNDARY",
                  "hold_reason": "actor answer isolation, effective model and receipt provenance unverified"}
        prior = con.execute("SELECT receipt FROM procedure_binder_receipts WHERE id=? AND task_id=?",
                            (identity, task_id)).fetchone()
        if prior:
            if json.loads(prior[0]) == result:
                return result
            raise ValueError("binder receipt conflicts with changed artifact, usage or grader")
        con.execute("INSERT INTO procedure_binder_receipts VALUES (?,?,?)",
                    (identity, task_id, encoded(result).decode()))
    return result


def change(home, project, identity, result=None, *, rollback=False):
    project = _scope(project)
    with _db(home) as con:
        row = con.execute("SELECT * FROM procedures WHERE id=? AND project=?", (identity, project)).fetchone()
        if not row:
            raise ValueError("no procedure in this project")
        if rollback:
            if row["status"] != "active":
                raise ValueError("only an active procedure can be rolled back")
            status, receipt, evidence = "rolled_back", None, row["evidence"]
        else:
            if row["status"] != "proposed":
                raise ValueError("procedure is already " + row["status"])
            # A matching score and grader hash in caller JSON are assertions,
            # not independent evidence. Local binder receipts remain held until
            # native answer isolation and evaluator provenance are established.
            raise ValueError("independent grader receipt and actor isolation are required; "
                             "local binder receipts remain on hold")
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
            "SELECT p.payload FROM procedures p WHERE p.project=? AND p.status='active' "
            "AND EXISTS (SELECT 1 FROM procedure_events e WHERE e.id=p.id "
            "AND e.action='native_verified_active')", (str(project),))]
    finally:
        con.close()
    return records


def _source_current(record):
    try:
        _episodes(record["candidate"], record["project"])
        return True
    except (OSError, ValueError, TypeError, KeyError):
        return False


def inspect(home, project, identity):
    """Show one method's source and promotion status without copying evaluator data."""
    project = _scope(project)
    path = Path(home) / "procedures.sqlite"
    if not path.is_file():
        raise ValueError("no procedure in this project")
    con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        row = con.execute("SELECT payload,status,evidence FROM procedures WHERE id=? AND project=?",
                          (identity, project)).fetchone()
        verified = con.execute("SELECT 1 FROM procedure_events WHERE id=? "
                               "AND action='native_verified_active'", (identity,)).fetchone()
        # Older read-only stores predate the correction table. Viewing one must
        # not turn a safe draft or withdrawal into an unavailable record.
        has_links = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                                "AND name='procedure_corrections'").fetchone()
        replacement = (con.execute("SELECT new_id FROM procedure_corrections WHERE old_id=? AND project=?",
                                   (identity, project)).fetchone() if has_links else None)
    finally:
        con.close()
    if row is None:
        raise ValueError("no procedure in this project")
    payload = json.loads(row[0])
    status = ("held_unverified" if row[1] == "active" and not verified else
              "stale" if row[1] == "active" and not _source_current(payload) else row[1])
    try:
        evidence_sha = digest(json.loads(row[2])) if row[2] else None
    except ValueError:
        raise ValueError("procedure evidence is unreadable") from None
    result = {"id": identity, "project": project, "status": status,
              "candidate": payload["candidate"], "evidence_sha256": evidence_sha}
    if replacement:
        result["superseded_by"] = replacement[0]
    if payload.get("supersedes"):
        result["supersedes"] = payload["supersedes"]
    return result


def list_active(home, project):
    project = _scope(project)
    return [{"name": r["id"], "origin": "qualified-procedure",
             "description": r["candidate"]["title"] + ": " + r["candidate"]["trigger"]}
            for r in _active(home, project) if _source_current(r)]


def _item(record):
    method = record["candidate"]
    fix = "Advisory procedure %s: %s Exceptions: %s" % (
        record["id"], " ".join(method["steps"]), " ".join(method["exceptions"]))
    return {"id": record["id"], "trigger": method["trigger"], "fix": fix,
            "mistake": "See source episodes in the bound procedure candidate.", "uses": 0,
            "project": record["project"], "sha256": record["sha256"]}


def recover(home, project, ids):
    return {r["id"]: _item(r) for r in _active(home, project)
            if r["id"] in ids and _source_current(r)}


def _explicitly_rejected(query, method):
    """A narrow literal stop cue; lexical overlap alone must not undo it."""
    for phrase in (method["title"], method["trigger"]):
        words = re.findall(r"[a-z0-9]+", phrase.lower())
        if not words:
            continue
        target = r"\W+".join(map(re.escape, words))
        cue = r"\b(?:do\s+not|don['’]t|never|avoid)\s+(?:(?:use|apply|run|perform|do)\s+)?(?:the\s+)?"
        if re.search(cue + target + r"\b", query, re.I):
            return True
    return False


def matches(home, project, query, min_score=0.2):
    """Active project procedures only; uses the existing lexical relevance model."""
    from .mcp import kb
    terms = kb.query_terms(query)
    if not terms:
        return []
    out = []
    for record in _active(home, project):
        method = record["candidate"]
        if _explicitly_rejected(query, method):
            continue
        tokens = kb.tokens(method["title"] + " " + method["trigger"])
        score = kb.relevance(terms, tokens, 1, len(tokens), {t: 1 for t in set(tokens)}, doc_coverage=True)
        if score < min_score or not _source_current(record):
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


def stale(home, project, recalled_ids):
    """Previously supplied active advice whose pinned sources no longer match."""
    return [r["id"] for r in _active(home, project)
            if r["id"] in recalled_ids and not _source_current(r)]
