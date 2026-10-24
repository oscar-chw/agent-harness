"""Memory and lessons (self-learning).

Source of truth: one small JSON file per item, human-readable and hand-editable:
    <HARNESS_HOME>/memory/<scope>/<id>.json      scope = "user" | "project"
    <HARNESS_HOME>/lessons/<id>.json
Archived items move to an ``archive/`` subfolder (never deleted). The files are mirrored into a
separate table (+ FTS5 table when available) in the shared ``index.sqlite``, synced by content.

CLI (session-start and per-prompt hooks; both print nothing when there is nothing to say):
    python3 -m agent_harness.mcp.memory digest [--project DIR] [--max-bytes 2048]
    python3 -m agent_harness.mcp.memory recall --session ID [--max-bytes 1200] [--project DIR] < prompt
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from agent_harness.mcp import kb as _kb  # type: ignore
    from agent_harness.mcp.skills import Skills  # type: ignore
    from agent_harness.mcp.state import State, project_root  # type: ignore
else:
    from . import kb as _kb
    from .skills import Skills
    from .state import State, project_root

CAPS = {"memory": 500, "lessons": 200}
SCOPES = ("user", "project")
RECALL_TTL_DAYS = 7
# Relevance threshold on the normalised score (kb.relevance with doc_coverage=True), calibrated on the
# memory fixtures in tests/test_mcp.py (FTS5 and pure-Python give identical scores):
#   unrelated prompts ("write a haiku about autumn leaves", "what is the capital of France")  0.00
#   prompts sharing one generic word ("the second test failed", "update the config file
#     for the server" against facts about tests / servers)                                   0.14-0.15
#   paraphrases ("which port does the staging db listen on?", "set up kaggle auth token",
#     "can you fix the network route on the VPN")                                             0.25-0.29
#   close restatements ("please make the tests pass", "how do I deploy a release")            0.48-0.61
# 0.2 sits in the gap between the second and third rows.
MEM_MIN_SCORE = 0.2
SNAPSHOT_CHARS = 2200     # Hermes' MEMORY.md cap


def _duplicate_key(text: str) -> tuple:
    """Ignore sentence separators, not meaning-bearing words, order or operators.

    Similarity is useful for retrieval but cannot authorize discarding a new fact:
    one negation, number or reversed relationship can change the entire instruction.
    Keep code spans and internal punctuation/case; tolerate initial capitalization.
    """
    parts = re.findall(r"`[^`]*`|\.\d+|\w+(?:[.,]\w+)*|[^\w\s.,]", text.strip())
    if not parts:
        return (text.strip(),)
    first = parts[0].casefold() if parts[0].istitle() else parts[0]
    return (first, *parts[1:])


class Memory:
    def __init__(self, home: Optional[os.PathLike] = None, fts: Optional[bool] = None,
                 caps: Optional[Dict[str, int]] = None, project: Optional[os.PathLike] = None,
                 db_path: Optional[os.PathLike] = None, user_home: Optional[os.PathLike] = None):
        self.home = _kb.harness_home(home)
        # whose ~/.agents/skills the recall reads: the real home in use; next to an explicit harness home in tests
        self.user_home = Path(user_home) if user_home else (Path.home() if home is None else self.home.parent)
        self.fts = _kb.fts5_available() if fts is None else (fts and _kb.fts5_available())
        self.caps = dict(CAPS, **(caps or {}))
        self.project = str(project_root(project))
        self.con = _kb.connect(Path(db_path) if db_path else self.home / "index.sqlite")
        self.con.executescript("""
            CREATE TABLE IF NOT EXISTS mem_items(
                rowid INTEGER PRIMARY KEY, id TEXT UNIQUE, kind TEXT, scope TEXT, project TEXT,
                text TEXT, data TEXT, uses INTEGER, updated REAL, file TEXT, mtime REAL);
        """)
        if self.fts:
            self.con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS mem_fts USING fts5("
                             "text, tags, tokenize='porter unicode61')")
        self.con.commit()

    # ------------------------------------------------------------ files
    def _dir(self, kind: str, scope: str = "user") -> Path:
        return self.home / "memory" / scope if kind == "memory" else self.home / "lessons"

    def _dirs(self):
        for s in SCOPES:
            yield "memory", s, self._dir("memory", s)
        yield "lesson", "", self._dir("lessons")

    @staticmethod
    def _text(kind: str, item: dict) -> str:
        if kind in ("lesson", "procedure"):
            return "%s\n%s\n%s" % (item.get("trigger", ""), item.get("mistake", ""), item.get("fix", ""))
        return item.get("text", "")

    def _write(self, path: Path, item: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(item, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(str(tmp), str(path))

    def sync(self) -> None:
        """Mirror the JSON files into SQLite: (re)index new/changed files, drop vanished ones."""
        c = self.con
        known = {r["file"]: (r["rowid"], json.loads(r["data"]))
                 for r in c.execute("SELECT rowid, file, data FROM mem_items")}
        seen = set()
        for kind, scope, d in self._dirs():
            if not d.is_dir():
                continue
            for f in d.glob("*.json"):
                if is_conflict(f):  # `<id>.conflict-<host>.json` from sync: never an item
                    continue
                key = str(f)
                seen.add(key)
                mt = f.stat().st_mtime
                k = known.get(key)
                try:
                    item = json.loads(f.read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    raise ValueError("cannot read memory source " + f.name) from exc
                # Restores and sync tools can preserve mtime while changing a fact.
                if k and k[1] == item:
                    continue
                self._upsert(kind, scope, item, key, mt, k[0] if k else None)
        for key, (rowid, _) in known.items():
            if key not in seen:
                self._unindex(rowid)
        c.commit()

    def _upsert(self, kind, scope, item, key, mt, rowid) -> None:
        c = self.con
        if rowid is not None:
            self._unindex(rowid)
        old = c.execute("SELECT rowid FROM mem_items WHERE id=?", (item["id"],)).fetchone()
        if old:
            self._unindex(old["rowid"])
        text = self._text(kind, item)
        cur = c.execute(
            "INSERT INTO mem_items(id,kind,scope,project,text,data,uses,updated,file,mtime) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (item["id"], kind, scope, item.get("project", ""), text, json.dumps(item),
             int(item.get("uses", 0)), float(item.get("updated", item.get("created", 0))), key, mt))
        if self.fts:
            c.execute("INSERT INTO mem_fts(rowid,text,tags) VALUES (?,?,?)",
                      (cur.lastrowid, text, " ".join(item.get("tags", []))))

    def _unindex(self, rowid: int) -> None:
        if self.fts:
            self.con.execute("DELETE FROM mem_fts WHERE rowid=?", (rowid,))
        self.con.execute("DELETE FROM mem_items WHERE rowid=?", (rowid,))

    def _load(self, id: str):
        r = self.con.execute("SELECT * FROM mem_items WHERE id=?", (id,)).fetchone()
        if not r:
            return None, None
        return r, json.loads(r["data"])

    def _bump(self, row, item) -> dict:
        item["uses"] = int(item.get("uses", 0)) + 1
        item["updated"] = time.time()
        p = Path(row["file"])
        self._write(p, item)
        self._upsert(row["kind"], row["scope"], item, str(p), p.stat().st_mtime, row["rowid"])
        return item

    # ------------------------------------------------------------ add / dedupe / caps
    def _visible(self, kind: str, scope: Optional[str] = None, a: str = ""):
        """SQL filter + params: this kind; project-scope items only for the current project."""
        if kind == "lesson":
            return "%skind='lesson'" % a, []
        sql = "{a}kind='memory' AND ({a}scope='user' OR {a}project=?)".format(a=a)
        params = [self.project]
        if scope:
            sql += " AND %sscope=?" % a
            params.append(scope)
        return sql, params

    def _add(self, kind: str, scope: str, item: dict) -> dict:
        self.sync()
        text = self._text(kind, item)
        vis, params = self._visible(kind, scope or None)
        for r in self.con.execute("SELECT * FROM mem_items WHERE " + vis, params).fetchall():
            if _duplicate_key(text) == _duplicate_key(r["text"]):
                existing = json.loads(r["data"])
                self._bump(r, existing)
                self.con.commit()
                return {"id": existing["id"], "duplicate": True, "uses": existing["uses"]}
        prefix = "m-" if kind == "memory" else "l-"
        now = time.time()
        item.update({"id": prefix + uuid.uuid4().hex[:12], "created": now, "updated": now, "uses": 0})
        path = self._dir("memory" if kind == "memory" else "lessons", scope or "user") / (item["id"] + ".json")
        self._write(path, item)
        self._upsert(kind, scope, item, str(path), path.stat().st_mtime, None)
        archived = self._enforce_cap(kind, scope)
        self.con.commit()
        return {"id": item["id"], "duplicate": False, "archived": archived}

    def _enforce_cap(self, kind: str, scope: str) -> List[str]:
        """Archive the least-used, oldest items beyond the cap; pinned items go last."""
        cap = self.caps["memory" if kind == "memory" else "lessons"]
        where, params = ("kind='lesson'", []) if kind == "lesson" else ("kind='memory' AND scope=?", [scope])
        rows = self.con.execute("SELECT * FROM mem_items WHERE %s ORDER BY uses ASC, updated ASC" % where,
                                params).fetchall()
        rows.sort(key=lambda r: bool(json.loads(r["data"]).get("pinned")))  # stable: keeps uses/age order
        out = []
        for r in rows[: max(0, len(rows) - cap)]:
            self._archive(r)
            out.append(r["id"])
        return out

    def _archive(self, row, reason: str = "cap") -> None:
        src = Path(row["file"])
        item = json.loads(row["data"])
        item["archived"] = {"at": time.time(), "reason": reason}
        dst = src.parent / "archive" / src.name
        self._write(dst, item)
        if src.exists():
            src.unlink()
        self._unindex(row["rowid"])

    # ------------------------------------------------------------ search
    @staticmethod
    def _toks(row) -> List[str]:
        return _kb.tokens(row["text"] + " " + " ".join(json.loads(row["data"]).get("tags", [])))

    def scored(self, kind: str, query: str, min_score: Optional[float] = None) -> List[Tuple[float, object]]:
        """(score, row) for visible items scoring >= min_score, best first. Does not touch `uses`.

        Corpus statistics come from all visible items of this kind (<= the cap, so cheap); FTS5, when
        present, only narrows the candidates.
        """
        self.sync()
        return self._score_index(kind, query, min_score)

    def _score_index(self, kind, query, min_score=None):
        """Score one kind from the current snapshot without resyncing all files."""
        min_score = MEM_MIN_SCORE if min_score is None else float(min_score)
        qt = _kb.query_terms(query or "")
        if not qt:
            return []
        vis, params = self._visible(kind)
        rows = self.con.execute("SELECT * FROM mem_items WHERE " + vis, params).fetchall()
        if not rows:
            return []
        toks = {r["rowid"]: self._toks(r) for r in rows}
        df: Dict[str, int] = {}
        for t in toks.values():
            for w in set(t):
                df[w] = df.get(w, 0) + 1
        n, avgdl = len(rows), sum(len(t) for t in toks.values()) / float(len(rows))
        cand = rows
        if self.fts:
            hit = {r[0] for r in self.con.execute("SELECT rowid FROM mem_fts WHERE mem_fts MATCH ?",
                                                  (_kb.fts_query(qt.values()),))}
            cand = [r for r in rows if r["rowid"] in hit]
        out = [(_kb.relevance(qt, toks[r["rowid"]], n, avgdl, df, doc_coverage=True), r) for r in cand]
        return sorted((x for x in out if x[0] >= min_score), key=lambda x: -x[0])

    def _search(self, kind: str, query: str, k: int, min_score: Optional[float] = None) -> List[dict]:
        k = max(1, min(int(k), 50))
        out = [self._bump(r, json.loads(r["data"])) for _, r in self.scored(kind, query, min_score)[:k]]
        self.con.commit()
        return out

    # ------------------------------------------------------------ tools
    def mem_add(self, text: str, tags: Sequence[str] = (), scope: str = "user", pin: bool = False) -> dict:
        if scope not in SCOPES:
            raise ValueError("scope must be 'user' or 'project'")
        if not text or not text.strip():
            raise ValueError("text is empty")
        item = {"text": text.strip(), "tags": [str(t) for t in tags], "pinned": bool(pin)}
        if scope == "project":
            item["project"] = self.project
        res = self._add("memory", scope, item)
        if pin and res.get("duplicate"):  # pinning an existing fact pins it
            r, existing = self._load(res["id"])
            if r is not None and not existing.get("pinned"):
                existing["pinned"] = True
                p = Path(r["file"])
                self._write(p, existing)
                self._upsert(r["kind"], r["scope"], existing, str(p), p.stat().st_mtime, r["rowid"])
                self.con.commit()
        return res

    def mem_search(self, query: str, k: int = 5, min_score: Optional[float] = None) -> List[dict]:
        items = self._search("memory", query, k, min_score)
        return [{"id": i["id"], "text": i["text"], "tags": i.get("tags", []), "uses": i["uses"],
                 **({"scope": "project", "project": i["project"]} if i.get("project") else {})}
                for i in items]

    def mem_forget(self, id: str) -> dict:
        """Forgotten items are archived (moved to archive/), never deleted; the index drops them."""
        self.sync()
        r = self.con.execute("SELECT * FROM mem_items WHERE id=?", (id,)).fetchone()
        if not r or (r["kind"] == "memory" and r["scope"] == "project" and r["project"] != self.project):
            return {"ok": False, "error": "no item %r" % id}
        self._archive(r, reason="forgotten")
        self.con.commit()
        return {"ok": True}

    def lesson_add(self, mistake: str, fix: str, trigger: str) -> dict:
        if not (mistake.strip() and fix.strip()):
            raise ValueError("mistake and fix are required")
        return self._add("lesson", "", {"mistake": mistake.strip(), "fix": fix.strip(),
                                        "trigger": trigger.strip(), "project": self.project})

    def lesson_search(self, query: str, k: int = 3, min_score: Optional[float] = None) -> List[dict]:
        from agent_harness.procedures import matches
        hits = [(sc, json.loads(row["data"]), row) for sc, row in self.scored("lesson", query, min_score)]
        hits.extend((sc, item, None) for sc, item in matches(
            self.home, self.project, query, MEM_MIN_SCORE if min_score is None else min_score))
        out = []
        for _, item, row in sorted(hits, key=lambda hit: -hit[0])[:max(1, min(int(k), 50))]:
            if row is not None:
                item = self._bump(row, item)
            out.append({key: item[key] for key in ("id", "trigger", "mistake", "fix", "uses")}
                       | ({"project": item["project"], "sha256": item["sha256"]} if row is None else {}))
        self.con.commit()
        return out

    # ------------------------------------------------------------ session hooks
    def digest(self, max_bytes: int = 2048) -> str:
        """Session-start digest: pinned facts, a one-line count, the open-work pointer. Never bumps uses.

        Only explicitly pinned items are printed; everything else is recalled when relevant."""
        self.sync()
        vis, params = self._visible("memory")
        facts = [json.loads(r["data"]) for r in
                 self.con.execute("SELECT * FROM mem_items WHERE %s ORDER BY updated ASC" % vis, params)]
        n_lessons = self.con.execute("SELECT COUNT(*) FROM mem_items WHERE kind='lesson'").fetchone()[0]
        pinned = [i for i in facts if i.get("pinned") and not i.get("project")]
        pinned += [i for i in facts if i.get("pinned") and i.get("project")]
        st = State(home=self.home, project=self.project).state_path()
        if not facts and not n_lessons and st is None:
            return ""
        lines = ["Memory (harness):\n"]
        for i in pinned:
            lines.append("- %s%s\n" % ("[project] " if i.get("project") else "", _one_line(i["text"])))
        if facts or n_lessons:
            lines.append("%d facts, %d lessons stored; they are recalled when relevant (mem_search, "
                         "lesson_search).\n" % (len(facts), n_lessons))
        if st is not None:
            lines.append("open work: STATE.md saved %s (state_load reads it)\n"
                         % _dt.datetime.fromtimestamp(st.stat().st_mtime).strftime("%Y-%m-%d %H:%M"))
        return _fit(lines, max_bytes)

    def snapshot(self, max_chars: int = SNAPSHOT_CHARS) -> str:
        """Arm memory_snapshot (off by default): the saved facts visible here, most used and newest first, as
        Hermes injects MEMORY.md, frozen once per session; cut at max_chars. Does not bump uses."""
        self.sync()
        vis, params = self._visible("memory")
        rows = self.con.execute("SELECT text FROM mem_items WHERE %s ORDER BY uses DESC, updated DESC" % vis,
                                params).fetchall()
        out, size = [], 0
        for r in rows:
            line = "- %s\n" % _one_line(r["text"])
            if size + len(line) > max_chars:
                break
            out.append(line)
            size += len(line)
        return "".join(out)

    def _recall_path(self, session: str) -> Path:
        sid = re.sub(r"[^A-Za-z0-9_.-]", "_", session)[:120] or "default"
        sid += "-" + hashlib.sha256(json.dumps([self.project, session]).encode()).hexdigest()[:24]
        return self.home / "sessions" / ("recalled-%s.txt" % sid)

    @staticmethod
    def _recalled_id(line):
        prefix, _, digest = line.rpartition(":")
        return prefix if re.fullmatch(r"[0-9a-f]{64}", digest) else line

    def resume_context(self, session: str, max_bytes: int = 1200) -> str:
        """Rehydrate current whole records; reset suppression after context loss.

        Prior content is never recovered from the marker: it contains IDs/hashes
        only. Missing records and over-budget records remain explicit handles.
        """
        self.sync()
        seen_file = self._recall_path(session)
        ids = list(dict.fromkeys(self._recalled_id(line) for line in
                   (seen_file.read_text().splitlines() if seen_file.exists() else [])))
        vis, params = self._visible("memory")
        rows = {r["id"]: r for r in self.con.execute("SELECT * FROM mem_items WHERE " + vis, params)}
        for identity, row in rows.items():
            if json.loads(row["data"]).get("pinned") and identity not in ids:
                ids.append(identity)
        # Legacy lessons were originally global. Replay only those actually
        # supplied to this session, never unrelated lesson contents.
        for row in self.con.execute("SELECT * FROM mem_items WHERE kind='lesson'"):
            if row["id"] in ids:
                rows[row["id"]] = row
        from agent_harness.procedures import recover, stale, withdrawn
        methods = recover(self.home, self.project, ids)
        revoked = set(withdrawn(self.home, self.project, ids))
        outdated = set(stale(self.home, self.project, ids))
        lines, included, omitted = [], [], []
        for identity in ids:
            if identity in rows:
                row = rows[identity]
                item = json.loads(row["data"])
                line = "- %s: %s\n" % (identity, self._text(row["kind"], item))
            elif identity in methods:
                line = "- %s: when %s -> %s\n" % (
                    identity, methods[identity]["trigger"], methods[identity]["fix"])
            elif identity in revoked:
                line = "- %s: withdrawn; do not rely on that advice.\n" % identity
            elif identity in outdated:
                line = "- %s: source stale; do not rely on that advice.\n" % identity
            elif identity.startswith("skill:"):
                line = "- %s: use skill_manage view %s to reload the current method.\n" % (
                    identity, identity.removeprefix("skill:"))
            else:
                line = "- %s: prior context unavailable; retrieve and verify before reuse.\n" % identity
            if len(("".join(lines) + line).encode()) > max_bytes:
                omitted.append(identity)
            else:
                lines.append(line)
                included.append(identity)
        if omitted:
            def notice():
                return "- omitted %d records (%s); use mem_search/lesson_search/skill_manage.\n" % (
                    len(omitted), ", ".join(omitted[:2]))
            while lines and len(("".join(lines) + notice()).encode()) > max_bytes:
                lines.pop()
                omitted.insert(0, included.pop())
            message = notice()
            if len(message.encode()) > max_bytes:
                raise ValueError("recovery budget cannot include omission handles")
            lines.append(message)
        if ids:
            seen_file.parent.mkdir(parents=True, exist_ok=True)
            # Keep identity provenance for repeated recovery/rollback notices,
            # but remove delivery hashes so the next prompt may supply content.
            seen_file.write_text("".join(identity + "\n" for identity in ids), encoding="utf-8")
        return "".join(lines)

    def recall(self, prompt: str, session: str, max_bytes: int = 1200,
               min_score: Optional[float] = None) -> str:
        """Memories and lessons relevant to `prompt`, most relevant first, within max_bytes, skipping
        unchanged records already recalled in this project/session. Empty when irrelevant.
        Over-budget records get an explicit omission instead of a partial instruction."""
        sdir = self.home / "sessions"
        sdir.mkdir(parents=True, exist_ok=True)
        cutoff = time.time() - RECALL_TTL_DAYS * 86400
        for f in sdir.glob("recalled-*.txt"):
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink()
            except OSError:
                pass
        seen_f = self._recall_path(session)
        previous = seen_f.read_text(encoding="utf-8").splitlines() if seen_f.exists() else []
        latest = {self._recalled_id(line): line for line in previous}
        seen = set(latest.values())

        def recall_key(row):
            if row["kind"] == "skill":
                content = [row["name"], row["description"]]
            else:
                item = json.loads(row["data"])
                content = [row["kind"], row["scope"], row["project"],
                           self._text(row["kind"], item), item.get("tags", [])]
            digest = hashlib.sha256(json.dumps(content, ensure_ascii=False).encode()).hexdigest()
            return row["id"] + ":" + digest

        self.sync()  # One coherent source snapshot for both record kinds.
        hits = [(sc, r) for kind in ("memory", "lesson") for sc, r in self._score_index(kind, prompt, min_score)
                if recall_key(r) not in seen]
        tracked = {identity for identity in latest if re.fullmatch(r"[ml]-[0-9a-f]{12}", identity)}
        if tracked:
            vis, params = self._visible("memory")
            active = {row[0] for row in self.con.execute("SELECT id FROM mem_items WHERE " + vis, params)}
            active.update(row[0] for row in self.con.execute("SELECT id FROM mem_items WHERE kind='lesson'"))
            for identity in sorted(tracked - active):
                row = {"kind": "notice", "id": identity, "scope": "project", "project": self.project,
                       "data": json.dumps({"text": "Previously recalled memory %s is no longer active; "
                                           "do not rely on that advice." % identity})}
                if recall_key(row) not in seen:
                    hits.append((float("inf"), row))
        from agent_harness.procedures import matches, stale, withdrawn
        for identity in withdrawn(self.home, self.project, set(latest)):
            row = {"kind": "notice", "id": identity, "scope": "project", "project": self.project,
                   "data": json.dumps({"text": "Previously recalled procedure %s is withdrawn; "
                                       "do not rely on that advice." % identity})}
            if recall_key(row) not in seen:
                hits.append((float("inf"), row))
        for identity in stale(self.home, self.project, set(latest)):
            row = {"kind": "notice", "id": identity, "scope": "project", "project": self.project,
                   "data": json.dumps({"text": "Previously recalled procedure %s has stale source evidence; "
                                       "do not rely on that advice." % identity})}
            if recall_key(row) not in seen:
                hits.append((float("inf"), row))
        for score, item in matches(self.home, self.project, prompt,
                                   MEM_MIN_SCORE if min_score is None else min_score):
            row = {"kind": "procedure", "id": item["id"], "scope": "project", "project": self.project,
                   "data": json.dumps(item)}
            if recall_key(row) not in seen:
                hits.append((score, row))
        # learned skills: Claude Code does not list ~/.agents/skills, so a relevant one is named here
        try:
            for sc, n, d in Skills(home=self.home, user_home=self.user_home).scored(prompt):
                row = {"id": "skill:" + n, "kind": "skill", "name": n, "description": d}
                if recall_key(row) not in seen:
                    hits.append((sc, row))
        except OSError:
            pass
        hits.sort(key=lambda x: -x[0])
        if not hits:
            return ""
        lines, used, omitted = ["Recalled from harness memory (relevant to this prompt):\n"], [], []
        size = len(lines[0].encode("utf-8"))
        for _, r in hits:
            if r["kind"] == "skill":
                line = "- learned skill %s: %s (skill_manage view %s)\n" % (r["name"], _one_line(r["description"], 200),
                                                                          r["name"])
                b = len(line.encode("utf-8"))
                if size + b <= max_bytes:
                    lines.append(line)
                    size += b
                    used.append(r)
                else:
                    omitted.append(r)
                continue
            i = json.loads(r["data"])
            if r["kind"] in ("lesson", "procedure"):
                line = "- lesson: when %s -> %s (mistake was: %s)\n" % (
                    i.get("trigger", "") or "relevant", i["fix"], i["mistake"])
            else:
                line = "- %s\n" % i["text"]
            b = len(line.encode("utf-8"))
            if size + b > max_bytes:
                omitted.append(r)
                continue
            lines.append(line)
            size += b
            used.append(r)
        if omitted:
            def omission_notice():
                return "- omitted %d (%s); retrieve with mem_search/lesson_search/skill_manage.\n" % (
                    len(omitted), ", ".join(r["id"] for r in omitted[:2]))

            # Reserve room for honest omission evidence instead of filling the
            # packet with matches and then silently dropping its qualifications.
            notice = omission_notice()
            while used and size + len(notice.encode()) > max_bytes:
                omitted.insert(0, used.pop())
                size -= len(lines.pop().encode())
                notice = omission_notice()
            if size + len(notice.encode()) > max_bytes:
                notice = "- omitted %d; use mem_search/lesson_search.\n" % len(omitted)
            if size + len(notice.encode()) > max_bytes:
                raise ValueError("recall budget cannot include omission notice")
            lines.append(notice)
        if not used and not omitted:
            return ""
        for r in used:
            if r["kind"] not in ("skill", "procedure", "notice"):
                self._bump(r, json.loads(r["data"]))
        self.con.commit()
        for r in used:
            latest[r['id']] = recall_key(r)
        seen_f.write_text("".join(line + "\n" for line in latest.values()), encoding="utf-8")
        return "".join(lines)

    def close(self) -> None:
        self.con.close()


def is_conflict(path: Path) -> bool:
    return ".conflict-" in path.name


def _one_line(text: str, limit: int = 300) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    return t if len(t) <= limit else t[: limit - 1] + "…"


def _fit(lines: List[str], max_bytes: int) -> str:
    """Join lines in order, stopping before the byte cap is exceeded (a hard cap)."""
    out, size = [], 0
    for line in lines:
        b = len(line.encode("utf-8"))
        if size + b > max_bytes:
            break
        out.append(line)
        size += b
    return "".join(out) if len(out) > 1 else ""


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m agent_harness.mcp.memory")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("digest", help="session-start digest (pinned facts, counts, open work)")
    d.add_argument("--project", default="")
    d.add_argument("--max-bytes", type=int, default=2048)
    r = sub.add_parser("recall", help="relevant memories/lessons for the prompt on stdin")
    r.add_argument("--session", required=True)
    r.add_argument("--project", default="")
    r.add_argument("--max-bytes", type=int, default=1200)
    a = ap.parse_args(argv)
    m = Memory(project=a.project or None)
    try:
        if a.cmd == "digest":
            out = m.digest(a.max_bytes)
        else:
            out = m.recall(sys.stdin.read(), a.session, a.max_bytes)
    finally:
        m.close()
    if out:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
