"""A plain user teaching is evidence to review, never an active method."""

import hashlib
import json

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
