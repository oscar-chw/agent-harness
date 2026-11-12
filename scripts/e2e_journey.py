#!/usr/bin/env python3
"""e2e_journey.py -- the pipeline's e2e tier (plan v3-eval-pipeline node 12).

Scripts four asserted lifecycles against sandboxed tmp stores (zero network,
zero model calls, nothing outside tmp mutated):

    fact_memory    Server.call_tool: mem_add -> mem_search finds -> mem_forget
                   -> absent -> re-add -> present again
    page_memory    memory_forget/memory_guard: unlearn two pages -> guard
                   refuses near-copies of both -> relearn restore one -> guard
                   admits the restored page, still refuses the other
    kb_honesty     add sources -> kb_search finds -> kb_get reads; honesty flag
                   off returns hits for a cross-vocabulary query, on returns the
                   honest miss []; same-vocabulary query keeps hits under the
                   flag (compound evidence escapes); byte-difference asserted
    plan_lifecycle workgraph bin/plan subprocess: new plan -> status 0/1 ->
                   gate -> exit 0 -> status 1/1

NOT_RUN, pre-declared in the plan node text (honest absence, not a skip):
    session_search    needs real transcripts; a sandboxed store has no session
                      history to search faithfully
    skill_promotion   held by design: promotion is a human decision, not
                      scriptable evidence

Exit 0 PASS / 1 FAIL (any journey assertion fails, loudly). Every run writes
one hash-bound receipt (harness.e2e-journey/v1); verify re-derives the verdict
and refuses silent removal of a journey or a reason-less NOT_RUN.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SCHEMA = "harness.e2e-journey/v1"
DEFAULT_RECEIPT_DIR = ROOT / ".harness-work" / "eval-pipeline-20261110" / "runs"
PLAN_BIN = ROOT / "src" / "agent_harness" / "workgraph" / "bin" / "plan"

EXPECTED_JOURNEYS = ("fact_memory", "page_memory", "kb_honesty", "plan_lifecycle")
EXPECTED_NOT_RUN = {
    "session_search": "needs real transcripts; a sandboxed store has no session history to search faithfully",
    "skill_promotion": "held by design: promotion is a human decision, not scriptable evidence",
}

ALPHA = "apple banana cherry durian elderberry fig grape melon".split()
BETA = "xenon yttrium zirconium cobalt nickel copper silver gold".split()


def _step(name, ok, detail=""):
    return {"step": name, "ok": bool(ok), "detail": detail}


def _journey(name, fn, tmp):
    """Fail-closed wrapper: an exception is a failed journey, never a skip."""
    try:
        steps = fn(tmp)
    except Exception as e:
        steps = [_step("unhandled-exception", False, repr(e))]
    return {"journey": name, "ok": all(s["ok"] for s in steps), "steps": steps}


# ------------------------------------------------------------------ journeys
def _fact_memory(tmp):
    from agent_harness.mcp.server import Server
    srv = Server(home=tmp / "srv-home")
    text = "e2e journey: the deploy key lives in the escrow vault"
    added = srv.call_tool("mem_add", {"text": text})
    mid = added.get("id")
    hits1 = srv.call_tool("mem_search", {"query": "deploy key escrow vault", "k": 5})
    found = any(h.get("id") == mid for h in hits1)
    forgotten = srv.call_tool("mem_forget", {"id": mid})
    hits2 = srv.call_tool("mem_search", {"query": "deploy key escrow vault", "k": 5})
    gone = not any(h.get("id") == mid for h in hits2)
    srv.call_tool("mem_add", {"text": text})  # re-add after the forget
    hits3 = srv.call_tool("mem_search", {"query": "deploy key escrow vault", "k": 5})
    present_again = any(h.get("text") == text for h in hits3)
    return [_step("mem_add returns an id", isinstance(mid, str) and mid.startswith("m-"), repr(added)[:120]),
            _step("search finds the new fact", found, "%d hits" % len(hits1)),
            _step("mem_forget acknowledges", forgotten.get("ok") is True, repr(forgotten)[:80]),
            _step("search after forget is absent", gone, "%d hits" % len(hits2)),
            _step("re-add present again", present_again, "%d hits" % len(hits3))]


def _page_memory(tmp):
    import random
    from agent_harness import memory_forget as mf
    from agent_harness.memory_guard import Guard
    rng = random.Random(20261111)
    vocab = ("network uplink calibration ledger escrow tombstone retrieval memory "
             "guard kernel router packet latency throughput dataset corpus index").split()
    mcorpus = tmp / "mem"
    mcorpus.mkdir()
    pages = []
    for i in range(20):
        text = "# page %d\n\n%s" % (i, " ".join(rng.choice(vocab) for _ in range(120)))
        pages.append(text)
        (mcorpus / ("p%03d.md" % i)).write_text(text, encoding="utf-8")
    escrow = tmp / "escrow"
    mf.unlearn(mcorpus, "p000.md", authority="e2e-journey", reason="journey leg one",
               escrow_dir=escrow, apply=True)
    mf.unlearn(mcorpus, "p001.md", authority="e2e-journey", reason="journey leg two",
               escrow_dir=escrow, apply=True)
    gone = not (mcorpus / "p000.md").exists() and not (mcorpus / "p001.md").exists()
    ref = [t for i, t in enumerate(pages) if i not in (0, 1)]
    guard = Guard(mcorpus, escrow_dir=escrow, reference_texts=ref)
    v0 = guard.check(pages[0], path="candidate.md")
    v1 = guard.check(pages[1], path="candidate2.md")
    novel = guard.check("# novel\n\n" + " ".join(["zzqxit", "plugh"] * 30), path="novel.md")
    rel = mf.relearn(mcorpus, "p000.md", authority="e2e-journey", reason="journey restore",
                     escrow_dir=escrow, mode="restore", apply=True)
    restored = (mcorpus / "p000.md").is_file() and (mcorpus / "p000.md").read_text() == pages[0]
    guard2 = Guard(mcorpus, escrow_dir=escrow, reference_texts=ref)
    a0 = guard2.check(pages[0], path="candidate.md")
    a1 = guard2.check(pages[1], path="candidate2.md")
    return [_step("unlearn removes both pages", gone),
            _step("guard refuses near-copy of p000", v0["admit"] is False,
                  "legs=%s" % (v0["refused"]["legs"] if v0["refused"] else None)),
            _step("guard refuses near-copy of p001", v1["admit"] is False,
                  "legs=%s" % (v1["refused"]["legs"] if v1["refused"] else None)),
            _step("guard admits genuinely novel text", novel["admit"] is True),
            _step("relearn honestly reports corpus still differs (p001 forgotten)",
                  rel.get("matches_pre_unlearn_root") is False,
                  "matches_pre_unlearn_root=%s" % rel.get("matches_pre_unlearn_root")),
            _step("restore puts the page bytes back", restored),
            _step("guard admits the restored page", a0["admit"] is True),
            _step("guard STILL refuses p001 (scoped restore)", a1["admit"] is False)]


def _kb_honesty(tmp):
    import random
    from agent_harness.mcp.server import Server
    rng = random.Random(7)
    corpus = tmp / "kb"
    corpus.mkdir()
    for i in range(40):
        vocab = ALPHA if i < 20 else BETA
        text = "# page %d\n\n%s" % (i, " ".join(rng.choice(vocab) for _ in range(150)))
        (corpus / ("page-%03d.md" % i)).write_text(text, encoding="utf-8")
    srv = Server(home=tmp / "kb-srv-home", kb_paths=[corpus])
    same = srv.call_tool("kb_search", {"query": "cherry grape", "k": 5})
    got = srv.call_tool("kb_get", {"id": same[0]["id"]}) if same else {}
    os.environ.pop("HARNESS_KB_HONESTY", None)
    cross_off = srv.call_tool("kb_search", {"query": "apple xenon", "k": 5})
    os.environ["HARNESS_KB_HONESTY"] = "1"
    cross_on = srv.call_tool("kb_search", {"query": "apple xenon", "k": 5})
    same_on = srv.call_tool("kb_search", {"query": "cherry grape", "k": 5})
    os.environ.pop("HARNESS_KB_HONESTY", None)  # never leak the flag out of the journey
    differs = json.dumps(cross_off, sort_keys=True) != json.dumps(cross_on, sort_keys=True)
    return [_step("added sources are found", len(same) >= 1, "%d hits" % len(same)),
            _step("kb_get reads the section", "# page" in got.get("text", ""), got.get("id", "")),
            _step("honesty OFF returns cross-vocabulary hits", len(cross_off) >= 1,
                  "%d hits" % len(cross_off)),
            _step("honesty ON returns the honest miss []", cross_on == []),
            _step("byte-difference between the arms", differs),
            _step("compound evidence escapes honesty (same-vocab keeps hits)", len(same_on) >= 1,
                  "%d hits" % len(same_on))]


def _plan_lifecycle(tmp):
    wg = tmp / "wg"
    wg.mkdir()
    subprocess.run(["git", "init", "-q", str(wg)], check=True, capture_output=True)
    (wg / "plan").mkdir()
    gate_cmd = '%s -c "print(\'journey-gate-ok\')"' % sys.executable
    (wg / "plan" / "g.md").write_text("## goal: g\n- [ ] 1. rec | gate: %s\n" % gate_cmd)
    env = dict(os.environ)
    env["HOME"] = str(tmp / "plan-home")
    env.pop("PLAN_DIR", None)
    env["QUIET_TESTS"] = "1"
    env["PLAN_QUIET"] = "1"

    def plan(*args):
        return subprocess.run([str(PLAN_BIN)] + list(args), cwd=str(wg), env=env,
                              capture_output=True, text=True, timeout=60)

    before = plan("status", "g")
    gated = plan("gate", "g", "1")
    after = plan("status", "g")
    return [_step("new plan status shows 0/1", before.returncode == 0 and "0/1" in before.stdout,
                  before.stdout.strip().splitlines()[0] if before.stdout.strip() else "<empty>"),
            _step("gate exits 0 and prints PASS",
                  gated.returncode == 0 and "PASS" in gated.stdout, gated.stdout.strip()[:80]),
            _step("status after gate shows 1/1", after.returncode == 0 and "1/1" in after.stdout,
                  after.stdout.strip().splitlines()[0] if after.stdout.strip() else "<empty>")]


def run_journeys():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        return [_journey("fact_memory", _fact_memory, tmp),
                _journey("page_memory", _page_memory, tmp),
                _journey("kb_honesty", _kb_honesty, tmp),
                _journey("plan_lifecycle", _plan_lifecycle, tmp)]


# ------------------------------------------------------------------- receipt
def _git(root, args):
    try:
        r = subprocess.run(["git"] + args, cwd=str(root), capture_output=True,
                           text=True, timeout=15)
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def make_receipt(journeys, kind="gating"):
    verdict = "PASS" if (all(j["ok"] for j in journeys)
                         and [j["journey"] for j in journeys] == list(EXPECTED_JOURNEYS)) else "FAIL"
    receipt = {
        "schema": SCHEMA,
        "kind": kind,
        "started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "git_head": _git(ROOT, ["rev-parse", "HEAD"]),
        "journeys": journeys,
        "not_run": [{"journey": j, "reason": r} for j, r in EXPECTED_NOT_RUN.items()],
        "verdict": verdict,
    }
    body = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    receipt["receipt_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return receipt


def verify_receipt(path_or_dict):
    """Re-verify: schema, self-hash, the full expected journey set present (a
    silently dropped journey fails here), every NOT_RUN carrying a reason, and
    the verdict re-derived from the recorded steps."""
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
    journeys = receipt.get("journeys", [])
    names = [j.get("journey") for j in journeys]
    if names != list(EXPECTED_JOURNEYS):
        errors.append("journey set changed: %s != %s" % (names, list(EXPECTED_JOURNEYS)))
    for j in journeys:
        steps = j.get("steps") or []
        if not steps:
            errors.append("journey %s has no recorded steps" % j.get("journey"))
            continue
        if any(not s.get("step") or not isinstance(s.get("ok"), bool) for s in steps):
            errors.append("journey %s has a malformed step" % j.get("journey"))
        if j.get("ok") != all(bool(s.get("ok")) for s in steps):
            errors.append("journey %s ok-flag inconsistent with its steps" % j.get("journey"))
    not_run = receipt.get("not_run", [])
    if {n.get("journey") for n in not_run} != set(EXPECTED_NOT_RUN):
        errors.append("NOT_RUN set changed: %s" % [n.get("journey") for n in not_run])
    if any(not n.get("reason") for n in not_run):
        errors.append("a NOT_RUN entry has no recorded reason")
    expect = "PASS" if (names == list(EXPECTED_JOURNEYS) and all(j.get("ok") for j in journeys)) else "FAIL"
    if receipt.get("verdict") != expect:
        errors.append("verdict %s != re-derived %s" % (receipt.get("verdict"), expect))
    return (not errors), errors


def _rehashed(receipt, **changes):
    forged = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    forged.update(changes)
    forged = json.loads(json.dumps(forged))
    body = json.dumps(forged, sort_keys=True, separators=(",", ":"))
    forged["receipt_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return forged


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--receipt-dir", default=str(DEFAULT_RECEIPT_DIR))
    args = ap.parse_args(argv)

    journeys = run_journeys()
    receipt = make_receipt(journeys)
    receipt_dir = Path(args.receipt_dir)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    run_id = receipt["started_utc"].replace("-", "").replace(":", "") + "-" + receipt["receipt_sha256"][:8]
    path = receipt_dir / ("e2e-%s.json" % run_id)
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    for j in journeys:
        print("[%s] %s" % (j["journey"], "PASS" if j["ok"] else "FAIL"))
        for s in j["steps"]:
            if not s["ok"]:
                print("  FAIL— %s (%s)" % (s["step"], s["detail"]))
    for n in receipt["not_run"]:
        print("[NOT_RUN] %s — %s" % (n["journey"], n["reason"]))
    print("receipt: %s\nverdict: %s" % (path, receipt["verdict"]))
    return 0 if receipt["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
