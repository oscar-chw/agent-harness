"""Workplace pickup acceptance across hook delivery and concurrent checkpoints.

All inputs are local temporary fixtures. These checks exercise transport behavior
under inherited process permissions and make no native-client uptake claim.
"""
from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier, BrokenBarrierError

import pytest

from agent_harness.board_hooks import participate
from agent_harness.mcp.server import Server
from agent_harness.operational_state import OperationalState
from agent_harness.shared_board import SharedBoard


@pytest.fixture
def workplace(tmp_path, monkeypatch):
    project = tmp_path / "workplace"
    (project / ".git").mkdir(parents=True)
    home = tmp_path / "harness"
    monkeypatch.chdir(project)
    monkeypatch.setenv("HARNESS_HOME", str(home))
    monkeypatch.delenv("HARNESS_PROJECT", raising=False)
    monkeypatch.delenv("HARNESS_DISABLE", raising=False)
    monkeypatch.delenv("HARNESS_ENABLE", raising=False)
    return project, home, OperationalState(home, project)


def rpc(server, method, **params):
    response = server.handle({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    assert "result" in response, response
    return response["result"]


def initialize(server):
    return rpc(server, "initialize", protocolVersion="2025-06-18", capabilities={},
               clientInfo={"name": "workplace-fixture", "version": "1"})["instructions"]


def automatic_text(response):
    assert response["isError"] is False, response
    return "\n".join(item["text"] for item in response["content"]
                     if item.get("type") == "text" and item["text"].startswith("Shared board"))


def reader(workplace, transport):
    project, home, _ = workplace
    if transport == "mcp":
        server = Server(home=home)
        initial = initialize(server)

        def boundary():
            return automatic_text(rpc(server, "tools/call", name="session_recent", arguments={}))
    else:
        event = {"cwd": str(project), "session_id": "workplace-reader"}
        initial = participate(event, "startup")

        def boundary():
            return participate(event, "prompt")
    return initial, boundary


@pytest.mark.integration
@pytest.mark.parametrize("transport", ["mcp", "hook"])
def test_lease_renewal_without_changed_work_adds_zero_automatic_context(workplace, transport):
    _, _, store = workplace
    store.put("parser", {"goal": "Fix parser", "next": "Run the independent integration gate"},
              expected=0, request_id="seed-parser")
    lease = store.claim("parser", expected=1, request_id="claim-parser", ttl=300)
    initial, boundary = reader(workplace, transport)
    assert "Fix parser" in initial and "leased_unverified" in initial
    renewed = store.renew("parser", expected=lease["version"], request_id="renew-parser",
                          token=lease["token"], fence=lease["fence"], ttl=300)
    assert renewed["version"] > lease["version"]
    assert boundary() == ""


@pytest.mark.integration
@pytest.mark.parametrize("transport", ["mcp", "hook"])
def test_long_checkpoint_stop_suffix_and_binding_reach_each_delivery_transport(workplace, transport):
    project, home, _ = workplace
    writer = Server(home=home)
    initialize(writer)
    first = rpc(writer, "tools/call", name="state_save",
                arguments={"project": str(project), "text": "A" * 350 + " previous status"})
    assert first["isError"] is False
    initial, boundary = reader(workplace, transport)
    assert "checkpoint_saved" in initial
    marker = "STOP: newly discovered data loss"
    changed = rpc(writer, "tools/call", name="state_save",
                  arguments={"project": str(project), "text": "A" * 350 + " " + marker})
    assert changed["isError"] is False
    update = boundary()
    assert marker in update
    assert "full_text_sha256=" in update
    assert boundary() == ""


@pytest.mark.integration
@pytest.mark.parametrize("schedule", ["serial", "overlapping"])
def test_same_checkpoint_from_two_sessions_creates_one_advisory_record(workplace, monkeypatch, schedule):
    project, home, store = workplace
    publishers = [SharedBoard(home, project), SharedBoard(home, project)]
    summary = "Parser reviewed; independent gate remains pending"
    if schedule == "serial":
        for publisher in publishers:
            publisher.publish(summary)
    else:
        barrier = Barrier(2)
        snapshot = OperationalState.snapshot

        def overlapping_snapshot(instance):
            # Both callers read a real committed snapshot before either writes.
            # This fixes the schedule at the existing check/write seam.
            result = snapshot(instance)
            try:
                barrier.wait(timeout=1)
            except BrokenBarrierError:
                # A serialized publisher can finish after this bounded wait.
                return result
            return result

        with monkeypatch.context() as patch:
            patch.setattr(OperationalState, "snapshot", overlapping_snapshot)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(publisher.publish, summary) for publisher in publishers]
                for future in futures:
                    future.result(timeout=10)
    matching = [row for row in store.snapshot()["tasks"] if row["value"].get("summary") == summary]
    assert len(matching) == 1
    assert matching[0]["status"] == "open"
    assert "independent gate remains pending" in json.dumps(matching[0]["value"])
