"""A caller cannot promote a method by inventing scores and a grader hash."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from agent_harness import procedures

from .test_v1_learning_loop import draft, receipt


@pytest.fixture
def lab(tmp_path):
    home = tmp_path / "home"
    projects = [tmp_path / name for name in ("launcher", "alpha", "bravo")]
    home.mkdir()
    for project in projects:
        project.mkdir()
        (project / ".git").mkdir()
    return home, projects


def test_caller_written_scores_and_grader_hash_cannot_activate_a_method(lab):
    _, proposal = draft(lab)
    evidence = receipt(proposal)
    home, project = lab[0] / "harness", lab[1][1]
    # All fields and hashes are plausible, but the caller wrote every score.
    try:
        procedures.change(home, str(project), proposal["id"], evidence)
    except ValueError as error:
        assert "independent" in str(error) or "receipt" in str(error)
    else:
        raise AssertionError("caller-attested scores activated a procedure")
    assert procedures.inspect(home, str(project), proposal["id"])["status"] == "proposed"


def native_usage(tokens=10, **overrides):
    receipt = {"native_completion": "COMPLETED_UNGRADED", "task_evaluation": "NOT_RUN",
               "usage_scope": "fresh_thread_total", "usage_status": "PROVIDER_REPORTED",
               "usage_report_count": 1,
               "usage": {"input_tokens": tokens - 2, "cached_input_tokens": 1,
                         "output_tokens": 2}, "effective_model_evidence": "UNKNOWN",
               "permission_boundary": "requested_eval_profile_unverified"}
    receipt.update(overrides)
    return receipt


def test_local_binder_hashes_frozen_task_artifacts_grader_and_provider_usage(lab):
    _, proposal = draft(lab)
    home, project = lab[0] / "harness", str(lab[1][1])
    task, answer = b"task without answer", b"correct output"
    frozen = procedures.freeze_case(home, project, proposal["id"], "new-task", task, answer)
    result = procedures.bind_hold(home, project, proposal["id"], "new-task", task, answer,
                                  b"wrong output", answer, native_usage(20), native_usage(10))
    assert result["decision"] == "HOLD_UNVERIFIED_BOUNDARY"
    assert result["candidate_sha256"] == proposal["sha256"]
    assert result["task_sha256"] == frozen["task_sha256"]
    assert result["answer_sha256"] == hashlib.sha256(answer).hexdigest()
    assert result["artifacts"]["candidate_sha256"] == hashlib.sha256(answer).hexdigest()
    assert result["grader"]["version"] == "exact-bytes-v1"
    assert result["grader"]["sha256"] == hashlib.sha256(Path(procedures.__file__).read_bytes()).hexdigest()
    assert result["quality"] == {"base": 0, "candidate": 1}
    assert result["tokens"] == {"base": 20, "candidate": 10}
    assert result["usage_receipts"]["base_sha256"] == procedures.digest(native_usage(20))
    assert procedures.inspect(home, project, proposal["id"])["status"] == "proposed"
    with procedures._db(home) as con:
        row = con.execute("SELECT receipt FROM procedure_binder_receipts WHERE id=? AND task_id=?",
                          (proposal["id"], "new-task")).fetchone()
        assert row is not None and "correct output" not in row[0] and "task without answer" not in row[0]
    assert procedures.bind_hold(home, project, proposal["id"], "new-task", task, answer,
                                b"wrong output", answer, native_usage(20), native_usage(10)) == result
    # Neither a scored binder receipt nor a fabricated caller comparison can activate.
    with pytest.raises(ValueError, match="independent|receipt"):
        procedures.change(home, project, proposal["id"], result)


@pytest.mark.parametrize("fault", ["task", "answer", "incomplete-usage", "missing-artifact"])
def test_local_binder_refuses_changed_or_missing_evidence(lab, fault):
    _, proposal = draft(lab)
    home, project = lab[0] / "harness", str(lab[1][1])
    task, answer = b"frozen task", b"answer"
    procedures.freeze_case(home, project, proposal["id"], "new-task", task, answer)
    base, cand = native_usage(20), native_usage(10)
    if fault == "task":
        task = b"changed task"
    elif fault == "answer":
        answer = b"changed answer"
    elif fault == "incomplete-usage":
        cand["usage_status"] = "UNKNOWN"
    else:
        cand = None
    with pytest.raises(ValueError):
        procedures.bind_hold(home, project, proposal["id"], "new-task", task, answer,
                                     b"wrong", b"answer", base, cand)
    assert procedures.inspect(home, project, proposal["id"])["status"] == "proposed"


def test_old_caller_scored_active_row_is_quarantined_from_recall(lab):
    _, proposal = draft(lab)
    home, project = lab[0] / "harness", str(lab[1][1])
    evidence = receipt(proposal)
    with procedures._db(home) as con:
        con.execute("UPDATE procedures SET status='active',evidence=? WHERE id=?",
                    (procedures.encoded(evidence).decode(), proposal["id"]))
    assert procedures.inspect(home, project, proposal["id"])["status"] == "held_unverified"
    assert procedures.list_active(home, project) == []
    assert procedures.matches(home, project, "archive recovery") == []


def test_concurrent_same_task_retry_is_idempotent_but_conflict_is_refused(lab):
    _, proposal = draft(lab)
    home, project = lab[0] / "harness", str(lab[1][1])
    task, answer = b"frozen task", b"correct output"
    start = Barrier(6)

    def freeze(_):
        start.wait(timeout=5)
        return procedures.freeze_case(home, project, proposal["id"], "heldout", task, answer)

    # Each worker opens its own SQLite connection; a retried caller can race
    # another caller after a timeout without creating two frozen cases.
    with ThreadPoolExecutor(max_workers=6) as workers:
        freezes = list(workers.map(freeze, range(6)))
    assert all(item == freezes[0] for item in freezes)
    with procedures._db(home) as con:
        assert con.execute("SELECT count(*) FROM procedure_frozen_cases").fetchone()[0] == 1
    with pytest.raises(ValueError, match="conflict|changed"):
        procedures.freeze_case(home, project, proposal["id"], "heldout", task, b"different answer")

    start = Barrier(6)

    def bind(_):
        start.wait(timeout=5)
        return procedures.bind_hold(home, project, proposal["id"], "heldout", task, answer,
                                    b"wrong output", answer, native_usage(20), native_usage(10))

    with ThreadPoolExecutor(max_workers=6) as workers:
        receipts = list(workers.map(bind, range(6)))
    assert all(item == receipts[0] for item in receipts)
    with procedures._db(home) as con:
        assert con.execute("SELECT count(*) FROM procedure_binder_receipts").fetchone()[0] == 1
    with pytest.raises(ValueError, match="conflict|changed"):
        procedures.bind_hold(home, project, proposal["id"], "heldout", task, answer,
                             b"different output", answer, native_usage(20), native_usage(10))
    assert procedures.inspect(home, project, proposal["id"])["status"] == "proposed"


def test_quarantined_legacy_active_row_can_be_withdrawn_without_resurrection(lab):
    _, proposal = draft(lab)
    home, project = lab[0] / "harness", str(lab[1][1])
    with procedures._db(home) as con:
        con.execute("UPDATE procedures SET status='active',evidence=? WHERE id=?",
                    (procedures.encoded(receipt(proposal)).decode(), proposal["id"]))
    assert procedures.change(home, project, proposal["id"], rollback=True)["status"] == "rolled_back"
    assert procedures.inspect(home, project, proposal["id"])["status"] == "rolled_back"
    assert procedures.list_active(home, project) == []
    with pytest.raises(ValueError, match="proposed"):
        procedures.freeze_case(home, project, proposal["id"], "heldout", b"task", b"answer")
