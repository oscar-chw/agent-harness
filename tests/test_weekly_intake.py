"""Bounded on-demand intake of changed evidence; no model run or promotion."""
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"


def candidate(identity, count=1, last="2026-01-01T00:00:00"):
    return {"id": identity, "key": identity + "abcd", "source": "gate",
            "summary": "A check failed and later passed", "evidence": "fixture failure line",
            "count": count, "first": "2026-01-01T00:00:00", "last": last}


def save(home, rows):
    hh = home / ".agent-harness"
    hh.mkdir(exist_ok=True)
    (hh / "candidates.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))


def intake(home, *args):
    env = dict(os.environ, PYTHONPATH=str(SRC), PYTHONNOUSERSITE="1")
    run = subprocess.run([sys.executable, "-m", "agent_harness.cli", "--home", str(home),
                          "improve", "--weekly-intake", "--json", *args],
                         cwd=home, env=env, capture_output=True, text=True, timeout=10)
    return run.returncode, json.loads(run.stdout) if run.returncode == 0 else run.stdout + run.stderr


def test_weekly_intake_advances_only_delivered_changes_with_a_bounded_audit(tmp_path):
    save(tmp_path, [candidate("first"), candidate("second", last="2026-01-02T00:00:00")])
    rc, one = intake(tmp_path, "--since", "0", "--max-items", "1", "--max-output-bytes", "1024")
    assert rc == 0, one
    assert one["status"] == "CHANGED" and [x["id"] for x in one["candidates"]] == ["first"]
    assert one["cursor"] == 1 and one["remaining"] == 1 and one["output_bytes"] <= 1024
    assert one["promotion"] == "NOT_RUN"
    rc, two = intake(tmp_path, "--since", "1", "--max-items", "1", "--max-output-bytes", "1024")
    assert rc == 0 and [x["id"] for x in two["candidates"]] == ["second"] and two["cursor"] == 2
    rc, quiet = intake(tmp_path, "--since", "2", "--max-items", "1", "--max-output-bytes", "1024")
    assert rc == 0 and quiet["status"] == "NO_CHANGE" and quiet["cursor"] == 2
    assert quiet["candidates"] == []
    assert intake(tmp_path, "--since", "1")[0] != 0  # stale reader cannot advance the cursor

    # A repeated observation is a candidate, never an activated method.
    save(tmp_path, [candidate("first", count=2, last="2026-01-03T00:00:00"),
                    candidate("second", last="2026-01-02T00:00:00")])
    rc, repeat = intake(tmp_path, "--since", "2", "--max-items", "1")
    assert rc == 0 and repeat["candidates"][0]["count"] == 2
    raw = subprocess.run([sys.executable, "-m", "agent_harness.cli", "--home", str(tmp_path),
                          "improve", "--weekly-intake", "--json", "--since", "3"],
                         cwd=tmp_path, env=dict(os.environ, PYTHONPATH=str(SRC)),
                         capture_output=True, text=True, timeout=10)
    assert raw.returncode == 0 and len(raw.stdout.encode("utf-8")) == json.loads(raw.stdout)["output_bytes"]
    plain = subprocess.run([sys.executable, "-m", "agent_harness.cli", "--home", str(tmp_path),
                            "improve", "--weekly-intake", "--since", "3"],
                           cwd=tmp_path, env=dict(os.environ, PYTHONPATH=str(SRC)),
                           capture_output=True, text=True, timeout=10)
    assert plain.returncode == 0 and len(plain.stdout.encode("utf-8")) == json.loads(plain.stdout)["output_bytes"]
    assert not (tmp_path / ".agent-harness/procedures.sqlite").exists()
    assert not (tmp_path / ".agent-harness/proposals").exists()
    audit = tmp_path / ".agent-harness/weekly-intake/intake.sqlite"
    assert audit.is_file() and audit.stat().st_size < 1024 * 1024
    with sqlite3.connect(audit) as db:
        bodies = " ".join(row[0] for row in db.execute("SELECT body FROM receipts"))
        receipt = json.loads(db.execute("SELECT body FROM receipts ORDER BY seq DESC LIMIT 1").fetchone()[0])
    assert "fixture failure line" not in bodies and "A check failed" not in bodies
    canonical = json.dumps(receipt, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical).hexdigest() == repeat["receipt_sha256"]


def test_weekly_intake_holds_on_rewound_corrupt_or_unbounded_input(tmp_path):
    save(tmp_path, [candidate("one", count=2)])
    assert intake(tmp_path, "--since", "0")[0] == 0
    save(tmp_path, [candidate("one", count=1)])
    rc, rewind = intake(tmp_path, "--since", "1")
    assert rc != 0 and "count_rewind" in rewind
    save(tmp_path, [candidate("one", count=2)])
    rc, tiny = intake(tmp_path, "--since", "1", "--max-output-bytes", "120")
    assert rc != 0 and "budget" in tiny
    with (tmp_path / ".agent-harness/candidates.jsonl").open("a") as stream:
        stream.write("{broken JSON\n")
    rc, malformed = intake(tmp_path, "--since", "1")
    assert rc != 0 and "invalid_candidate" in malformed
    save(tmp_path, [candidate("one", count=2), {**candidate("bad"), "source": "untrusted"}])
    rc, invalid = intake(tmp_path, "--since", "1")
    assert rc != 0 and "invalid_candidate" in invalid
    save(tmp_path, [candidate("one", count=2)])
    rc, evicted = intake(tmp_path, "--since", "1")
    assert rc == 0 and evicted["status"] == "NO_CHANGE"
    save(tmp_path, [candidate("different")])
    rc, lost = intake(tmp_path, "--since", "1")
    assert rc != 0 and "source_evicted" in lost


def test_disappeared_capture_store_is_not_a_false_no_change(tmp_path):
    save(tmp_path, [candidate("one")])
    assert intake(tmp_path, "--since", "0")[0] == 0
    (tmp_path / ".agent-harness/candidates.jsonl").unlink()
    rc, missing = intake(tmp_path, "--since", "1")
    assert rc != 0 and "source_missing" in missing
    external = tmp_path / "external.jsonl"
    external.write_text(json.dumps(candidate("outside")) + "\n")
    (tmp_path / ".agent-harness/candidates.jsonl").symlink_to(external)
    rc, redirected = intake(tmp_path, "--since", "1")
    assert rc != 0 and "source_redirected" in redirected


def test_audit_receipts_are_bounded_without_losing_the_current_cursor(tmp_path):
    from agent_harness.weekly_intake import take
    home = tmp_path / ".agent-harness"
    for number in range(1, 55):
        save(tmp_path, [candidate("one", count=number, last=f"2026-01-01T00:00:{number:02d}")])
        result = take(home, since=number - 1)
        assert result["cursor"] == number and result["status"] == "CHANGED"
    with sqlite3.connect(home / "weekly-intake/intake.sqlite") as db:
        count = db.execute("SELECT count(*) FROM receipts").fetchone()[0]
        last = db.execute("SELECT max(seq) FROM receipts").fetchone()[0]
    assert count == 52 and last == 54
    assert take(home, since=54)["status"] == "NO_CHANGE"


def test_a_real_capture_summary_can_exceed_the_evidence_line_limit(tmp_path):
    row = candidate("long-check")
    row["summary"] = "`" + "a" * 300 + "` failed, then passed after a change"
    save(tmp_path, [row])
    raw = subprocess.run([sys.executable, "-m", "agent_harness.cli", "--home", str(tmp_path),
                          "improve", "--weekly-intake", "--since", "0",
                          "--max-output-bytes", "512"],
                         cwd=tmp_path, env=dict(os.environ, PYTHONPATH=str(SRC)),
                         capture_output=True, text=True, timeout=10)
    assert raw.returncode == 0, raw.stdout + raw.stderr
    result = json.loads(raw.stdout)
    assert result["candidates"][0]["id"] == "long-check"
    assert len(raw.stdout.encode("utf-8")) == result["output_bytes"] <= 512
    assert len(result["candidates"][0]["summary"]) <= 120
    conflict = subprocess.run([sys.executable, "-m", "agent_harness.cli", "--home", str(tmp_path),
                               "improve", "--weekly-intake", "--apply", "anything", "--since", "1"],
                              cwd=tmp_path, env=dict(os.environ, PYTHONPATH=str(SRC)),
                              capture_output=True, text=True, timeout=10)
    assert conflict.returncode != 0 and "cannot also" in conflict.stdout


def test_two_weekly_readers_cannot_deliver_the_same_row_twice(tmp_path):
    save(tmp_path, [candidate("one")])
    cmd = [sys.executable, "-m", "agent_harness.cli", "--home", str(tmp_path),
           "improve", "--weekly-intake", "--json", "--since", "0"]
    env = dict(os.environ, PYTHONPATH=str(SRC), PYTHONNOUSERSITE="1")
    readers = [subprocess.Popen(cmd, cwd=tmp_path, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
    results = [reader.communicate(timeout=10) for reader in readers]
    assert sorted(reader.returncode for reader in readers) == [0, 1], results
    with sqlite3.connect(tmp_path / ".agent-harness/weekly-intake/intake.sqlite") as db:
        assert db.execute("SELECT count(*) FROM receipts").fetchone()[0] == 1


def test_a_redirected_audit_database_is_refused(tmp_path):
    save(tmp_path, [candidate("one")])
    store = tmp_path / ".agent-harness/weekly-intake"
    store.mkdir()
    external = tmp_path / "outside.sqlite"
    store.joinpath("intake.sqlite").symlink_to(external)
    rc, result = intake(tmp_path, "--since", "0")
    assert rc != 0 and "redirected" in result
    assert not external.exists()


def test_a_directory_at_the_capture_path_is_not_reported_as_no_change(tmp_path):
    source = tmp_path / ".agent-harness/candidates.jsonl"
    source.parent.mkdir()
    source.mkdir()
    rc, result = intake(tmp_path, "--since", "0")
    assert rc != 0 and "invalid_candidate" in result
