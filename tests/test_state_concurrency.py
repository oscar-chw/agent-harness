"""Independent writers must preserve state history and session notes."""
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import time

import pytest

import agent_harness
from agent_harness.mcp.state import State


@pytest.mark.parametrize("operation", ["state", "note"])
def test_independent_processes_keep_both_writes(tmp_path, operation):
    worker = textwrap.dedent("""
        import os
        import sys
        import time
        from pathlib import Path
        from agent_harness.mcp.state import State

        project, operation, label = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
        state = State(home=project / "harness", project=project)
        destination = state._dir("") / "STATE.md" if operation == "state" else state._log()
        prefix = project / ("wrote-" + label)
        replace = os.replace

        def overlap(source, target):
            if Path(target) == destination:
                # Hold the commit briefly so an unlocked peer attempts to commit
                # against the same prior state. A locked peer arrives afterward.
                prefix.touch()
                deadline = time.monotonic() + .75
                while len(list(project.glob("wrote-*"))) < 2 and time.monotonic() < deadline:
                    time.sleep(.01)
            return replace(source, target)

        os.replace = overlap
        (project / ("ready-" + label)).touch()
        sys.stdin.readline()
        if operation == "state":
            state.state_save(label)
        else:
            state.session_note(label)
    """)
    env = {**os.environ, "PYTHONPATH": str(Path(agent_harness.__file__).resolve().parents[1])}
    with subprocess.Popen([sys.executable, "-c", worker, str(tmp_path), operation, "first"],
                          stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env) as first, \
         subprocess.Popen([sys.executable, "-c", worker, str(tmp_path), operation, "second"],
                          stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env) as second:
        deadline = time.monotonic() + 6
        while len(list(tmp_path.glob("ready-*"))) < 2:
            assert time.monotonic() < deadline, "state writers did not become ready"
            time.sleep(.01)
        for process in (first, second):
            process.stdin.write("\n")
            process.stdin.flush()
        results = [process.communicate(timeout=12)[1] for process in (first, second)]
        assert (first.returncode, second.returncode) == (0, 0), results

    state = State(home=tmp_path / "harness", project=tmp_path)
    if operation == "state":
        assert sorted([state.state_load(), *(path.read_text() for path in state.versions())]) == ["first", "second"]
    else:
        assert sorted(row["summary"] for row in state.session_recent()) == ["first", "second"]


def test_failed_state_replacement_keeps_current_checkpoint(tmp_path, monkeypatch):
    state = State(home=tmp_path / "harness", project=tmp_path)
    state.state_save("last usable checkpoint")
    current = state.state_path()
    replace = os.replace

    def fail_current(source, target):
        if Path(target) == current:
            raise OSError("fixture replacement failure")
        return replace(source, target)

    with monkeypatch.context() as patch:
        patch.setattr(os, "replace", fail_current)
        with pytest.raises(OSError, match="fixture replacement failure"):
            state.state_save("new checkpoint")
    assert state.state_load() == "last usable checkpoint"
