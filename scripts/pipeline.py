#!/usr/bin/env python3
"""pipeline.py -- the local evaluation pipeline runner. The local runner IS the CI.

Design: docs/v3/eval-pipeline-design-20261110.md. Six tiers in fixed order
(push -> unit -> integration -> e2e -> perf -> ship), fail-fast, tier-scoped,
one hash-bound receipt per run. Orchestrates the repo's existing surfaces
READ-ONLY; stdlib only; Python 3.9+.

    python3 scripts/pipeline.py                      all tiers, fixed order
    python3 scripts/pipeline.py --tier push [--tier unit ...]
    python3 scripts/pipeline.py --list
    python3 scripts/pipeline.py verify <receipt.json>

Exit codes: 0 PASS, 1 FAIL, 2 INCOMPLETE, 64 usage.
Verdict rules (fail-closed): any tier FAIL -> run FAIL and every later tier is
NOT_RUN; an empty tier is NOT_RUN and makes a run INCOMPLETE, never green
(the repo's own tiers/pytest.ini lesson: an empty tier must fail, not pass
vacuously); NOT_RUN with no FAIL -> INCOMPLETE.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "harness.pipeline-receipt/v1"
TIER_ORDER = ("push", "unit", "integration", "e2e", "perf", "ship")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT_DIR = ROOT / ".harness-work" / "eval-pipeline-20261110" / "runs"

# --fast unit subset (plan node 14): the highest-risk module areas, chosen per
# area below. Measured 2026-11-11: 893 tests in 40.2 s vs the full suite's
# >300 s (two 300 s timeouts; ~490 s observed across the node-13 gate runs).
FAST_UNIT_PATHS = [
    # plan/workgraph: the gating engine this pipeline reports through — state
    # machine, concurrency regressions, recording hygiene, routing, versions
    "tests/test_plan_autonomy.py",
    "tests/test_plan_concurrency_regressions.py",
    "tests/test_plan_recording_hygiene.py",
    "tests/test_plan_routing.py",
    "tests/test_plan_status_chronology.py",
    "tests/test_plan_versions.py",
    "tests/test_workgraph_routing.py",
    # (test_plan_component.py is deliberately EXCLUDED: its vendored component
    # suites are 63 s of the 110 s candidate run; plan logic stays covered by
    # the seven files above)
    # memory core: the store, concurrency, transport, project-memory scoping
    "tests/test_memory_concurrency.py",
    "tests/test_memory_consolidate.py",
    "tests/test_memory_transport.py",
    "tests/test_sandbox_memory_flow.py",
    "tests/test_project_memory_claim_support.py",
    "tests/test_project_memory_selection_boundaries.py",
    "tests/test_project_memory_source_packets.py",
    # memory forget + guard: the unlearn/relearn ledger and admission guard
    "tests/test_memory_forget.py",
    "tests/test_memory_guard.py",
    "tests/test_guard.py",
    "tests/test_guard_cases.py",
    "tests/test_guard_cross.py",
    "tests/test_guard_heldout.py",
    "tests/test_guard_recovery.py",
    # command guard: the pre-exec command checker
    "tests/test_check_guard.py",
    # kb: availability, honesty layer, caches/budgets, scope, source revision
    "tests/test_kb_availability.py",
    "tests/test_kb_honesty.py",
    "tests/test_kb_performance_cache.py",
    "tests/test_kb_read_budget.py",
    "tests/test_kb_runtime_metadata.py",
    "tests/test_kb_scope.py",
    "tests/test_kb_scope_leads.py",
    "tests/test_kb_selective_performance.py",
    "tests/test_kb_source_revision.py",
    # the pipeline itself: runner + this workstream's tier probes
    "tests/test_pipeline_runner.py",
    "tests/test_perf_probe.py",
    "tests/test_e2e_journey.py",
]


def _c(argv, timeout):
    return {"argv": argv, "timeout_s": timeout}


# -- deterministic tool resolution (plan node 19) ------------------------------
# 2026-11-11 incident: the runner built tool commands from sys.executable, so
# when the managed venv lost ruff mid-session (runtime recreated), the push tier
# died with a bare `exit 1 in 0.0s` and NO named reason; green only returned by
# invoking the whole pipeline via /usr/bin/python3. Module-invoked TOOLS (audit:
# ruff in push; pytest in unit and integration — nothing else uses `-m`) now
# resolve their interpreter deterministically, probe availability right before
# they run, and fail with the tool NAMED. Repo scripts (tamper_guard.py,
# e2e_journey.py, perf_probe.py, check_settlement.py) deliberately stay on the
# runner's own interpreter: they are repo-versioned code pinned into the receipt
# by artifact hash, needing only stdlib + the repo — not external tools.
SYSTEM_PYTHON = "/usr/bin/python3"
TOOL_ENV_VAR = "HARNESS_PIPELINE_PYTHON"
# hosted lint.yml pins ruff 0.16.10 (design doc, push-tier choice); the local
# interpreter carries 0.16.3. Policy: a MISSING tool fails the tier (named);
# a version DRIFT is recorded in the receipt and the run stays green.
RUFF_PINNED_VERSION = "0.16.10"


def _resolve_tool_python(environ=None, system_py=SYSTEM_PYTHON, fallback=None):
    """Interpreter for module-invoked tools, in strict preference order:
    (a) HARNESS_PIPELINE_PYTHON env override, (b) /usr/bin/python3 when present,
    (c) sys.executable as the last-resort fallback. Returns (path, source); the
    source string is stamped into the receipt next to the resolved path."""
    environ = os.environ if environ is None else environ
    fallback = sys.executable if fallback is None else fallback
    override = environ.get(TOOL_ENV_VAR)
    if override:
        return override, "env:%s" % TOOL_ENV_VAR
    if Path(system_py).is_file():
        return system_py, "system:%s" % system_py
    return fallback, "fallback:sys.executable"


def _tool(module, pinned=None):
    """Receipt metadata for a module-invoked tool command: the runner probes
    `import <module>` in the resolved interpreter immediately before executing,
    then records `<module> --version` output. pinned carries the hosted-lint
    pin for drift notes (None = version recorded, drift not applicable)."""
    return {"tool_module": module, "tool_version_argv": ["-m", module, "--version"],
            "tool_pinned": pinned}


def _probe_tool(spec):
    """Pre-flight a module-invoked tool in its resolved interpreter. Returns the
    receipt 'tool' record: interpreter, resolution source, availability, version,
    and (only when a pinned version differs) the version-drift note. A missing
    module produces a NAMED error ('tool ruff unavailable in <interp>: No module
    named ...'); probe crashes are fail-closed (treated as unavailable)."""
    module = spec["tool_module"]
    interp = str(spec["argv"][0])
    rec = {"module": module, "interpreter": interp,
           "resolution": spec.get("tool_resolution", "registry-unstamped")}
    if spec.get("tool_pinned"):
        rec["pinned"] = spec["tool_pinned"]
    # NOTE: no `-I` here on purpose — the probe must see the SAME import
    # environment the real `[interp, -m, module, ...]` invocation gets (ruff
    # 0.16.3 lives in the user site-packages, which -I would exclude; probing
    # isolated and running non-isolated would fail-closed on a working tool).
    try:
        p = subprocess.run([interp, "-c", "import %s" % module],
                           capture_output=True, text=True, timeout=20)
    except Exception as e:
        rec.update(available=False, error="tool %s unavailable in %s: probe failed: %s"
                   % (module, interp, e))
        return rec
    if p.returncode != 0:
        m = re.search(r"No module named [^\n]+", p.stderr or "")
        detail = m.group(0) if m else ((p.stderr or "").strip().splitlines()
                                       or ["import probe exit %d" % p.returncode])[-1]
        rec.update(available=False, error="tool %s unavailable in %s: %s" % (module, interp, detail))
        return rec
    rec["available"] = True
    try:
        v = subprocess.run([interp] + list(spec["tool_version_argv"]),
                           capture_output=True, text=True, timeout=20)
        line = ((v.stdout or "") + (v.stderr or "")).strip().splitlines()
        rec["version_raw"] = line[0] if line else ""
        rec["version"] = rec["version_raw"].split()[-1] if v.returncode == 0 and line else "unknown"
    except Exception as e:
        rec["version"] = "unknown"
        rec["version_raw"] = "version probe failed: %s" % e
    pinned = spec.get("tool_pinned")
    if pinned and rec["version"] == "unknown":
        rec["version_note"] = ("version indeterminate; drift vs pinned %s unassessed "
                               "(never fails — only a MISSING tool fails)" % pinned)
    elif pinned and rec["version"] != pinned:
        rec["version_drift"] = ("resolved %s %s != pinned %s (hosted lint pin, design doc); "
                                "drift is NOTED, the run stays green — policy: fail only on "
                                "a MISSING tool" % (module, rec["version"], pinned))
    return rec


def _staging_python():
    """tests/test_v1_staging.py builds the offline wheel with HARNESS_STAGING_PYTHON
    (falling back to the test runner's own interpreter): it needs Python 3.9+ with
    setuptools>=61 and wheel. Mirror check.sh's probe so a bare pipeline run tests
    exactly what check.sh tests — the runner's own contract, staged identically.
    Returns the interpreter path, or None (env left untouched; the staging tests
    then fail loudly on the system setuptools — the honest signal, as today)."""
    preset = os.environ.get("HARNESS_STAGING_PYTHON")
    candidates = [preset] if preset else ["python3", "python3.14", "python3.13", "python3.12",
                                          "python3.11", "python3.10", "python3.9"]
    probe = ("import importlib.metadata as m, sys; "
             "assert sys.version_info >= (3, 9) and int(m.version('setuptools').split('.')[0]) >= 61; "
             "m.version('wheel')")
    for cand in candidates:
        path = shutil.which(cand)
        if not path:
            continue
        try:
            if subprocess.run([path, "-I", "-c", probe], capture_output=True, timeout=20).returncode == 0:
                return path
        except Exception:
            continue
    return None


def default_registry(fast=False):
    """The real tier registry. Commands run with cwd=repo root, in order.

    Built lazily so tests inject stub registries and nothing here executes on
    import. Module-invoked TOOLS (ruff, pytest) run under the deterministically
    resolved tool interpreter (node 19: HARNESS_PIPELINE_PYTHON override ->
    /usr/bin/python3 -> sys.executable; each spec is stamped with the resolution
    source and probed for availability/version immediately before it runs).
    Repo scripts stay on sys.executable, the interpreter that launched the
    runner. fast=True swaps the unit tier for FAST_UNIT_PATHS (plan node 14).
    Stages HARNESS_STAGING_PYTHON into the environment (subprocesses inherit)
    so the offline-wheel tests build with a capable setuptools (node 15).
    """
    staged = _staging_python()
    if staged:
        os.environ["HARNESS_STAGING_PYTHON"] = staged
    py = sys.executable
    tpy, resolution = _resolve_tool_python()

    def _t(argv, timeout, module, pinned=None):
        return {**_c([tpy] + argv, timeout), **_tool(module, pinned),
                "tool_resolution": resolution}

    unit = (["-m", "pytest", "-q"] + FAST_UNIT_PATHS) if fast else ["-m", "pytest", "-q", "tests", "eval"]
    return {
        "push": [
            # the tamper guard runs FIRST: any test/eval-surface diff since the last
            # green run must carry a sha256-bound attestation or the tier fails here
            # (plan node 17; design doc Amendment 3)
            {**_c([py, "scripts/tamper_guard.py", "--repo", ".", "--test-command",
                   "pytest -q tests eval", "--json-out", TAMPER_VERDICT], 300),
             "evidence_file": TAMPER_VERDICT},
            _t(["-m", "ruff", "check", "--config", "ruff.toml", "."], 300, "ruff",
               pinned=RUFF_PINNED_VERSION),
            _c(["bash", "scripts/secret-scan.sh", "--tree-only"], 300),
        ],
        "unit": [_t(unit, 300 if fast else 1800, "pytest")],
        "integration": [_t(["-m", "pytest", "-q", "tests", "-m", "integration"], 900, "pytest")],
        "e2e": [_c(["bash", "scripts/demo.sh"], 900),
                _c([py, "scripts/e2e_journey.py"], 300)],
        "perf": [_c([py, "scripts/perf_probe.py"], 300)],
        "ship": [],   # verdict assembly is the runner's own job, not a command
    }


def _sha_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _artifact_hashes(argv, root):
    """Hash every argv element that resolves to an existing file under root:
    the receipt is bound to the exact bytes of every script/config it invoked."""
    out = {}
    for a in argv:
        p = (root / a).resolve() if not Path(a).is_absolute() else Path(a)
        try:
            rel = p.relative_to(root.resolve())
        except ValueError:
            continue
        if p.is_file():
            out[rel.as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


# A command may declare an evidence_file: a JSON document the command rewrites
# every run (e.g. the tamper guard's verdict, carrying the applied attestations).
# Its CONTENT is embedded into the command record ("evidence") — that embed is
# the binding. The file itself is deliberately NOT artifact-pinned: it is volatile
# by design, and hashing it would invalidate every older receipt after each run.
# The file is deleted before the command runs so stale content can never be
# mistaken for this run's evidence; a passing command that leaves no parseable
# evidence is failed as if the command itself had failed (fail-closed).
EVIDENCE_CAP_BYTES = 200000

TAMPER_VERDICT = ".harness-work/tamper-guard-verdict.json"


def _collect_evidence(spec, rec, root):
    path = root / spec["evidence_file"]
    try:
        raw = path.read_bytes()
        if len(raw) > EVIDENCE_CAP_BYTES:
            raise ValueError("evidence exceeds %d bytes" % EVIDENCE_CAP_BYTES)
        rec["evidence"] = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as e:
        rec["evidence_error"] = "evidence unreadable: %s" % e
        if rec["exit"] == 0:
            rec["exit"] = 1
            rec["stderr_tail"] = (rec.get("stderr_tail") or "") + \
                "\nevidence_file declared but not produced by a passing command (fail-closed)"


def _git(root, args):
    try:
        r = subprocess.run(["git"] + args, cwd=str(root), capture_output=True,
                           text=True, timeout=15)
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def run(selected=None, registry=None, root=ROOT, receipt_dir=DEFAULT_RECEIPT_DIR):
    """Run the selected tiers in fixed order; write the receipt; return (receipt, code)."""
    registry = registry if registry is not None else default_registry()
    root = Path(root)
    selected = list(selected) if selected else list(TIER_ORDER)
    unknown = [t for t in selected if t not in TIER_ORDER]
    if unknown:
        raise ValueError("unknown tier(s): %s (known: %s)" % (", ".join(unknown), ", ".join(TIER_ORDER)))

    started = datetime.now(timezone.utc)
    # receipts are ADDITIVE: two runs in the same second must never overwrite
    run_id = started.strftime("%Y%m%dT%H%M%SZ") + "-" + hashlib.sha256(
        str(time.time_ns()).encode()).hexdigest()[:8]
    tiers = []
    failed = False
    for name in TIER_ORDER:
        if name not in selected:
            tiers.append({"name": name, "status": "NOT_RUN", "commands": []})
            continue
        commands = registry.get(name, [])
        if failed or not commands:
            tiers.append({"name": name, "status": "NOT_RUN", "commands": []})
            continue
        entry = {"name": name, "status": "PASS", "commands": []}
        for spec in commands:
            if spec.get("evidence_file"):
                try:
                    (root / spec["evidence_file"]).unlink()  # no stale evidence from prior runs
                except FileNotFoundError:
                    pass
            t0 = time.monotonic()
            tool_rec = _probe_tool(spec) if spec.get("tool_module") else None
            if tool_rec and not tool_rec["available"]:
                # fail-closed with the tool NAMED (node 19): the command is NOT
                # executed; the tier fails here and the receipt records why —
                # never again a bare `exit 1 in 0.0s` for a missing ruff
                rec = {
                    "argv": [str(a) for a in spec["argv"]],
                    "exit": 1,
                    "timed_out": False,
                    "not_executed": True,
                    "duration_s": round(time.monotonic() - t0, 3),
                    "stdout_sha256": _sha_text(""),
                    "stderr_sha256": _sha_text(tool_rec["error"]),
                    "stdout_tail": "",
                    "stderr_tail": tool_rec["error"],
                    "artifacts": _artifact_hashes(
                        [str(a) for a in spec["argv"] if str(a) != spec.get("evidence_file")], root),
                    "tool": tool_rec,
                }
                entry["commands"].append(rec)
                print("[%s] %s -> TOOL UNAVAILABLE in %.1fs: %s"
                      % (name, " ".join(rec["argv"]), rec["duration_s"], tool_rec["error"]))
                entry["status"] = "FAIL"
                failed = True
                break  # fail-fast within the tier; unrun commands simply absent
            timed_out = False
            try:
                r = subprocess.run(spec["argv"], cwd=str(root), capture_output=True,
                                   text=True, timeout=spec["timeout_s"])
                code, out, err = r.returncode, r.stdout, r.stderr
            except subprocess.TimeoutExpired as e:
                timed_out = True
                code, out, err = -1, e.stdout or "", (e.stderr or "") + "\nTIMEOUT after %ss" % spec["timeout_s"]
                if isinstance(out, bytes):
                    out = out.decode("utf-8", "replace")
                if isinstance(err, bytes):
                    err = err.decode("utf-8", "replace")
            rec = {
                "argv": [str(a) for a in spec["argv"]],
                "exit": code,
                "timed_out": timed_out,
                "duration_s": round(time.monotonic() - t0, 3),
                "stdout_sha256": _sha_text(out),
                "stderr_sha256": _sha_text(err),
                "stdout_tail": out[-500:],
                "stderr_tail": err[-500:],
                "artifacts": _artifact_hashes(
                    [str(a) for a in spec["argv"] if str(a) != spec.get("evidence_file")], root),
            }
            if tool_rec:
                rec["tool"] = tool_rec  # resolved interpreter + version (+ drift note)
            if spec.get("evidence_file"):
                _collect_evidence(spec, rec, root)
            entry["commands"].append(rec)
            print("[%s] %s -> exit %s in %.1fs" % (name, " ".join(rec["argv"]), rec["exit"], rec["duration_s"]))
            if rec["exit"] != 0:
                entry["status"] = "FAIL"
                failed = True
                break  # fail-fast within the tier; unrun commands simply absent
        if entry["status"] == "FAIL":
            failed = True
        tiers.append(entry)

    n_fail = sum(1 for t in tiers if t["status"] == "FAIL")
    n_notrun = sum(1 for t in tiers if t["status"] == "NOT_RUN")
    verdict = "FAIL" if n_fail else ("INCOMPLETE" if n_notrun else "PASS")

    receipt = {
        "schema": SCHEMA,
        "run_id": run_id,
        "started_utc": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": {"root": str(root), "git_head": _git(root, ["rev-parse", "HEAD"]),
                 "tree_dirty": bool(_git(root, ["status", "--porcelain"]))},
        "selected": selected,
        "tiers": tiers,
        "verdict": verdict,
    }
    body = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    receipt["receipt_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()

    receipt_dir = Path(receipt_dir)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    path = receipt_dir / ("run-%s.json" % run_id)
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("receipt: %s\nverdict: %s (FAIL=%d NOT_RUN=%d)" % (path, verdict, n_fail, n_notrun))
    return receipt, {"PASS": 0, "FAIL": 1, "INCOMPLETE": 2}[verdict]


def verify(path_or_dict, root=ROOT, allow_not_run=()):
    """Re-verify a receipt: schema, tier order, status consistency, artifact
    hashes against the live tree, and the receipt self-hash. Returns (ok, errors).

    allow_not_run (adapter policy, e.g. check.sh): after all forensic checks,
    additionally require that NO tier FAILED and that every NOT_RUN tier is in
    the allowed set — a FAIL is never excused, and an unexpected empty tier
    stays visible instead of passing silently."""
    errors = []
    if isinstance(path_or_dict, dict):
        receipt = path_or_dict
    else:
        try:
            receipt = json.loads(Path(path_or_dict).read_text(encoding="utf-8"))
        except Exception as e:
            return False, ["receipt unreadable: %s" % e]
    if receipt.get("schema") != SCHEMA:
        errors.append("schema != %s" % SCHEMA)
    declared = receipt.get("receipt_sha256")
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    actual = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    if declared != actual:
        errors.append("receipt self-hash mismatch: declared %s recomputed %s" % (declared, actual))
    names = [t.get("name") for t in receipt.get("tiers", [])]
    if tuple(names) != TIER_ORDER:
        errors.append("tier order changed: %s" % names)
    seen_fail = False
    for t in receipt.get("tiers", []):
        if t.get("status") not in ("PASS", "FAIL", "NOT_RUN"):
            errors.append("tier %s bad status %s" % (t.get("name"), t.get("status")))
        if seen_fail and t.get("status") != "NOT_RUN":
            errors.append("tier %s ran after a FAIL (fail-fast violated)" % t.get("name"))
        if t.get("status") == "FAIL":
            seen_fail = True
        for c in t.get("commands", []):
            for rel, h in c.get("artifacts", {}).items():
                p = Path(root) / rel
                if not p.is_file():
                    errors.append("artifact missing: %s" % rel)
                elif hashlib.sha256(p.read_bytes()).hexdigest() != h:
                    errors.append("artifact changed since the run: %s" % rel)
    n_fail = sum(1 for t in receipt.get("tiers", []) if t.get("status") == "FAIL")
    n_notrun = sum(1 for t in receipt.get("tiers", []) if t.get("status") == "NOT_RUN")
    expect = "FAIL" if n_fail else ("INCOMPLETE" if n_notrun else "PASS")
    if receipt.get("verdict") != expect:
        errors.append("verdict %s != re-derived %s" % (receipt.get("verdict"), expect))
    if allow_not_run:
        if n_fail:
            errors.append("FAIL tiers present; --allow-not-run never excuses a FAIL")
        for t in receipt.get("tiers", []):
            if t.get("status") == "NOT_RUN" and t.get("name") not in allow_not_run:
                errors.append("tier %s NOT_RUN outside --allow-not-run %s"
                              % (t.get("name"), list(allow_not_run)))
    return (not errors), errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", nargs="?", choices=["verify"], help="verify <receipt.json>")
    ap.add_argument("receipt", nargs="?")
    ap.add_argument("--tier", action="append", dest="tiers")
    ap.add_argument("--fast", action="store_true",
                    help="unit tier runs FAST_UNIT_PATHS instead of the full suite (plan node 14)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--receipt-dir", default=str(DEFAULT_RECEIPT_DIR))
    ap.add_argument("--allow-not-run", action="append", default=[], metavar="TIER",
                    help="verify policy: accept a receipt whose NOT_RUN tiers are all listed here")
    ap.add_argument("--settle", action="append", default=[], metavar="PLAN",
                    help="opt-in settlement hooks (plan v3-settlement-plugin-loop): append one "
                    "settlement scan of PLAN (repeatable) to the push tier for this run only; "
                    "the default registry is unchanged")
    args = ap.parse_args(argv)

    if args.list:
        reg = default_registry()
        for name in TIER_ORDER:
            cmds = reg.get(name, [])
            print("%-12s %s" % (name, "%d command(s)" % len(cmds) if cmds else "EMPTY (NOT_RUN)"))
        return 0
    if args.command == "verify":
        if not args.receipt:
            print("usage: pipeline.py verify <receipt.json>", file=sys.stderr)
            return 64
        ok, errors = verify(args.receipt, allow_not_run=args.allow_not_run)
        for e in errors:
            print("FAIL— %s" % e)
        print("verify: %s" % ("OK" if ok else "FAILED"))
        return 0 if ok else 1
    try:
        registry = default_registry(fast=args.fast)
        if args.settle:
            # opt-in settlement hooks: one extra push-tier command for THIS run;
            # without the flag the registry is byte-identical to the default
            argv = [sys.executable, "scripts/check_settlement.py"]
            for plan_path in args.settle:
                argv += ["--plan", plan_path]
            registry["push"] = list(registry["push"]) + [_c(argv, 300)]
        _, code = run(selected=args.tiers, registry=registry,
                      receipt_dir=Path(args.receipt_dir))
        return code
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 64


if __name__ == "__main__":
    sys.exit(main())
