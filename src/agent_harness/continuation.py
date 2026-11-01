"""Explicit local operator interface; caller-supplied scope labels are not authentication.

No default store, native identity inference, legacy fallback or permission change.
The host must supply an authorized scope file before handing a worker this command.
"""
import json
from pathlib import Path
import re
import sys

from .scoped_state import Conflict, MAX_TEXT_BYTES, Scope, ScopedState


def _unique(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError("duplicate scope field")
        data[key] = value
    return data


def _scope(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("scope must be an explicit regular JSON file")
    with path.open("rb") as handle:
        raw = handle.read(4097)
    if len(raw) > 4096:
        raise ValueError("scope file exceeds 4096 bytes")
    try:
        data = json.loads(raw, object_pairs_hook=_unique)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("scope file must contain UTF-8 JSON") from error
    if not isinstance(data, dict) or set(data) != {"tenant", "user", "project", "chat", "agent"}:
        raise ValueError("scope requires exactly tenant, user, project, chat and agent")
    return Scope(**data)


def add_parser(sub):
    parser = sub.add_parser("continuation", help="explicit local scoped notes; does not replace native/MCP memory")
    parser.add_argument("action", choices=["load", "save", "clear", "share", "revoke", "read-shared"])
    parser.add_argument("--store-root", required=True, help="explicit authorized store; no default or migration")
    parser.add_argument("--scope-file", required=True, help="host-authorized five-field scope JSON; labels are not authentication")
    parser.add_argument("--expected", help="exact receipt from load, required for every mutation")
    parser.add_argument("--peer-scope-file", help="explicit target for share/revoke, source for read-shared")


def command(args):
    try:
        scope = _scope(args.scope_file)
        mutation = args.action in {"save", "clear", "share", "revoke"}
        if mutation and (not isinstance(args.expected, str) or not re.fullmatch(r"[0-9a-f]{64}", args.expected)):
            raise ValueError("an exact --expected receipt is required for every mutation")
        if args.action in {"share", "revoke", "read-shared"}:
            if not args.peer_scope_file:
                raise ValueError("an explicit --peer-scope-file is required")
            peer = _scope(args.peer_scope_file)
        elif args.peer_scope_file:
            raise ValueError("peer scope is only valid for share, revoke or read-shared")
        text = None
        if args.action == "save":
            raw = sys.stdin.buffer.read(MAX_TEXT_BYTES + 1)
            if len(raw) > MAX_TEXT_BYTES:
                raise ValueError("continuation exceeds 4096 UTF-8 bytes")
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as error:
                raise ValueError("continuation must be UTF-8 text") from error
        store = ScopedState(args.store_root, scope)
        if args.action == "load":
            result = store.load()
        elif args.action == "save":
            result = store.save(text, expected=args.expected)
        elif args.action == "clear":
            result = store.clear(expected=args.expected)
        elif args.action == "share":
            result = store.share(peer, expected=args.expected)
        elif args.action == "revoke":
            store.revoke(peer, expected=args.expected)
            result = {"revoked": True, "authority": "advisory"}
        else:
            result = store.read_shared(peer)
    except Conflict as error:
        print(f"harness continuation: {error}", file=sys.stderr)
        return 4
    except (OSError, ValueError) as error:
        print(f"harness continuation: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0
