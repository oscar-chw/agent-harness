"""Opt-in advisory project records with immutable revisions and explicit source receipts.

Not a native memory migration, authorization service, or defense against a user rewriting the
whole project. Receipts bind reads to retained evidence; metadata labels do not confer authority.
The verified label requires a direct citation match; other proposed verified claims are retained
as pending until an independent semantic check is available.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .vault_sources import SourceVault, _area, _bytes, _project, _publish, _read, _sha

LAYERS = {"authority": "authority", "project_facts": "fact", "task_state": "task",
          "procedure": "lesson", "knowledge": "knowledge", "evidence": "evidence"}
FIELDS = {"id", "project_id", "layer", "kind", "scope", "text", "provenance", "confidence",
          "sensitivity", "access_boundary", "owner", "freshness"}
GENERATED = {"revision", "created_at", "updated_at", "supersedes"}
CONTRACT = {"id", "project_id", "layer", "kind", "scope", "sensitivity", "access_boundary", "owner"}
RECEIPT_FIELDS = {"project_id", "id", "revision", "sequence", "sha256"}
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
ITEM_LIMIT = 65536


def _validate(item, project_id):
    if not isinstance(item, dict) or set(item) != FIELDS:
        raise ValueError("memory item schema requires all declared fields and no extras")
    if any(not isinstance(item[key], str) or not item[key] for key in FIELDS - {"provenance"}):
        raise ValueError("memory metadata and text must be nonempty strings")
    if item["project_id"] != project_id or not ID.fullmatch(item["id"]):
        raise ValueError("memory identity or project scope is invalid")
    if LAYERS.get(item["layer"]) != item["kind"]:
        raise ValueError("memory layer and kind disagree")
    if item["confidence"] not in ("user_stated", "verified", "inferred", "pending"):
        raise ValueError("unknown evidence classification")
    if item["kind"] == "authority" and item["confidence"] != "user_stated":
        raise ValueError("inferred or model-verified content cannot be authority")
    if item["sensitivity"] not in ("public", "internal", "private"):
        raise ValueError("unknown sensitivity")
    if item["freshness"] not in ("current", "unknown", "expired", "withdrawn"):
        raise ValueError("unknown freshness")
    provenance = item["provenance"]
    if (not isinstance(provenance, list) or not provenance
            or any(not isinstance(p, dict) or set(p) != {"source", "start_line", "end_line"}
                   or not isinstance(p["source"], dict) or type(p["start_line"]) is not int
                   or type(p["end_line"]) is not int or not 1 <= p["start_line"] <= p["end_line"]
                   for p in provenance)):
        raise ValueError("memory provenance needs explicit source receipts and line spans")


def _validate_receipt(receipt, project_id):
    if (not isinstance(receipt, dict) or set(receipt) != RECEIPT_FIELDS
            or receipt["project_id"] != project_id or not isinstance(receipt["id"], str)
            or not ID.fullmatch(receipt["id"])
            or any(type(receipt[key]) is not int or receipt[key] < 1 for key in ("revision", "sequence"))
            or not isinstance(receipt["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", receipt["sha256"])):
        raise ValueError("invalid memory receipt")


def _scope_lists(allowed_sensitivities, allowed_scopes, layers):
    frozen = []
    for values, permitted in ((allowed_sensitivities, {"public", "internal", "private"}),
                              (allowed_scopes, None), (layers, set(LAYERS))):
        if not isinstance(values, list) or len(values) > 100:
            raise ValueError("search needs explicit unique sensitivity, item-scope and layer lists")
        values = values.copy()
        if (len(values) > 100
                or any(not isinstance(v, str) or not v.strip() or len(v) > 512 for v in values)
                or len(values) != len(set(values))
                or (permitted is not None and not set(values) <= permitted)):
            raise ValueError("search needs explicit unique sensitivity, item-scope and layer lists")
        frozen.append(values)
    return frozen


class ProjectMemory:
    def __init__(self, root, project_id, *, max_bytes=16 * 1024 * 1024):
        self.root = Path(root).resolve(strict=True)
        self.project_id = project_id
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("memory storage budget must be positive")
        self.max_bytes = max_bytes
        self._directory()

    def _directory(self):
        if _project(self.root) != self.project_id:
            raise ValueError("project identity does not match the memory root")
        directory = _area(self.root) / "records"
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise ValueError("memory storage boundary is redirected or invalid")
        return directory

    def _load(self):
        events, latest, total, previous = [], {}, 0, None
        for sequence, path in enumerate(sorted(self._directory().glob("*.json")), 1):
            if path.name != f"{sequence:08}.json" or path.is_symlink() or not path.is_file():
                raise ValueError("memory history has a gap or invalid file boundary")
            raw = _read(path, ITEM_LIMIT)
            total += len(raw)
            event = json.loads(raw)
            if (not isinstance(event, dict) or set(event) != {"schema", "sequence", "previous", "item"}
                    or type(event["schema"]) is not int or event["schema"] != 1
                    or type(event["sequence"]) is not int or event["sequence"] != sequence
                    or event["previous"] != previous or _bytes(event) != raw):
                raise ValueError("memory history integrity failure")
            item = event["item"]
            if not isinstance(item, dict) or set(item) != FIELDS | GENERATED:
                raise ValueError("invalid stored memory schema")
            _validate({key: item[key] for key in FIELDS}, self.project_id)
            old = latest.get(item["id"])
            if item["supersedes"] is not None:
                _validate_receipt(item["supersedes"], self.project_id)
            if (type(item["revision"]) is not int or item["revision"] != (old["item"]["revision"] + 1 if old else 1)
                    or item["supersedes"] != (old["receipt"] if old else None)):
                raise ValueError("memory item revision chain is invalid")
            if any(not isinstance(item[key], str) for key in ("created_at", "updated_at")):
                raise ValueError("memory revision timestamps are invalid")
            try:
                created, updated = (datetime.fromisoformat(item[key]) for key in ("created_at", "updated_at"))
            except ValueError:
                # A malformed timestamp can belong to a record outside the query's scope.
                raise ValueError("memory revision timestamps are invalid") from None
            if created.tzinfo is None or updated.tzinfo is None or created > updated:
                raise ValueError("memory revision timestamps are invalid")
            if old and (any(item[key] != old["item"][key] for key in CONTRACT)
                        or item["created_at"] != old["item"]["created_at"]):
                raise ValueError("memory ownership/access contract changed in history")
            receipt = {"project_id": self.project_id, "id": item["id"], "revision": item["revision"],
                       "sequence": sequence, "sha256": _sha(raw)}
            result = {"item": item, "receipt": receipt}
            events.append(result)
            latest[item["id"]] = result
            previous = receipt["sha256"]
        return events, latest, total

    def _resolve_sources(self, item, historical):
        vault = SourceVault(self.root, self.project_id)
        spans = []
        for entry in item["provenance"]:
            spans.append(vault.resolve(entry["source"], start_line=entry["start_line"],
                                       end_line=entry["end_line"], historical=historical)["text"])
        return spans

    def append(self, item, *, expected):
        _validate(item, self.project_id)
        if expected is not None:
            _validate_receipt(expected, self.project_id)
        # Work on a private immutable representation; a caller cannot mutate provenance mid-save.
        item = json.loads(_bytes(item))
        spans = self._resolve_sources(item, historical=False)
        if item["confidence"] == "verified":
            # A source receipt proves the cited bytes exist, not that a paraphrase follows
            # from them. Only an entire cited assertion can retain this label without an
            # independent semantic check. Keep uncertain claims, but mark them pending.
            claim = item["text"].rstrip("\r\n")
            if not all(span.rstrip("\r\n") == claim for span in spans):
                item["confidence"] = "pending"
        for _ in range(8):
            events, latest, total = self._load()
            old = latest.get(item["id"])
            if expected != (old["receipt"] if old else None):
                raise ValueError("memory revision conflict: refresh the current receipt before changing it")
            if old:
                if any(item[key] != old["item"][key] for key in CONTRACT):
                    raise ValueError("correction cannot change the ownership/access contract")
                if item == {key: old["item"][key] for key in FIELDS}:
                    return old["receipt"]
                if old["item"]["freshness"] == "withdrawn":
                    raise ValueError("withdrawal is terminal for this record; a new grant needs new evidence and identity")
            now = datetime.now(timezone.utc).isoformat()
            if old and datetime.fromisoformat(now) < datetime.fromisoformat(old["item"]["updated_at"]):
                raise ValueError("clock precedes the current revision; no correction was stored")
            record = {**item, "revision": old["item"]["revision"] + 1 if old else 1,
                      "created_at": old["item"]["created_at"] if old else now, "updated_at": now,
                      "supersedes": old["receipt"] if old else None}
            sequence = len(events) + 1
            raw = _bytes({"schema": 1, "sequence": sequence,
                          "previous": events[-1]["receipt"]["sha256"] if events else None, "item": record})
            if len(raw) > ITEM_LIMIT or total + len(raw) > self.max_bytes:
                raise ValueError("memory storage budget exceeded; retained facts were not pruned")
            directory = self._directory()
            directory.mkdir(exist_ok=True)
            target = directory / f"{sequence:08}.json"
            try:
                # The sequence slot serializes all commits, including the aggregate byte check.
                # Unrelated writers refresh/retry; an edited same-item receipt conflicts above.
                _publish(target, raw)
            except ValueError:
                if target.is_file() and not target.is_symlink():
                    continue
                raise
            return {"project_id": self.project_id, "id": item["id"], "revision": record["revision"],
                    "sequence": sequence, "sha256": _sha(raw)}
        raise RuntimeError("memory commit busy; no update was accepted for this caller")

    def _visible(self, result, allowed_sensitivities, historical):
        if (not isinstance(allowed_sensitivities, list)
                or any(value not in ("public", "internal", "private") for value in allowed_sensitivities)):
            raise ValueError("explicit sensitivity scope is required")
        if result["item"]["sensitivity"] not in allowed_sensitivities:
            raise PermissionError("memory item is outside the caller's declared scope")
        if result["item"]["freshness"] in ("expired", "withdrawn") and not historical:
            raise ValueError(result["item"]["freshness"] + " memory requires an explicit historical read")
        self._resolve_sources(result["item"], historical=historical)
        return result

    def _selected_receipt(self, receipt, historical):
        receipt = receipt.copy() if isinstance(receipt, dict) else receipt
        _validate_receipt(receipt, self.project_id)
        if type(historical) is not bool:
            raise ValueError("historical must be boolean")
        events, latest, _ = self._load()
        if receipt["sequence"] > len(events) or events[receipt["sequence"] - 1]["receipt"] != receipt:
            raise ValueError("memory receipt does not match retained evidence")
        result = events[receipt["sequence"] - 1]
        if not historical and latest[receipt["id"]]["receipt"] != receipt:
            raise ValueError("superseded memory requires an explicit historical read")
        if historical:
            current = latest[receipt["id"]]
            if current["receipt"] != receipt or current["item"]["freshness"] != "current":
                # Keep superseded words for diagnosis, but a historical receipt
                # must never look like a presently usable fact or old grant.
                status = current["item"]["freshness"]
                return {**result, "current_status": status if status != "current" else "superseded",
                        "usable_for_current_decisions": False}
        return result

    def read(self, receipt, *, allowed_sensitivities, historical=False):
        result = self._selected_receipt(receipt, historical)
        result = self._visible(result, allowed_sensitivities, historical)
        if result["item"]["confidence"] == "pending":
            raise ValueError("pending memory requires an explicit scoped read for review")
        return result

    def read_scoped(self, receipt, *, allowed_sensitivities, allowed_scopes, layers,
                    historical=False, max_bytes=8192):
        """Resolve an exact receipt with caller scope and an explicit current/history label."""
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("budget must be a positive integer")
        sensitivities, scopes, selected_layers = _scope_lists(allowed_sensitivities, allowed_scopes, layers)
        result = self._selected_receipt(receipt, historical)
        item = result["item"]
        if (item["sensitivity"] not in sensitivities or item["scope"] not in scopes
                or item["layer"] not in selected_layers):
            raise PermissionError("memory item is outside the caller's declared scope")
        # Check scope before touching provenance, including historical source snapshots.
        self._visible(result, sensitivities, historical)
        pending = item["confidence"] == "pending"
        packet = {"schema": "harness.project-memory-read/v1",
                  "kind": "pending-memory-data" if pending else "retrieved-memory-data",
                  "project_id": self.project_id, "historical": historical, **result}
        if pending:
            packet["usable_for_current_decisions"] = False
        if len(json.dumps(packet, ensure_ascii=False).encode("utf-8")) > max_bytes:
            raise ValueError("resolved memory and receipt exceed budget")
        return packet

    def latest(self, identity, *, allowed_sensitivities):
        _, latest, _ = self._load()
        if identity not in latest:
            raise KeyError("memory item is not recorded")
        result = self._visible(latest[identity], allowed_sensitivities, False)
        if result["item"]["confidence"] == "pending":
            raise ValueError("pending memory requires an explicit scoped read for review")
        return result

    def recover(self, receipt, *, phase, depends_on_memory, allowed_sensitivities,
                allowed_scopes, layers, verified_receipt=None, max_bytes=8192):
        """Revalidate one recovered dependency using retained state, never caller status.

        This is advisory retrieval, not permission enforcement. The caller must
        already be entitled to the project/scope. Reuse saves repeated emitted
        context; it still checks the current source. No broad history is injected.
        """
        if type(depends_on_memory) is not bool or not isinstance(phase, str):
            raise ValueError("recovery needs an explicit phase and boolean dependency")
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("budget must be a positive integer")
        sensitivities, scopes, selected_layers = _scope_lists(allowed_sensitivities, allowed_scopes, layers)
        if phase not in ("resume", "compact") or not depends_on_memory:
            return {"decision": "SKIP"}
        recovered = self._selected_receipt(receipt, True)
        item = recovered["item"]
        if (item["sensitivity"] not in sensitivities or item["scope"] not in scopes
                or item["layer"] not in selected_layers):
            raise PermissionError("memory item is outside the caller's declared scope")
        if verified_receipt is not None:
            verified = self._selected_receipt(verified_receipt, True)
            if verified["item"]["id"] != item["id"]:
                raise ValueError("verified receipt belongs to a different dependency")
        _, latest, _ = self._load()
        current = latest[item["id"]]
        status = current["item"]["freshness"]
        result = {"decision": "REFUSE_WITHDRAWN" if status == "withdrawn" else "HOLD",
                  "receipt": current["receipt"], "current_status": status}
        if status == "current":
            if current["item"]["confidence"] == "pending":
                # A receipt cannot promote an unreviewed claim to a reusable fact.
                self._visible(self._selected_receipt(current["receipt"], False), sensitivities, False)
                result["reason"] = "pending"
            elif verified_receipt == current["receipt"]:
                # Reuse still validates retained currentness and source bytes,
                # but its output budget need not fit content it won't emit.
                self._visible(self._selected_receipt(current["receipt"], False), sensitivities, False)
                result["decision"] = "REUSE_VERIFIED"
            else:
                record = self.read_scoped(current["receipt"], allowed_sensitivities=sensitivities,
                                          allowed_scopes=scopes, layers=selected_layers, max_bytes=max_bytes)
                result.update(decision="CANDIDATE", record=record)
        if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > max_bytes:
            raise ValueError("recovery packet and complete receipt exceed budget")
        return result

    def _search_matches(self, query, allowed_sensitivities, allowed_scopes, layers):
        from .mcp.kb import BM25, query_terms, tokens

        allowed_sensitivities, allowed_scopes, layers = _scope_lists(allowed_sensitivities, allowed_scopes, layers)
        if not isinstance(query, str) or not query.strip() or len(query) > 512:
            raise ValueError("query must be nonempty and at most 512 characters")
        events, latest, _ = self._load()
        visible = {identity: result for identity, result in latest.items()
                   if result["item"]["sensitivity"] in allowed_sensitivities
                   and result["item"]["scope"] in allowed_scopes and result["item"]["layer"] in layers}
        if sum(len((identity + result["item"]["text"]).encode("utf-8"))
               for identity, result in visible.items()) > 4 * 1024 * 1024:
            raise ValueError("scoped record text exceeds the 4 MiB search budget")
        exact = query.strip() if query.strip() in visible else None
        terms = set(query_terms(query))
        corpus, omitted = [], []
        for identity, result in sorted(visible.items()):
            words = tokens(identity + "\n" + result["item"]["text"])
            matches = identity == exact or (exact is None and terms.intersection(words))
            if result["item"]["freshness"] in ("expired", "withdrawn"):
                if matches:
                    omitted.append({"receipt": result["receipt"], "reason": result["item"]["freshness"]})
            elif result["item"]["confidence"] == "pending":
                if matches:
                    self._visible(result, allowed_sensitivities, False)
                    omitted.append({"receipt": result["receipt"], "reason": "pending"})
            else:
                corpus.append((identity, words))
        if exact is not None:
            ranked = [(exact, 1.0)] if (visible[exact]["item"]["freshness"] not in ("expired", "withdrawn")
                                         and visible[exact]["item"]["confidence"] != "pending") else []
        else:
            ranked = BM25(corpus).search(terms, len(corpus))
            ranked.sort(key=lambda pair: (-pair[1], pair[0]))
        hits = []
        for identity, score in ranked:
            result = self._visible(visible[identity], allowed_sensitivities, False)
            hits.append({**result, "score": round(score, 8)})
        head = {"sequence": len(events), "sha256": events[-1]["receipt"]["sha256"] if events else None}
        scope = {"query": query.strip(), "sensitivities": sorted(allowed_sensitivities),
                 "scopes": sorted(allowed_scopes), "layers": sorted(layers)}
        return hits, omitted, _sha(_bytes(head)), scope

    def search(self, query, *, allowed_sensitivities, allowed_scopes, layers,
               max_results=5, max_bytes=8192):
        """Retrieve advisory current records in an explicit scope, never infer authority.

        Expired and pending matches have receipt-only omissions; stale matching source evidence
        and corrupt history raise. Different matching identities remain separate, even when their text
        disagrees. Scores express lexical overlap, not truth or confidence. No index is persisted.
        """
        if type(max_results) is not int or not 1 <= max_results <= 100:
            raise ValueError("max_results must be an integer from 1 to 100")
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("budget must be a positive integer")
        hits, withheld, _, _ = self._search_matches(query, allowed_sensitivities, allowed_scopes, layers)
        selected = set()

        def packet():
            return {"schema": "harness.project-memory-search/v1", "kind": "retrieved-memory-data",
                    "project_id": self.project_id,
                    "status": "matches" if selected else "omitted" if hits else
                              "unavailable" if withheld else "no_match",
                    "hits": [hit for i, hit in enumerate(hits) if i in selected],
                    "omitted": withheld + [{"receipt": hit["receipt"],
                                           "reason": "limit" if i >= max_results else "budget"}
                                          for i, hit in enumerate(hits) if i not in selected]}

        def fits(result):
            return len(json.dumps(result, ensure_ascii=False).encode("utf-8")) <= max_bytes

        result = packet()
        if not fits(result):
            raise ValueError("budget cannot fit complete memory and omission metadata")
        for i in range(min(len(hits), max_results)):
            selected.add(i)
            candidate = packet()
            if fits(candidate):
                result = candidate
            else:
                selected.remove(i)
        return result

    def search_page(self, query, *, allowed_sensitivities, allowed_scopes, layers,
                    cursor=None, page_size=5, max_bytes=8192):
        """Return bounded pages without listing every remaining receipt in every response.

        Continuations bind the query/scope and observed journal head, not a filesystem path.
        Their digest detects corruption, not deliberate forgery or authorization. All matching
        current sources are still validated on every call; no cross-query cache hides changes.
        """
        if type(page_size) is not int or not 1 <= page_size <= 100:
            raise ValueError("page_size must be an integer from 1 to 100")
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("budget must be a positive integer")
        if cursor is not None:
            if not isinstance(cursor, dict) or len(cursor) != 4:
                raise ValueError("malformed memory cursor")
            cursor = cursor.copy()
            if (set(cursor) != {"schema", "binding", "offset", "sha256"}
                    or type(cursor["schema"]) is not int or cursor["schema"] != 1
                    or type(cursor["offset"]) is not int or cursor["offset"] <= 0
                    or any(not isinstance(cursor[k], str) or not re.fullmatch(r"[0-9a-f]{64}", cursor[k])
                           for k in ("binding", "sha256"))):
                raise ValueError("malformed memory cursor")
        hits, withheld, head, scope = self._search_matches(query, allowed_sensitivities, allowed_scopes, layers)
        binding = _sha(_bytes({"schema": "harness.project-memory-page/v1", "project_id": self.project_id,
                               "head": head, **scope}))
        total = len(hits) + len(withheld)

        def continuation(offset):
            data = {"schema": 1, "binding": binding, "offset": offset}
            return {**data, "sha256": _sha(_bytes(data))}

        start = 0
        if cursor is not None:
            if cursor["offset"] >= total:
                raise ValueError("out-of-range memory cursor")
            if cursor["binding"] != binding:
                raise ValueError("memory cursor is stale or belongs to another query/project/scope")
            if cursor != continuation(cursor["offset"]):
                raise ValueError("memory cursor integrity failure")
            start = cursor["offset"]

        def packet(end, selected, omitted, offset=start):
            result = {"schema": "harness.project-memory-page/v1", "kind": "retrieved-memory-data",
                    "project_id": self.project_id, "binding": binding, "offset": offset,
                    "status": "matches" if selected else
                              "omitted" if any(o["reason"] == "budget" for o in omitted) else
                              "unavailable" if omitted else "no_match",
                    "total_matches": len(hits), "total_expired": sum(e["reason"] == "expired" for e in withheld),
                    "hits": selected, "omitted": omitted, "remaining": total - end,
                    "next_cursor": continuation(end) if end < total else None}
            withdrawn = sum(e["reason"] == "withdrawn" for e in withheld)
            if withdrawn:
                result["total_withdrawn"] = withdrawn
            return result

        def fits(value):
            return len(json.dumps(value, ensure_ascii=False).encode("utf-8")) <= max_bytes

        selected, omitted, end = [], [], start
        result = packet(end, selected, omitted)
        if not fits(result):
            raise ValueError("budget cannot fit the memory page and continuation metadata")
        while end < min(total, start + page_size):
            hit = hits[end] if end < len(hits) else None
            missing = withheld[end - len(hits)] if hit is None else None
            proposed_hits = selected + ([hit] if hit is not None else [])
            proposed_omitted = omitted + ([missing] if missing is not None else [])
            candidate = packet(end + 1, proposed_hits, proposed_omitted)
            if not fits(candidate):
                # A normal entry that fits on its own belongs on the next page, not in an
                # omission. An intrinsically oversized entry needs a handle to make progress.
                if hit is not None and not fits(packet(end + 1, [hit], [], offset=end)):
                    proposed_hits = selected
                    proposed_omitted = omitted + [{"receipt": hit["receipt"], "reason": "budget"}]
                    candidate = packet(end + 1, proposed_hits, proposed_omitted)
                if not fits(candidate):
                    if end == start:
                        raise ValueError("budget cannot fit one memory entry or its retrieval handle")
                    break
            selected, omitted = proposed_hits, proposed_omitted
            end += 1
            result = candidate
        return result
