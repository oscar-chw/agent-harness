"""JEV typed-decision records: schema `harness.jev-decision/v1`, a fail-closed
validator, and an on-disk binding/receipt verifier.

Design: docs/v3/jev-decision-records-20261111.md (plan v3-jev-needle). The Jev
pattern (docs/v3/harness-pillars-20261110.md) contributes the typed
choice/score/boolean verdict with confidence; this module is the RECORD, not
the model — v0 records are filled by gates and humans, and the
execute-above-confidence / escalate-below rule is stored as policy data.

One envelope for every harness decision (dependency, hypothesis, adoption,
promotion, routing, escalation): hash-bound inputs, a receipts pointer,
confidence, scope, reversibility, authority. Fail-closed: missing authority
refuses, unbound inputs refuse, a verdict outside its enum refuses. A record
never grants authority: `promotion` is always NOT_GRANTED, and UNKNOWN is
never zero (unknowns must be non-empty) — both carried from
harness.rea-record/v1 (src/agent_harness/rea.py), whose dependency decisions
are expressible here as domain="dependency", kind="choice".

Stdlib only, Python 3.9+. Same idioms as rea.py by design; the modules stay
independent so either can evolve without a shared-edit hazard.
"""
import hashlib
import json
import os
import re

SCHEMA = "harness.jev-decision/v1"
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
KINDS = ("choice", "score", "boolean")
DOMAINS = ("dependency", "hypothesis", "adoption", "promotion", "routing", "escalation")
CONFIDENCE_LEVELS = ("high", "medium", "low")
REVERSIBILITY = ("reversible", "reversible-with-receipt", "irreversible")
BOOLEAN_VERDICTS = ("YES", "NO")
BINDING_KINDS = ("local-file", "upstream-pin")
MAX_TEXT = 4096
MAX_ITEMS = 1000


class JevError(ValueError):
    """One validation or verification defect, named."""


def _require(condition, message):
    if not condition:
        raise JevError(message)


def _fields(value, fields, label):
    _require(isinstance(value, dict) and set(value) == set(fields),
             "invalid " + label + " fields")


def _text(value, label):
    _require(isinstance(value, str) and bool(value.strip()) and len(value) <= MAX_TEXT,
             "invalid " + label)
    return value


def _sha(value, label):
    _require(isinstance(value, str) and SHA256_RE.fullmatch(value) is not None,
             "invalid " + label + " (need a 64-hex sha256)")


def _text_list(value, label, minimum=0):
    _require(isinstance(value, list) and minimum <= len(value) <= MAX_ITEMS,
             "invalid " + label + " list")
    for item in value:
        _text(item, label)
    return value


def _validate_verdict(record):
    kind = record["kind"]
    verdict = record["verdict"]
    options = record["options"]
    score_range = record["score_range"]
    if kind == "choice":
        _require(isinstance(options, list) and 1 <= len(options) <= MAX_ITEMS,
                 "choice decision needs a non-empty options list")
        for option in options:
            _text(option, "choice option")
        _require(len(set(options)) == len(options), "duplicate choice options")
        _require(score_range is None, "choice decision carries no score_range")
        _require(verdict in options,
                 "verdict outside the enum (not one of the declared options)")
    elif kind == "boolean":
        _require(options == [], "boolean decision carries no options")
        _require(score_range is None, "boolean decision carries no score_range")
        _require(verdict in BOOLEAN_VERDICTS,
                 "verdict outside the enum (boolean verdicts are YES or NO)")
    else:
        _require(options == [], "score decision carries no options")
        _fields(score_range, ("min", "max"), "score_range")
        _require(type(score_range["min"]) in (int, float)
                 and type(score_range["max"]) in (int, float)
                 and score_range["min"] <= score_range["max"],
                 "invalid score_range bounds")
        try:
            value = float(verdict)
        except (TypeError, ValueError):
            raise JevError("verdict outside the enum (score verdict must parse as a number)")
        _require(score_range["min"] <= value <= score_range["max"],
                 "verdict outside the enum (score outside score_range)")


def _validate_binding(value):
    _fields(value, ("ref", "kind", "role", "digest"), "input binding")
    _text(value["ref"], "binding ref")
    _text(value["role"], "binding role")
    _require(value["kind"] in BINDING_KINDS, "invalid binding kind")
    if value["kind"] == "local-file":
        _sha(value["digest"], "local-file binding digest")
        ref = value["ref"]
        _require(not os.path.isabs(ref) and ".." not in ref.split("/"),
                 "binding ref must stay inside the repo: " + ref)
    else:
        _require(isinstance(value["digest"], str)
                 and re.fullmatch(r"[0-9a-f]{7,64}", value["digest"]) is not None,
                 "invalid upstream-pin digest")


def validate(record):
    """Raise JevError on the first defect; return the record unchanged when valid."""
    _fields(record, ("schema", "record_id", "created", "subject", "kind", "domain",
                     "options", "score_range", "verdict", "confidence", "policy", "scope",
                     "reversibility", "authority", "inputs", "receipts", "unknowns",
                     "links", "promotion"), "record")
    _require(record["schema"] == SCHEMA, "unsupported record schema")
    _text(record["record_id"], "record id")
    _text(record["created"], "record date")
    _fields(record["subject"], ("name", "question"), "subject")
    _text(record["subject"]["name"], "subject name")
    _text(record["subject"]["question"], "subject question")
    _require(record["kind"] in KINDS, "invalid decision kind")
    _require(record["domain"] in DOMAINS, "invalid decision domain")
    _validate_verdict(record)
    _fields(record["confidence"], ("level", "basis"), "confidence")
    _require(record["confidence"]["level"] in CONFIDENCE_LEVELS, "invalid confidence level")
    _text(record["confidence"]["basis"], "confidence basis")
    _fields(record["policy"], ("execute_at_or_above", "below"), "policy")
    _require(record["policy"]["execute_at_or_above"] in CONFIDENCE_LEVELS,
             "invalid policy threshold")
    _require(record["policy"]["below"] == "escalate",
             "policy below-action must be escalate (fail-closed)")
    _text(record["scope"], "scope")
    _require(record["reversibility"] in REVERSIBILITY, "invalid reversibility")
    _text(record["authority"], "authority")  # missing authority refuses: a
    # decision that cannot name who/what decided it is a rumor, not a record
    inputs = record["inputs"]
    _require(isinstance(inputs, list) and 1 <= len(inputs) <= MAX_ITEMS,
             "unbound inputs (a decision must bind at least one evidence artifact)")
    seen_refs = set()
    for binding in inputs:
        _validate_binding(binding)
        _require(binding["ref"] not in seen_refs, "duplicate binding ref " + binding["ref"])
        seen_refs.add(binding["ref"])
    _text_list(record["receipts"], "receipt", minimum=1)
    for ref in record["receipts"]:
        _require(not os.path.isabs(ref) and ".." not in ref.split("/"),
                 "receipt ref must stay inside the repo: " + ref)
    _text_list(record["unknowns"], "unknowns", minimum=1)  # UNKNOWN is never zero
    links = record["links"]
    _require(isinstance(links, dict), "invalid links")
    for name, link in links.items():
        _text(name, "link name")
        _fields(link, ("ref", "sha256"), "link")
        _text(link["ref"], "link ref")
        _sha(link["sha256"], "link hash")
    _require(record["promotion"] == "NOT_GRANTED",
             "a record never grants authority (promotion must be NOT_GRANTED)")
    return record


def _repo_file(root, ref):
    path = os.path.realpath(os.path.join(root, ref))
    base = os.path.realpath(root)
    _require(path == base or path.startswith(base + os.sep),
             "ref escapes the repo root: " + ref)
    return path


def verify_bindings(record, root):
    """Re-hash every local input on disk and require every receipt to exist."""
    for binding in record["inputs"]:
        if binding["kind"] != "local-file":
            continue
        path = _repo_file(root, binding["ref"])
        _require(os.path.isfile(path), "bound input not found on disk: " + binding["ref"])
        with open(path, "rb") as fh:
            actual = hashlib.sha256(fh.read()).hexdigest()
        _require(actual == binding["digest"],
                 "input hash mismatch for " + binding["ref"] + " (bound evidence changed)")
    for ref in record["receipts"]:
        _require(os.path.isfile(_repo_file(root, ref)),
                 "receipt not found on disk: " + ref)
    return True


def load_record(path):
    with open(path, "r", encoding="utf-8") as fh:
        record = json.load(fh)
    _require(isinstance(record, dict), "record is not a JSON object")
    return record


def verify_record(path, root):
    """Load, validate and verify a decision record file. Gate scripts call this."""
    record = load_record(path)
    validate(record)
    verify_bindings(record, root)
    return record
