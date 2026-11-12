"""Settlement hooks: scan plan/workgraph activity and prove that every action
claiming done has a closing receipt — schema `harness.settlement-record/v1`.

Design: docs/v3/settlement-plugin-loop-design-20261111.md (plan
v3-settlement-plugin-loop). Pi's pattern (docs/v3/oss-mechanics-20261110.md):
awaited hook subscribers count toward run settlement — our gates already are
those subscribers; this module makes settlement itself auditable. An action
is not done until its settlement receipt closes.

One settlement record per scanned node. Fail-closed: a done-mark without a
verifiable receipt chain is reported failed (fabricated or tampered), never
assumed; UNKNOWN is never zero — the checker emits exactly one record per
parsed node, and a done node it cannot classify is failed, never omitted.

The receipt chain per done node (all required): a graph note line matching
the workgraph's NOTE_RE with exit 0 carrying an 8-hex gate signature; the
node record file with an applied exit-0 Attempt block; note/record duration
agreement; a note tail rebuild matching the stored record body; and the gate
signature re-derived from the stored body. The tool signs the redacted,
UNSTRIPPED output blob but stores blob.strip(), so re-derivation tries
{body, body+"\\n"}. When post-gate hygiene redaction rewrote the stored
bytes after signing (owner convention), an inverse-redaction candidate set
reconstructs the signed bytes from LIVE runtime values (home, hostname,
user) — tokens are never stored as literals with real values. Verification
is machine-local by construction: a relocated repo reports failed, never
silently settles. The 8-hex sha1 signature is a drift/hygiene control, not
a security boundary (the tool's own STUCK detector posture).

Stdlib only, Python 3.9+. Pure functions on text plus one filesystem seam
(scan_plan reads the plan file and record files); no writes here — the CLI
emits the document.
"""
import getpass
import glob
import hashlib
import json
import os
import re
import socket

from agent_harness.workgraph import plan as _plan_tool

SCHEMA = "harness.settlement-record/v1"
EXPECTED_RECEIPTS = ["graph-note", "node-record"]
STATUSES = ("open", "settled", "failed")
VERIFICATIONS = ("direct", "inverse-redacted")
MAX_TEXT = 4096

NOTE_RE = _plan_tool.NOTE_RE
NODE_RE = re.compile(r"^- \[([x >])\] (\d+)\. (.*)$")
ATTEMPT_RE = re.compile(
    r"## Attempt ([^\n]*?) — ([^—]*?) — (\d+)s — exit (-?\d+)"
    r"( \(NOT APPLIED[^\n]*\))?\n\n```\n(.*?)\n```", re.S)
# Tokens written by the owner-directed post-gate hygiene redaction; the live
# values come from the runtime environment at verification time.
REDACTION_TOKENS = ("/Users/me", "redacted-host", "agent@")


class SettlementError(ValueError):
    """One settlement-scan defect, named."""


def _require(condition, message):
    if not condition:
        raise SettlementError(message)


def _sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def gate_signature(blob):
    """The workgraph's own signature, reused so the definitions cannot drift."""
    return _plan_tool.gate_signature(blob)


def _inverse_redact(text):
    """Undo ONLY the documented post-gate hygiene tokens, from live values."""
    out = text.replace("/Users/me", os.path.expanduser("~"))
    out = out.replace("redacted-host", socket.gethostname())
    out = out.replace("agent@", getpass.getuser() + "@")
    return out


def parse_plan(text):
    """Parse a plan graph file into actions with their NOTE_RE notes.

    Returns a list of {node, title, mark, notes}; raises SettlementError on
    a malformed node line (fail-closed: a graph we cannot parse is not a
    graph we can settle).
    """
    actions, current = [], None
    for line in text.split("\n"):
        m = NODE_RE.match(line)
        if m:
            mark, node_id, rest = m.group(1), m.group(2), m.group(3)
            _require(mark in ("x", " ", ">"),
                     "unrecognized node mark %r on node %s" % (mark, node_id))
            current = {"node": node_id, "title": rest.split(" | ")[0].strip(),
                       "mark": mark, "notes": []}
            actions.append(current)
        elif re.match(r"^- \[[^\]]*\]", line):
            # looks like a node line but is not one the workgraph writes:
            # a graph we cannot parse is a graph we cannot settle
            raise SettlementError("unrecognized node line: " + line[:60])
        elif current is not None:
            nm = NOTE_RE.search(line)
            if nm:
                current["notes"].append({"exit": nm.group(1), "secs": nm.group(2),
                                         "sig": nm.group(3), "tail": nm.group(4),
                                         "line": line.strip()})
    return actions


def _attempts(record_text):
    out = []
    for m in ATTEMPT_RE.finditer(record_text):
        out.append({"secs": m.group(3), "exit": m.group(4),
                    "not_applied": m.group(5) is not None, "body": m.group(6)})
    return out


def _tail_of(body):
    lines = [l.strip() for l in body.strip().split("\n") if l.strip()]
    return (" / ".join(lines[-3:])[:400] if lines else "(no output)")


def _sig_match(body, sig):
    """Try direct candidates, then inverse-redacted ones. Return mode or None."""
    bodies = [("direct", body)]
    inverse = _inverse_redact(body)
    if inverse != body:
        bodies.append(("inverse-redacted", inverse))
    if body == "(no output)":
        bodies = [("direct", ""), ("direct", "\n")] + bodies
    for mode, candidate_body in bodies:
        for candidate in (candidate_body, candidate_body + "\n"):
            if gate_signature(candidate) == sig:
                return mode
    return None


def _record(node, title, mark, status, detail, settled_by=None):
    _require(status in STATUSES, "invalid settlement status")
    rec = {"action": {"node": node, "title": title[:MAX_TEXT], "mark": mark},
           "expected_receipts": list(EXPECTED_RECEIPTS),
           "status": status, "settled_by": settled_by, "detail": detail[:MAX_TEXT]}
    return rec


def verify_action(action, record_text, record_sha256):
    """Verify one parsed action against its record file (None when missing).

    Pure text verification; the caller reads files. Returns a settlement
    record. A done-mark whose chain does not close is failed, with the
    reason named; UNKNOWN is never zero.
    """
    node, title, mark = action["node"], action["title"], action["mark"]
    if mark != "x":
        return _record(node, title, mark, "open",
                       "no done-mark claimed; open is listed, never a failure")
    notes = action["notes"]
    ok_notes = [n for n in notes if n["exit"] == "0"]
    if not ok_notes:
        return _record(node, title, mark, "failed",
                       "done-mark without an exit-0 gate note (fabricated done)")
    note = ok_notes[-1]
    later = notes[notes.index(note) + 1:]
    for n in later:
        if (n["exit"] != "0" and "re-claimed" not in n["tail"]
                and "NOT_RUN" not in n["tail"] and "NOT APPLIED" not in n["tail"]):
            return _record(node, title, mark, "failed",
                           "a newer applied failure note sits under the done-mark "
                           "(inconsistent)")
    if not note["sig"]:
        return _record(node, title, mark, "failed",
                       "exit-0 gate note carries no signature (unverifiable)")
    if record_text is None:
        return _record(node, title, mark, "failed",
                       "node record file missing (expected receipt absent)")
    attempts = _attempts(record_text)
    applied = [a for a in attempts if not a["not_applied"]]
    if not applied:
        return _record(node, title, mark, "failed",
                       "record file holds no applied gate attempt")
    attempt = applied[-1]
    if attempt["exit"] != "0":
        return _record(node, title, mark, "failed",
                       "last applied attempt exited {} (inconsistent with the "
                       "done-mark)".format(attempt["exit"]))
    if note["secs"] is not None and note["secs"] != attempt["secs"]:
        return _record(node, title, mark, "failed",
                       "note/record duration mismatch ({}s vs {}s)".format(
                           note["secs"], attempt["secs"]))
    if _tail_of(attempt["body"]) != note["tail"][:400]:
        sig_mode = _sig_match(attempt["body"], note["sig"])
        detail = "note tail does not match the record body"
        if sig_mode is not None:
            detail += (" (the gate signature DOES verify {}; era divergence in "
                       "the stored receipts, not forged output)".format(sig_mode))
        return _record(node, title, mark, "failed", detail)
    mode = _sig_match(attempt["body"], note["sig"])
    if mode is None:
        return _record(node, title, mark, "failed",
                       "gate signature mismatch (tampered or corrupted receipt)")
    settled_by = {"note_sha256": _sha_text(note["line"]),
                  "record_sha256": record_sha256,
                  "gate_signature": note["sig"],
                  "verification": mode}
    _require(mode in VERIFICATIONS, "invalid verification mode")
    return _record(node, title, mark, "settled",
                   "receipts closed: exit-0 note + record verified "
                   "({})".format(mode), settled_by=settled_by)


def scan_plan(plan_path):
    """Scan one plan file (records live beside it under <slug>/). Fail-closed:
    returns settlement records; unreadable files raise SettlementError."""
    _require(os.path.isfile(plan_path), "plan file not found: " + plan_path)
    with open(plan_path, "r", encoding="utf-8") as fh:
        text = fh.read()
    slug = os.path.splitext(os.path.basename(plan_path))[0]
    record_dir = os.path.join(os.path.dirname(plan_path), slug)
    records = []
    for action in parse_plan(text):
        record_text, record_sha256 = None, None
        hits = sorted(glob.glob(os.path.join(
            record_dir, "{}-*.md".format(str(int(action["node"])).zfill(2)))))
        if hits:
            with open(hits[0], "r", encoding="utf-8") as fh:
                record_text = fh.read()
            record_sha256 = _sha_text(record_text)
        rec = verify_action(action, record_text, record_sha256)
        rec = dict(rec, plan={"ref": plan_path})
        records.append(rec)
    return records


def scan(plan_paths, checked_at):
    """Build the settlement document over an explicit plan set (fail-closed:
    an empty plan set is a usage defect, never a green scan)."""
    _require(plan_paths, "no plans given (an empty scan is not a settlement)")
    records = []
    for path in plan_paths:
        records.extend(scan_plan(path))
    return {"schema": SCHEMA, "checked_at": checked_at, "records": records}


def summarize(document):
    counts = {s: 0 for s in STATUSES}
    for rec in document["records"]:
        counts[rec["status"]] += 1
    return counts


def dumps(document):
    return json.dumps(document, indent=2, sort_keys=True) + "\n"
