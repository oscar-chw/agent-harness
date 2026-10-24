"""A plain user teaching is evidence to review, never an active method."""

import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

from agent_harness.capture import candidates, record
from agent_harness.weekly_intake import take


def test_nontechnical_teaching_enters_bounded_candidate_intake_without_promotion(tmp_path):
    message = "Please remember that for archive recovery, check the checksum before extraction."
    transcript = tmp_path / "synthetic.jsonl"
    transcript.write_text(json.dumps({"type": "user", "uuid": "turn-a",
                                      "message": {"content": message}}) + "\n")
    found = candidates(str(transcript))
    assert len(found) == 1
    assert found[0]["source"] == "user"
    assert found[0]["source_sha256"] == hashlib.sha256(message.encode()).hexdigest()
    home = tmp_path / ".agent-harness"
    rows = record(home, found)
    result = take(home, since=0)
    assert len(rows) == 1 and result["status"] == "CHANGED"
    assert result["candidates"][0]["count"] == 1
    assert result["promotion"] == "NOT_RUN"
    assert not (home / "procedures.sqlite").exists()


def test_neutral_user_prompt_is_not_a_teaching_candidate(tmp_path):
    transcript = tmp_path / "synthetic.jsonl"
    transcript.write_text(json.dumps({"type": "user", "uuid": "turn-b",
                                      "message": {"content": "What does checksum mean?"}}) + "\n")
    assert candidates(str(transcript)) == []


def test_teaching_candidate_masks_credential_text_before_storage(tmp_path):
    token = "sk-" + "ant-api03-" + "Q" * 30
    transcript = tmp_path / "synthetic.jsonl"
    transcript.write_text(json.dumps({"type": "user", "uuid": "turn-c",
                                      "message": {"content": "Please remember that API_KEY=" + token}}) + "\n")
    found = candidates(str(transcript))
    assert len(found) == 1
    assert token not in json.dumps(found)
    assert "[REDACTED]" in found[0]["summary"]


def test_two_projects_and_two_source_events_stay_distinct(tmp_path):
    projects = [tmp_path / "alpha", tmp_path / "bravo"]
    for project in projects:
        project.mkdir()
        (project / ".git").mkdir()
    home = tmp_path / ".agent-harness"
    message = "Please remember that for archive recovery, check the checksum first."

    def observe(project, turn):
        transcript = project / "synthetic.jsonl"
        transcript.write_text(json.dumps({"type": "user", "uuid": turn,
                                          "message": {"content": message}}) + "\n")
        found = candidates(str(transcript), project=project)
        assert len(found) == 1
        return found[0]

    first = observe(projects[0], "turn-1")
    other = observe(projects[1], "turn-2")
    assert first["project_sha256"] != other["project_sha256"]
    assert first["key"] != other["key"]
    record(home, [first, other])
    again = observe(projects[0], "turn-3")
    rows = record(home, [again, again])
    by_id = {row["id"]: row for row in rows}
    assert sorted(row["count"] for row in rows) == [1, 2]
    assert len(by_id[first["key"][:12]]["source_events"]) == 2
    intake = take(home, since=0)
    assert {item["project_sha256"] for item in intake["candidates"]} == {
        first["project_sha256"], other["project_sha256"]}
    assert not (home / "procedures.sqlite").exists()


def test_repeat_stays_dormant_for_a_fresh_client_and_irrelevant_task(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
    home = tmp_path / ".agent-harness"
    for turn in ("first", "second"):
        transcript = project / "synthetic.jsonl"
        transcript.write_text(json.dumps({"type": "user", "uuid": turn,
                                          "message": {"content": "Please remember that archive recovery needs checksum checks."}}) + "\n")
        record(home, candidates(str(transcript), project=project))
    row = json.loads((home / "candidates.jsonl").read_text())
    assert row["count"] == 2 and len(row["source_events"]) == 2
    source = Path(__file__).resolve().parents[1] / "src"
    code = ("import json,sys; from agent_harness.procedures import matches; "
            "print(json.dumps([matches(sys.argv[1],sys.argv[2],q) "
            "for q in ('archive recovery','database migration')]))")
    env = {**os.environ, "PYTHONPATH": str(source)}
    run = subprocess.run([sys.executable, "-c", code, str(home), str(project)],
                         cwd=project, env=env, capture_output=True, text=True, timeout=5)
    assert run.returncode == 0 and json.loads(run.stdout) == [[], []]


def test_capture_hook_uses_its_actual_project_cwd(tmp_path, monkeypatch):
    from agent_harness.cli import capture_hook

    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
    transcript = project / "synthetic.jsonl"
    transcript.write_text(json.dumps({"type": "user", "uuid": "turn-hook",
                                      "message": {"content": "Please remember that checks precede releases."}}) + "\n")
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HARNESS_HOME", str(home / ".agent-harness"))
    payload = {"transcript_path": str(transcript), "session_id": "fixture",
               "cwd": str(tmp_path / "somewhere-else")}
    assert capture_hook(io.StringIO(json.dumps(payload))) == 0
    row = json.loads((home / ".agent-harness/candidates.jsonl").read_text())
    assert row["project_sha256"] == hashlib.sha256(str(project).encode()).hexdigest()
