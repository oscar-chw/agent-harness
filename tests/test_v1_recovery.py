"""Scoped recovery and withdrawal histories; synthetic development, not model holdouts."""
import copy
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent_harness.project_memory import ProjectMemory
from agent_harness.vault_sources import SourceVault, initialize


@pytest.fixture
def history(tmp_path):
    pid = initialize(tmp_path)
    source = tmp_path / "decision.md"
    source.write_text("Drafts only: limit 3; exception: never export.\n")
    ref = SourceVault(tmp_path, pid).capture("decision.md")
    item = {"id": "decision", "project_id": pid, "layer": "authority", "kind": "authority",
            "scope": "offline", "text": source.read_text(), "provenance": [
                {"source": ref, "start_line": 1, "end_line": 1}], "confidence": "user_stated",
            "sensitivity": "private", "access_boundary": "local_user", "owner": "synthetic-owner",
            "freshness": "current"}
    policy = {"allowed_sensitivities": ["private"], "allowed_scopes": ["offline"], "layers": ["authority"]}
    return tmp_path, pid, item, policy


@pytest.mark.parametrize("seed", range(20))
def test_revision_exception_and_withdrawal_survive_twenty_reset_histories(history, seed):
    root, pid, item, policy = history
    store = ProjectMemory(root, pid)
    receipts = [store.append(item, expected=None)]
    # Correcting the same item, including a return to an earlier value, must not
    # erase exceptions or reactivate a withdrawn grant after reconstructing the store.
    for value in (seed + 5, seed + 8, 3):
        (root / "decision.md").write_text(f"Drafts only: limit {value}; exception: never export.\n")
        item["text"] = (root / "decision.md").read_text()
        item["provenance"][0]["source"] = SourceVault(root, pid).capture("decision.md")
        store = ProjectMemory(root, pid)
        receipts.append(store.append(item, expected=receipts[-1]))
        current = store.recover(receipts[0], phase="compact", depends_on_memory=True, **policy)
        assert current["decision"] == "CANDIDATE"
        assert current["record"]["receipt"] == receipts[-1]
        assert current["record"]["item"]["text"] == item["text"]
        assert "never export" in current["record"]["item"]["text"]
        reuse = store.recover(receipts[0], phase="resume", depends_on_memory=True,
                              verified_receipt=receipts[-1], **policy)
        assert reuse["decision"] == "REUSE_VERIFIED"
        assert "record" not in reuse  # no repeated content injection
    item["freshness"] = "withdrawn"
    withdrawn = store.append(item, expected=receipts[-1])
    for _ in range(2):
        store = ProjectMemory(root, pid)
        for receipt in receipts + [withdrawn]:
            result = store.recover(receipt, phase="resume", depends_on_memory=True,
                                   verified_receipt=receipt, **policy)
            assert result["decision"] == "REFUSE_WITHDRAWN"
            assert "record" not in result
        with pytest.raises(ValueError, match="withdrawn"):
            store.read_scoped(withdrawn, **policy)
        with pytest.raises(ValueError, match="withdrawn"):
            store.latest("decision", allowed_sensitivities=["private"])
        result = store.search("decision", **policy)
        assert result["hits"] == []
        assert result["omitted"] == [{"receipt": withdrawn, "reason": "withdrawn"}]
        page = store.search_page("decision", **policy)
        assert page["total_expired"] == 0
        assert page["total_withdrawn"] == 1
        assert page["hits"] == []
        assert page["omitted"] == [{"receipt": withdrawn, "reason": "withdrawn"}]
        archived = store.read_scoped(receipts[0], historical=True, **policy)
        assert archived["historical"] is True
        assert archived["item"]["freshness"] == "current"  # history isn't rewritten
        assert archived["current_status"] == "withdrawn"
        assert archived["usable_for_current_decisions"] is False
        with pytest.raises(ValueError, match="withdrawal"):
            store.append({**item, "freshness": "current"}, expected=withdrawn)


def test_recovery_validates_scope_before_resolving_current_or_old_sources(history):
    root, pid, item, policy = history
    store = ProjectMemory(root, pid)
    receipt = store.append(item, expected=None)
    for status in ("current", "unknown", "withdrawn"):
        receipt = store.append({**item, "freshness": status}, expected=receipt)
        with patch.object(SourceVault, "resolve", side_effect=AssertionError("out-of-scope read")):
            with pytest.raises(PermissionError):
                store.recover(receipt, phase="resume", depends_on_memory=True,
                              **{**policy, "allowed_scopes": ["other"]})


def test_irrelevant_recovery_does_not_read_the_journal(history):
    root, pid, item, policy = history
    store = ProjectMemory(root, pid)
    receipt = store.append(item, expected=None)
    with patch.object(store, "_load", side_effect=AssertionError("unnecessary history read")):
        for phase, dependent in (("startup", True), ("resume", False)):
            assert store.recover(receipt, phase=phase, depends_on_memory=dependent,
                                 **policy)["decision"] == "SKIP"
        with pytest.raises(ValueError):
            store.recover(receipt, phase="resume", depends_on_memory="yes", **policy)


def test_unknown_or_changed_source_never_reuses_a_receipt(history):
    root, pid, item, policy = history
    store = ProjectMemory(root, pid)
    receipt = store.append({**item, "freshness": "unknown"}, expected=None)
    assert store.recover(receipt, phase="resume", depends_on_memory=True,
                         verified_receipt=receipt, **policy)["decision"] == "HOLD"
    current = store.append(item, expected=receipt)
    malformed = {**current, "sha256": "0" * 64}
    with pytest.raises(ValueError, match="receipt"):
        store.recover(current, phase="resume", depends_on_memory=True, verified_receipt=malformed, **policy)
    (root / "decision.md").write_text("Changed outside the store.\n")
    with pytest.raises(ValueError, match="stale source"):
        store.recover(current, phase="resume", depends_on_memory=True, verified_receipt=current, **policy)


def test_withdrawal_is_distinct_from_expiry_and_reopens_only_under_a_new_record(history):
    root, pid, item, policy = history
    store = ProjectMemory(root, pid)
    old = store.append({**item, "freshness": "expired"}, expected=None)
    renewed = store.append(item, expected=old)
    assert store.recover(renewed, phase="resume", depends_on_memory=True, **policy)["decision"] == "CANDIDATE"
    revoked = store.append({**item, "freshness": "withdrawn"}, expected=renewed)
    before = {p.name: p.read_bytes() for p in (root / ".harness/records").iterdir()}
    for status in ("current", "unknown", "expired"):
        with pytest.raises(ValueError, match="withdrawal"):
            store.append({**item, "freshness": status}, expected=revoked)
    assert before == {p.name: p.read_bytes() for p in (root / ".harness/records").iterdir()}


def test_recovery_uses_no_caller_supplied_status_or_truncated_receipt(history):
    root, pid, item, policy = history
    store = ProjectMemory(root, pid)
    receipt = store.append(item, expected=None)
    for forged in ({"id": "decision", "revision": 1}, {**receipt, "sequence": True}):
        with pytest.raises(ValueError, match="receipt"):
            store.recover(receipt, phase="compact", depends_on_memory=True,
                          verified_receipt=forged, **policy)
    with pytest.raises(ValueError, match="budget"):
        store.recover(receipt, phase="compact", depends_on_memory=True, max_bytes=20, **policy)


def test_verified_reuse_budgets_only_its_receipt_but_still_checks_source(history):
    root, pid, item, policy = history
    store = ProjectMemory(root, pid)
    item["text"] += " retained diagnostic" * 400
    receipt = store.append(item, expected=None)
    result = store.recover(receipt, phase="resume", depends_on_memory=True,
                           verified_receipt=receipt, max_bytes=500, **policy)
    assert result["decision"] == "REUSE_VERIFIED"
    assert len(json.dumps(result, ensure_ascii=False).encode()) <= 500
    with pytest.raises(ValueError, match="budget"):
        store.recover(receipt, phase="resume", depends_on_memory=True, max_bytes=500, **policy)
    (root / "decision.md").write_text("A subsequent source correction.\n")
    with pytest.raises(ValueError, match="stale source"):
        store.recover(receipt, phase="resume", depends_on_memory=True,
                      verified_receipt=receipt, max_bytes=500, **policy)


def test_fresh_process_recovers_withdrawal_from_retained_events(history):
    root, pid, item, policy = history
    store = ProjectMemory(root, pid)
    first = store.append(item, expected=None)
    store.append({**copy.deepcopy(item), "freshness": "withdrawn"}, expected=first)
    payload = json.dumps({"root": str(root), "pid": pid, "receipt": first, "policy": policy})
    code = """import json,sys
from agent_harness.project_memory import ProjectMemory
x=json.loads(sys.argv[1])
s=ProjectMemory(x['root'],x['pid'])
print(json.dumps(s.recover(x['receipt'],phase='resume',depends_on_memory=True,**x['policy'])))
"""
    run = subprocess.run([sys.executable, "-c", code, payload], capture_output=True, text=True,
                         timeout=15, env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")})
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["decision"] == "REFUSE_WITHDRAWN"


def test_existing_cli_exposes_scoped_recovery_and_rejects_history_ambiguity(history):
    root, pid, item, policy = history
    store = ProjectMemory(root, pid)
    receipt = store.append(item, expected=None)
    launcher = Path(__file__).resolve().parents[1] / "bin/harness"
    argv = [sys.executable, str(launcher), "memory-read", "--project-root", str(root),
            "--project-id", pid, "--receipt", json.dumps(receipt), "--allow-sensitivity", "private",
            "--allow-scope", "offline", "--layer", "authority", "--recover", "resume"]
    run = subprocess.run(argv, capture_output=True, text=True, timeout=15)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["decision"] == "CANDIDATE"
    reuse = subprocess.run(argv + ["--verified-receipt", json.dumps(receipt)],
                           capture_output=True, text=True, timeout=15)
    assert reuse.returncode == 0, reuse.stderr
    assert json.loads(reuse.stdout)["decision"] == "REUSE_VERIFIED"
    # Historical data cannot masquerade as a current recovery result, and a
    # verified handle has no meaning without an explicit recovery operation.
    for bad_argv in (argv + ["--historical"], argv[:-2] + ["--verified-receipt", json.dumps(receipt)]):
        bad = subprocess.run(bad_argv, capture_output=True, text=True, timeout=15)
        assert bad.returncode == 2
        assert bad.stdout == ""
    empty = subprocess.run(argv + ["--verified-receipt", ""], capture_output=True, text=True, timeout=15)
    assert empty.returncode == 2
    assert empty.stdout == ""
