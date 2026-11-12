"""Independent shared-admission acceptance cases; no worker/model is launched.

The public interface supplied by the orchestrator is the oracle. Missing module
or missing behavior is a failure, never a skip. Processes share only an explicit
temporary admission home; their writes and project roots are fixture paths.
"""
import json
import multiprocessing
from pathlib import Path
from queue import Empty
import time

import pytest

from agent_harness.workgraph.admission import Admission


def admitted(result):
    assert isinstance(result, dict)
    assert result["admitted"] is True
    assert isinstance(result["reason"], str) and result["reason"]
    assert isinstance(result["reservation"], str) and result["reservation"]
    return result["reservation"]


def denied(result):
    assert isinstance(result, dict)
    assert result["admitted"] is False
    assert isinstance(result["reason"], str) and result["reason"]
    assert not result.get("reservation"), "a refused request must not receive a usable reservation"


def snapshot(ledger):
    records = ledger.inspect()
    assert isinstance(records, list)
    assert all(isinstance(row, dict) for row in records)
    # Record order and additional diagnostic fields are not an admission policy.
    return sorted(json.dumps(row, sort_keys=True) for row in records)


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    return root


def test_disjoint_outputs_sharing_context_can_enter_without_a_project_wide_lock(tmp_path, project):
    ledger = Admission(tmp_path / "admission", capacity=3)
    (project / "ctx.md").write_text("Both tasks may read this same context.\n")
    first = admitted(ledger.acquire(project, ["results/a.txt"], "owner-a", "read ctx.md; write a"))
    second = admitted(ledger.acquire(project, ["results/b.txt"], "owner-b", "read ctx.md; write b"))
    assert first != second
    assert len(snapshot(ledger)) == 2
    assert not (project / "results").exists(), "declaring writes must not create task output files"


def test_read_only_requests_consume_capacity_without_claiming_write_paths(tmp_path, project):
    ledger = Admission(tmp_path / "admission", capacity=3)
    tokens = [admitted(ledger.acquire(project, [], "reader-a", "read shared source")),
              admitted(ledger.acquire(project, [], "reader-b", "read shared source")),
              admitted(ledger.acquire(project, ["result.txt"], "writer", "produce result"))]
    assert len(set(tokens)) == 3
    before = snapshot(ledger)
    denied(ledger.acquire(project, [], "reader-c", "one reader too many"))
    assert snapshot(ledger) == before


@pytest.mark.parametrize("first,second", [
    (None, None), (None, ["src/a.py"]), (["src/a.py"], None),
    (["."], ["src/a.py"]), (["src/a.py"], ["."]),
    (["src"], ["src/nested/a.py"]), (["src/nested/a.py"], ["src"]),
])
def test_exclusive_root_and_parent_child_scopes_conflict_in_both_directions(
        tmp_path, project, first, second):
    ledger = Admission(tmp_path / "admission", capacity=2)
    admitted(ledger.acquire(project, first, "owner-a", "first"))
    before = snapshot(ledger)
    denied(ledger.acquire(project, second, "owner-b", "overlap"))
    assert snapshot(ledger) == before, "a write conflict must leave no extra admission entry"


def test_component_prefix_is_not_path_containment(tmp_path, project):
    ledger = Admission(tmp_path / "admission", capacity=3)
    tokens = [admitted(ledger.acquire(project, [name], f"owner-{i}", f"task-{i}"))
              for i, name in enumerate(["src/a", "src/ab", "src/a-other/file.py"])]
    assert len(set(tokens)) == 3
    assert len(snapshot(ledger)) == 3


def test_internal_normalization_and_missing_output_components_use_one_identity(tmp_path, project):
    ledger = Admission(tmp_path / "admission", capacity=2)
    admitted(ledger.acquire(project, ["new/../new/output.json"], "owner-a", "new output"))
    denied(ledger.acquire(project, ["new/./output.json"], "owner-b", "same output"))
    assert len(snapshot(ledger)) == 1
    assert not (project / "new").exists()


def test_symlink_alias_of_an_inside_directory_conflicts_with_its_target(tmp_path, project):
    (project / "real").mkdir()
    (project / "alias").symlink_to(project / "real", target_is_directory=True)
    ledger = Admission(tmp_path / "admission", capacity=2)
    admitted(ledger.acquire(project, ["alias/sub/result.txt"], "owner-a", "alias output"))
    denied(ledger.acquire(project, ["real/sub/result.txt"], "owner-b", "same target"))
    assert len(snapshot(ledger)) == 1


def test_symlink_alias_of_project_root_cannot_evade_existing_write_ownership(tmp_path, project):
    alias = tmp_path / "project-alias"
    alias.symlink_to(project, target_is_directory=True)
    ledger = Admission(tmp_path / "admission", capacity=2)
    admitted(ledger.acquire(project, ["shared.txt"], "owner-a", "target root"))
    denied(ledger.acquire(alias, ["shared.txt"], "owner-b", "aliased root"))
    assert len(snapshot(ledger)) == 1


def test_nested_project_roots_compare_actual_output_paths(tmp_path, project):
    nested = project / "nested"
    nested.mkdir()
    ledger = Admission(tmp_path / "admission", capacity=3)
    admitted(ledger.acquire(project, ["nested/result.txt"], "outer", "outer output"))
    denied(ledger.acquire(nested, ["result.txt"], "inner", "same physical output"))
    admitted(ledger.acquire(nested, ["other.txt"], "other", "unrelated physical output"))
    assert len(snapshot(ledger)) == 2


@pytest.mark.parametrize("bad", ["../outside.txt", "src/../../outside.txt", "absolute-inside",
                                      "absolute-outside", "external-link/result.txt", ""])
def test_invalid_or_escaping_write_raises_and_preserves_existing_entries(tmp_path, project, bad):
    outside = tmp_path / "outside"
    outside.mkdir()
    (project / "external-link").symlink_to(outside, target_is_directory=True)
    if bad == "absolute-inside":
        bad = str(project / "inside.txt")
    elif bad == "absolute-outside":
        bad = str(outside / "result.txt")
    ledger = Admission(tmp_path / "admission", capacity=3)
    admitted(ledger.acquire(project, ["existing.txt"], "owner", "existing"))
    before = snapshot(ledger)
    with pytest.raises(ValueError):
        ledger.acquire(project, ["valid-first.txt", bad], "invalid", "validate the entire request")
    assert snapshot(ledger) == before, "validation failure must not reserve the earlier valid path"
    assert not (outside / "result.txt").exists()


@pytest.mark.parametrize("writes", ["src/file.py", [1], {"src/file.py": True}])
def test_malformed_write_collection_does_not_create_an_entry(tmp_path, project, writes):
    ledger = Admission(tmp_path / "admission", capacity=2)
    with pytest.raises((ValueError, TypeError)):
        ledger.acquire(project, writes, "owner", "invalid declaration")
    assert snapshot(ledger) == []


def test_multi_output_request_reserves_one_slot_and_all_paths_atomically(tmp_path, project):
    ledger = Admission(tmp_path / "admission", capacity=2)
    token = admitted(ledger.acquire(project, ["a.txt", "b.txt"], "owner-a", "two outputs"))
    assert len(snapshot(ledger)) == 1
    denied(ledger.acquire(project, ["free.txt", "b.txt"], "owner-b", "one conflicting output"))
    admitted(ledger.acquire(project, ["free.txt"], "owner-c", "must remain available"))
    assert len(snapshot(ledger)) == 2
    assert ledger.release(token) is True


def test_capacity_is_shared_between_projects_and_denial_does_not_leak_a_slot(tmp_path, project):
    other = tmp_path / "other-project"
    other.mkdir()
    home = tmp_path / "admission"
    first = Admission(home, capacity=1)
    token = admitted(first.acquire(project, ["result.txt"], "owner-a", "project a"))
    second = Admission(home, capacity=1)
    denied(second.acquire(other, ["result.txt"], "owner-b", "project b"))
    assert len(snapshot(second)) == 1
    assert second.release(token) is False, "reopening the shared home grants no release authority"
    assert first.release(token) is True
    admitted(second.acquire(other, ["result.txt"], "owner-b", "project b after release"))
    assert len(snapshot(first)) == 1


def test_reopen_retains_reservations_and_release_is_exact_and_idempotent(tmp_path, project):
    home = tmp_path / "admission"
    original = Admission(home, capacity=2)
    a = admitted(original.acquire(project, ["a.txt"], "owner-a", "a"))
    b = admitted(original.acquire(project, ["b.txt"], "owner-b", "b"))
    reopened = Admission(home, capacity=2)
    before = snapshot(reopened)
    assert len(before) == 2
    assert reopened.release(a + "-not-the-token") is False
    assert reopened.release("unknown-reservation") is False
    assert reopened.release(a) is False, "knowing an inspected id is not acquiring-instance authority"
    assert reopened.release(b) is False
    assert snapshot(reopened) == before
    assert original.release(a + "-not-the-token") is False
    assert original.release("unknown-reservation") is False
    assert snapshot(original) == before
    assert original.release(a) is True
    assert original.release(a) is False
    assert len(snapshot(original)) == 1
    denied(original.acquire(project, ["b.txt"], "owner-c", "b remains owned"))
    admitted(original.acquire(project, ["a.txt"], "owner-c", "a is free"))
    assert reopened.release(b) is False
    assert original.release(b) is True


@pytest.mark.parametrize("capacity", [0, -1, True, False, 1.5, "2", None])
def test_invalid_capacity_cannot_initialize_a_new_shared_home(tmp_path, capacity):
    home = tmp_path / "admission"
    with pytest.raises((ValueError, TypeError)):
        Admission(home, capacity=capacity)
    assert snapshot(Admission(home, capacity=2)) == []


@pytest.mark.parametrize("capacity", [0, -1, True, False, 1.5, "2", None])
def test_invalid_capacity_fails_without_resetting_existing_state(tmp_path, project, capacity):
    home = tmp_path / "admission"
    ledger = Admission(home, capacity=2)
    admitted(ledger.acquire(project, ["existing.txt"], "owner", "existing"))
    before = snapshot(ledger)
    with pytest.raises((ValueError, TypeError)):
        Admission(home, capacity=capacity)
    assert snapshot(Admission(home, capacity=2)) == before


@pytest.mark.parametrize("replacement", [1, 3])
def test_capacity_mismatch_is_refused_and_does_not_reset_even_after_release(
        tmp_path, project, replacement):
    home = tmp_path / "admission"
    ledger = Admission(home, capacity=2)
    token = admitted(ledger.acquire(project, ["existing.txt"], "owner", "existing"))
    before = snapshot(ledger)
    with pytest.raises(ValueError):
        Admission(home, capacity=replacement)
    assert snapshot(ledger) == before
    assert ledger.release(token) is True
    with pytest.raises(ValueError):
        Admission(home, capacity=replacement)
    assert snapshot(Admission(home, capacity=2)) == []


def _acquire_process(home, capacity, root, writes, index, start, output):
    ledger = Admission(Path(home), capacity=capacity)
    start.wait(timeout=15)
    output.put(ledger.acquire(Path(root), writes, f"process-{index}", f"race-{index}"))
    # Deliberately exit without release: a dead owner must not silently free a
    # still-recorded reservation while the parent checks the shared capacity.


def race(home, capacity, requests):
    context = multiprocessing.get_context("spawn")
    start = context.Barrier(len(requests) + 1)
    output = context.Queue()
    processes = [context.Process(target=_acquire_process,
                                 args=(str(home), capacity, str(root), writes, i, start, output))
                 for i, (root, writes) in enumerate(requests)]
    launched = []
    try:
        for process in processes:
            process.start()
            launched.append(process)
        # Every independent process opens the shared ledger before this barrier
        # releases their competing acquire calls. No sleep or retry picks a winner.
        start.wait(timeout=15)
        deadline = time.monotonic() + 15
        results = []
        for _ in processes:
            try:
                results.append(output.get(timeout=max(0.01, deadline - time.monotonic())))
            except Empty:
                pytest.fail("an admission process produced no result before the bounded deadline")
        for process in processes:
            process.join(timeout=max(0, deadline - time.monotonic()))
            assert process.exitcode == 0, "admission subprocess failed or survived its test deadline"
        return results
    finally:
        for process in launched:
            if process.is_alive():
                process.terminate()
        for process in launched:
            process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join(timeout=2)
            assert not process.is_alive(), "owned admission test process survived cleanup"
        output.close()
        output.join_thread()


@pytest.mark.parametrize("capacity", [1, 2])
def test_actual_process_race_caps_all_projects_and_retains_exited_owners(tmp_path, capacity):
    home = tmp_path / "admission"
    roots = [tmp_path / f"project-{i}" for i in range(6)]
    for root in roots:
        root.mkdir()
    results = race(home, capacity, [(root, ["result.txt"]) for root in roots])
    winners = [admitted(row) for row in results if row["admitted"] is True]
    for row in results:
        if row["admitted"] is not True:
            denied(row)
    assert len(winners) == len(set(winners)) == capacity
    reopened = Admission(home, capacity=capacity)
    assert len(snapshot(reopened)) == capacity
    denied(reopened.acquire(roots[0], [], "parent", "exited owners still count"))
    assert reopened.release(winners[0]) is False, "a dead child does not transfer its release authority"
    denied(reopened.acquire(roots[0], [], "parent", "cold inspect cannot free a dead owner's slot"))
    assert len(snapshot(reopened)) == capacity


def test_actual_process_race_rejects_alias_overlaps_even_with_spare_capacity(tmp_path, project):
    (project / "real").mkdir()
    (project / "alias").symlink_to(project / "real", target_is_directory=True)
    names = ["real/shared.txt", "real/./shared.txt", "alias/shared.txt",
             "real/new/../shared.txt", "alias/./shared.txt", "real/shared.txt"]
    home = tmp_path / "admission"
    results = race(home, 6, [(project, [name]) for name in names])
    winners = [admitted(row) for row in results if row["admitted"] is True]
    for row in results:
        if row["admitted"] is not True:
            denied(row)
    assert len(winners) == 1, "canonical write ownership, not capacity, must reject five contenders"
    ledger = Admission(home, capacity=6)
    assert len(snapshot(ledger)) == 1
    admitted(ledger.acquire(project, ["real/unrelated.txt"], "parent", "spare slot and disjoint output"))
    assert len(snapshot(ledger)) == 2


def test_actual_process_race_allows_disjoint_writers_in_one_project(tmp_path, project):
    home = tmp_path / "admission"
    requests = [(project, [f"out/{i}.txt"]) for i in range(4)]
    tokens = [admitted(row) for row in race(home, 4, requests)]
    assert len(set(tokens)) == 4
    assert len(snapshot(Admission(home, capacity=4))) == 4
