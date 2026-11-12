"""Inspect one explicitly selected coverage ledger, not primary-source truth.

No linked files are opened, URLs fetched or indexes written. Corrections need
an explicitly supplied, base-hash-bound reconciliation; originals stay intact.
The caller selects an authorized metadata file; this is not an access-control
service against other processes running as the same user.
"""
from collections import Counter
import copy
import hashlib
import json
import os
from pathlib import Path
import stat

from .qualification import MANIFEST_LIMIT, identity, require
from .vault_sources import _unique_object


def _text(value, label, limit=4096):
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= limit,
            "invalid " + label)
    return value


def _object(value, label):
    require(isinstance(value, dict), "invalid " + label)
    return value


def _nonfinite(_):
    raise ValueError("nonfinite JSON value")


def _load(path):
    path = Path(path)
    try:
        require(not path.is_symlink(), "linked ledger is not allowed")
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
        try:
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode), "ledger must be a regular file")
            require(before.st_size <= MANIFEST_LIMIT, "ledger exceeds size limit")
            with os.fdopen(fd, "rb", closefd=False) as handle:
                raw = handle.read(MANIFEST_LIMIT + 1)
            after = os.fstat(fd)
        finally:
            os.close(fd)
        require(len(raw) <= MANIFEST_LIMIT, "ledger exceeds size limit")
        require(identity(before) == identity(after) == identity(path.stat()),
                "ledger changed during read")
        return json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_nonfinite), raw
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError("coverage ledger cannot be read") from error


def _reconcile(ledger, raw, packet_path):
    packet, packet_raw = _load(packet_path)
    _object(packet, "reconciliation")
    require(packet.get("schema") == "harness.source-reconciliation/v1", "unsupported reconciliation schema")
    base = _object(packet.get("base"), "reconciliation base")
    require(base.get("sha256") == hashlib.sha256(raw).hexdigest(), "reconciliation base hash mismatch")
    base_name = _text(base.get("path"), "logical base path")
    old = ledger["sources"]
    added = packet.get("new_sources")
    index = packet.get("source_index")
    corrections = packet.get("corrections")
    require(isinstance(added, list) and len(old) + len(added) <= 1000, "invalid reconciliation additions")
    require(isinstance(index, list) and len(index) == len(old) + len(added), "incomplete reconciliation index")
    require(isinstance(corrections, list) and len(corrections) <= len(old), "invalid correction list")
    projected = copy.deepcopy(old)
    positions = [{"pointer": "/sources/" + str(i), "container_sha256": hashlib.sha256(raw).hexdigest()}
                 for i in range(len(old))]
    for i, row in enumerate(added):
        value = copy.deepcopy(_object(row, "added source"))
        value["transfer"] = None
        value["source_revision"] = {"content_sha256": value.get("primary_content_sha256")}
        projected.append(value)
        positions.append({"pointer": "/new_sources/" + str(i),
                          "container_sha256": hashlib.sha256(packet_raw).hexdigest()})
    by_id = {}
    for i, row in enumerate(projected):
        key = _text(_object(row, "source record").get("source_id"), "source ID")
        require(key not in by_id, "duplicate reconciliation identity")
        by_id[key] = i
    other_inputs = set()
    observed = {}
    for row in index:
        row = _object(row, "source index entry")
        key = _text(row.get("source_id"), "index source ID")
        require(key in by_id and key not in observed, "unknown or duplicate index identity")
        i = by_id[key]
        require(row.get("canonical_url") == projected[i].get("canonical_url"), "index URL mismatch")
        ref = _object(row.get("record"), "index reference")
        name = _text(ref.get("input"), "logical record input")
        require(ref.get("json_pointer") == positions[i]["pointer"], "index pointer mismatch")
        if i < len(old):
            require(name == base_name, "index base input mismatch")
        else:
            require(name != base_name, "addition points to base")
            other_inputs.add(name)
        override = row.get("reading_override")
        if override is not None:
            other_inputs.add(_text(_object(override, "reading override").get("input"), "override input"))
        observed[key] = row
    require(len(other_inputs) <= 1 and base_name not in other_inputs, "ambiguous reconciliation identity")
    self_name = next(iter(other_inputs), None)
    changed = {}
    for number, item in enumerate(corrections):
        item = _object(item, "correction")
        key = _text(item.get("source_id"), "corrected source ID")
        require(key in by_id and by_id[key] < len(old) and key not in changed,
                "invalid or repeated corrected identity")
        i = by_id[key]
        reading = _object(projected[i].get("reading"), "corrected reading")
        original_status = _text(reading.get("status"), "original reading status", 256)
        require(item.get("axis") == "reading" and item.get("old_status") == original_status,
                "correction does not match original reading")
        require(all(item.get(flag) is False for flag in (
            "verified_primary_read", "acceptance_change", "access_or_activation_change")),
            "correction cannot widen authority or certify a read")
        require(item.get("original_preserved") == {
            "input": base_name, "json_pointer": positions[i]["pointer"] + "/reading"},
            "correction original pointer mismatch")
        replacement = _text(item.get("replacement_status"), "replacement status", 256)
        expected = {"input": self_name, "json_pointer": "/corrections/" + str(number)}
        require(self_name is not None and observed[key].get("reading_override") == expected,
                "correction override missing or misbound")
        positions[i]["original_reading_status"] = original_status
        reading["status"] = replacement
        changed[key] = expected
    require(all(row.get("reading_override") == changed.get(key) for key, row in observed.items()),
            "unresolved reading override")
    return projected, positions, packet, packet_raw


def coverage_report(path, *, source_id=None, reconciliation=None):
    """Recompute declared-record counts; retain unknowns and snapshot boundaries."""
    ledger, raw = _load(path)
    _object(ledger, "ledger")
    require(ledger.get("schema") == "harness.source-coverage/v1", "unsupported ledger schema")
    as_of = _text(ledger.get("as_of"), "snapshot date", 128)
    boundary = _text(ledger.get("denominator_boundary"), "denominator boundary", 8192)
    claim_class = _text(ledger.get("claim_class"), "claim class", 256)
    sources = ledger.get("sources")
    require(isinstance(sources, list) and len(sources) <= 1000, "invalid source list or limit")
    summary = _object(ledger.get("summary", {}), "declared summary")
    positions = [{"pointer": "/sources/" + str(i), "container_sha256": hashlib.sha256(raw).hexdigest()}
                 for i in range(len(sources))]
    packet = packet_raw = None
    if reconciliation is not None:
        sources, positions, packet, packet_raw = _reconcile(ledger, raw, reconciliation)
    axes = {name: Counter() for name in (
        "incoming_transfer_status", "read_depth", "transfer_read_depth", "current_access",
        "historical_access", "adoption", "evaluation")}
    seen = set()
    transferred = variants = hashes = 0
    selected = None
    for index, row in enumerate(sources):
        _object(row, "source record")
        url = _text(row.get("canonical_url"), "canonical URL")
        key = row.get("source_id")
        require(key == "url-sha256:" + hashlib.sha256(url.encode()).hexdigest(),
                "source identity does not match canonical URL")
        require(key not in seen, "duplicate source identity")
        seen.add(key)
        reported = {}
        for section, fields in (("reading", ("status",)),
                                ("access", ("current", "historical")),
                                ("adoption", ("status",)), ("evaluation", ("status",))):
            value = _object(row.get(section), section)
            reported[section] = {field: _text(value.get(field), section + "/" + field, 256)
                                 for field in fields}
        primary = _object(row.get("source_revision"), "source revision").get("content_sha256")
        require(primary is None or (isinstance(primary, str) and len(primary) == 64
                and all(c in "0123456789abcdef" for c in primary)), "invalid primary content hash")
        hashes += primary is not None
        transfer = row.get("transfer")
        if transfer is not None:
            _object(transfer, "transfer")
            incoming = _text(transfer.get("incoming_read_status"), "incoming status", 256)
            exact = transfer.get("exact_variants")
            require(isinstance(exact, list) and bool(exact)
                    and all(isinstance(v, str) and 0 < len(v) <= 4096 for v in exact)
                    and len(exact) == len(set(exact)), "invalid transfer variants")
            transferred += 1
            variants += len(exact)
            axes["incoming_transfer_status"][incoming] += 1
            axes["transfer_read_depth"][reported["reading"]["status"]] += 1
            reported["transfer"] = {"incoming_read_status": incoming, "exact_variants": len(exact)}
        else:
            reported["transfer"] = None
        axes["read_depth"][reported["reading"]["status"]] += 1
        axes["current_access"][reported["access"]["current"]] += 1
        axes["historical_access"][reported["access"]["historical"]] += 1
        axes["adoption"][reported["adoption"]["status"]] += 1
        axes["evaluation"][reported["evaluation"]["status"]] += 1
        if source_id is not None and source_id in (key, url):
            selected = {"source_id": key, "canonical_url": url, **positions[index],
                        "reported": reported, "primary_content_sha256": primary}
    require(source_id is None or selected is not None, "source not present in selected ledger")
    result = {
        "schema": "harness.source-coverage-report/v1", "as_of": as_of,
        "ledger_sha256": hashlib.sha256(raw).hexdigest(), "claim_class": claim_class,
        "denominator_boundary": boundary,
        "denominator": {"identities": len(sources), "transferred_identities": transferred,
                        "transfer_exact_variants": variants, "additional_identities": len(sources) - transferred},
        "reported": {**{k: dict(v) for k, v in axes.items()}, "primary_hashes_present": hashes},
        "declared_summary": {k: v for k, v in summary.items() if type(v) is int and v >= 0},
        "declared_summary_scope": "BASE_LEDGER_DECLARATIONS; not validated totals",
        "evidence_verification": "NOT_RUN", "source_claim_joins": "NOT_EVALUATED",
        "corrections": "NOT_APPLIED; selected ledger only",
        "scope": "Declared historical snapshot; not current knowledge or a complete corpus. "
                 "Counts and hashes do not verify reads, source support, adoption, learning or authority.",
    }
    if selected is not None:
        result["source"] = selected
    if packet is not None:
        result["base_as_of"] = as_of
        result["base_claim_class"] = claim_class
        result["base_denominator_boundary"] = boundary
        result["claim_class"] = "SELECTED_LOCAL_METADATA_PROJECTION"
        result["denominator_boundary"] = (
            "Selected base ledger plus explicit reconciliation additions/corrections; "
            "membership checked against its complete source index, not a universal corpus.")
        result["as_of"] = _text(packet.get("as_of"), "reconciliation date", 128)
        result["reconciliation_sha256"] = hashlib.sha256(packet_raw).hexdigest()
        result["corrections"] = "APPLIED_FROM_EXPLICIT_RECONCILIATION; reports only"
        result["reading_corrections"] = len(packet["corrections"])
        result["scope"] += " Explicit reconciliation additions/corrections are applied; linked evidence remains unverified."
    require(len(json.dumps(result).encode()) <= 32768, "coverage report exceeds output limit")
    return result
