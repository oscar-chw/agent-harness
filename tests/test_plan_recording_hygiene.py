"""Recording hygiene for the plan tool — plan v3-eval-pipeline node 10.

The plan tool persists gate output into note lines and record files. Before
2026-11-10 it persisted verbatim, so any gate whose output named the repo root or
$HOME wrote a machine-specific absolute path into plan/ — the exact strings
secret-scan refuses as deployment identifiers. Now the RECORDED form is redacted
(<repo>/…, ~/…) while the DISPLAYED form stays verbatim.

Proves: (i) new recordings contain no absolute home/repo prefixes, end to end;
(ii) a pre-fix signed note containing an absolute path still parses and its stored
signature is preferred verbatim; (iii) redaction collapses nothing — distinct
outputs still get distinct signatures, and volatile timestamps still share one.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from agent_harness.workgraph import plan as P

PLAN_BIN = ROOT / "src" / "agent_harness" / "workgraph" / "bin" / "plan"


def test_repo_prefix_becomes_repo_token():
    out = P.redact_machine_paths("receipt: %s/.harness-work/x.json" % ROOT, str(ROOT))
    assert str(ROOT) not in out and "<repo>/.harness-work/x.json" in out


def test_home_prefix_becomes_tilde():
    out = P.redact_machine_paths("at /Users/alice/lib/x", str(ROOT), home="/Users/alice")
    assert "/Users/alice" not in out and "~/lib/x" in out


def test_repo_wins_over_home_when_nested():
    out = P.redact_machine_paths("at /Users/alice/proj/x", "/Users/alice/proj", home="/Users/alice")
    assert out == "at <repo>/x"


def test_shared_prefix_is_not_a_match():
    out = P.redact_machine_paths("/u/alice2/x and /r2/y", "/r", home="/u/alice")
    assert out == "/u/alice2/x and /r2/y"


def test_bare_prefix_at_end_and_before_punctuation():
    assert P.redact_machine_paths("in /u/alice", "/r", home="/u/alice") == "in ~"
    assert P.redact_machine_paths("in (/u/alice),", "/r", home="/u/alice") == "in (~),"


def _gate_recording(tmp, gate):
    os.makedirs(os.path.join(tmp, "plan"), exist_ok=True)
    with open(os.path.join(tmp, "plan", "g.md"), "w") as f:
        f.write("## goal: g\n- [ ] 1. rec | gate: %s\n" % gate)
    subprocess.run(["git", "init", "-q", tmp], check=True)
    env = dict(os.environ, PLAN=str(PLAN_BIN), QUIET_TESTS="1", PLAN_QUIET="1",
               HOME=os.path.join(tmp, "home"))
    env.pop("PLAN_DIR", None)
    os.makedirs(env["HOME"], exist_ok=True)
    return subprocess.run([str(PLAN_BIN), "gate", "g", "1"], cwd=tmp,
                          capture_output=True, text=True, env=env, timeout=120)


def test_new_recordings_carry_no_absolute_home_or_repo_prefixes():
    with tempfile.TemporaryDirectory() as tmp:
        r = _gate_recording(tmp, 'echo "root=$PWD home=$HOME"')
        assert r.returncode == 0, r.stdout + r.stderr
        recorded = open(os.path.join(tmp, "plan", "g.md")).read()
        records = list(Path(tmp, "plan", "g").glob("*.md"))
        assert records, "no record file written"
        recorded += "".join(p.read_text() for p in records)
        assert tmp not in recorded, "absolute repo path leaked into the record"
        assert "<repo>" in recorded, "redaction token missing from the record"
        assert tmp in r.stderr, "DISPLAY must stay verbatim — only recording is redacted"


def test_legacy_signed_note_with_absolute_path_still_verifies():
    line = ("2026-11-10T04:58:45Z exit 0 in 6s [7c6245e1] — receipt: "
            "/Users/alice/Documents/x/.harness-work/v3-h2/mutation-controls-h2.json / OK")
    m = P.NOTE_RE.search(line)
    assert m, "a pre-fix signed note no longer parses"
    assert m.group(1) == "0" and m.group(3) == "7c6245e1"
    # the stored signature is preferred verbatim over any re-derivation from text
    note = {"code": "0", "sig": "7c6245e1", "tail": "receipt: /Users/alice/x"}
    assert P._sig(note) == ("0", "7c6245e1")


def test_distinct_outputs_still_get_distinct_signatures():
    a = P.gate_signature(P.redact_machine_paths("exit 1: alpha FAILED", str(ROOT)))
    b = P.gate_signature(P.redact_machine_paths("exit 1: bravo FAILED", str(ROOT)))
    assert a != b, "redaction collapsed two different failures into one signature"


def test_volatile_reruns_of_one_failure_still_share_a_signature():
    a = P.gate_signature(P.redact_machine_paths("2026-11-10T04:58:45Z boom, %s/x" % ROOT, str(ROOT)))
    b = P.gate_signature(P.redact_machine_paths("2026-11-11T05:59:46Z boom, %s/x" % ROOT, str(ROOT)))
    assert a == b, "same failure on different days must keep one signature"
