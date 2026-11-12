#!/usr/bin/env python3
"""build_outcome_table.py — the NEEDLE outcome table generator (v0).

Design: docs/v3/jev-decision-records-20261111.md §5 (plan v3-jev-needle).
NEEDLE's rule applied to hypothesis outcomes: "if an outcome can happen, it
has a handler" — every registered track MUST appear in the emitted table;
absent rows are impossible because any binding that cannot be verified
FAILS generation instead of skipping the row.

Reads the frozen registry (docs/v3/outcome-tracks-20261111.json), re-hashes
every bound verdict doc / receipt on disk, and only then emits
docs/v3/outcome-table-20261111.md + .json (all-or-nothing, atomic writes).
The registry pins doc BYTES as of its date; legitimate later amendments take
the dated additive-amendment path — the generator never re-binds silently.

    /usr/bin/python3 scripts/build_outcome_table.py            # verify + emit
    /usr/bin/python3 scripts/build_outcome_table.py --check    # verify + regenerate + byte-compare, write nothing

Exit 0 ok / 1 verification or drift failure / 2 usage or internal error.
Stdlib only, Python 3.9+, zero network.
"""
import argparse
import hashlib
import json
import os
import sys

REGISTRY_SCHEMA = "harness.outcome-tracks/v1"
TABLE_SCHEMA = "harness.outcome-table/v1"
MAX_TEXT = 8192
EXPECTED_TRACKS = ("h1", "h2", "h3a", "h3b", "h4", "h5", "h6a", "h6b", "h6c", "v2-node4")


class TableError(Exception):
    """One verification or generation defect, named."""


def _require(condition, message):
    if not condition:
        raise TableError(message)


def _sha_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_registry(path):
    with open(path, "r", encoding="utf-8") as fh:
        registry = json.load(fh)
    _require(isinstance(registry, dict), "registry is not a JSON object")
    _require(registry.get("schema") == REGISTRY_SCHEMA, "unsupported registry schema")
    tracks = registry.get("tracks")
    _require(isinstance(tracks, list) and tracks, "registry has no tracks")
    seen = set()
    for track in tracks:
        for field in ("id", "title", "plan", "hypothesis", "criteria", "key_numbers",
                      "verdict", "bindings"):
            _require(field in track, "track missing field {}: {}".format(field, track.get("id")))
        for field in ("id", "title", "plan", "hypothesis", "criteria", "verdict"):
            _require(isinstance(track[field], str) and track[field].strip()
                     and len(track[field]) <= MAX_TEXT,
                     "invalid track {} field {}".format(track["id"], field))
        _require(track["id"] not in seen, "duplicate track id " + track["id"])
        seen.add(track["id"])
        numbers = track["key_numbers"]
        _require(isinstance(numbers, list) and numbers, "track {} has no key numbers".format(track["id"]))
        for pair in numbers:
            _require(isinstance(pair, list) and len(pair) == 2
                     and all(isinstance(p, str) and p.strip() for p in pair),
                     "invalid key-number pair in track " + track["id"])
        bindings = track["bindings"]
        _require(isinstance(bindings, list) and bindings,
                 "track {} binds no evidence".format(track["id"]))
        for binding in bindings:
            _require(set(binding) == {"path", "sha256"}, "invalid binding fields in " + track["id"])
            _require(isinstance(binding["sha256"], str)
                     and len(binding["sha256"]) == 64
                     and all(c in "0123456789abcdef" for c in binding["sha256"]),
                     "invalid binding sha256 in " + track["id"])
            ref = binding["path"]
            _require(isinstance(ref, str) and ref and not os.path.isabs(ref)
                     and ".." not in ref.split("/"),
                     "binding path must stay inside the repo: " + str(ref))
    return registry


def verify_registry(registry, root):
    """Re-hash every bound file. Any drift or absence fails the whole build —
    a row is never emitted from unverified evidence."""
    problems = []
    for track in registry["tracks"]:
        for binding in track["bindings"]:
            path = os.path.join(root, binding["path"])
            if not os.path.isfile(path):
                problems.append("{}: MISSING {}".format(track["id"], binding["path"]))
                continue
            actual = _sha_file(path)
            if actual != binding["sha256"]:
                problems.append("{}: DRIFT {} (bound {}, actual {})".format(
                    track["id"], binding["path"], binding["sha256"][:12], actual[:12]))
    return problems


def build_table(registry):
    """Deterministic table payload: a function of the registry bytes only."""
    registry_bytes = json.dumps(registry, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return {
        "schema": TABLE_SCHEMA,
        "created": registry["created"],
        "registry_sha256": hashlib.sha256(registry_bytes).hexdigest(),
        "tracks": registry["tracks"],
    }


def render_md(table):
    lines = [
        "# v3 hypothesis outcome table",
        "",
        "Generated by `scripts/build_outcome_table.py` from the frozen registry "
        "`docs/v3/outcome-tracks-20261111.json` (registry sha256 `{}`).".format(
            table["registry_sha256"]),
        "Every row's verdict doc and receipts were re-hashed and verified at "
        "generation time; drift or absence fails regeneration — no row is ever "
        "skipped silently. Do not edit by hand: amend the registry by dated, "
        "additive amendment.",
        "",
        "| track | verdict | key numbers |",
        "|---|---|---|",
    ]
    for track in table["tracks"]:
        numbers = "; ".join("{}: {}".format(k, v) for k, v in track["key_numbers"][:2])
        lines.append("| {} | {} | {} |".format(track["id"], track["verdict"], numbers))
    lines.append("")
    for track in table["tracks"]:
        lines += [
            "## {} — {}".format(track["id"], track["title"]),
            "",
            "- plan: `{}`".format(track["plan"]),
            "- hypothesis: {}".format(track["hypothesis"]),
            "- pre-registered criteria: {}".format(track["criteria"]),
            "- verdict: **{}**".format(track["verdict"]),
            "- key numbers:",
        ]
        lines += ["  - {}: {}".format(k, v) for k, v in track["key_numbers"]]
        lines.append("- verified bindings:")
        lines += ["  - `{}` sha256 `{}`".format(b["path"], b["sha256"][:12] + "…")
                  for b in track["bindings"]]
        lines.append("")
    return "\n".join(lines)


def _write_atomic(path, text):
    tmp = "{}.tmp-{}".format(path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="build_outcome_table.py")
    parser.add_argument("--root", default=".")
    parser.add_argument("--registry", default=None,
                        help="default <root>/docs/v3/outcome-tracks-20261111.json")
    parser.add_argument("--out-md", default=None,
                        help="default <root>/docs/v3/outcome-table-20261111.md")
    parser.add_argument("--out-json", default=None,
                        help="default <root>/docs/v3/outcome-table-20261111.json")
    parser.add_argument("--check", action="store_true",
                        help="verify + regenerate + byte-compare with the outputs; write nothing")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    registry_path = args.registry or os.path.join(root, "docs", "v3", "outcome-tracks-20261111.json")
    out_md = args.out_md or os.path.join(root, "docs", "v3", "outcome-table-20261111.md")
    out_json = args.out_json or os.path.join(root, "docs", "v3", "outcome-table-20261111.json")
    try:
        registry = load_registry(registry_path)
        problems = verify_registry(registry, root)
        _require(not problems, "binding verification failed: " + "; ".join(problems))
        table = build_table(registry)
        ids = [t["id"] for t in table["tracks"]]
        _require(ids == list(EXPECTED_TRACKS),
                 "row completeness: emitted tracks {} != expected {}".format(ids, list(EXPECTED_TRACKS)))
        md_text = render_md(table)
        json_text = json.dumps(table, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        if args.check:
            for path, text in ((out_md, md_text), (out_json, json_text)):
                _require(os.path.isfile(path), "--check: output missing: " + path)
                with open(path, "r", encoding="utf-8") as fh:
                    _require(fh.read() == text, "--check: output drifted: " + path)
            print("outcome table: OK — {} tracks verified against the tree; outputs "
                  "byte-identical".format(len(table["tracks"])))
            return 0
        _write_atomic(out_md, md_text)
        _write_atomic(out_json, json_text)
        print("outcome table: emitted {} tracks ({}, {})".format(
            len(table["tracks"]), os.path.basename(out_md), os.path.basename(out_json)))
        return 0
    except TableError as exc:
        print("REFUSED: {}".format(exc))
        return 1
    except (OSError, ValueError) as exc:
        print("ERROR: {}".format(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
