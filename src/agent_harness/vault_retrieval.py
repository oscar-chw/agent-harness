"""Opt-in scoped search of shared notes. No corpus copy, persistent index, or model call."""
import json
import sqlite3
from contextlib import closing

from .mcp.kb import BM25, fts_query, query_terms, tokens
from .vault_sources import SOURCE_LIMIT, _lines, _shared_text, _unique_object, read_shared_document


def _candidates(documents, query, backend):
    if backend == "lexical":
        return {identity for identity, _ in documents}
    # FTS is a candidate selector over the same normalized tokens, not a different scorer.
    # In-memory construction makes failure/rebuild explicit and keeps shared sources canonical.
    try:
        with closing(sqlite3.connect(":memory:")) as database:
            database.execute("CREATE VIRTUAL TABLE notes USING fts5(id UNINDEXED, body, tokenize='unicode61')")
            database.executemany("INSERT INTO notes VALUES (?, ?)",
                                 [(identity, " ".join(words)) for identity, words in documents])
            return {row[0] for row in database.execute("SELECT id FROM notes WHERE notes MATCH ?",
                                                       (fts_query(query),))}
    except sqlite3.Error as error:
        raise ValueError("FTS5 search failed; no results were substituted") from error


def search_shared_documents(root, *, vault_id, manifest, manifest_sha256, allowed_ids, query,
                            backend="lexical", max_results=5, max_bytes=8192, context_lines=0):
    """Filter approved IDs before reading/scoring; resolve every returned excerpt by its pin.

    Caller-supplied allowed_ids is an explicit scope, not an authentication service. BM25 scores
    express lexical overlap, not answer confidence. A zero-overlap query abstains; missing/stale
    approved evidence is an error. This pilot caps each scope at 100 notes and total text at 4 MiB.
    Opt-in neighbouring lines retain local qualifications; they do not guarantee a complete
    answer. The byte cap admits a whole requested window or records its omission.
    """
    if not isinstance(vault_id, str) or not vault_id.strip():
        raise ValueError("shared vault identity is required")
    if (not isinstance(allowed_ids, list) or len(allowed_ids) > 100
            or any(not isinstance(identity, str) or not identity or len(identity) > 256 for identity in allowed_ids)
            or len(set(allowed_ids)) != len(allowed_ids)):
        raise ValueError("scope must contain at most 100 unique document IDs")
    if not isinstance(query, str) or not query.strip() or len(query) > 512:
        raise ValueError("query must be nonempty and at most 512 characters")
    if backend not in ("lexical", "fts5"):
        raise ValueError("unsupported search backend")
    if type(max_results) is not int or not 1 <= max_results <= 100:
        raise ValueError("max_results must be an integer from 1 to 100")
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError("budget must be a positive integer")
    if type(context_lines) is not int or not 0 <= context_lines <= 8:
        raise ValueError("context_lines must be an integer from 0 to 8")
    catalogue = json.loads(_shared_text(root, manifest, manifest_sha256), object_pairs_hook=_unique_object)
    if (not isinstance(catalogue, dict) or catalogue.get("schema") != "quant-shared-notes/v1"
            or not isinstance(catalogue.get("revision"), str) or not catalogue["revision"]
            or not isinstance(catalogue.get("documents"), list)):
        raise ValueError("invalid shared catalogue schema")
    identities = []
    for doc in catalogue["documents"]:
        if not isinstance(doc, dict) or not isinstance(doc.get("id"), str) or not doc["id"]:
            raise ValueError("invalid catalogue identity")
        identities.append(doc["id"])
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate catalogue document identity")
    if set(allowed_ids) - set(identities):
        raise ValueError("scope includes an unknown document")

    documents, total = {}, 0
    for identity in sorted(allowed_ids):
        document = read_shared_document(root, vault_id=vault_id, manifest=manifest,
                                        manifest_sha256=manifest_sha256, document_id=identity,
                                        max_bytes=2 * SOURCE_LIMIT)
        total += len(document["content"].encode("utf-8"))
        if total > 4 * SOURCE_LIMIT:
            raise ValueError("authorized source text exceeds the 4 MiB search budget")
        documents[identity] = document
    exact = query if query in identities else query.strip() if query.strip() in identities else None
    q = set(query_terms(query))
    if exact is not None:
        # Exact identities are opaque: stopword and minimum-word-length filters cannot erase them.
        # The source was validated above only if this identity belongs to the approved scope.
        ranked = [(exact, 1.0)] if exact in documents else []
    else:
        corpus = [(identity, tokens(doc["title"] + "\n" + doc["content"])) for identity, doc in documents.items()]
        candidates = _candidates(corpus, sorted(q), backend) if q else set()
        ranked = [(identity, score) for identity, score in BM25(corpus).search(q, len(corpus))
                  if identity in candidates]
        ranked.sort(key=lambda pair: (-pair[1], pair[0]))
    hits = []
    for identity, score in ranked:
        document = documents[identity]
        lines = _lines(document["content"])
        number, _ = ((1, lines[0]) if exact is not None else
                           next((number, line) for number, line in enumerate(lines, 1)
                                if q.intersection(tokens(line))))
        start, end = max(1, number - context_lines), min(len(lines), number + context_lines)
        excerpt = "".join(lines[start - 1:end])
        hits.append({"document_id": identity, "title": document["title"], "score": round(score, 8),
                     "text": excerpt, "citation": {**document["citation"], "start_line": start, "end_line": end}})
    selected = set()

    def packet():
        return {"schema": "harness.shared-search/v1", "kind": "retrieved-source-data",
                "vault_id": vault_id, "manifest_sha256": manifest_sha256, "backend": backend,
                "status": "matches" if hits else "no_match",
                "hits": [hit for i, hit in enumerate(hits) if i in selected],
                "omitted": [{"document_id": hit["document_id"], "sha256": hit["citation"]["sha256"],
                             "reason": "limit" if i >= max_results else "budget"}
                            for i, hit in enumerate(hits) if i not in selected]}

    def fits(result):
        return len(json.dumps(result, ensure_ascii=False).encode("utf-8")) <= max_bytes

    result = packet()
    if not fits(result):
        raise ValueError("budget cannot fit complete retrieval and omission metadata")
    for i in range(min(len(hits), max_results)):
        selected.add(i)
        candidate = packet()
        if fits(candidate):
            result = candidate
        else:
            selected.remove(i)
    return result
