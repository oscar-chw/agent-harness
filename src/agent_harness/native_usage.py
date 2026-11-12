"""Explicit, read-only Codex counter windows; never whole-campaign certification.

The caller supplies an authorized source root and thread, not a discovery query.
Native bookkeeping is trusted to the local OS owner, not cryptographically
authenticated. A consistent window neither covers other roles nor proves task
quality, invocation isolation, all preparation cost or promotion authority.
"""

from contextlib import ExitStack, contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat

FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)
HEADER_LIMIT = 1024 * 1024
WINDOW_LIMIT = 4 * 1024 * 1024
TURN_LIMIT = 32 * 1024 * 1024


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _counter(value, *, last=False):
    if (
        not isinstance(value, dict)
        or set(value) - set(FIELDS) - {"cache_write_input_tokens"}
        or any(type(value.get(k)) is not int or value[k] < 0 for k in FIELDS)
    ):
        raise ValueError("native counter fields are missing, unsupported or invalid")
    write = value.get("cache_write_input_tokens", 0)
    if (
        type(write) is not int
        or write < 0
        or value["cached_input_tokens"] + write > value["input_tokens"]
        or value["reasoning_output_tokens"] > value["output_tokens"]
    ):
        raise ValueError("native counter subsets exceed their parent counts")
    if last and value["total_tokens"] != value["input_tokens"] + value["output_tokens"]:
        raise ValueError("native last-request total is inconsistent")
    return {k: value[k] for k in FIELDS}


@contextmanager
def _source(root, path):
    selected = Path(root).absolute()
    root = selected.resolve(strict=True)
    path = Path(path)
    if not path.is_absolute():
        path = root / path
    try:
        # Resolve the explicitly selected root once. Do not resolve a child
        # symlink: traversal below that root stays descriptor-relative/no-follow.
        relative = path.relative_to(selected if path.is_relative_to(selected) else root)
    except ValueError:
        raise ValueError("native counter source is outside its selected root") from None
    parts = relative.parts
    if (
        not parts
        or ".." in parts
        or path.suffix != ".jsonl"
        or any(
            p in (".ssh", "Keychains", "auth.json", "id_rsa", "id_ed25519")
            or p.startswith(".env")
            for p in parts
        )
    ):
        raise ValueError("native counter source path is not an allowed JSONL source")
    if (
        not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_DIRECTORY")
        or os.open not in os.supports_dir_fd
    ):
        raise ValueError(
            "race-safe native counter reads are unsupported on this platform"
        )
    try:
        with ExitStack() as opened:
            flags = getattr(os, "O_SEARCH", getattr(os, "O_PATH", os.O_RDONLY))
            flags |= os.O_DIRECTORY | os.O_NOFOLLOW
            directory = os.open(root, flags)
            opened.callback(os.close, directory)
            for part in parts[:-1]:
                directory = os.open(part, flags, dir_fd=directory)
                opened.callback(os.close, directory)
            fd = os.open(
                parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
            )
            opened.callback(os.close, fd)
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError("native counter source must be a regular file")
            stream = opened.enter_context(os.fdopen(fd, "rb", closefd=False))
            yield (
                stream,
                relative,
                lambda: os.stat(parts[-1], dir_fd=directory, follow_symlinks=False),
            )
    except OSError as error:
        raise ValueError("native counter source unavailable") from error


def inspect_window(
    source_root, source, *, thread_id, start_offset, end_offset, max_bytes=WINDOW_LIMIT
):
    """Validate every counter transition in one exact original byte interval.

    The first counter is an anchor, not an additional request to charge. Exact
    duplicates count once. Every subsequent increment must equal that event's
    last-request fields, so missing counter events and resets fail. A constant
    historical cumulative-total offset stays visible; it is never repaired into
    a claim of complete historical or whole-workflow usage.
    """
    if not isinstance(thread_id, str) or not thread_id or len(thread_id) > 160:
        raise ValueError("native thread identity is required")
    if (
        type(start_offset) is not int
        or type(end_offset) is not int
        or not 0 <= start_offset < end_offset
        or type(max_bytes) is not int
        or not 0 < max_bytes <= WINDOW_LIMIT
        or end_offset - start_offset > max_bytes
    ):
        raise ValueError("native counter window exceeds its explicit byte budget")
    with _source(source_root, source) as (stream, relative, current):
        initial = os.fstat(stream.fileno())
        header = stream.readline(HEADER_LIMIT + 1)
        if len(header) > HEADER_LIMIT or not header.endswith(b"\n"):
            raise ValueError(
                "native thread header exceeds the read budget or is incomplete"
            )
        try:
            metadata = json.loads(header)
        except (ValueError, UnicodeError) as error:
            raise ValueError("native thread header is invalid") from error
        if (
            not isinstance(metadata, dict)
            or metadata.get("type") != "session_meta"
            or not isinstance(metadata.get("payload"), dict)
            or metadata["payload"].get("id") != thread_id
        ):
            raise ValueError("native source belongs to a different thread")
        if end_offset > initial.st_size:
            raise ValueError("native counter window extends past the observed source")
        if start_offset:
            stream.seek(start_offset - 1)
            if stream.read(1) != b"\n":
                raise ValueError("native counter window begins inside a record")
        stream.seek(start_offset)
        raw = stream.read(end_offset - start_offset)
        if len(raw) != end_offset - start_offset or not raw.endswith(b"\n"):
            raise ValueError("native counter window has an incomplete record")
        records = []
        offset = start_offset
        for line in raw.splitlines(keepends=True):
            try:
                item = json.loads(line)
            except (ValueError, UnicodeError) as error:
                raise ValueError("invalid native counter source record") from error
            if not isinstance(item, dict):
                raise ValueError("native source record must be an object")
            payload = item.get("payload")
            if (
                item.get("type") == "event_msg"
                and isinstance(payload, dict)
                and payload.get("type") == "token_count"
            ):
                info = payload.get("info")
                if info is None:
                    raise ValueError(
                        "missing native token-count information; usage is not zero"
                    )
                if not isinstance(info, dict):
                    raise ValueError("invalid native token-count information")
                records.append(
                    {
                        "offset": offset,
                        "length": len(line),
                        "sha256": _sha(line),
                        "total": _counter(info.get("total_token_usage")),
                        "last": _counter(info.get("last_token_usage"), last=True),
                    }
                )
            offset += len(line)
        if len(records) < 2:
            raise ValueError(
                "at least two observed counter anchors are required; missing usage is not zero"
            )
        unique = [records[0]]
        duplicates = 0
        for row in records[1:]:
            previous = unique[-1]
            if row["total"] == previous["total"]:
                if row["last"] != previous["last"]:
                    raise ValueError(
                        "duplicate cumulative counter has conflicting request usage"
                    )
                duplicates += 1
                continue
            delta = {k: row["total"][k] - previous["total"][k] for k in FIELDS}
            if any(value < 0 for value in delta.values()) or delta != row["last"]:
                raise ValueError(
                    "native counter reset, missing event or request/cumulative mismatch"
                )
            unique.append(row)
        if len(unique) < 2:
            raise ValueError(
                "no distinct counter increment was observed; not complete zero usage"
            )
        first, last = unique[0], unique[-1]
        delta = {k: last["total"][k] - first["total"][k] for k in FIELDS}
        residual = (
            first["total"]["total_tokens"]
            - first["total"]["input_tokens"]
            - first["total"]["output_tokens"]
        )
        # A live native source may append. Replacement, in-range edits and a
        # changed identity invalidate this observation; never fall back to cache.
        stream.seek(0)
        head_again = stream.read(len(header))
        stream.seek(start_offset)
        span_again = stream.read(len(raw))
        after = current()
        if (
            (after.st_dev, after.st_ino) != (initial.st_dev, initial.st_ino)
            or after.st_size < end_offset
            or head_again != header
            or span_again != raw
        ):
            raise ValueError("native counter source changed during inspection")
    return {
        "schema": 1,
        "thread_id": thread_id,
        "source": relative.as_posix(),
        "status": (
            "CONSISTENT_DELTA_WITH_HISTORICAL_OFFSET"
            if residual
            else "CONSISTENT_COUNTER_WINDOW"
        ),
        "source_span": {
            "start_offset": start_offset,
            "end_offset": end_offset,
            "sha256": _sha(raw),
            "header_sha256": _sha(header),
        },
        "first_anchor": first,
        "last_anchor": last,
        "delta": delta,
        "distinct_increments": len(unique) - 1,
        "duplicate_notifications": duplicates,
        "cumulative_total_residual": residual,
        "whole_workflow_usage_complete": False,
        "limitations": "Selected local native source only; no role coverage, invocation authentication, task quality, cost attribution or promotion authority.",
    }


def inspect_turn(source_root, source, *, thread_id, turn_id, scan_start, scan_end,
                 max_bytes=TURN_LIMIT):
    """Bind a complete native turn to its preceding anchor and terminal record.

    Native sources report usage before task_complete. Task state is read from
    those original records, never inferred from an app-server's local liveness
    or a caller's completion flag. This still cannot certify a whole campaign.
    """
    if not isinstance(turn_id, str) or not turn_id or len(turn_id) > 160:
        raise ValueError('native turn identity is required')
    if (type(scan_start) is not int or type(scan_end) is not int
            or not 0 <= scan_start < scan_end or type(max_bytes) is not int
            or not 0 < max_bytes <= TURN_LIMIT or scan_end - scan_start > max_bytes):
        raise ValueError('native turn scan exceeds its explicit byte budget')
    with _source(source_root, source) as (stream, _, current):
        initial = os.fstat(stream.fileno())
        header = stream.readline(HEADER_LIMIT + 1)
        if len(header) > HEADER_LIMIT or not header.endswith(b'\n'):
            raise ValueError('native thread header is incomplete or exceeds its budget')
        if scan_end > initial.st_size:
            raise ValueError('native turn scan extends past the observed source')
        if scan_start:
            stream.seek(scan_start - 1)
            if stream.read(1) != b'\n':
                raise ValueError('native turn scan begins inside a record')
        stream.seek(scan_start)
        raw = stream.read(scan_end - scan_start)
        if len(raw) != scan_end - scan_start or not raw.endswith(b'\n'):
            raise ValueError('native turn scan has an incomplete record')
        parsed, offset = [], scan_start
        for line in raw.splitlines(keepends=True):
            try:
                item = json.loads(line)
            except (ValueError, UnicodeError) as error:
                raise ValueError('invalid native turn source record') from error
            if not isinstance(item, dict):
                raise ValueError('native turn source record must be an object')
            payload = item.get('payload')
            if (item.get('type') == 'event_msg' and isinstance(payload, dict)
                    and payload.get('type') in ('task_started', 'task_complete', 'turn_aborted', 'token_count')):
                parsed.append((offset, offset + len(line), payload))
            offset += len(line)
        starts = [r for r in parsed if r[2].get('type') == 'task_started' and r[2].get('turn_id') == turn_id]
        ends = [r for r in parsed if r[2].get('type') == 'task_complete' and r[2].get('turn_id') == turn_id]
        if len(starts) != 1 or len(ends) != 1 or starts[0][0] >= ends[0][0]:
            raise ValueError('native turn is incomplete or has ambiguous terminal boundaries')
        start, end = starts[0], ends[0]
        root = start[2].get('root_turn_id')
        if (root is not None and (not isinstance(root, str) or not root)
                or end[2].get('root_turn_id') != root):
            raise ValueError('native turn root boundary does not match')
        for row in parsed:
            if start[0] < row[0] < end[0] and row[2].get('type') in (
                    'task_started', 'task_complete', 'turn_aborted'):
                raise ValueError('native turn has an interleaved or aborted boundary')
        anchors = [r for r in parsed if r[0] < start[0] and r[2].get('type') == 'token_count']
        if not anchors:
            raise ValueError('native turn has no preceding counter anchor')
        anchor = anchors[-1]
        # Long turns must not be truncated or force an unbounded counter read.
        # Adjacent pages share exactly one observed anchor, never charge it twice.
        counters = [r for r in parsed if anchor[0] <= r[0] < end[0]
                    and r[2].get('type') == 'token_count']
        windows, index = [], 0
        while index < len(counters) - 1:
            stop = index
            for candidate in range(index + 1, len(counters)):
                if counters[candidate][1] - counters[index][0] > WINDOW_LIMIT:
                    break
                stop = candidate
            if stop == index:
                raise ValueError('native turn counter gap exceeds the page budget')
            page_start, page_end = counters[index][0], counters[stop][1]
            result = inspect_window(source_root, source, thread_id=thread_id,
                                    start_offset=page_start, end_offset=page_end,
                                    max_bytes=min(max_bytes, WINDOW_LIMIT))
            page = raw[page_start - scan_start:page_end - scan_start]
            if (result['source_span']['sha256'] != _sha(page)
                    or result['source_span']['header_sha256'] != _sha(header)
                    or windows and windows[-1]['last_anchor'] != result['first_anchor']):
                raise ValueError('native turn source changed between counter pages')
            windows.append(result)
            index = stop
        if not windows:
            raise ValueError('native turn has no observed counter increment')
        selected = raw[anchor[0] - scan_start:end[1] - scan_start]
        stream.seek(scan_start)
        again = stream.read(len(raw))
        after = current()
        if ((after.st_dev, after.st_ino) != (initial.st_dev, initial.st_ino)
                or after.st_size < scan_end or again != raw):
            raise ValueError('native turn source changed during inspection')
    result = {**windows[0], 'last_anchor': windows[-1]['last_anchor'],
              'delta': {k: sum(w['delta'][k] for w in windows) for k in FIELDS},
              'distinct_increments': sum(w['distinct_increments'] for w in windows),
              'duplicate_notifications': sum(w['duplicate_notifications'] for w in windows),
              'source_span': {'start_offset': anchor[0], 'end_offset': end[1],
                              'sha256': _sha(selected), 'header_sha256': _sha(header)}}
    return {**result, 'turn_id': turn_id, 'root_turn_id': root, 'terminal_observed': True,
            'counter_windows': windows,
            'turn_span': {'start_offset': start[0], 'end_offset': end[1],
                          'sha256': _sha(raw[start[0] - scan_start:end[1] - scan_start])},
            'limitations': 'One closed native turn only; other roles, campaign attribution, quality and promotion remain unverified.'}
