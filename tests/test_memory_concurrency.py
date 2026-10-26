"""Real-process checks for the shared local memory store."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

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
