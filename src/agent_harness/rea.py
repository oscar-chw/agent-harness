"""REA source-analysis records: schema `harness.rea-record/v1`, a fail-closed
validator, and an on-disk binding verifier.

Design: docs/v3/rea-support-design-20261111.md (plan v3-rea-support). REA =
"Reverse Engineer Anything" (docs/v3/harness-pillars-20261110.md): the adopted
discipline is that every conclusion ships with attached evidence — as a plain
first-party record, not an upstream dependency.

A record is EVIDENCE for a dependency decision (reuse / adapter / fork /
pattern-only / independent build); it never grants authority: `promotion` is
always NOT_GRANTED. Fail-closed rules: missing license refuses, an unpinned or
unhash-bound source refuses, an observed claim without bound evidence refuses
(inference presented as observed), and empty unknowns refuse — UNKNOWN is
never zero.

Stdlib only, Python 3.9+. Style follows loop_contract.py: pure validation that
raises on the first defect, with filesystem verification kept in one separate
function so the contract stays testable in memory.
"""
import hashlib
import json
import os
import re

SCHEMA = "harness.rea-record/v1"
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
PIN_RE = re.compile(r"[0-9a-f]{7,64}\Z")
DECISIONS = ("reuse", "adapter", "fork", "pattern-only", "independent-build")
CLAIM_BASIS = ("observed", "inferred")
OBSERVATION_CLASSES = ("documented", "source-observed", "measured")
BINDING_KINDS = ("local-file", "upstream-pin")
MAX_TEXT = 4096
MAX_ITEMS = 1000


class ReaError(ValueError):
    """One validation or binding defect, named."""


def _require(condition, message):
    if not condition:
        raise ReaError(message)


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


def _validate_license(value):
    _fields(value, ("spdx", "holder", "evidence"), "license")
    _text(value["spdx"], "license spdx")  # a missing license refuses the record
    _text(value["holder"], "license holder")
    ev = value["evidence"]
    _fields(ev, ("url", "doc_ref", "doc_sha256", "file_sha256"), "license evidence")
    if ev["file_sha256"] is not None:
        _sha(ev["file_sha256"], "license file hash")
        _require(ev["url"] is None and ev["doc_ref"] is None and ev["doc_sha256"] is None,
                 "license evidence: file hash or pinned-url-via-doc, not both")
    else:
        _text(ev["url"], "license evidence url")
        _text(ev["doc_ref"], "license evidence doc ref")
        _sha(ev["doc_sha256"], "license evidence doc hash")


def _validate_binding(value, pins):
    _fields(value, ("ref", "kind", "role", "digest"), "evidence binding")
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
                 and PIN_RE.fullmatch(value["digest"]) is not None,
                 "invalid upstream-pin digest")
        _require(value["digest"] in pins, "upstream-pin digest must equal the version pin")


def _validate_claim(value, bound_digests, claim_ids):
    _fields(value, ("id", "statement", "basis", "observation_class", "reasoning",
                    "evidence", "covers"), "claim")
    cid = _text(value["id"], "claim id")
    _require(cid not in claim_ids, "duplicate claim id " + cid)
    claim_ids.add(cid)
    _text(value["statement"], "claim statement")
    _require(value["basis"] in CLAIM_BASIS, "invalid claim basis")
    _text_list(value["covers"], "claim covers")
    if value["basis"] == "observed":
        _require(value["observation_class"] in OBSERVATION_CLASSES,
                 "observed claim " + cid + " needs an observation class "
                 "(documented / source-observed / measured)")
        _require(value["reasoning"] is None, "observed claim " + cid + " carries no reasoning")
        evidence = value["evidence"]
        # THE refusal that keeps inference from dressing up as observation:
        # an observed claim must cite evidence bound in evidence_bindings.
        _require(isinstance(evidence, list) and len(evidence) >= 1,
                 "observed claim " + cid + " cites no bound evidence "
                 "(inference presented as observed)")
        _require(len(evidence) <= MAX_ITEMS, "claim evidence list too long")
        for item in evidence:
            _fields(item, ("ref", "sha256", "note"), "claim evidence")
            _text(item["ref"], "claim evidence ref")
            _sha(item["sha256"], "claim evidence hash")
            _text(item["note"], "claim evidence note")
            _require(item["sha256"] in bound_digests,
                     "observed claim " + cid + " cites evidence not present in "
                     "evidence_bindings (inference presented as observed)")
    else:
        _require(value["observation_class"] is None,
                 "inferred claim " + cid + " may not claim an observation class")
        _text(value["reasoning"], "inferred claim reasoning")
        _require(isinstance(value["evidence"], list) and not value["evidence"],
                 "inferred claim " + cid + " carries evidence bindings; only "
                 "observed claims bind evidence")


def _validate_decision(value, claim_ids, claims):
    _require(isinstance(value, dict) and isinstance(value.get("type"), str)
             and value["type"] in DECISIONS, "invalid decision type")
    dtype = value["type"]
    common = ("type", "summary", "evidence")
    extras = {
        "reuse": ("license_compatible", "used_surface", "integration_cost"),
        "adapter": ("license_compatible", "used_surface", "integration_cost", "boundary_map"),
        "fork": ("license_permits_fork", "fork_reason", "maintenance_budget"),
        "pattern-only": ("paraphrase_only", "code_copied"),
        "independent-build": ("prior_exposure", "rationale"),
    }[dtype]
    _fields(value, common + extras, "decision")
    _text(value["summary"], "decision summary")
    evidence = value["evidence"]
    _require(isinstance(evidence, list) and 1 <= len(evidence) <= MAX_ITEMS,
             "decision must cite at least one claim")
    for cid in evidence:
        _require(cid in claim_ids, "decision cites unknown claim id " + str(cid))
    if dtype in ("reuse", "adapter"):
        _require(value["license_compatible"] is True,
                 "reuse/adapter requires license_compatible: true")
        surface = _text_list(value["used_surface"], "used surface", minimum=1)
        _text(value["integration_cost"], "integration cost")
        covered = set()
        for claim in claims:
            if claim["basis"] == "observed" and claim["observation_class"] in (
                    "source-observed", "measured"):
                covered.update(claim["covers"])
        for element in surface:
            _require(element in covered,
                     "used surface element %r lacks a source-observed or measured claim"
                     % element)
        if dtype == "adapter":
            _text_list(value["boundary_map"], "boundary map", minimum=1)
    elif dtype == "fork":
        _require(value["license_permits_fork"] is True,
                 "fork requires license_permits_fork: true")
        _text(value["fork_reason"], "fork reason")
        _text(value["maintenance_budget"], "maintenance budget")
    elif dtype == "pattern-only":
        _require(value["paraphrase_only"] is True, "pattern-only requires paraphrase_only: true")
        _require(value["code_copied"] is False, "pattern-only requires code_copied: false")
    else:
        _text(value["prior_exposure"], "prior exposure")
        _text(value["rationale"], "independent-build rationale")


def validate(record):
    """Raise ReaError on the first defect; return the record unchanged when valid."""
    _fields(record, ("schema", "record_id", "created", "subject", "license", "lawfulness",
                     "reading_scope", "evidence_bindings", "claims", "unknowns",
                     "decision", "integration", "promotion"), "record")
    _require(record["schema"] == SCHEMA, "unsupported record schema")
    _text(record["record_id"], "record id")
    _text(record["created"], "record date")
    subject = record["subject"]
    _fields(subject, ("name", "source_locator", "version_pin", "version_label"), "subject")
    _text(subject["name"], "subject name")
    _text(subject["source_locator"], "subject source locator")
    _require(isinstance(subject["version_pin"], str)
             and PIN_RE.fullmatch(subject["version_pin"]) is not None,
             "unpinned source version (a commit/tag digest is required; "
             "'latest' is not analyzable)")
    _text(subject["version_label"], "subject version label")
    _validate_license(record["license"])
    _fields(record["lawfulness"], ("basis",), "lawfulness")
    _text(record["lawfulness"]["basis"], "lawfulness basis")
    scope = record["reading_scope"]
    _fields(scope, ("read", "not_read"), "reading scope")
    _text_list(scope["read"], "reading scope read", minimum=1)
    _text_list(scope["not_read"], "reading scope not_read")
    bindings = record["evidence_bindings"]
    _require(isinstance(bindings, list) and 1 <= len(bindings) <= MAX_ITEMS,
             "a record must bind at least one evidence artifact (unhash-bound source)")
    seen_refs, digests = set(), set()
    for binding in bindings:
        _validate_binding(binding, {subject["version_pin"]})
        _require(binding["ref"] not in seen_refs, "duplicate binding ref " + binding["ref"])
        seen_refs.add(binding["ref"])
        if binding["kind"] == "local-file":
            digests.add(binding["digest"])
    claims = record["claims"]
    _require(isinstance(claims, list) and 1 <= len(claims) <= MAX_ITEMS, "invalid claims list")
    claim_ids = set()
    for claim in claims:
        _validate_claim(claim, digests, claim_ids)
    _text_list(record["unknowns"], "unknowns", minimum=1)  # UNKNOWN is never zero
    _validate_decision(record["decision"], claim_ids, claims)
    integration = record["integration"]
    _fields(integration, ("referenced_by",), "integration")
    _text_list(integration["referenced_by"], "referenced_by")
    _require(record["promotion"] == "NOT_GRANTED",
             "a record never grants authority (promotion must be NOT_GRANTED)")
    return record


def _repo_file(root, ref):
    """Resolve a repo-relative ref under root, refusing escapes."""
    path = os.path.realpath(os.path.join(root, ref))
    _require(path == os.path.realpath(root) or path.startswith(os.path.realpath(root) + os.sep),
             "ref escapes the repo root: " + ref)
    return path


def _check_file_sha(path, digest, label):
    _require(os.path.isfile(path), label + " not found on disk: " + path)
    with open(path, "rb") as fh:
        actual = hashlib.sha256(fh.read()).hexdigest()
    _require(actual == digest,
             label + " hash mismatch for " + path + " (bound evidence changed)")


def verify_bindings(record, root):
    """Re-hash every local binding and referenced plan on disk; fail-closed."""
    for binding in record["evidence_bindings"]:
        if binding["kind"] == "local-file":
            _check_file_sha(_repo_file(root, binding["ref"]), binding["digest"],
                            "binding " + binding["ref"])
    evidence = record["license"]["evidence"]
    if evidence["doc_ref"] is not None:
        _check_file_sha(_repo_file(root, evidence["doc_ref"]), evidence["doc_sha256"],
                        "license evidence doc")
    for ref in record["integration"]["referenced_by"]:
        path = _repo_file(root, ref)
        _require(os.path.isfile(path), "referenced_by path not found on disk: " + ref)
    return True


def load_record(path):
    with open(path, "r", encoding="utf-8") as fh:
        record = json.load(fh)
    _require(isinstance(record, dict), "record is not a JSON object")
    return record


def verify_record(path, root):
    """Load, validate and binding-verify a record file. Gate scripts call this."""
    record = load_record(path)
    validate(record)
    verify_bindings(record, root)
    return record
