"""Capability research must be reusable, source bound and preference aware."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_harness import research_registry as R


@pytest.fixture
def registry(tmp_path):
    content = tmp_path / "content"
    (content / "knowledge").mkdir(parents=True)
    guide = content / "knowledge/RESEARCH.md"
    guide.write_text("# Research\n## Question design\nState a falsifiable question.\n")
    entry = {"id": "research-paper", "summary": "Question design, evidence and writing.",
             "sources": [{"path": "knowledge/RESEARCH.md", "sha256": hashlib.sha256(guide.read_bytes()).hexdigest()}],
             "related": ["reasoning-decisions"], "reviewed_at": "2026-11-17",
             "quality_evaluation": "NOT_MEASURED"}
    (content / "knowledge/capability-research.json").write_text(json.dumps({"schema": 1, "capabilities": [entry]}))
    return tmp_path / ".agent-harness", content, entry


def test_known_capability_reuses_research_without_writes(registry):
    home, content, entry = registry
    before = {str(p): p.read_bytes() for p in content.rglob("*") if p.is_file()}
    result = R.check(home, "research-paper", content=content)
    assert result["status"] == "REUSE_EXISTING" and result["record"] == entry
    assert not home.exists()
    assert before == {str(p): p.read_bytes() for p in content.rglob("*") if p.is_file()}


def test_learned_research_uses_the_durable_shared_vault(registry):
    home, content, entry = registry
    document = home / "vault/methods/new-research.md"
    document.parent.mkdir(parents=True)
    document.write_text("# Learned method\nKeep source claims and uncertainty distinct.\n")
    learned = {**entry, "id": "learned-method", "source_root": "vault",
               "sources": [{"path": "methods/new-research.md", "sha256": hashlib.sha256(document.read_bytes()).hexdigest()}]}
    result = R.record(home, learned, content=content)
    assert result["status"] == "REUSE_EXISTING"
    document.write_text("Changed source.\n")
    assert R.check(home, "learned-method", content=content)["status"] == "SOURCE_REVIEW_REQUIRED"


def test_reinstall_preserves_learned_vault_and_research_records(registry):
    from agent_harness.installer import copy_harness
    home, content, entry = registry
    document = home / "vault/learned.md"
    document.parent.mkdir(parents=True)
    document.write_text("# Local research\nPreserved through source package replacement.\n")
    learned = {**entry, "id": "learned-method", "source_root": "vault",
               "sources": [{"path": "learned.md", "sha256": hashlib.sha256(document.read_bytes()).hexdigest()}]}
    R.record(home, learned, content=content)
    copy_harness(home, R.DEFAULT_CONTENT.parent, None)
    assert document.read_text().endswith("Preserved through source package replacement.\n")
    assert R.check(home, "learned-method")["status"] == "REUSE_EXISTING"


def test_new_capability_requests_research_without_inventing_coverage(registry):
    home, content, _ = registry
    result = R.check(home, "new-domain", content=content)
    assert result["status"] == "RESEARCH_REQUIRED" and result["record"] is None
    assert not home.exists()


def test_source_change_is_visible_and_not_relabelled_current(registry):
    home, content, _ = registry
    (content / "knowledge/RESEARCH.md").write_text("Changed knowledge.\n")
    assert R.check(home, "research-paper", content=content)["status"] == "SOURCE_REVIEW_REQUIRED"


def test_oversized_old_source_is_reviewable_and_can_be_replaced(registry):
    home, content, entry = registry
    (content / "knowledge/RESEARCH.md").write_bytes(b"x" * (R.LIMIT + 1))
    before = R.check(home, "research-paper", content=content)
    assert before["status"] == "SOURCE_REVIEW_REQUIRED"
    source = content / "knowledge/NEW.md"
    source.write_text("# Research\nRetain exclusions and observations.\n")
    replacement = {**entry, "sources": [{"path": "knowledge/NEW.md",
                                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}]}
    R.record(home, replacement, content=content, expected=before["record_sha256"])
    assert R.check(home, "research-paper", content=content)["status"] == "REUSE_EXISTING"
    with pytest.raises(ValueError, match="source"):
        R.record(home, entry, content=content, expected=R.check(home, "research-paper", content=content)["record_sha256"])


def test_preferences_survive_reuse_and_require_upgrade_confirmation(registry):
    home, content, _ = registry
    R.save_preference(home, "research-paper", "Explain purpose before terminology.", "user instruction 2026-11-17")
    result = R.check(home, "research-paper", content=content)
    assert result["status"] == "REUSE_EXISTING"
    assert result["preferences"][0]["text"] == "Explain purpose before terminology."
    update = R.check(home, "research-paper", content=content, update_requested=True)
    assert update["status"] == "CONFIRM_SAVED_PREFERENCES"


def test_update_is_bound_to_record_and_current_preference_digest(registry):
    home, content, entry = registry
    R.save_preference(home, "research-paper", "Keep negative findings.", "user instruction")
    before = R.check(home, "research-paper", content=content, update_requested=True)
    changed = {**entry, "summary": "Updated research guidance."}
    with pytest.raises(ValueError, match="preferences"):
        R.record(home, changed, content=content, expected=before["record_sha256"])
    R.save_preference(home, "research-paper", "Use concrete examples.", "later user instruction")
    with pytest.raises(ValueError, match="preferences"):
        R.record(home, changed, content=content, expected=before["record_sha256"],
                 confirmed_preferences=before["preferences_sha256"])
    current = R.check(home, "research-paper", content=content, update_requested=True)
    R.record(home, changed, content=content, expected=current["record_sha256"],
             confirmed_preferences=current["preferences_sha256"])
    assert R.check(home, "research-paper", content=content)["record"]["summary"] == changed["summary"]


def test_concurrent_stale_record_cannot_replace_an_update(registry):
    home, content, entry = registry
    before = R.check(home, "research-paper", content=content)
    first = {**entry, "summary": "First update."}
    R.record(home, first, content=content, expected=before["record_sha256"])
    with pytest.raises(ValueError, match="changed"):
        R.record(home, {**entry, "summary": "Stale writer."}, content=content, expected=before["record_sha256"])
    assert R.check(home, "research-paper", content=content)["record"] == first


def test_upgrades_preserve_the_previous_research_record(registry):
    home, content, entry = registry
    before = R.check(home, "research-paper", content=content)
    first = {**entry, "summary": "First local update."}
    R.record(home, first, content=content, expected=before["record_sha256"])
    current = R.check(home, "research-paper", content=content)
    R.record(home, {**entry, "summary": "Second local update."}, content=content,
             expected=current["record_sha256"])
    history = [json.loads(p.read_text()) for p in (home / "research/history").glob("*.json")]
    assert entry in history and first in history
    assert len(history) == 2


def test_saved_preferences_with_no_research_still_need_confirmation_before_recording(registry):
    home, content, entry = registry
    R.save_preference(home, "new-domain", "Preserve exploratory results.", "user instruction")
    new = {**entry, "id": "new-domain"}
    with pytest.raises(ValueError, match="preferences"):
        R.record(home, new, content=content)
    assert R.check(home, "new-domain", content=content)["record"] is None


def test_preference_store_cannot_grow_past_the_declared_file_bound(registry):
    home, _, _ = registry
    store = home / "research"
    store.mkdir(parents=True)
    for index in range(200):
        (store / ("existing-" + str(index) + ".json")).write_text("{}")
    with pytest.raises(ValueError, match="limit"):
        R.save_preference(home, "new-domain", "Keep limitations.", "user instruction")
    assert not (store / "new-domain.preferences.json").exists()


def test_shipped_research_catalogue_sources_and_relationships_resolve(tmp_path):
    catalogue = json.loads((R.DEFAULT_CONTENT / "knowledge/capability-research.json").read_text())
    identities = {row["id"] for row in catalogue["capabilities"]}
    assert "research-paper" in identities
    for entry in catalogue["capabilities"]:
        result = R.check(tmp_path / "hh", entry["id"])
        assert result["status"] == "REUSE_EXISTING"
        assert set(entry["related"]) <= identities
        assert entry["quality_evaluation"] != "PASS"


def test_fresh_kb_process_discovers_shared_research_and_retracts_removed_source(tmp_path, monkeypatch):
    from agent_harness.mcp.kb import KB
    monkeypatch.delenv("HARNESS_KB_PATHS", raising=False)
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "hh"
    knowledge = home / "content/knowledge"
    knowledge.mkdir(parents=True)
    source = knowledge / "RESEARCH.md"
    source.write_text("# Research\n## Evidence mapping\nquartzexperiment claims need matched comparisons.\n")
    reader = KB(home=home, fts=False)
    try:
        matches = reader.search("quartzexperiment")
        assert len(matches) == 1
        assert "matched comparisons" in reader.get(matches[0]["id"])["text"]
    finally:
        reader.close()
    script = ("import json; from pathlib import Path; from agent_harness.mcp.kb import KB; "
              f"kb=KB(home=Path({str(home)!r}), fts=False); "
              "print(json.dumps(kb.search('quartzexperiment'))); kb.close()")
    fresh = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=20,
                           env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
                           cwd=Path(__file__).resolve().parents[1])
    assert fresh.returncode == 0, fresh.stderr
    assert json.loads(fresh.stdout)[0]["id"] == matches[0]["id"]
    source.unlink()
    missing = KB(home=home, fts=False)
    try:
        assert missing.search("quartzexperiment") == []
    finally:
        missing.close()


def test_profile_alias_does_not_duplicate_the_builtin_knowledge_root(tmp_path, monkeypatch):
    from agent_harness.mcp.kb import KB
    monkeypatch.delenv("HARNESS_KB_PATHS", raising=False)
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "hh"
    knowledge = home / "content/knowledge"
    knowledge.mkdir(parents=True)
    (knowledge / "RESEARCH.md").write_text("# Research\nquartzpublication guide\n")
    profile = home / "profile"
    profile.mkdir()
    (profile / "research").symlink_to(knowledge, target_is_directory=True)
    reader = KB(home=home, fts=False)
    try:
        matches = reader.search("quartzpublication")
        assert len(matches) == 1
        assert "quartzpublication" in reader.get(matches[0]["id"])["text"]
    finally:
        reader.close()


def test_running_kb_discovers_knowledge_published_after_startup(tmp_path, monkeypatch):
    from agent_harness.mcp.kb import KB
    monkeypatch.delenv("HARNESS_KB_PATHS", raising=False)
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "hh"
    reader = KB(home=home, fts=False)
    try:
        assert reader.search("quartznewresearch") == []
        knowledge = home / "content/knowledge"
        knowledge.mkdir(parents=True)
        (knowledge / "RESEARCH.md").write_text("# Research\nquartznewresearch guide\n")
        assert len(reader.search("quartznewresearch")) == 1
    finally:
        reader.close()


@pytest.mark.parametrize("bad", ["../elsewhere", "", "x/y"])
def test_capability_ids_cannot_escape_storage(registry, bad):
    home, content, _ = registry
    with pytest.raises(ValueError):
        R.check(home, bad, content=content)


def test_claimed_research_with_missing_or_changed_sources_is_rejected(registry):
    home, content, entry = registry
    bad = copy.deepcopy(entry)
    bad["sources"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source"):
        R.record(home, bad, content=content, expected=None)


def test_cli_reads_the_same_state_in_a_fresh_process(registry):
    home, content, _ = registry
    R.save_preference(home, "research-paper", "Retain uncertainty.", "user instruction")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(root / "bin/harness"), "--home", str(home.parent),
        "research", "check", "research-paper", "--content-root", str(content)],
        env={**os.environ, "HARNESS_HOME": str(home)},
        capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["preferences"][0]["text"] == "Retain uncertainty."
    other = subprocess.run([sys.executable, str(root / "bin/harness"), "research",
        "check", "research-paper", "--content-root", str(content)],
        env={**os.environ, "HARNESS_HOME": str(home.parent / "unrelated")},
        capture_output=True, text=True, timeout=20)
    assert other.returncode == 0 and json.loads(other.stdout)["preferences"] == []


def withdraw(registry, *, expected=None, reason="Independent review rejected this method.",
             source="review/withdrawal-20261117"):
    home, content, entry = registry
    assert callable(getattr(R, "withdraw", None)), "explicit research withdrawal is missing"
    if expected is None:
        expected = R.check(home, entry["id"], content=content)["record_sha256"]
    return R.withdraw(home, entry["id"], content=content, expected=expected,
                      reason=reason, source=source)


def test_withdrawal_overrides_current_sources_and_update_intent(registry):
    home, content, entry = registry
    before = R.check(home, entry["id"], content=content)
    result = withdraw(registry)
    assert result["status"] == "WITHDRAWN"
    assert result["record"]["sources"] == entry["sources"]
    assert result["record"]["lifecycle"] == {
        "state": "withdrawn", "reason": "Independent review rejected this method.",
        "source": "review/withdrawal-20261117", "previous_sha256": before["record_sha256"]}
    assert result["record_sha256"] != before["record_sha256"]
    assert R.check(home, entry["id"], content=content, update_requested=True)["status"] == "WITHDRAWN"
    assert result["execution_authorized"] is False


def test_withdrawal_survives_missing_sources_and_preserves_preferences(registry):
    home, content, entry = registry
    R.save_preference(home, entry["id"], "Keep negative findings.", "user instruction")
    preferences = R.check(home, entry["id"], content=content)["preferences"]
    (content / entry["sources"][0]["path"]).unlink()
    result = withdraw(registry)
    assert result["status"] == "WITHDRAWN"
    assert result["preferences"] == preferences
    history = list((home / "research/history").glob("*.json"))
    assert len(history) == 1 and json.loads(history[0].read_text()) == entry


def test_stale_writer_cannot_replace_or_withdraw_current_research(registry):
    home, content, entry = registry
    before = R.check(home, entry["id"], content=content)
    withdrawn = withdraw(registry)
    with pytest.raises(ValueError, match="changed"):
        R.record(home, {**entry, "summary": "Stale update."}, content=content,
                 expected=before["record_sha256"])
    with pytest.raises(ValueError, match="changed"):
        withdraw(registry, expected=before["record_sha256"])
    assert R.check(home, entry["id"], content=content) == withdrawn


def test_ordinary_record_cannot_clear_a_withdrawal(registry):
    home, content, entry = registry
    result = withdraw(registry)
    with pytest.raises(ValueError, match="requalif"):
        R.record(home, entry, content=content, expected=result["record_sha256"])
    assert R.check(home, entry["id"], content=content)["status"] == "WITHDRAWN"


def test_requalification_requires_current_sources_provenance_and_preferences(registry):
    home, content, entry = registry
    R.save_preference(home, entry["id"], "Preserve caveats.", "user instruction")
    withdrawn = withdraw(registry)
    options = {"content": content, "expected": withdrawn["record_sha256"], "requalify": True,
               "confirmed_preferences": withdrawn["preferences_sha256"],
               "reason": "Rechecked bounded applicability.", "source": "review/requalification-20261117"}
    bad = copy.deepcopy(entry)
    bad["sources"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source"):
        R.record(home, bad, **options)
    for key in ("reason", "source", "confirmed_preferences"):
        missing = {k: v for k, v in options.items() if k != key}
        with pytest.raises(ValueError, match="provenance|preferences"):
            R.record(home, entry, **missing)
    R.save_preference(home, entry["id"], "Explain uncertainty.", "later user instruction")
    with pytest.raises(ValueError, match="preferences"):
        R.record(home, entry, **options)
    current = R.check(home, entry["id"], content=content)
    options["confirmed_preferences"] = current["preferences_sha256"]
    result = R.record(home, entry, **options)
    assert result["status"] == "REUSE_EXISTING"
    assert result["record"]["lifecycle"] == {
        "state": "requalified", "reason": options["reason"], "source": options["source"],
        "previous_sha256": withdrawn["record_sha256"]}
    assert result["preferences"] == current["preferences"]
    history = [json.loads(p.read_text()) for p in (home / "research/history").glob("*.json")]
    assert entry in history and withdrawn["record"] in history
    with pytest.raises(ValueError, match="changed"):
        R.record(home, entry, **options)
    with pytest.raises(ValueError, match="withdrawn"):
        R.record(home, entry, **{**options, "expected": result["record_sha256"]})


def test_legacy_and_freeform_quality_metadata_keep_existing_semantics(registry):
    home, content, entry = registry
    current = R.check(home, entry["id"], content=content)
    claimed = {**entry, "quality_evaluation": "WITHDRAWN in an unrelated historical trial"}
    result = R.record(home, claimed, content=content, expected=current["record_sha256"])
    assert result["status"] == "REUSE_EXISTING"
    assert "lifecycle" not in result["record"]


@pytest.mark.parametrize("field,value", [("reason", ""), ("source", " "),
                                         ("source", None), ("reason", "x" * 4097)])
def test_withdrawal_rejects_invalid_provenance_without_writes(registry, field, value):
    home, _, _ = registry
    with pytest.raises(ValueError, match="provenance"):
        withdraw(registry, **{field: value})
    assert not home.exists()


def test_lifecycle_metadata_cannot_be_forged_or_removed_by_record(registry):
    home, content, entry = registry
    current = R.check(home, entry["id"], content=content)
    forged = {**entry, "lifecycle": {"state": "requalified", "reason": "Trust me.",
                                   "source": "caller", "previous_sha256": "0" * 64}}
    with pytest.raises(ValueError, match="lifecycle"):
        R.record(home, forged, content=content, expected=current["record_sha256"])
    withdrawn = withdraw(registry)
    result = R.record(home, entry, content=content, expected=withdrawn["record_sha256"],
                      requalify=True, reason="Source review completed.", source="review/recheck")
    updated = R.record(home, {**entry, "summary": "Clarified wording."}, content=content,
                       expected=result["record_sha256"])
    assert updated["record"]["lifecycle"] == result["record"]["lifecycle"]


def test_withdrawal_history_capacity_failure_keeps_current_record(registry):
    home, content, entry = registry
    history = home / "research/history"
    history.mkdir(parents=True)
    for index in range(1000):
        (history / (str(index) + ".json")).write_text("{}")
    before = R.check(home, entry["id"], content=content)
    with pytest.raises(ValueError, match="history limit"):
        withdraw(registry)
    assert R.check(home, entry["id"], content=content) == before
    assert not (home / "research" / (entry["id"] + ".json")).exists()


def test_withdrawal_store_capacity_failure_keeps_builtin_record(registry):
    home, content, entry = registry
    store = home / "research"
    store.mkdir(parents=True)
    for index in range(200):
        (store / (str(index) + ".json")).write_text("{}")
    with pytest.raises(ValueError, match="store limit"):
        withdraw(registry)
    assert R.check(home, entry["id"], content=content)["record"] == entry


def test_cli_withdrawal_and_deliberate_requalification_survive_cold_reads(registry):
    home, content, entry = registry
    root = Path(__file__).resolve().parents[1]
    def run(action, *options):
        result = subprocess.run([sys.executable, str(root / "bin/harness"), "--home", str(home.parent),
            "research", action, entry["id"], "--content-root", str(content), *options],
            capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)
    current = run("check")
    withdrawn = run("withdraw", "--expected", current["record_sha256"],
                    "--reason", "Review rejected the method.", "--source", "review/withdrawal")
    assert run("check")["status"] == "WITHDRAWN"
    input_path = home.parent / "entry.json"
    input_path.write_text(json.dumps(entry))
    qualified = run("record", "--input", str(input_path), "--expected", withdrawn["record_sha256"],
                    "--requalify", "--reason", "Independent source review completed.",
                    "--source", "review/requalification")
    assert qualified["status"] == "REUSE_EXISTING"
    assert run("check")["record"] == qualified["record"]


def test_concurrent_update_and_withdrawal_commit_only_one_current_version(registry):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    home, content, entry = registry
    assert callable(getattr(R, "withdraw", None)), "explicit research withdrawal is missing"
    current = R.check(home, entry["id"], content=content)
    barrier = Barrier(2)
    def write(action):
        barrier.wait(timeout=10)
        try:
            if action == "withdraw":
                return R.withdraw(home, entry["id"], content=content, expected=current["record_sha256"],
                                  reason="Review rejected advice.", source="review/concurrent")
            return R.record(home, {**entry, "summary": "Concurrent clarification."},
                            content=content, expected=current["record_sha256"])
        except ValueError as error:
            assert "changed" in str(error)
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, ["withdraw", "record"]))
    successes = [result for result in results if result is not None]
    assert len(successes) == 1
    assert R.check(home, entry["id"], content=content) == successes[0]
    history = list((home / "research/history").glob("*.json"))
    assert len(history) == 1 and json.loads(history[0].read_text()) == entry


@pytest.mark.parametrize("lifecycle", [None, {}, {"state": "active"},
    {"state": "withdrawn", "reason": "Review", "source": "review", "previous_sha256": "invalid"},
    {"state": "withdrawn", "reason": "", "source": "review", "previous_sha256": "0" * 64}])
def test_malformed_persisted_lifecycle_fails_closed(registry, lifecycle):
    home, content, entry = registry
    store = home / "research"
    store.mkdir(parents=True)
    (store / (entry["id"] + ".json")).write_text(json.dumps({**entry, "lifecycle": lifecycle}))
    with pytest.raises(ValueError, match="lifecycle|provenance"):
        R.check(home, entry["id"], content=content)


def test_withdrawal_of_missing_or_already_withdrawn_research_is_rejected(registry):
    home, content, entry = registry
    assert callable(getattr(R, "withdraw", None)), "explicit research withdrawal is missing"
    with pytest.raises(ValueError, match="no research"):
        R.withdraw(home, "unknown-domain", content=content, expected=None,
                   reason="Review", source="review/missing")
    result = withdraw(registry)
    with pytest.raises(ValueError, match="already withdrawn"):
        withdraw(registry, expected=result["record_sha256"])
    assert R.check(home, entry["id"], content=content) == result


def test_requalification_history_capacity_failure_preserves_withdrawal(registry):
    home, content, entry = registry
    result = withdraw(registry)
    history = home / "research/history"
    for index in range(999):
        (history / (str(index) + ".json")).write_text("{}")
    with pytest.raises(ValueError, match="history limit"):
        R.record(home, entry, content=content, expected=result["record_sha256"], requalify=True,
                 reason="Review completed.", source="review/requalified")
    assert R.check(home, entry["id"], content=content) == result


def test_repeated_lifecycle_preserves_each_withdrawal_and_preference_file(registry):
    home, content, entry = registry
    R.save_preference(home, entry["id"], "Keep limitations.", "user instruction")
    preference_file = home / "research" / (entry["id"] + ".preferences.json")
    preferences = preference_file.read_bytes()
    first = withdraw(registry)
    qualified = R.record(home, first["record"], content=content, expected=first["record_sha256"],
                         confirmed_preferences=first["preferences_sha256"], requalify=True,
                         reason="Bounded review completed.", source="review/first-requalification")
    second = withdraw(registry, expected=qualified["record_sha256"],
                      reason="New contrary evidence.", source="review/second-withdrawal")
    history = [json.loads(p.read_text()) for p in (home / "research/history").glob("*.json")]
    assert entry in history and first["record"] in history and qualified["record"] in history
    assert len(history) == 3
    assert preference_file.read_bytes() == preferences
    assert second["status"] == "WITHDRAWN"
