"""Synthetic contract tests, not evidence of model transfer or token improvement.

The evaluator receipts below are test fixtures. Real promotion still requires a
matched, independently graded native campaign; no native campaign is run here.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from . import test_memory_transport as transport
from .test_memory_transport import SRC, exchange, value
from .test_v1_prompt_recall import prompt

lab = transport.lab

def cli(lab, *args, project=None):
    home, projects = lab
    env = {k: v for k, v in os.environ.items() if not k.startswith("HARNESS_")}
    env.update(HOME=str(home), HARNESS_HOME=str(home / "harness"), PYTHONPATH=str(SRC))
    return subprocess.run([sys.executable, "-m", "agent_harness.cli", "improve", *args,
                           "--project", str(project or projects[1])],
                          cwd=projects[0], env=env, text=True, capture_output=True, timeout=10)


def candidate_input(lab):
    alpha = lab[1][1]
    episodes = []
    for n in (1, 2):
        source = alpha / ("episode-%d.json" % n)
        raw = json.dumps({"task": "development-%d" % n, "before": 1, "after": 0}).encode()
        source.write_bytes(raw)
        task = alpha / ("task-%d.json" % n)
        task.write_text(json.dumps({"prompt": "Recover the archive", "fixture": n}))
        episodes.append({"task_id": "development-%d" % n, "path": source.name,
                         "sha256": hashlib.sha256(raw).hexdigest(), "task_path": task.name,
                         "task_sha256": hashlib.sha256(task.read_bytes()).hexdigest()})
    candidate = {"schema": 1, "title": "Archive recovery", "trigger": "archive recovery",
                 "steps": ["Validate the archive checksum before extracting.",
                           "Restore into a temporary directory and compare the inventory."],
                 "exceptions": ["Do not use for a live database."],
                 "episodes": episodes}
    return candidate


def draft(lab):
    alpha = lab[1][1]
    candidate = candidate_input(lab)
    path = alpha / "candidate.json"
    path.write_text(json.dumps(candidate))
    result = cli(lab, "--draft-procedure", str(path))
    assert result.returncode == 0, result.stdout + result.stderr
    return candidate, json.loads(result.stdout)


def receipt(candidate):
    # Same task/model/effort/tools/budget; disjoint from development episodes.
    result = {"schema": 1, "candidate_sha256": candidate["sha256"],
            "project": candidate["project"], "usage_complete": True,
            "comparison": "without-procedure", "grader_sha256": "a" * 64,
            "context": {"model": "fixture-model", "effort": "fixture", "tools_sha256": "b" * 64,
                        "budget": 4000, "benchmark_sha256": "c" * 64},
            "base_context": {"model": "fixture-model", "effort": "fixture", "tools_sha256": "b" * 64,
                             "budget": 4000, "benchmark_sha256": "c" * 64},
            "overhead_tokens": 10,
            "pairs": [
                {"task_id": "unseen-A", "class": "recovery", "split": "heldout",
                 "base": {"quality": {"correctness": 0, "integrity": 1}, "tokens": 100},
                 "cand": {"quality": {"correctness": 1, "integrity": 1}, "tokens": 80}},
                {"task_id": "unseen-B", "class": "recovery", "split": "heldout",
                 "base": {"quality": {"correctness": 1, "integrity": 1}, "tokens": 100},
                 "cand": {"quality": {"correctness": 1, "integrity": 1}, "tokens": 80}}]}
    for pair in result["pairs"]:
        task = Path(candidate["project"]) / (pair["task_id"] + ".json")
        task.write_text(json.dumps({"prompt": "Recover the archive", "fixture": pair["task_id"]}))
        pair.update(task_path=task.name, task_sha256=hashlib.sha256(task.read_bytes()).hexdigest())
    return result


def apply(lab, proposal, evidence):
    path = lab[1][1] / "comparison.json"
    path.write_text(json.dumps(evidence))
    return cli(lab, "--apply", proposal["id"], "--eval", str(path))


def synthetic_active(lab, proposal, evidence, *, project=None):
    """Seed only the active-state consumer fixture; never model promotion evidence.

    The production change path must refuse caller-written scores. We still
    exercise recall, source staleness, compact and rollback against an active
    row, without adding a runtime test bypass.
    """
    from agent_harness import procedures
    home = lab[0] / "harness"
    procedures.evaluate(proposal, evidence)  # keep arithmetic contract coverage
    with procedures._db(home) as con:
        con.execute("UPDATE procedures SET status='active',evidence=? WHERE id=? AND project=?",
                    (procedures.encoded(evidence).decode(), proposal["id"],
                     str(project or lab[1][1])))
        con.execute("INSERT INTO procedure_events(id,action,at) VALUES (?,?,0)",
                    (proposal["id"], "native_verified_active"))


def test_skill_manage_cannot_publish_or_rewrite_an_ungated_skill(lab):
    from agent_harness.mcp.skills import Skills
    home, projects = lab
    body = ("## When to Use\nArchive recovery.\n## Procedure\nCheck the archive.\n"
            "## Pitfalls\nNever use on a live database.\n## Verification\nCheck the checksum.\n")
    created = exchange(lab, [("skill_manage", {"action": "create", "name": "archive-recovery",
                                               "description": "Recover a project archive.", "body": body})])[0]
    assert created["isError"] is True
    assert "procedure" in created["content"][0]["text"]
    assert not (home / ".agents/skills/learned/archive-recovery/SKILL.md").exists()

    # An older locally learned skill stays available, but an agent cannot
    # silently replace it with an untested body through the MCP tool.
    legacy = Skills(home=home / "harness", user_home=home)
    legacy.create("archive-recovery", "Recover a project archive.", body)
    path = home / ".agents/skills/learned/archive-recovery/SKILL.md"
    before = path.read_bytes()
    updated = exchange(lab, [("skill_manage", {"action": "update", "name": "archive-recovery",
                                               "body": body.replace("Check the archive.", "Ignore the checksum.")})])[0]
    assert updated["isError"] is True
    assert path.read_bytes() == before


def test_skill_manage_draft_is_dormant_then_active_fixture_teaches_and_withdraws(lab):
    home, projects = lab
    alpha, bravo = projects[1:]
    candidate = candidate_input(lab)
    proposal = value(exchange(lab, [("skill_manage", {"action": "draft", "project": str(alpha),
                                                       "candidate": candidate})])[0])
    assert proposal["status"] == "proposed"
    assert not (home / ".agents/skills/learned/archive-recovery/SKILL.md").exists()
    assert prompt(lab, "archive recovery").stdout == ""
    proposed = value(exchange(lab, [("skill_manage", {"action": "view", "name": proposal["id"],
                                                       "project": str(alpha)})])[0])
    assert proposed["status"] == "proposed" and proposed["evidence_sha256"] is None
    assert proposed["candidate"]["episodes"] == candidate["episodes"]
    assert exchange(lab, [("skill_manage", {"action": "view", "name": proposal["id"],
                                           "project": str(bravo)})])[0]["isError"] is True

    promoted = apply(lab, proposal, receipt(proposal))
    assert promoted.returncode == 1 and "independent grader" in promoted.stdout
    synthetic_active(lab, proposal, receipt(proposal))
    active = value(exchange(lab, [("skill_manage", {"action": "view", "name": proposal["id"],
                                                     "project": str(alpha)})])[0])
    assert active["status"] == "active" and len(active["evidence_sha256"]) == 64
    listed = exchange(lab, [("skill_manage", {"action": "list", "project": str(alpha)})])[0]
    assert proposal["id"] in listed["content"][0]["text"]
    assert "qualified-procedure" in listed["content"][0]["text"]
    assert exchange(lab, [("skill_manage", {"action": "archive", "name": proposal["id"],
                                           "project": str(alpha)})])[0]["isError"] is True
    assert "Validate the archive checksum" in prompt(lab, "archive recovery", session="new").stdout
    assert "Do not use for a live database" in prompt(lab, "archive recovery", session="another").stdout
    assert prompt(lab, "archive recovery", project=bravo).stdout == ""

    revoked = cli(lab, "--rollback", proposal["id"])
    assert revoked.returncode == 0, revoked.stdout + revoked.stderr
    withdrawn = value(exchange(lab, [("skill_manage", {"action": "view", "name": proposal["id"],
                                                        "project": str(alpha)})])[0])
    assert withdrawn["status"] == "rolled_back"
    assert "Validate the archive checksum" not in prompt(lab, "archive recovery", session="later").stdout


def test_skill_manage_draft_explains_its_required_source_contract(lab):
    bad = exchange(lab, [("skill_manage", {"action": "draft", "project": str(lab[1][1]),
                                           "candidate": {}})])[0]
    assert bad["isError"] is True
    assert "episodes" in bad["content"][0]["text"]
    assert "task_sha256" in bad["content"][0]["text"]


def test_a_promoted_skill_stops_recall_when_its_bound_source_changes(lab):
    alpha = lab[1][1]
    candidate = candidate_input(lab)
    proposal = value(exchange(lab, [("skill_manage", {"action": "draft", "project": str(alpha),
                                                       "candidate": candidate})])[0])
    synthetic_active(lab, proposal, receipt(proposal))
    assert "Validate the archive checksum" in prompt(lab, "archive recovery", session="before-edit").stdout
    (alpha / "episode-1.json").write_text("source changed after promotion")
    status = value(exchange(lab, [("skill_manage", {"action": "view", "name": proposal["id"],
                                                     "project": str(alpha)})])[0])
    assert status["status"] == "stale"
    listed = exchange(lab, [("skill_manage", {"action": "list", "project": str(alpha)})])[0]
    assert proposal["id"] not in listed["content"][0]["text"]
    assert "Validate the archive checksum" not in prompt(lab, "archive recovery", session="after-edit").stdout
    notice = prompt(lab, "archive recovery", session="before-edit").stdout
    assert proposal["id"] in notice and "stale" in notice.lower()


def test_procedure_is_dormant_then_recalled_in_scope_and_revoked(lab):
    _, proposal = draft(lab)
    assert prompt(lab, "archive recovery").stdout == ""
    assert apply(lab, proposal, receipt(proposal)).returncode == 1
    synthetic_active(lab, proposal, receipt(proposal))
    out = prompt(lab, "archive recovery", session="fresh").stdout
    assert "Validate the archive checksum" in out
    assert "Do not use for a live database" in out
    assert "advisory" in out.lower() and proposal["id"] in out
    assert prompt(lab, "archive recovery", project=lab[1][2]).stdout == ""
    found = value(exchange(lab, [("lesson_search", {"query": "archive recovery",
                                                    "project": str(lab[1][1])})])[0])
    assert proposal["id"] in {r["id"] for r in found}
    rollback = cli(lab, "--rollback", proposal["id"])
    assert rollback.returncode == 0, rollback.stdout + rollback.stderr
    notice = prompt(lab, "archive recovery", session="fresh").stdout
    assert "withdrawn" in notice and proposal["id"] in notice
    assert prompt(lab, "archive recovery", session="fresh").stdout == ""
    assert prompt(lab, "archive recovery", session="after-rollback").stdout == ""
    assert apply(lab, proposal, receipt(proposal)).returncode != 0


def test_explicit_negative_procedure_does_not_trigger_but_unrelated_warning_does(lab):
    _, proposal = draft(lab)
    synthetic_active(lab, proposal, receipt(proposal))
    assert "Validate the archive checksum" in prompt(
        lab, "How should I perform archive recovery?", session="positive").stdout
    for n, text in enumerate(("Do not use archive recovery.", "Don't use archive recovery.",
                              "Never run archive recovery.", "Avoid archive recovery.")):
        rejected = prompt(lab, text, session="negative-%d" % n).stdout
        assert "Validate the archive checksum" not in rejected, text
    assert "Validate the archive checksum" in prompt(
        lab, "Do not use a live database; help with archive recovery offline.",
        session="unrelated-warning").stdout


@pytest.mark.parametrize("fault", ["cost", "regression", "overlap", "duplicate", "context",
                                  "unknown-usage", "stale-candidate", "wrong-project", "nan",
                                  "missing-dimension", "no-gain", "negative-overhead",
                                  "aggregate-overflow", "schema-bool"])
def test_promotion_refuses_invalid_or_unmatched_evidence(lab, fault):
    from agent_harness import procedures
    _, proposal = draft(lab)
    evidence = receipt(proposal)
    if fault == "cost":
        evidence["overhead_tokens"] = 41  # total 201 vs baseline 200
    elif fault == "regression":
        evidence["pairs"][1]["cand"]["quality"]["integrity"] = 0
    elif fault == "overlap":
        evidence["pairs"][0]["task_id"] = "development-1"
    elif fault == "duplicate":
        evidence["pairs"][1]["task_id"] = "unseen-A"
    elif fault == "context":
        evidence["context"]["model"] = "different-model"
    elif fault == "unknown-usage":
        evidence["usage_complete"] = False
    elif fault == "stale-candidate":
        evidence["candidate_sha256"] = "d" * 64
    elif fault == "wrong-project":
        evidence["project"] = str(lab[1][2])
    elif fault == "nan":
        evidence["pairs"][0]["cand"]["tokens"] = float("nan")
    elif fault == "missing-dimension":
        del evidence["pairs"][1]["cand"]["quality"]["integrity"]
    elif fault == "no-gain":
        for pair in evidence["pairs"]:
            pair["cand"] = copy.deepcopy(pair["base"])
        evidence["overhead_tokens"] = 0
    elif fault == "negative-overhead":
        evidence["overhead_tokens"] = -1
    elif fault == "aggregate-overflow":
        for pair in evidence["pairs"]:
            pair["base"]["tokens"] = pair["cand"]["tokens"] = 1e308
    elif fault == "schema-bool":
        evidence["schema"] = True
    with pytest.raises((ValueError, KeyError, TypeError, OverflowError)):
        procedures.evaluate(proposal, evidence)
    assert apply(lab, proposal, evidence).returncode != 0
    assert prompt(lab, "archive recovery").stdout == ""


def test_equal_quality_and_lower_total_tokens_is_a_valid_gain(lab):
    from agent_harness import procedures
    _, proposal = draft(lab)
    evidence = receipt(proposal)
    for pair in evidence["pairs"]:
        pair["base"]["quality"] = copy.deepcopy(pair["cand"]["quality"])
    assert procedures.evaluate(proposal, evidence)["candidate_tokens"] < 200
    assert apply(lab, proposal, evidence).returncode == 1


def test_other_project_cannot_activate_or_rollback(lab):
    _, proposal = draft(lab)
    evidence = lab[1][1] / "eval.json"
    evidence.write_text(json.dumps(receipt(proposal)))
    assert cli(lab, "--apply", proposal["id"], "--eval", str(evidence),
               project=lab[1][2]).returncode != 0
    synthetic_active(lab, proposal, receipt(proposal))
    assert cli(lab, "--rollback", proposal["id"], project=lab[1][2]).returncode != 0
    assert "Validate the archive checksum" in prompt(lab, "archive recovery").stdout


def test_source_edit_after_draft_refuses_promotion(lab):
    from agent_harness import procedures
    _, proposal = draft(lab)
    (lab[1][1] / "episode-1.json").write_text("changed evidence")
    with pytest.raises(ValueError, match="source changed"):
        procedures.evaluate(proposal, receipt(proposal))
    assert apply(lab, proposal, receipt(proposal)).returncode != 0


def test_repeated_draft_does_not_duplicate_or_resurrect(lab):
    _, one = draft(lab)
    _, two = draft(lab)
    assert one["id"] == two["id"]
    synthetic_active(lab, one, receipt(one))
    assert cli(lab, "--rollback", one["id"]).returncode == 0
    _, three = draft(lab)
    assert three["id"] == one["id"] and three["status"] == "rolled_back"


def test_invalid_comparison_shape_is_a_refusal_without_traceback(lab):
    from agent_harness import procedures
    _, proposal = draft(lab)
    evidence = receipt(proposal)
    evidence["pairs"] = ["claimed success"]
    with pytest.raises(ValueError, match="pair"):
        procedures.evaluate(proposal, evidence)
    result = apply(lab, proposal, evidence)
    assert result.returncode == 1
    assert "Traceback" not in result.stderr


def test_missing_task_input_fingerprints_cannot_establish_unseen_transfer(lab):
    from agent_harness import procedures
    _, proposal = draft(lab)
    evidence = receipt(proposal)
    for pair in evidence["pairs"]:
        pair.pop("task_path", None)
        pair.pop("task_sha256", None)
    with pytest.raises(ValueError):
        procedures.evaluate(proposal, evidence)
    assert apply(lab, proposal, evidence).returncode != 0


def test_renaming_a_development_task_does_not_make_it_unseen(lab):
    from agent_harness import procedures
    _, proposal = draft(lab)
    evidence = receipt(proposal)
    episode = proposal["candidate"]["episodes"][0]
    evidence["pairs"][0].update(task_id="new-name", task_path=episode["task_path"],
                                task_sha256=episode["task_sha256"])
    with pytest.raises(ValueError, match="overlap"):
        procedures.evaluate(proposal, evidence)
    assert apply(lab, proposal, evidence).returncode != 0


def test_changed_heldout_input_and_duplicate_input_under_two_names_are_refused(lab):
    from agent_harness import procedures
    _, proposal = draft(lab)
    evidence = receipt(proposal)
    (Path(proposal["project"]) / evidence["pairs"][0]["task_path"]).write_text("different input")
    with pytest.raises(ValueError, match="source changed"):
        procedures.evaluate(proposal, evidence)
    assert apply(lab, proposal, evidence).returncode != 0
    evidence = receipt(proposal)
    evidence["pairs"][1].update(task_path=evidence["pairs"][0]["task_path"],
                                task_sha256=evidence["pairs"][0]["task_sha256"])
    with pytest.raises(ValueError, match="overlap"):
        procedures.evaluate(proposal, evidence)
    assert apply(lab, proposal, evidence).returncode != 0


def test_two_episodes_of_one_input_do_not_establish_recurrence(lab):
    candidate, _ = draft(lab)
    candidate["episodes"][1].update(task_path=candidate["episodes"][0]["task_path"],
                                     task_sha256=candidate["episodes"][0]["task_sha256"])
    path = lab[1][1] / "repeated-input.json"
    path.write_text(json.dumps(candidate))
    assert cli(lab, "--draft-procedure", str(path)).returncode != 0


def test_two_task_inputs_one_observation_do_not_establish_recurrence(lab):
    candidate = candidate_input(lab)
    alpha = lab[1][1]
    first, second = candidate["episodes"]
    # Different task inputs do not make a copied observation two independent
    # development episodes. Renaming the source must not bypass the check.
    (alpha / second["path"]).write_bytes((alpha / first["path"]).read_bytes())
    second["sha256"] = first["sha256"]
    assert first["task_sha256"] != second["task_sha256"]
    path = alpha / "reused-source.json"
    path.write_text(json.dumps(candidate))
    refused = cli(lab, "--draft-procedure", str(path))
    assert refused.returncode != 0 and "source evidence" in refused.stdout

    distinct = candidate_input(lab)
    path.write_text(json.dumps(distinct))
    accepted = cli(lab, "--draft-procedure", str(path))
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
