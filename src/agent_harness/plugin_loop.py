"""DSH-pattern plugin admission loop: discovery → qualification → typed
decision → fail-closed admission, with a hash-bound registry.

Design: docs/v3/settlement-plugin-loop-design-20261111.md (plan
v3-settlement-plugin-loop). DSH (docs/v3/oss-mechanics-20261110.md): every
capability is a mounted plugin — this module adopts the ADMISSION discipline
for external capabilities, not the Cordis runtime (rejected per the sweep).

Schemas: `harness.plugin-candidate/v1` (the discovery descriptor),
`harness.plugin-registry/v1` (the registry), entries carrying
`harness.plugin-admission/v1`. The loop is a pipeline of named stages, each
fail-closed (NEEDLE: every outcome has a handler — refusals are first-class
registry entries):

1. qualification — an REA record (`harness.rea-record/v1`) is REQUIRED:
   the candidate's declared sha256 must equal the file's current bytes, then
   rea.validate + rea.verify_bindings must pass on disk. No REA record
   refuses.
2. typed decision — a JEV record (`harness.jev-decision/v1`) is REQUIRED:
   declared sha256 must match, jev.validate + jev.verify_bindings must pass,
   domain must be `adoption`, and subject.name must equal the candidate
   name. No JEV adoption decision refuses.
3. admission — the verdict must equal the candidate's admit_verdict exactly;
   confidence must meet policy.execute_at_or_above (ordinal: low < medium <
   high). Below threshold ESCALATES — refused, never auto-admitted.

A registry entry never grants authority: promotion is always NOT_GRANTED —
admission is repo-local residency, not a tier promotion. Malformed
candidates/registries raise PluginLoopError (usage defects); stage refusals
return refused entries (auditable outcomes). Stdlib only, Python 3.9+.
"""
import hashlib
import json
import os

from agent_harness import jev
from agent_harness import rea

SCHEMA_CANDIDATE = "harness.plugin-candidate/v1"
SCHEMA_REGISTRY = "harness.plugin-registry/v1"
SCHEMA_ENTRY = "harness.plugin-admission/v1"
KINDS = ("plugin", "skill", "adapter", "pattern")
STATUSES = ("admitted", "refused")
CONFIDENCE_ORDINAL = {"low": 0, "medium": 1, "high": 2}
MAX_TEXT = 4096
SHA256_LEN = 64


class PluginLoopError(ValueError):
    """One candidate/registry defect, named (stage refusals are entries,
    not exceptions)."""


def _require(condition, message):
    if not condition:
        raise PluginLoopError(message)


def _text(value, label):
    _require(isinstance(value, str) and bool(value.strip()) and len(value) <= MAX_TEXT,
             "invalid " + label)
    return value


def _binding(value, label):
    _require(isinstance(value, dict) and set(value) == {"ref", "sha256"},
             "invalid " + label + " binding fields")
    ref = _text(value["ref"], label + " ref")
    _require(not os.path.isabs(ref) and ".." not in ref.split("/"),
             label + " ref must stay inside the repo: " + ref)
    _require(isinstance(value["sha256"], str)
             and len(value["sha256"]) == SHA256_LEN
             and all(c in "0123456789abcdef" for c in value["sha256"]),
             "invalid " + label + " sha256")


def validate_candidate(candidate):
    """Raise PluginLoopError on the first defect; return the candidate."""
    _require(isinstance(candidate, dict)
             and set(candidate) == {"schema", "name", "kind", "rea", "jev",
                                    "admit_verdict"},
             "invalid candidate fields")
    _require(candidate["schema"] == SCHEMA_CANDIDATE, "unsupported candidate schema")
    _text(candidate["name"], "candidate name")
    _require(candidate["kind"] in KINDS, "invalid candidate kind")
    _binding(candidate["rea"], "rea")
    _binding(candidate["jev"], "jev")
    _text(candidate["admit_verdict"], "admit verdict")
    return candidate


def _check_declared_hash(root, binding, label):
    """The declared sha256 must equal the file's current bytes (drift =
    tampered or stale evidence; fail-closed). Returns the absolute path."""
    path = os.path.realpath(os.path.join(root, binding["ref"]))
    base = os.path.realpath(root)
    _require(path == base or path.startswith(base + os.sep),
             label + " ref escapes the repo root: " + binding["ref"])
    _require(os.path.isfile(path), label + " not found on disk: " + binding["ref"])
    with open(path, "rb") as fh:
        actual = hashlib.sha256(fh.read()).hexdigest()
    _require(actual == binding["sha256"],
             label + " hash drift for " + binding["ref"] +
             " (declared bytes no longer on disk)")
    return path


def _entry(candidate, status, detail, decision=None, admitted_at=None):
    return {"schema": SCHEMA_ENTRY,
            "name": candidate["name"],
            "kind": candidate["kind"],
            "status": status,
            "rea": dict(candidate["rea"]),
            "jev": dict(candidate["jev"]),
            "verdict": decision["verdict"] if decision else None,
            "confidence": decision["confidence"]["level"] if decision else None,
            "detail": detail[:MAX_TEXT],
            "admitted_at": admitted_at if status == "admitted" else None,
            "promotion": "NOT_GRANTED"}


def admit(candidate, root, admitted_at):
    """Run the admission loop for one candidate. Returns a registry entry:
    status admitted or refused with the stage's named reason. Raises
    PluginLoopError only for malformed candidates (usage defects)."""
    validate_candidate(candidate)
    name = candidate["name"]
    # ---- qualification: the REA record is REQUIRED -------------------------
    try:
        rea_path = _check_declared_hash(root, candidate["rea"], "REA record")
        rea.verify_record(rea_path, root)
    except (PluginLoopError, rea.ReaError, OSError, ValueError) as exc:
        return _entry(candidate, "refused",
                      "qualification refused (no REA record or invalid one): "
                      + str(exc))
    # ---- typed decision: the JEV adoption record is REQUIRED ---------------
    try:
        jev_path = _check_declared_hash(root, candidate["jev"], "JEV record")
        decision = jev.verify_record(jev_path, root)
        _require(decision["domain"] == "adoption",
                 "JEV record domain is %r, not adoption" % decision["domain"])
        _require(decision["subject"]["name"] == name,
                 "JEV record decides %r, not this capability %r"
                 % (decision["subject"]["name"], name))
    except (PluginLoopError, jev.JevError, OSError, ValueError) as exc:
        return _entry(candidate, "refused",
                      "typed decision refused (no JEV adoption decision or "
                      "invalid one): " + str(exc))
    # ---- admission: verdict and confidence, escalate below threshold -------
    if decision["verdict"] != candidate["admit_verdict"]:
        return _entry(candidate, "refused",
                      "verdict %r is not the admitting verdict %r"
                      % (decision["verdict"], candidate["admit_verdict"]),
                      decision=decision)
    threshold = decision["policy"]["execute_at_or_above"]
    level = decision["confidence"]["level"]
    if CONFIDENCE_ORDINAL[level] < CONFIDENCE_ORDINAL[threshold]:
        return _entry(candidate, "refused",
                      "ESCALATED: confidence {} is below the policy threshold "
                      "{} — routed to human review, never auto-admitted".format(
                          level, threshold),
                      decision=decision)
    return _entry(candidate, "admitted",
                  "admitted: REA-qualified, JEV adoption verdict {!r} at {} "
                  "confidence (threshold {})".format(
                      decision["verdict"], level, threshold),
                  decision=decision, admitted_at=admitted_at)


def load_registry(path):
    """Missing file → an empty registry; malformed file → PluginLoopError."""
    if not os.path.isfile(path):
        return {"schema": SCHEMA_REGISTRY, "entries": []}
    with open(path, "r", encoding="utf-8") as fh:
        registry = json.load(fh)
    _require(isinstance(registry, dict)
             and set(registry) == {"schema", "entries"}
             and registry["schema"] == SCHEMA_REGISTRY
             and isinstance(registry["entries"], list),
             "invalid registry: " + path)
    for entry in registry["entries"]:
        _require(isinstance(entry, dict)
                 and entry.get("schema") == SCHEMA_ENTRY
                 and entry.get("status") in STATUSES
                 and entry.get("promotion") == "NOT_GRANTED",
                 "invalid registry entry in " + path)
    return registry


def append_entry(registry, entry):
    """One entry per name. Re-admission with IDENTICAL bindings and status is
    idempotent (gates re-run); any other duplicate refuses — amendments are
    new dated registry files."""
    for existing in registry["entries"]:
        if existing["name"] != entry["name"]:
            continue
        same = (existing["rea"] == entry["rea"] and existing["jev"] == entry["jev"]
                and existing["status"] == entry["status"]
                and existing["verdict"] == entry["verdict"])
        _require(same,
                 "duplicate capability name %r with changed bindings or status — "
                 "amend via a new dated registry" % entry["name"])
        return registry, False
    registry["entries"].append(entry)
    return registry, True


def write_registry(path, registry):
    """Atomic all-or-nothing write (the outcome-table idiom)."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(registry, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)
    return registry
