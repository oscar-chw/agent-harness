#!/usr/bin/env python3
"""perf_probe.py -- the pipeline's perf tier (plan v3-eval-pipeline node 11).

Measures four probe surfaces against seeded, deterministic fixtures in tmp
sandboxes (zero network, zero model calls):

    kb_search                 fts5/bm25 search over a 200-page fixture corpus
    guard_admission           memory_guard admission over a 132-doc reference (H6b shape)
    mcp_roundtrip             in-process Server.call_tool mem_search round-trip
    runner_overhead_*         pipeline-runner self-overhead, subprocess + in-process

THRESHOLDS LOCKED PRE-GATE (plan node 11 text): 3x the p95 of the calibration
run (.harness-work/eval-pipeline-20261110/perf-calibration-20261111.json),
applied to the p95 of the fresh gating sample set so a transient spike cannot
flake the gate. The gate is a regression tripwire, not an H6b re-enactment
(H6b's 7.7 ms was a real-corpus measure; ours is a same-shape fixture).

Exit 0 PASS / 1 FAIL (any probe's p95 over its locked threshold, loudly).
Every run writes one hash-bound receipt (harness.perf-probe/v1).
--self-test demonstrates both directions on synthetic samples: green passes,
a synthetic slowdown FAILs, and tampered receipts are refused by verify.
"""
import argparse
import contextlib
import hashlib
import io
import json
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

SCHEMA = "harness.perf-probe/v1"
CALIBRATION = ROOT / ".harness-work" / "eval-pipeline-20261110" / "perf-calibration-20261111.json"
DEFAULT_RECEIPT_DIR = ROOT / ".harness-work" / "eval-pipeline-20261110" / "runs"

# LOCKED before the first gating run: 3x calibration p95 (plan node 11).
THRESHOLDS_P95_MS = {
    "kb_search": 56.0,                    # calib p95 18.51 ms
    "guard_admission": 2.1,               # calib p95 0.693 ms
    "mcp_roundtrip": 1.8,                 # calib p95 0.577 ms (max 3.67 absorbed by p95-not-max)
    "runner_overhead_subprocess": 215.0,  # calib p95 71.45 ms
    "runner_overhead_inprocess": 62.0,    # calib p95 20.59 ms
}

WORDS = ("network uplink calibration ledger escrow tombstone retrieval memory guard "
         "kernel router packet latency throughput dataset corpus index token vector "
         "snapshot receipt ledger verify archive restore snapshot module server client "
         "buffer cache pipeline benchmark fixture sandbox profile schema storage sync").split()


def gen_pages(n, words_per=160, seed=20261111):
    import random
    rng = random.Random(seed)
    return ["# page %d\n\n%s" % (i, " ".join(rng.choice(WORDS) for _ in range(words_per)))
            for i in range(n)]


def stats(samples):
    s = sorted(samples)
    return {"n": len(s), "min_ms": round(s[0], 3),
            "p50_ms": round(statistics.median(s), 3),
            "p95_ms": round(s[max(0, int(0.95 * len(s)) - 1)], 3),
            "max_ms": round(s[-1], 3),
            "mean_ms": round(statistics.fmean(s), 3)}


def evaluate(probes):
    """Compare each probe's p95 against its locked threshold. FAIL-CLOSED:
    a missing probe or a missing p95 is a violation, never a skip."""
    violations = []
    for name, limit in THRESHOLDS_P95_MS.items():
        st = probes.get(name)
        if not isinstance(st, dict):
            violations.append({"probe": name, "error": "probe missing from results"})
            continue
        p95 = st.get("p95_ms")
        if not isinstance(p95, (int, float)):
            violations.append({"probe": name, "error": "p95_ms missing"})
        elif p95 > limit:
            violations.append({"probe": name, "p95_ms": p95, "threshold_p95_ms": limit})
    return violations


def _git(root, args):
    try:
        r = subprocess.run(["git"] + args, cwd=str(root), capture_output=True,
                           text=True, timeout=15)
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def make_receipt(probes, violations, kind="gating"):
    receipt = {
        "schema": SCHEMA,
        "kind": kind,
        "started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "git_head": _git(ROOT, ["rev-parse", "HEAD"]),
        "thresholds_p95_ms": dict(THRESHOLDS_P95_MS),
        "probes": probes,
        "violations": violations,
        "verdict": "PASS" if not violations else "FAIL",
    }
    body = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    receipt["receipt_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return receipt


def verify_receipt(path_or_dict):
    """Re-verify a perf receipt: schema, self-hash, thresholds still equal the
    locked constants (a receipt written against relaxed thresholds is refused),
    every probe present with a numeric p95, and the recorded verdict re-derived
    from the recorded numbers — a self-consistent hash over a lying verdict
    still fails here. Returns (ok, errors)."""
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
    if receipt.get("thresholds_p95_ms") != THRESHOLDS_P95_MS:
        errors.append("thresholds differ from the locked constants")
    probes = receipt.get("probes", {})
    rederived = evaluate(probes)
    if [v.get("probe") for v in rederived] != [v.get("probe") for v in receipt.get("violations", [])]:
        errors.append("recorded violations do not match the recorded probe numbers")
    expect = "PASS" if not rederived else "FAIL"
    if receipt.get("verdict") != expect:
        errors.append("verdict %s != re-derived %s" % (receipt.get("verdict"), expect))
    return (not errors), errors


def run_probes():
    """The real measurement. Same probe code and sample counts as the
    calibration run; fixtures seeded; everything under a tmp sandbox."""
    from agent_harness.mcp import kb as kbmod
    from agent_harness.mcp.server import Server
    from agent_harness import memory_forget as mf
    from agent_harness.memory_guard import Guard
    import pipeline

    probes = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # (i) KB search over a 200-page fixture corpus (seed 20261111)
        corpus = tmp / "kb"
        corpus.mkdir()
        for i, text in enumerate(gen_pages(200)):
            (corpus / ("page-%03d.md" % i)).write_text(text, encoding="utf-8")
        fts = kbmod.fts5_available()
        k = kbmod.KB(home=tmp / "home", paths=[corpus], fts=fts)
        queries = ["uplink calibration", "ledger escrow verify", "rare vector token",
                   "pipeline benchmark", "tombstone restore", "kernel router packet",
                   "snapshot archive sync", "corpus index schema"]
        for q in queries:  # warm-up
            k.search(q, k=5)
        samples = []
        for rep in range(240):
            q = queries[rep % len(queries)]
            t0 = time.perf_counter()
            k.search(q, k=5)
            samples.append((time.perf_counter() - t0) * 1000)
        probes["kb_search"] = stats(samples)
        probes["kb_search"]["backend"] = "fts5" if fts else "bm25"
        probes["kb_search"]["corpus_pages"] = 200

        # (ii) memory_guard admission over a 132-doc reference (H6b shape, seed 42)
        mcorpus = tmp / "mem"
        mcorpus.mkdir()
        pages = gen_pages(133, seed=42)
        for i, text in enumerate(pages):
            (mcorpus / ("p%03d.md" % i)).write_text(text, encoding="utf-8")
        escrow = tmp / "escrow"
        mf.unlearn(mcorpus, "p000.md", authority="perf-probe", reason="perf fixture",
                   escrow_dir=escrow, apply=True)
        ref = [t for i, t in enumerate(pages) if i != 0]
        guard = Guard(mcorpus, escrow_dir=escrow, reference_texts=ref)
        candidate = "# novel\n\n" + " ".join(["zzqxit", "plugh", "frob"] * 40)
        guard.check(candidate, path="candidate.md")  # warm-up
        samples = []
        for _ in range(200):
            t0 = time.perf_counter()
            guard.check(candidate, path="candidate.md")
            samples.append((time.perf_counter() - t0) * 1000)
        probes["guard_admission"] = stats(samples)
        probes["guard_admission"]["reference_docs"] = 132

        # (iii) MCP in-process round-trip on a sandbox store
        srv = Server(home=tmp / "mcp-home")
        srv.call_tool("mem_add", {"text": "perf probe fact about uplink calibration"})
        srv.call_tool("mem_search", {"query": "calibration", "k": 5})  # warm-up
        samples = []
        for _ in range(300):
            t0 = time.perf_counter()
            srv.call_tool("mem_search", {"query": "calibration", "k": 5})
            samples.append((time.perf_counter() - t0) * 1000)
        probes["mcp_roundtrip"] = stats(samples)

        # (iv) runner self-overhead. The subprocess arm scopes to --tier ship
        # (EMPTY by design: promotion stays human) so it measures interpreter +
        # runner + receipt with no work — scoping to perf would recurse into
        # this probe now that the perf tier is wired.
        samples = []
        for _ in range(30):
            t0 = time.perf_counter()
            subprocess.run([sys.executable, str(ROOT / "scripts" / "pipeline.py"),
                            "--tier", "ship", "--receipt-dir", str(tmp / "runs")],
                           capture_output=True, text=True)
            samples.append((time.perf_counter() - t0) * 1000)
        probes["runner_overhead_subprocess"] = stats(samples)
        samples = []
        empty = {t: [] for t in pipeline.TIER_ORDER}
        with contextlib.redirect_stdout(io.StringIO()):  # 200 receipt prints stay out of the report
            for _ in range(200):
                t0 = time.perf_counter()
                pipeline.run(registry=empty, root=tmp, receipt_dir=tmp / "ipruns")
                samples.append((time.perf_counter() - t0) * 1000)
        probes["runner_overhead_inprocess"] = stats(samples)
    return probes


def _rehashed(receipt, **changes):
    """A sophisticated forgery: change fields AND recompute the self-hash, so
    only the semantic checks in verify_receipt can catch it."""
    forged = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    forged.update(changes)
    forged = json.loads(json.dumps(forged))  # deep copy through json
    body = json.dumps(forged, sort_keys=True, separators=(",", ":"))
    forged["receipt_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return forged


def self_test():
    """Both directions on SYNTHETIC samples (fast, deterministic):
    green passes; a synthetic slowdown FAILs; three forgeries are refused."""
    green_probes = {p: {"n": 50, "min_ms": 0.1, "p50_ms": limit / 4, "p95_ms": limit / 2,
                        "max_ms": limit, "mean_ms": limit / 3}
                    for p, limit in THRESHOLDS_P95_MS.items()}
    ok = True

    def expect(cond, label):
        nonlocal ok
        print("self-test %-42s %s" % (label, "ok" if cond else "FAILED"))
        ok = ok and cond

    # green direction
    expect(evaluate(green_probes) == [], "green: synthetic samples all pass")
    green = make_receipt(green_probes, [], kind="self-test")
    gok, gerr = verify_receipt(green)
    expect(gok and not gerr, "green: honest PASS receipt verifies")

    # red direction 1: synthetic slowdown -> FAIL verdict, receipt still faithful
    red = json.loads(json.dumps(green_probes))
    red["kb_search"]["p95_ms"] = THRESHOLDS_P95_MS["kb_search"] * 10
    v = evaluate(red)
    expect([x["probe"] for x in v] == ["kb_search"], "red: synthetic slowdown names kb_search")
    red_rc = make_receipt(red, v, kind="self-test")
    rok, _ = verify_receipt(red_rc)
    expect(red_rc["verdict"] == "FAIL" and rok, "red: honest FAIL receipt verifies as faithful")

    # red direction 2: crude tamper (edit after hashing) -> self-hash catches it
    crude = json.loads(json.dumps(green))
    crude["probes"]["kb_search"]["p95_ms"] = 0.001
    cok, cerr = verify_receipt(crude)
    expect(not cok and any("self-hash" in e for e in cerr), "red: edited-after-hash refused")

    # red direction 3: rehashed lying verdict -> semantic check catches it
    forged = _rehashed(red_rc, verdict="PASS")
    fok, ferr = verify_receipt(forged)
    expect(not fok and any("verdict" in e for e in ferr), "red: rehashed PASS-over-FAIL refused")

    # red direction 4: rehashed relaxed thresholds -> threshold binding catches it
    relaxed = dict(THRESHOLDS_P95_MS, kb_search=1e9)
    forged2 = _rehashed(green, thresholds_p95_ms=relaxed)
    t2ok, t2err = verify_receipt(forged2)
    expect(not t2ok and any("threshold" in e for e in t2err), "red: relaxed thresholds refused")

    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--self-test", action="store_true",
                    help="synthetic both-directions check; no real probes")
    ap.add_argument("--receipt-dir", default=str(DEFAULT_RECEIPT_DIR))
    args = ap.parse_args(argv)

    if args.self_test:
        return 0 if self_test() else 1

    probes = run_probes()
    violations = evaluate(probes)
    receipt = make_receipt(probes, violations)
    receipt_dir = Path(args.receipt_dir)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    run_id = receipt["started_utc"].replace("-", "").replace(":", "") + "-" + receipt["receipt_sha256"][:8]
    path = receipt_dir / ("perf-%s.json" % run_id)
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    print("%-28s %6s %8s %8s %9s  %s" % ("probe", "n", "p50_ms", "p95_ms", "limit_ms", "verdict"))
    for name in THRESHOLDS_P95_MS:
        st = probes.get(name, {})
        bad = any(v.get("probe") == name for v in violations)
        print("%-28s %6s %8s %8s %9s  %s" % (
            name, st.get("n", "?"), st.get("p50_ms", "?"), st.get("p95_ms", "?"),
            THRESHOLDS_P95_MS[name], "EXCEEDED" if bad else "ok"))
    for v in violations:
        print("FAIL— %s" % json.dumps(v, sort_keys=True))
    print("receipt: %s\nverdict: %s" % (path, receipt["verdict"]))
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
