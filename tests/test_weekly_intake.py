"""Bounded on-demand intake of changed evidence; no model run or promotion."""
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


SRC = Path(__file__).resolve().parents[1] / "src"


def cli_env():
    # Other suite fixtures may install into a separate HARNESS_HOME. These
    # subprocesses intentionally exercise only their own temporary --home.
    return {**{k: v for k, v in os.environ.items() if not k.startswith("HARNESS_")},
            "PYTHONPATH": str(SRC), "PYTHONNOUSERSITE": "1"}


def candidate(identity, count=1, last="2026-01-01T00:00:00"):
    return {"id": identity, "key": identity + "abcd", "source": "gate",
            "summary": "A check failed and later passed", "evidence": "fixture failure line",
            "count": count, "first": "2026-01-01T00:00:00", "last": last}


def save(home, rows):
    hh = home / ".agent-harness"
    hh.mkdir(exist_ok=True)
    (hh / "candidates.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))


def intake(home, *args):
    run = subprocess.run([sys.executable, "-m", "agent_harness.cli", "--home", str(home),
                          "improve", "--weekly-intake", "--json", *args],
                         cwd=home, env=cli_env(), capture_output=True, text=True, timeout=10)
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
                         cwd=tmp_path, env=cli_env(),
                         capture_output=True, text=True, timeout=10)
    assert raw.returncode == 0 and len(raw.stdout.encode("utf-8")) == json.loads(raw.stdout)["output_bytes"]
    plain = subprocess.run([sys.executable, "-m", "agent_harness.cli", "--home", str(tmp_path),
                            "improve", "--weekly-intake", "--since", "3"],
                           cwd=tmp_path, env=cli_env(),
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
                         cwd=tmp_path, env=cli_env(),
                         capture_output=True, text=True, timeout=10)
    assert raw.returncode == 0, raw.stdout + raw.stderr
    result = json.loads(raw.stdout)
    assert result["candidates"][0]["id"] == "long-check"
    assert len(raw.stdout.encode("utf-8")) == result["output_bytes"] <= 512
    assert len(result["candidates"][0]["summary"]) <= 120
    conflict = subprocess.run([sys.executable, "-m", "agent_harness.cli", "--home", str(tmp_path),
                               "improve", "--weekly-intake", "--apply", "anything", "--since", "1"],
                              cwd=tmp_path, env=cli_env(),
                              capture_output=True, text=True, timeout=10)
    assert conflict.returncode != 0 and "cannot also" in conflict.stdout


def test_two_weekly_readers_cannot_deliver_the_same_row_twice(tmp_path):
    save(tmp_path, [candidate("one")])
    cmd = [sys.executable, "-m", "agent_harness.cli", "--home", str(tmp_path),
           "improve", "--weekly-intake", "--json", "--since", "0"]
    env = cli_env()
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


def test_fixture_targets_its_own_home_despite_external_harness_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_HOME", str(tmp_path / "unrelated"))
    save(tmp_path, [candidate("local")])
    rc, result = intake(tmp_path, "--since", "0")
    assert rc == 0 and [item["id"] for item in result["candidates"]] == ["local"]
    assert not (tmp_path / "unrelated").exists()


def test_intake_continues_after_verified_capture_retention(tmp_path, monkeypatch):
    from agent_harness.storage import CAPS, prune
    from agent_harness.weekly_intake import take

    save(tmp_path, [candidate("previous", count=3)])
    home = tmp_path / ".agent-harness"
    first = take(home, since=0)
    assert first["cursor"] == 1 and first["candidates"][0]["id"] == "previous"
    save(tmp_path, [candidate("previous", count=3), candidate("new-a"), candidate("new-b")])
    monkeypatch.setitem(CAPS, "candidates", 2)
    prune(home)
    assert "previous" not in (home / "candidates.jsonl").read_text()
    after = take(home, since=1, max_items=1)
    assert after["status"] == "CHANGED" and after["cursor"] == 2
    assert after["retired_count"] == 1 and [x["id"] for x in after["candidates"]] == ["new-a"]
    assert after["promotion"] == "NOT_RUN"
    next_ = take(home, since=2)
    assert next_["cursor"] == 3 and [x["id"] for x in next_["candidates"]] == ["new-b"]
    assert "retired_count" not in next_
    assert take(home, since=3)["status"] == "NO_CHANGE"
    with sqlite3.connect(home / "weekly-intake/intake.sqlite") as db:
        receipt = json.loads(db.execute("SELECT body FROM receipts WHERE seq=2").fetchone()[0])
        assert receipt["retired_count"] == 1 and '"previous"' not in json.dumps(receipt)
    assert not (home / "procedures.sqlite").exists()



@pytest.mark.parametrize("timing", ["before", "after", "drift"])
def test_retirement_recovery_distinguishes_interrupted_write_and_drift(tmp_path, monkeypatch, timing):
    from agent_harness import weekly_intake
    from agent_harness.storage import CAPS, prune

    save(tmp_path, [candidate("previous")])
    home = tmp_path / ".agent-harness"
    assert weekly_intake.take(home)["cursor"] == 1
    old, fresh = candidate("previous"), candidate("latest")
    save(tmp_path, [old, fresh])
    monkeypatch.setitem(CAPS, "candidates", 1)
    replace = weekly_intake._durable_replace

    def interrupted(path, content):
        if path.name != "candidates.jsonl":
            return replace(path, content)
        if timing != "before":
            replace(path, content)
        raise OSError("retention fixture interruption")

    with monkeypatch.context() as fault:
        fault.setattr(weekly_intake, "_durable_replace", interrupted)
        prune(home)
    pending = home / "weekly-intake/retention-pending.json"
    assert pending.is_file() and "fixture failure line" not in pending.read_text()
    if timing == "drift":
        save(tmp_path, [candidate("unverified")])
        with pytest.raises(ValueError, match="retention_source_drift"):
            weekly_intake.take(home, since=1)
        assert pending.is_file()
        with sqlite3.connect(home / "weekly-intake/intake.sqlite") as db:
            assert db.execute("SELECT max(seq) FROM receipts").fetchone()[0] == 1
        return

    code, observed = intake(tmp_path, "--since", "1")
    assert code == 0, observed
    assert observed["cursor"] == 2 and [row["id"] for row in observed["candidates"]] == ["latest"]
    assert observed.get("retired_count", 0) == (1 if timing == "after" else 0)
    assert not pending.exists()
    assert weekly_intake.take(home, since=2)["status"] == "NO_CHANGE"


def test_retirement_only_is_reported_and_reappearance_starts_new_evidence(tmp_path, monkeypatch):
    from agent_harness.storage import CAPS, prune
    from agent_harness.weekly_intake import take

    save(tmp_path, [candidate("previous", count=3), candidate("still-here")])
    home = tmp_path / ".agent-harness"
    assert take(home, since=0)["cursor"] == 1
    monkeypatch.setitem(CAPS, "candidates", 1)
    prune(home)
    after = take(home, since=1)
    assert after["cursor"] == 2 and after["retired_count"] == 1 and not after["candidates"]
    assert take(home, since=2)["status"] == "NO_CHANGE"
    save(tmp_path, [candidate("still-here"), candidate("previous", count=1)])
    reappeared = take(home, since=2)
    assert reappeared["cursor"] == 3
    assert reappeared["candidates"][0]["id"] == "previous" and reappeared["candidates"][0]["count"] == 1
    assert reappeared["promotion"] == "NOT_RUN"


def test_retention_check_is_cheap_below_the_existing_cap(tmp_path, monkeypatch):
    from agent_harness import weekly_intake
    from agent_harness.storage import prune

    save(tmp_path, [candidate("one")])
    home = tmp_path / ".agent-harness"
    assert weekly_intake.take(home)["cursor"] == 1
    source = home / "candidates.jsonl"
    before = source.read_bytes()

    def unexpected_parse(*args):
        raise AssertionError("a routine capture prune must skip candidate parsing below the cap")

    monkeypatch.setattr(weekly_intake, "_rows", unexpected_parse)
    prune(home)
    assert before == source.read_bytes()
    assert not (home / "weekly-intake/retention-pending.json").exists()


def test_accepted_retirement_does_not_authorize_other_missing_rows(tmp_path, monkeypatch):
    from agent_harness.storage import CAPS, prune
    from agent_harness.weekly_intake import take

    old, current, fresh = candidate("old"), candidate("current"), candidate("fresh")
    hh = tmp_path / ".agent-harness"
    save(tmp_path, [old, current])
    assert take(hh)["cursor"] == 1
    save(tmp_path, [old, current, fresh])
    monkeypatch.setitem(CAPS, "candidates", 2)
    prune(hh)
    save(tmp_path, [fresh])
    with pytest.raises(ValueError, match="source_evicted"):
        take(hh, since=1)
    save(tmp_path, [current, fresh])
    restored = take(hh, since=1)
    assert restored["cursor"] == 2 and restored["retired_count"] == 1
    assert [row["id"] for row in restored["candidates"]] == ["fresh"]


def test_closed_output_stream_leaves_candidate_and_cursor_for_the_next_reader(tmp_path):
    save(tmp_path, [candidate("waiting")])
    command = [sys.executable, "-m", "agent_harness.cli", "--home", str(tmp_path),
               "improve", "--weekly-intake", "--since", "0"]
    reader, writer = os.pipe()
    os.close(reader)
    try:
        failed = subprocess.run(command, cwd=tmp_path, env=cli_env(), stdout=writer,
                                stderr=subprocess.PIPE, text=True, timeout=10)
    finally:
        os.close(writer)
    assert failed.returncode != 0

    rc, redelivered = intake(tmp_path, "--since", "0")
    assert rc == 0, redelivered
    assert redelivered["status"] == "CHANGED" and redelivered["cursor"] == 1
    assert [row["id"] for row in redelivered["candidates"]] == ["waiting"]

    rc, quiet = intake(tmp_path, "--since", "1")
    assert rc == 0 and quiet["status"] == "NO_CHANGE" and quiet["candidates"] == []
    with sqlite3.connect(tmp_path / ".agent-harness/weekly-intake/intake.sqlite") as db:
        assert db.execute("SELECT count(*) FROM receipts").fetchone()[0] == 1
