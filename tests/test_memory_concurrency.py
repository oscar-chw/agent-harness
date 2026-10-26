"""Real-process checks for the shared local memory store."""

import json
import errno
import os
import subprocess
import sys
import time
import types
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

WORKER = """
import json, os, sys, time
from pathlib import Path
from agent_harness.mcp.memory import Memory

try:
    memory = Memory(home=os.environ["STORE"], project=os.environ["PROJECT"],
                    user_home=os.environ["USER_STORE"], fts=os.environ["FTS"] == "1")
    Path(os.environ["READY"]).touch()
    deadline = time.monotonic() + 15
    while not Path(os.environ["GO"]).exists():
        if time.monotonic() > deadline:
            raise TimeoutError("start gate not opened")
        time.sleep(.002)
    result = memory.mem_add(os.environ["FACT"], scope="project")
    print(json.dumps(result))
    memory.con.close()
except Exception as exc:
    print(type(exc).__name__ + ": " + str(exc), file=sys.stderr)
    sys.exit(1)
"""


@pytest.mark.parametrize("same_fact", [False, True])
@pytest.mark.parametrize("preseed", [False, True])
@pytest.mark.parametrize("fts", [False, True])
def test_simultaneous_process_writes_keep_every_fact(tmp_path, same_fact, preseed, fts):
    from agent_harness.mcp.memory import Memory

    store = tmp_path / "store"
    project = tmp_path / "project"
    project.mkdir()
    if preseed:
        seed = Memory(home=store, project=project, user_home=tmp_path / "user", fts=fts)
        seed.con.close()
    go = tmp_path / "go"
    processes = []
    for index in range(12):
        env = dict(os.environ, PYTHONPATH=str(SRC), STORE=str(store), PROJECT=str(project),
                   USER_STORE=str(tmp_path / "user"), READY=str(tmp_path / ("ready-%d" % index)),
                   GO=str(go), FTS="1" if fts else "0",
                   FACT="shared synthetic fact" if same_fact else "unique synthetic fact %d" % index)
        processes.append(subprocess.Popen([sys.executable, "-c", WORKER], env=env,
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
    try:
        deadline = time.monotonic() + 15
        while sum((tmp_path / ("ready-%d" % i)).exists() for i in range(12)) < 12:
            assert time.monotonic() < deadline, "workers did not initialize"
            time.sleep(.005)
        go.touch()
        results = [process.communicate(timeout=20) for process in processes]
        assert all(process.returncode == 0 for process in processes), results
        receipts = [json.loads(out) for out, _ in results]
        assert len({receipt["id"] for receipt in receipts}) == (1 if same_fact else 12)
        fresh = Memory(home=store, project=project, user_home=tmp_path / "user", fts=fts)
        fresh.sync()
        count = fresh.con.execute("SELECT COUNT(*) FROM mem_items").fetchone()[0]
        fresh.con.close()
        assert count == (1 if same_fact else 12)
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)


def test_windows_lock_retries_without_reading_a_locked_byte(tmp_path):
    from agent_harness.mcp import memory

    real_open = Path.open

    class LockedByte:
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            self.handle.__enter__()
            return self

        def __exit__(self, *args):
            return self.handle.__exit__(*args)

        def read(self, *args):
            raise PermissionError(errno.EACCES, "another process owns the byte")

        def __getattr__(self, name):
            return getattr(self.handle, name)

    def open_lock(path, *args, **kwargs):
        handle = real_open(path, *args, **kwargs)
        return LockedByte(handle) if path.name == ".memory.lock" else handle

    calls = []

    def locking(_fd, operation, _length):
        calls.append(operation)
        if operation == 1 and calls.count(1) == 1:
            raise PermissionError(errno.EACCES, "busy")

    fake_msvcrt = types.SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2, locking=locking)
    with mock.patch.object(memory.os, "name", "nt"), mock.patch.dict(sys.modules, {"msvcrt": fake_msvcrt}), \
            mock.patch.object(Path, "open", open_lock):
        with memory._store_lock(tmp_path / "store"):
            pass
    assert calls == [1, 1, 2]
