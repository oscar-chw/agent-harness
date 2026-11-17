"""Dream scores cannot create live knowledge links without independent evidence."""
import json
from pathlib import Path
import os
import subprocess
import sys

import pytest

from agent_harness import dream_candidates as D
from agent_harness.mcp.kb import KB
from agent_harness import memory_dreaming, memory_dreaming_v1


@pytest.fixture
def corpus(tmp_path):
    root = tmp_path / "vault"
    (root / "memory").mkdir(parents=True)
    (root / "memory/contracts.md").write_text("# Contract\nquartzapi quota reset is specified by the API contract.\n")
    (root / "memory/reference.md").write_text("# Reference\nquartzapi quota reset field reference.\n")
    return root


def gate(tmp_path, candidate, *, correct=True):
    project = tmp_path / "project"
    (project / "plan").mkdir(parents=True, exist_ok=True)
    (project / ".git").mkdir(exist_ok=True)
    output = candidate if correct else "not-this-candidate"
    (project / "plan/dream.md").write_text(
        "## goal: Independently check a proposed relation\n\n"
        f"- [ ] 1. Relation check | gate: python3 -c 'print(\"{output}\")'\n")
    command = Path(__file__).resolve().parents[1] / "src/agent_harness/workgraph/plan.py"
    result = subprocess.run([sys.executable, str(command), "gate", "dream", "1"],
                            cwd=project, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    return project / "plan/dream.md"


def test_staged_proposal_does_not_enter_retrieval_or_change_the_corpus(corpus, tmp_path):
    before = (corpus / "memory/contracts.md").read_bytes()
    candidate = D.propose(corpus, "memory/contracts.md", "memory/reference.md", origin="dream-v1")
    assert candidate["status"] == "proposed" and not candidate["admitted"]
    assert D.read(corpus, candidate["id"])["id"] == candidate["id"]
    assert (corpus / "memory/contracts.md").read_bytes() == before
    kb = KB(home=tmp_path / "hh", paths=[corpus], fts=False)
    try:
        assert kb.search(candidate["id"]) == []
    finally:
        kb.close()


def test_a_claimed_pass_without_real_gate_receipts_cannot_admit(corpus, tmp_path):
    candidate = D.propose(corpus, "memory/contracts.md", "memory/reference.md", origin="dream-v1")
    plan = tmp_path / "fake.md"
    plan.write_text(f"- [x] 1. Claimed done {candidate['id']} | gate: true\n")
    with pytest.raises(ValueError, match="gate"):
        D.admit(corpus, candidate["id"], plan, 1)
    assert "Related" not in (corpus / "memory/contracts.md").read_text()


def test_a_real_gate_for_another_candidate_cannot_admit(corpus, tmp_path):
    candidate = D.propose(corpus, "memory/contracts.md", "memory/reference.md", origin="dream-v1")
    plan = gate(tmp_path, candidate["id"], correct=False)
    with pytest.raises(ValueError, match="candidate"):
        D.admit(corpus, candidate["id"], plan, 1)


def test_source_drift_requires_fresh_review(corpus, tmp_path):
    candidate = D.propose(corpus, "memory/contracts.md", "memory/reference.md", origin="dream-v1")
    plan = gate(tmp_path, candidate["id"])
    (corpus / "memory/reference.md").write_text("# Changed\nA different contract.\n")
    with pytest.raises(ValueError, match="source"):
        D.admit(corpus, candidate["id"], plan, 1)


def test_admission_binds_a_real_gate_and_preserves_the_original(corpus, tmp_path):
    original = (corpus / "memory/contracts.md").read_bytes()
    candidate = D.propose(corpus, "memory/contracts.md", "memory/reference.md", origin="dream-v1")
    plan = gate(tmp_path, candidate["id"])
    receipt = D.admit(corpus, candidate["id"], plan, 1)
    assert receipt["status"] == "admitted"
    assert receipt["candidate"] == candidate["id"]
    assert (corpus / "memory/contracts.md").read_bytes().startswith(original)
    assert "reference.md" in (corpus / "memory/contracts.md").read_text()
    assert Path(receipt["backup"]).read_bytes() == original
    assert D.read(corpus, candidate["id"])["status"] == "admitted"
    assert D.admit(corpus, candidate["id"], plan, 1) == receipt


def test_dream_scorer_results_are_only_proposals(corpus):
    before = {str(p): p.read_bytes() for p in corpus.rglob("*.md")}
    result = D.stage(corpus, limit=8)
    assert result["admitted"] == 0
    assert result["mode"] == "candidate_only"
    assert before == {str(p): p.read_bytes() for p in corpus.rglob("*.md")}


@pytest.fixture
def scored_corpus(tmp_path):
    root = tmp_path / "scored"
    memory = root / "memory"
    memory.mkdir(parents=True)
    for index, stem in enumerate("abc"):
        shared = " ".join(stem * 3 + chr(letter) * 4 for letter in range(97, 112))
        pages = {"hub": f"{shared}\n[[anchor{index}]]", "anchor": f"[[hub{index}]]", "note": shared}
        for role, body in pages.items():
            name = f"{role}{index}"
            (memory / f"{name}.md").write_text(f"---\nname: {name}\n---\n\n# {role}\n{body}\n")
    return root


def dream_cli(corpus, *arguments):
    repo = Path(__file__).resolve().parents[1]
    return [sys.executable, str(repo / "bin/harness"), "dream", arguments[0], str(corpus), *arguments[1:]]


def test_successive_batches_and_cold_list_recover_every_proposal(scored_corpus):
    before = {p: p.read_bytes() for p in scored_corpus.rglob("*.md")}
    batches = [D.stage(scored_corpus, limit=1) for _ in range(4)]
    assert [len(batch["candidates"]) for batch in batches] == [1, 1, 1, 0]
    assert [batch["remaining_scored"] for batch in batches] == [2, 1, 0, 0]
    identities = {row["id"] for batch in batches for row in batch["candidates"]}
    assert len(identities) == 3
    result = subprocess.run(dream_cli(scored_corpus, "list"), capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    rows = json.loads(result.stdout)["candidates"]
    assert {row["id"] for row in rows} == identities
    assert all(row["status"] == "proposed" and not row["admitted"] for row in rows)
    assert before == {p: p.read_bytes() for p in scored_corpus.rglob("*.md")}


def test_parallel_batches_stage_distinct_proposals(scored_corpus):
    command = dream_cli(scored_corpus, "stage", "--limit", "1")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env) as first:
        second = subprocess.run(command, capture_output=True, text=True, env=env, timeout=10)
        stdout, stderr = first.communicate(timeout=10)
    assert first.returncode == second.returncode == 0, (stderr, second.stderr)
    first_batch, second_batch = json.loads(stdout), json.loads(second.stdout)
    assert first_batch["candidates"][0]["id"] != second_batch["candidates"][0]["id"]
    assert sorted(batch["remaining_scored"] for batch in (first_batch, second_batch)) == [1, 2]


def test_full_queue_reports_unstaged_work_and_preserves_existing_proposals(scored_corpus, monkeypatch):
    monkeypatch.setattr(D, "MAX_CANDIDATES", 2)
    first = D.stage(scored_corpus)
    assert len(first["candidates"]) == 2
    assert first["storage_remaining"] == 0 and first["remaining_scored"] == 1
    replay = D.stage(scored_corpus)
    assert replay["candidates"] == []
    assert replay["storage_remaining"] == 0 and replay["remaining_scored"] == 1
    assert {row["id"] for row in D.list_candidates(scored_corpus)["candidates"]} == {
        row["id"] for row in first["candidates"]
    }


def test_scanning_an_empty_queue_creates_no_store(corpus):
    assert D.list_candidates(corpus) == {"candidates": []}
    assert D.stage(corpus)["candidates"] == []
    assert not (corpus / ".harness").exists()


def test_review_packet_cli_deduplicates_without_losing_exact_evidence(corpus):
    first = D.propose(corpus, "memory/contracts.md", "memory/reference.md", origin="dream-v1")
    other = corpus / "memory/other.md"
    other.write_bytes("# Approach\r\nEvidence in café.\r\n".encode())
    second = D.propose(corpus, first["source"], "memory/other.md", origin="dream-v1")
    result = subprocess.run(dream_cli(corpus, "review", first["id"], second["id"]),
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    packet = json.loads(result.stdout)
    assert len(packet["sources"]) == 3
    assert [row["id"] for row in packet["candidates"]] == [first["id"], second["id"]]
    for candidate in (first, second):
        for path, digest in candidate["sources"].items():
            assert packet["sources"][path] == {
                "sha256": digest, "text": (corpus / path).read_bytes().decode("utf-8")
            }
    assert D.read(corpus, first["id"])["status"] == "proposed"


def test_review_packet_refuses_excess_output(corpus):
    for name in ("contracts", "reference"):
        (corpus / "memory" / f"{name}.md").write_text("# Evidence\n" + "x" * 33000)
    candidate = D.propose(corpus, "memory/contracts.md", "memory/reference.md", origin="dream-v1")
    result = subprocess.run(dream_cli(corpus, "review", candidate["id"]),
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "REFUSED" and "review packet" in payload["error"]
    assert "sources" not in payload


def test_review_packet_refuses_source_drift(corpus):
    candidate = D.propose(corpus, "memory/contracts.md", "memory/reference.md", origin="dream-v1")
    (corpus / candidate["target"]).write_text("# Changed\nFresh evidence.\n")
    result = subprocess.run(dream_cli(corpus, "review", candidate["id"]),
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "REFUSED" and "source changed" in payload["error"]


def test_candidate_tamper_is_refused(corpus):
    candidate = D.propose(corpus, "memory/contracts.md", "memory/reference.md", origin="dream-v1")
    path = corpus / ".harness/dreaming/candidates" / (candidate["id"] + ".json")
    value = json.loads(path.read_text())
    value["target"] = "memory/other.md"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="candidate"):
        D.read(corpus, candidate["id"])


def test_a_fabricated_admission_receipt_cannot_replace_the_gate(corpus, tmp_path):
    candidate = D.propose(corpus, "memory/contracts.md", "memory/reference.md", origin="dream-v1")
    path = corpus / ".harness/dreaming" / (candidate["id"] + ".admitted.json")
    path.write_text(json.dumps({"status": "admitted", "after_sha256": candidate["sources"][candidate["source"]]}))
    plan = tmp_path / "fake.md"
    plan.write_text("- [x] 1. Claimed pass | gate: true\n")
    with pytest.raises(ValueError):
        D.admit(corpus, candidate["id"], plan, 1)


def test_withdrawal_restores_only_its_own_change_and_prevents_silent_readmission(corpus, tmp_path):
    original = (corpus / "memory/contracts.md").read_bytes()
    candidate = D.propose(corpus, "memory/contracts.md", "memory/reference.md", origin="dream-v1")
    plan = gate(tmp_path, candidate["id"])
    D.admit(corpus, candidate["id"], plan, 1)
    D.withdraw(corpus, candidate["id"], reason="Independent review rejected this relation.")
    assert (corpus / "memory/contracts.md").read_bytes() == original
    assert D.read(corpus, candidate["id"])["status"] == "withdrawn"
    with pytest.raises(ValueError, match="withdrawn"):
        D.admit(corpus, candidate["id"], plan, 1)


def test_withdrawal_never_erases_later_user_edits(corpus, tmp_path):
    candidate = D.propose(corpus, "memory/contracts.md", "memory/reference.md", origin="dream-v1")
    D.admit(corpus, candidate["id"], gate(tmp_path, candidate["id"]), 1)
    target = corpus / "memory/contracts.md"
    target.write_text(target.read_text() + "A later user correction.\n")
    changed = target.read_bytes()
    with pytest.raises(ValueError, match="changed"):
        D.withdraw(corpus, candidate["id"], reason="A mistaken relation.")
    assert target.read_bytes() == changed


def test_interrupted_admission_can_finish_from_its_bound_prepared_receipt(corpus, tmp_path, monkeypatch):
    candidate = D.propose(corpus, "memory/contracts.md", "memory/reference.md", origin="dream-v1")
    plan = gate(tmp_path, candidate["id"])
    original = D._write

    def interrupted(path, data, **kwargs):
        if str(path).endswith(".admitted.json") and json.loads(data)["status"] == "admitted":
            raise OSError("fixture interruption before final receipt")
        return original(path, data, **kwargs)

    monkeypatch.setattr(D, "_write", interrupted)
    with pytest.raises(OSError):
        D.admit(corpus, candidate["id"], plan, 1)
    monkeypatch.setattr(D, "_write", original)
    receipt = D.admit(corpus, candidate["id"], plan, 1)
    assert receipt["status"] == "admitted"
    assert (corpus / "memory/contracts.md").read_text().count("Related (reviewed dream)") == 1


def test_interrupted_withdrawal_can_finish_without_losing_its_reason(corpus, tmp_path, monkeypatch):
    candidate = D.propose(corpus, "memory/contracts.md", "memory/reference.md", origin="dream-v1")
    plan = gate(tmp_path, candidate["id"])
    D.admit(corpus, candidate["id"], plan, 1)
    original = D._write

    def interrupted(path, data, **kwargs):
        if str(path).endswith(".withdrawn.json") and json.loads(data)["status"] == "withdrawn":
            raise OSError("fixture interruption before final withdrawal receipt")
        return original(path, data, **kwargs)

    monkeypatch.setattr(D, "_write", interrupted)
    with pytest.raises(OSError):
        D.withdraw(corpus, candidate["id"], reason="Independent review found an error.")
    monkeypatch.setattr(D, "_write", original)
    receipt = D.withdraw(corpus, candidate["id"], reason="A retried call.")
    assert receipt["reason"] == "Independent review found an error."
    with pytest.raises(ValueError, match="withdrawn"):
        D.admit(corpus, candidate["id"], plan, 1)


@pytest.mark.parametrize("engine", [memory_dreaming.dream, memory_dreaming_v1.dream_v1])
def test_legacy_copy_engine_never_replaces_an_existing_destination(corpus, tmp_path, engine):
    destination = tmp_path / "existing-work"
    destination.mkdir()
    valuable = destination / "keep.txt"
    valuable.write_text("Unrelated user work.\n")
    with pytest.raises(FileExistsError):
        engine(corpus, dst=destination, work_dir=tmp_path / "work", apply=True)
    assert valuable.read_text() == "Unrelated user work.\n"


@pytest.mark.parametrize("engine", [memory_dreaming.dream, memory_dreaming_v1.dream_v1])
def test_legacy_copy_engine_never_recursively_copies_inside_its_source(corpus, tmp_path, monkeypatch, engine):
    module = sys.modules[engine.__module__]
    monkeypatch.setattr(module.shutil, "copytree", lambda *a, **k: pytest.fail("unsafe recursive copy reached"))
    with pytest.raises(ValueError, match="outside"):
        engine(corpus, dst=corpus / "nested-copy", work_dir=tmp_path / "work", apply=True)
