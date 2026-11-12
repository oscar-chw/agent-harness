#!/usr/bin/env python3
"""tamper_guard.py — push-tier test-surface guard with fail-closed attestation (v1).

Integration of .harness-work/tamper-guard-20261110/tamper_guard.py (v0 prototype,
9/9 fixture criteria) into the pipeline's push tier (plan v3-eval-pipeline node 17).
Design: docs/v3/tamper-guard-design-20261110.md + eval-pipeline-design Amendment 3.
Model-free, stdlib-only, Python 3.9-compatible.

Why not "diff vs HEAD": the working tree legitimately carries uncommitted owner
work. So the guard anchors on the LAST-GREEN surface instead: any test/eval-surface
diff since the recorded baseline is a finding, and every finding needs an attestation
on record — sha256-bound, dated, one-line reason — or the tier fails.

Baseline (.harness-work/tamper-baseline.json):
    refreshed ONLY on PASS (clean or attested), never on TRIP/NOT_RUN/ERROR, so a
    weakened tree can never become the new baseline. Bootstrap: with no baseline on
    record the anchor is the HEAD tree's surface (git show bytes), so the first run
    flags exactly the uncommitted diffs instead of silently blessing them (D7 of the
    prototype deliberately NOT inherited: blessing a dirty tree would be the naive
    diff-vs-HEAD failure mode inverted).

Findings — any diff vs baseline, per file:
    new_file / deleted_file / modified_file, with mechanical sub-signals on modified
    files: function_drop (PER-FILE, policy ON — closes the prototype's net-count
    masking blind spot; see Amendment 3), new_skip_xfail, assertion_density_drop>20%.

Attestation (.harness-work/tamper-attestations.json):
    {"schema": "harness.tamper-attestations/v1", "attestations": [
        {"path", "sha256", "reason", "noted"}, ...]}
    new/modified excused iff an entry matches path + CURRENT sha256 + non-empty reason
    deleted          excused iff an entry matches path + BASELINE sha256 + non-empty reason
    A tampered or stale-hash entry does not match -> the finding stands -> TRIP.
    Structurally invalid entries / malformed file -> ERROR (fail-closed).
    Stale entries (no matching finding) are reported, not fatal.

Exit codes: 0 PASS (baseline refreshed) / 1 TRIP (unexcused findings; baseline NOT
refreshed) / 2 NOT_RUN (empty surface, no test command) or ERROR (fail-closed).

Known blind spots (documented, accepted): value-changed assertions and fixture edits
keep the same mechanical shape — covered by the repo's mutation controls on critical
suites, not by this static guard. The receipt embeds this run's verdict JSON
(incl. every applied attestation) via the pipeline's evidence_file channel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

TOOL_NAME = "tamper_guard.py"
TOOL_VERSION = "1.0.0"
BASELINE_FORMAT = 1
ATTESTATION_SCHEMA = "harness.tamper-attestations/v1"

TEST_DIRS = ("tests/", "eval/")
DENSITY_TRIP_THRESHOLD = 0.20

EXIT_PASS = 0
EXIT_TRIP = 1
EXIT_NOT_RUN = 2

FUNC_RE = re.compile(r"^\s*(?:async\s+)?def\s+(test_[A-Za-z0-9_]+)", re.MULTILINE)
SKIP_XFAIL_RE = re.compile(
    r"@\s*(?:pytest\.mark\.(?:skip|skipif|xfail)|unittest\.skip(?:If|Unless)?)\b"
    r"|\bpytest\.(?:skip|xfail)\s*\("
    r"|\b(?:self|cls)\.skipTest\s*\("
)
ASSERT_RE = re.compile(
    r"^\s*assert\b"
    r"|\bself\.assert\w*\s*\("
    r"|\bpytest\.raises\s*\(",
    re.MULTILINE,
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class GuardError(Exception):
    """Internal failure -> exit 2 with explicit ERROR verdict (fail-closed)."""


# --------------------------------------------------------------------------- git

def _git_bytes(repo, args):
    proc = subprocess.run(["git", "-C", repo] + args, capture_output=True)
    if proc.returncode != 0:
        raise GuardError(
            "git {} failed (exit {}): {}".format(
                " ".join(args), proc.returncode,
                proc.stderr.decode("utf-8", "replace").strip() or "<no stderr>"))
    return proc.stdout


def _git_ok(repo, args):
    return subprocess.run(["git", "-C", repo] + args, capture_output=True).returncode == 0


def repo_root(path):
    if not os.path.isdir(path):
        raise GuardError("repo path does not exist or is not a directory: {}".format(path))
    if not _git_ok(path, ["rev-parse", "--is-inside-work-tree"]):
        raise GuardError("not a git work tree: {}".format(path))
    out = _git_bytes(path, ["rev-parse", "--show-toplevel"])
    return os.path.abspath(out.decode("utf-8", "surrogateescape").strip())


def head_sha(repo):
    proc = subprocess.run(["git", "-C", repo, "rev-parse", "--verify", "-q", "HEAD"],
                          capture_output=True)
    return proc.stdout.decode("ascii", "replace").strip() if proc.returncode == 0 else None


def _decode_paths(raw):
    return [c.decode("utf-8", "surrogateescape") for c in raw.split(b"\x00") if c]


def head_test_paths(repo):
    """paths tracked at HEAD under the test dirs (empty when HEAD has none)."""
    if head_sha(repo) is None:
        return []
    raw = _git_bytes(repo, ["ls-tree", "-r", "-z", "HEAD", "--"] + list(TEST_DIRS))
    out = []
    for entry in raw.split(b"\x00"):
        if not entry:
            continue
        tab = entry.find(b"\t")
        if tab != -1:
            out.append(entry[tab + 1:].decode("utf-8", "surrogateescape"))
    return sorted(out)


def enumerate_test_paths(repo):
    """HEAD tree ∪ index ∪ untracked under tests/ eval/ — -z everywhere so
    non-ASCII names are never octal-quoted (no_human's disclosed bug)."""
    paths = set(head_test_paths(repo))
    paths.update(_decode_paths(_git_bytes(repo, ["ls-files", "-z", "--"] + list(TEST_DIRS))))
    paths.update(_decode_paths(
        _git_bytes(repo, ["ls-files", "--others", "--exclude-standard", "-z", "--"] + list(TEST_DIRS))))
    return [rel for rel in sorted(paths) if os.path.isfile(os.path.join(repo, rel))]


# ------------------------------------------------------------------ surface

def analyze_bytes(data):
    text = data.decode("utf-8", "replace")
    functions = sorted(FUNC_RE.findall(text))
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "function_count": len(functions),
        "functions": functions,
        "skip_count": len(SKIP_XFAIL_RE.findall(text)),
        "assertion_count": len(ASSERT_RE.findall(text)),
    }


def analyze_file(abspath):
    with open(abspath, "rb") as fh:
        return analyze_bytes(fh.read())


def _totals(files):
    return {
        "files": len(files),
        "functions": sum(f["function_count"] for f in files.values()),
        "skips": sum(f["skip_count"] for f in files.values()),
        "assertions": sum(f["assertion_count"] for f in files.values()),
    }


def build_surface(repo):
    files = {rel: analyze_file(os.path.join(repo, rel)) for rel in enumerate_test_paths(repo)}
    return {"files": files, "totals": _totals(files)}


def build_head_surface(repo):
    """The committed test surface, from git object bytes — the bootstrap anchor."""
    files = {}
    for rel in head_test_paths(repo):
        data = _git_bytes(repo, ["show", "HEAD:" + rel])
        files[rel] = analyze_bytes(data)
    return {"files": files, "totals": _totals(files)}


# ------------------------------------------------------------------ baseline

def default_baseline_path(repo):
    return os.path.join(repo, ".harness-work", "tamper-baseline.json")


def load_baseline(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, ValueError) as exc:
        raise GuardError("baseline unreadable: {} ({})".format(path, exc))
    if not isinstance(payload, dict) or "files" not in payload or "totals" not in payload:
        raise GuardError("baseline malformed: {}".format(path))
    return payload


def save_baseline(path, repo, surface, anchor):
    payload = {
        "format": BASELINE_FORMAT,
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
        "repo": repo,
        "anchor": anchor,
        "files": surface["files"],
        "totals": surface["totals"],
    }
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    tmp = "{}.tmp-{}".format(path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)  # atomic: a crashed run never leaves half a baseline


# ------------------------------------------------------------------ compare

def compare(baseline, surface):
    """Any diff is a finding; modified files carry mechanical sub-signals.

    Per-file function_drop is always computed (policy ON): the prototype's net-only
    T1 let a drop in one file be masked by growth in another; under attestation the
    finding list is the reviewer's surface, so the drop must be first-class.
    """
    findings = []
    bfiles = baseline["files"]
    cfiles = surface["files"]

    for path in sorted(set(cfiles) - set(bfiles)):
        c = cfiles[path]
        findings.append({
            "type": "new_file", "path": path, "sha256": c["sha256"],
            "function_count": c["function_count"],
            "detail": "test file absent from the baseline ({} test function(s))".format(
                c["function_count"]),
        })

    for path in sorted(set(bfiles) - set(cfiles)):
        findings.append({
            "type": "deleted_file", "path": path, "sha256": bfiles[path]["sha256"],
            "functions_lost": bfiles[path]["function_count"],
            "detail": "test file present in the baseline is gone from the working tree",
        })

    for path in sorted(set(bfiles) & set(cfiles)):
        b, c = bfiles[path], cfiles[path]
        if b["sha256"] == c["sha256"]:
            continue
        signals = []
        if c["function_count"] < b["function_count"]:
            signals.append({
                "type": "function_drop",
                "baseline": b["function_count"], "current": c["function_count"],
                "detail": "test functions {} -> {}".format(
                    b["function_count"], c["function_count"]),
            })
        if c["skip_count"] > b["skip_count"]:
            signals.append({
                "type": "new_skip_xfail",
                "baseline": b["skip_count"], "current": c["skip_count"],
                "detail": "skip/xfail markers {} -> {}".format(b["skip_count"], c["skip_count"]),
            })
        bd = b["assertion_count"] / max(b["function_count"], 1)
        cd = c["assertion_count"] / max(c["function_count"], 1)
        if bd > 0:
            drop = (bd - cd) / bd
            if drop > DENSITY_TRIP_THRESHOLD:
                signals.append({
                    "type": "assertion_density_drop",
                    "baseline_density": round(bd, 4), "current_density": round(cd, 4),
                    "detail": "assertion density {:.3f} -> {:.3f} ({:.1f}% drop, threshold 20%)".format(
                        bd, cd, drop * 100.0),
                })
        findings.append({
            "type": "modified_file", "path": path, "sha256": c["sha256"],
            "baseline_sha256": b["sha256"],
            "function_count": [b["function_count"], c["function_count"]],
            "skip_count": [b["skip_count"], c["skip_count"]],
            "assertion_count": [b["assertion_count"], c["assertion_count"]],
            "signals": signals,
            "detail": "test file bytes differ from the baseline ({} sub-signal(s))".format(
                len(signals)),
        })
    return findings


# ------------------------------------------------------------- attestation

def default_attestation_path(repo):
    return os.path.join(repo, ".harness-work", "tamper-attestations.json")


def load_attestations(path):
    """Missing file -> zero attestations (recorded). Malformed -> ERROR."""
    if not os.path.isfile(path):
        return [], False
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, ValueError) as exc:
        raise GuardError("attestation file unreadable: {} ({})".format(path, exc))
    if not isinstance(payload, dict) or payload.get("schema") != ATTESTATION_SCHEMA \
            or not isinstance(payload.get("attestations"), list):
        raise GuardError("attestation file malformed or wrong schema: {}".format(path))
    entries = []
    for i, e in enumerate(payload["attestations"]):
        if not isinstance(e, dict) or not isinstance(e.get("path"), str) \
                or not isinstance(e.get("sha256"), str) or not SHA256_RE.match(e["sha256"]) \
                or not isinstance(e.get("reason"), str) or not e["reason"].strip() \
                or not isinstance(e.get("noted"), str) or not e["noted"].strip():
            raise GuardError("attestation entry {} structurally invalid "
                             "(needs path, 64-hex sha256, non-empty reason, noted)".format(i))
        entries.append(e)
    return entries, True


def excuse_findings(findings, entries):
    """Split findings into excused/unexcused; report stale entries. A finding is
    excused only by an entry matching path AND the finding's reference sha256
    (current bytes for new/modified, baseline bytes for deleted)."""
    by_path = {}
    for e in entries:
        by_path.setdefault(e["path"], []).append(e)
    excused, unexcused, applied = [], [], []
    for f in findings:
        match = next((e for e in by_path.get(f["path"], []) if e["sha256"] == f["sha256"]), None)
        if match:
            excused.append(f)
            applied.append({"path": f["path"], "sha256": f["sha256"],
                            "finding": f["type"],
                            "signals": [s["type"] for s in f.get("signals", [])],
                            "reason": match["reason"], "noted": match["noted"]})
        else:
            unexcused.append(f)
    finding_keys = {(f["path"], f["sha256"]) for f in findings}
    stale = [{"path": e["path"], "sha256": e["sha256"], "reason": e["reason"]}
             for e in entries if (e["path"], e["sha256"]) not in finding_keys]
    return excused, unexcused, applied, stale


# ------------------------------------------------------------ test command

def detect_test_command(repo, explicit):
    if explicit:
        return explicit, "argument"
    probes = (("pytest.ini", None), ("pyproject.toml", "[tool.pytest"),
              ("tox.ini", "[pytest]"), ("setup.cfg", "[tool:pytest]"))
    for name, needle in probes:
        p = os.path.join(repo, name)
        if not os.path.isfile(p):
            continue
        if needle is None:
            return "pytest (via {})".format(name), name
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                if needle in fh.read():
                    return "pytest (via {})".format(name), name
        except OSError:
            continue
    return None, None


# ------------------------------------------------------------------ report

def _fmt_finding(f):
    if f["type"] == "new_file":
        return "new_file: {} ({})".format(f["path"], f["detail"])
    if f["type"] == "deleted_file":
        return "deleted_file: {} ({} test function(s) lost)".format(f["path"], f["functions_lost"])
    sig = "; ".join(s["detail"] for s in f.get("signals", [])) or "counts unchanged"
    return "modified_file: {} ({})".format(f["path"], sig)


def emit(verdict, json_out=None):
    lines = ["tamper-guard {} — repo: {}".format(TOOL_VERSION, verdict["repo"])]
    totals = verdict.get("totals")
    if totals is not None:
        lines.append("surface: {} file(s), {} test function(s), {} skip/xfail marker(s), "
                     "{} assertion(s)".format(totals["files"], totals["functions"],
                                              totals["skips"], totals["assertions"]))
    if verdict.get("test_command"):
        lines.append("test command: {} [{}]".format(verdict["test_command"],
                                                    verdict.get("test_command_source")))
    anchor = verdict.get("baseline_anchor") or {}
    lines.append("baseline: {} (anchor {} {}, {})".format(
        verdict.get("baseline_path"), anchor.get("kind", "?"),
        (anchor.get("head") or "")[:12],
        "refreshed" if verdict.get("baseline_refreshed") else "not refreshed"))
    v = verdict["verdict"]
    if v == "PASS":
        applied = verdict.get("applied_attestations", [])
        if applied:
            lines.append("VERDICT: PASS (attested — {} finding(s) excused by recorded attestation)"
                         .format(len(applied)))
            for a in applied:
                lines.append("  excused: {} {} — {} (noted {})".format(
                    a["finding"], a["path"], a["reason"], a["noted"]))
        else:
            lines.append("VERDICT: PASS ({})".format(verdict.get("note", "no diff vs baseline")))
    elif v == "TRIP":
        lines.append("VERDICT: TRIP")
        for f in verdict.get("findings_unexcused", []):
            lines.append("  - " + _fmt_finding(f))
        lines.append("  baseline NOT refreshed; record each diff in tamper-attestations.json "
                     "(path + sha256 + reason) to pass")
    elif v == "NOT_RUN":
        lines.append("VERDICT: NOT_RUN — {}".format(verdict.get("reason", "<no reason>")))
    else:
        lines.append("VERDICT: ERROR — {}".format(verdict.get("reason", "<no reason>")))
    stale = verdict.get("stale_attestations")
    if stale:
        lines.append("stale attestations (no matching finding; informational): {}".format(len(stale)))
    text = "\n".join(lines)
    print(text)
    if json_out:
        out_dir = os.path.dirname(os.path.abspath(json_out))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(json_out, "w", encoding="utf-8") as fh:
            json.dump(verdict, fh, indent=2, sort_keys=True, ensure_ascii=False)
            fh.write("\n")


# --------------------------------------------------------------------- main

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Push-tier test-surface guard with fail-closed attestation "
                    "(plan v3-eval-pipeline node 17).")
    parser.add_argument("--repo", default=".", help="git work-tree root (default: cwd)")
    parser.add_argument("--baseline", default=None,
                        help="baseline path (default: <repo>/.harness-work/tamper-baseline.json)")
    parser.add_argument("--attestation", default=None,
                        help="attestation path (default: <repo>/.harness-work/tamper-attestations.json)")
    parser.add_argument("--test-command", default=None,
                        help="gate test command (recorded; absence of any command -> NOT_RUN)")
    parser.add_argument("--json-out", default=None, help="write machine-readable verdict JSON here")
    parser.add_argument("--no-refresh", action="store_true",
                        help="never refresh the baseline (control runs against copied state)")
    args = parser.parse_args(argv)

    verdict = {"tool": TOOL_NAME, "tool_version": TOOL_VERSION,
               "timestamp": datetime.now(timezone.utc).isoformat(),
               "verdict": None, "exit_code": None}
    try:
        repo = repo_root(os.path.abspath(args.repo))
        baseline_path = args.baseline or default_baseline_path(repo)
        attestation_path = args.attestation or default_attestation_path(repo)
        verdict.update({"repo": repo, "baseline_path": baseline_path,
                        "attestation_path": attestation_path})

        surface = build_surface(repo)
        verdict["totals"] = surface["totals"]

        if surface["totals"]["files"] == 0:
            verdict.update({"verdict": "NOT_RUN", "exit_code": EXIT_NOT_RUN,
                            "reason": "no test files found under tests/ or eval/ (empty test surface)",
                            "baseline_refreshed": False})
            emit(verdict, args.json_out)
            return EXIT_NOT_RUN

        command, source = detect_test_command(repo, args.test_command)
        verdict["test_command"] = command
        verdict["test_command_source"] = source
        if command is None:
            verdict.update({"verdict": "NOT_RUN", "exit_code": EXIT_NOT_RUN,
                            "reason": "no test command configured (pass --test-command or add pytest configuration)",
                            "baseline_refreshed": False})
            emit(verdict, args.json_out)
            return EXIT_NOT_RUN

        baseline = load_baseline(baseline_path)
        if baseline is None:
            # Bootstrap anchor: the COMMITTED surface, never the dirty tree.
            baseline_surface = build_head_surface(repo)
            anchor = {"kind": "head", "head": head_sha(repo)}
            verdict["note"] = "baseline initialized from the HEAD tree (no prior baseline on record)"
        else:
            baseline_surface = {"files": baseline["files"], "totals": baseline["totals"]}
            anchor = baseline.get("anchor") or {"kind": "unknown"}
        verdict["baseline_anchor"] = anchor
        verdict["baseline_totals"] = baseline_surface["totals"]

        entries, attestation_present = load_attestations(attestation_path)
        verdict["attestation_present"] = attestation_present

        findings = compare(baseline_surface, surface)
        verdict["findings"] = findings
        if not findings:
            # Byte-stability: persist the bootstrap, and persist convergence after an
            # attested pass — but a clean pass over an already-current baseline must
            # not rewrite it (a timestamp-only rewrite would churn receipt evidence).
            need_write = baseline is None or baseline_surface["files"] != surface["files"]
            refreshed = bool(not args.no_refresh and need_write)
            if refreshed:
                save_baseline(baseline_path, repo, surface,
                              {"kind": "surface", "head": head_sha(repo)})
            verdict.update({"verdict": "PASS", "exit_code": EXIT_PASS,
                            "baseline_refreshed": refreshed,
                            "applied_attestations": []})
            if not need_write:
                verdict["note"] = "no diff vs baseline; baseline already current"
            if entries:
                _, _, _, stale = excuse_findings(findings, entries)
                verdict["stale_attestations"] = stale
            emit(verdict, args.json_out)
            return EXIT_PASS

        excused, unexcused, applied, stale = excuse_findings(findings, entries)
        verdict["stale_attestations"] = stale
        verdict["applied_attestations"] = applied
        if unexcused:
            verdict.update({"verdict": "TRIP", "exit_code": EXIT_TRIP,
                            "findings_unexcused": unexcused,
                            "findings_excused": [f["path"] for f in excused],
                            "baseline_refreshed": False})
            emit(verdict, args.json_out)
            return EXIT_TRIP

        if not args.no_refresh:
            save_baseline(baseline_path, repo, surface, {"kind": "surface", "head": head_sha(repo)})
        verdict.update({"verdict": "PASS", "exit_code": EXIT_PASS, "attested": True,
                        "baseline_refreshed": not args.no_refresh})
        emit(verdict, args.json_out)
        return EXIT_PASS

    except GuardError as exc:
        verdict.update({"verdict": "ERROR", "exit_code": EXIT_NOT_RUN,
                        "reason": str(exc), "baseline_refreshed": False})
        verdict.setdefault("repo", os.path.abspath(args.repo))
        verdict.setdefault("baseline_path", args.baseline or "<unknown>")
        emit(verdict, args.json_out)
        return EXIT_NOT_RUN


if __name__ == "__main__":
    sys.exit(main())
