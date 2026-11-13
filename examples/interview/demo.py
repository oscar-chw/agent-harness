"""A real installed-runtime demo using disposable state and zero model calls.

Run python3 demo.py --output demo-run. Existing output folders are refused.
The two readers are fresh MCP server processes, not native model sessions.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import shlex
import subprocess
import sys
import threading

from check_pack import validate_receipt


def check(condition, explanation):
    if not condition:
        raise RuntimeError(explanation)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(text, output, runtime):
    for path, label in ((output / "home", "$DEMO_HOME"), (output, "$DEMO"),
                        (runtime, "$RUNTIME"), (Path.home(), "$OWNER_HOME")):
        text = text.replace(str(path), label)
    return text


class Commands:
    def __init__(self, project, home, runtime):
        self.project, self.home, self.runtime = project, home, runtime
        self.events = []
        prefixes = ("HARNESS_", "PLAN_", "PYTHON", "GIT_", "CODEX_", "CLAUDE_")
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(prefixes)}
        self.env.update(HOME=str(home), USERPROFILE=str(home), HARNESS_HOME=str(home / "harness"),
                        CODEX_HOME=str(home / "codex"), CLAUDE_CONFIG_DIR=str(home / "claude"),
                        XDG_CONFIG_HOME=str(home / "config"), APPDATA=str(home / "appdata"),
                        PYTHONPATH=str(runtime / "lib"), PYTHONDONTWRITEBYTECODE="1",
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")

    def clean(self, text):
        return normalize(text, self.project.parent, self.runtime)

    def run(self, module, *args):
        command = [sys.executable, "-m", module, *args]
        process = subprocess.run(command, cwd=self.project, env=self.env, text=True,
                                 capture_output=True, timeout=25)
        self.events.append({"argv": [self.clean(a) for a in command], "exit": process.returncode,
                            "stdout": self.clean(process.stdout), "stderr": self.clean(process.stderr)})
        (self.project.parent / "commands.json").write_text(
            json.dumps(self.events, indent=2) + "\n", encoding="utf-8")
        return process

    def cli(self, *args):
        return self.run("agent_harness.cli", *args)

    def plan(self, *args):
        return self.run("agent_harness.workgraph.plan", *args)

    def checkpoint(self, version, stage, summary, next_step):
        result = self.cli("task", "checkpoint", "shipping", "--expected", str(version),
                          "--goal", "Correct the free-shipping boundary", "--stage", stage,
                          "--summary", summary, "--next", next_step,
                          "--checkpoint", "handoff.md", "--json")
        check(result.returncode == 0, "checkpoint failed " + result.stderr)
        return json.loads(result.stdout)

    def snapshot(self):
        result = self.cli("task", "status", "shipping", "--json")
        check(result.returncode == 0, "status failed " + result.stderr)
        return json.loads(result.stdout)["tasks"][0]


class Reader:
    def __init__(self, commands, log):
        self.commands = commands
        self.error_log = log.open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [sys.executable, "-m", "agent_harness.mcp.server"], cwd=commands.project,
            env=commands.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self.error_log, text=True, bufsize=1)
        self.lines = queue.Queue()
        self.sequence = 0
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.process.stdout:
            self.lines.put(line)
        self.lines.put(None)

    def call(self, method, **params):
        self.sequence += 1
        request = {"jsonrpc": "2.0", "id": self.sequence, "method": method, "params": params}
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        line = self.lines.get(timeout=20)
        check(line is not None, "MCP server exited before replying")
        response = json.loads(line)
        check(response.get("id") == self.sequence and "result" in response,
              "invalid MCP reply " + self.commands.clean(line))
        check(response["result"].get("isError") is not True, "MCP tool reported an error")
        return response["result"]

    def initialize(self):
        return self.call("initialize", protocolVersion="2025-06-18", capabilities={},
                         clientInfo={"name": "interview-reader", "version": "1"})

    def boundary(self):
        result = self.call("tools/call", name="session_recent", arguments={})
        return "\n".join(c["text"] for c in result["content"]
                         if c.get("type") == "text" and c["text"].startswith("Shared board"))

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=5)
        self.process.stdout.close()
        self.error_log.close()
        check(self.process.returncode == 0, "MCP process did not close cleanly")


def run(output, runtime):
    project, home = output / "project", output / "home"
    project.mkdir()
    home.mkdir()
    (project / "plan").mkdir()
    commands = Commands(project, home, runtime)
    identity = commands.cli("status", "--runtime", "--json")
    check(identity.returncode == 0, "installed runtime could not start " + identity.stderr)
    version = json.loads(identity.stdout)["current"]["declared_version"]
    init = subprocess.run(["git", "init", "--quiet", str(project)], env=commands.env,
                          capture_output=True, text=True, timeout=10)
    check(init.returncode == 0, "git could not initialize the disposable project")
    (project / "handoff.md").write_text(
        "# Shipping task\nFree shipping starts at a subtotal of 50.\n"
        "Keep acceptance tests unchanged. Check 49, 50 and 80.\n", encoding="utf-8")
    tests = project / "test_feature.py"
    tests.write_text(
        "import unittest\nfrom feature import shipping_fee\n\n"
        "class ShippingTests(unittest.TestCase):\n"
        "    def test_below_threshold(self):\n        self.assertEqual(shipping_fee(49), 5)\n"
        "    def test_exact_threshold(self):\n        self.assertEqual(shipping_fee(50), 0)\n"
        "    def test_above_threshold(self):\n        self.assertEqual(shipping_fee(80), 0)\n",
        encoding="utf-8")
    original_tests = sha(tests)
    feature = project / "feature.py"
    feature.write_text("def shipping_fee(subtotal):\n    return 5\n", encoding="utf-8")
    gate_argv = [sys.executable, "-m", "unittest", "-q", "test_feature"]
    gate = subprocess.list2cmdline(gate_argv) if os.name == "nt" else shlex.join(gate_argv)
    graph = project / "plan" / "shipping.md"
    graph.write_text("## goal: Free shipping from 50\n\n"
                     "- [ ] 1. Correct the boundary | ctx: feature.py | gate: " + gate + "\n",
                     encoding="utf-8")
    commands.checkpoint(0, "implementation", "Boundary bug reproduced in a small fixture",
                        "Run the independent shipping boundary gate")
    first = Reader(commands, output / "reader-a.stderr.log")
    try:
        initial = first.initialize()["instructions"]
        quiet_a = first.boundary()
        reader_a = {"pid": first.process.pid,
                    "cold_pickup": "Run the independent shipping boundary gate" in initial,
                    "instruction_bytes": len(initial.encode()), "unchanged_board_bytes": len(quiet_a.encode())}
        (output / "reader-a.txt").write_text(commands.clean(initial), encoding="utf-8")
    finally:
        first.close()
    check(reader_a["cold_pickup"] and reader_a["unchanged_board_bytes"] == 0,
          "reader A did not receive the current task or repeated unchanged context")
    print("PASS 1/5  A fresh MCP process received the task and next action automatically.", flush=True)

    failed = commands.plan("gate", "shipping", "1")
    pending = "- [ ] 1." in graph.read_text()
    check(failed.returncode == 1 and pending, "broken implementation did not fail the gate")
    failed_output = failed.stdout + failed.stderr
    check(all(text in failed_output for text in ("Ran 3 tests", "FAILED (failures=2)",
              "FAIL: test_exact_threshold", "FAIL: test_above_threshold")),
          "the expected assertion failures were not observed; inspect the gate execution")
    commands.checkpoint(1, "debug", "Boundary gate failed at 50 and 80; task is pending",
                        "Fix feature.py while preserving test_feature.py")
    print("PASS 2/5  Broken code failed the real gate and remained pending.", flush=True)

    second = Reader(commands, output / "reader-b.stderr.log")
    try:
        initial_b = second.initialize()["instructions"]
        quiet_b = second.boundary()
        reader_b = {"pid": second.process.pid,
                    "cold_pickup": "Boundary gate failed" in initial_b and "Fix feature.py" in initial_b,
                    "instruction_bytes": len(initial_b.encode()), "unchanged_board_bytes": len(quiet_b.encode())}
        check(reader_b["cold_pickup"] and reader_b["unchanged_board_bytes"] == 0,
              "reader B did not recover the current failure or repeated unchanged context")
        (output / "reader-b.txt").write_text(commands.clean(initial_b), encoding="utf-8")
        before = commands.snapshot()
        stale = commands.cli("task", "checkpoint", "shipping", "--expected", "1",
                             "--summary", "Outdated writer says complete", "--json")
        after = commands.snapshot()
        stale_row = {"exit": stale.returncode, "version_before": before["version"],
                     "version_after": after["version"],
                     "version_conflict_observed": "task version changed" in stale.stderr,
                     "summary_preserved": before["value"] == after["value"]}
        check(stale.returncode != 0 and stale_row["summary_preserved"]
              and stale_row["version_conflict_observed"], "expected stale-version rejection was not observed")
        print("PASS 3/5  A second process recovered the failure. Its stale writer was rejected.", flush=True)

        feature.write_text("def shipping_fee(subtotal):\n    return 0 if subtotal >= 50 else 5\n",
                           encoding="utf-8")
        passed = commands.plan("gate", "shipping", "1")
        done = "- [x] 1." in graph.read_text()
        check(passed.returncode == 0 and done, "corrected implementation did not settle")
        check("Ran 3 tests" in passed.stderr and "\nOK\n" in passed.stderr,
              "the passing gate did not run the expected acceptance tests")
        commands.checkpoint(2, "verified", "All 3 shipping tests passed; graph node is done",
                            "Review the diff and package the change")
        delta, repeated = second.boundary(), second.boundary()
        delta_row = {"first_bytes": len(delta.encode()), "repeat_bytes": len(repeated.encode()),
                     "contains_next_step": "Review the diff and package the change" in delta}
        (output / "reader-b-update.txt").write_text(commands.clean(delta), encoding="utf-8")
    finally:
        second.close()
    check(delta_row["first_bytes"] > 0 and delta_row["repeat_bytes"] == 0
          and delta_row["contains_next_step"], "changed board context was missing or repeated")
    print("PASS 4/5  The fix passed the same tests. The graph recorded completion.", flush=True)
    print("PASS 5/5  The running reader received the update once, then zero board bytes.", flush=True)
    receipt = {
        "schema": "harness.interview-demo/v1", "status": "PASS", "model_calls": 0,
        "demo_sha256": sha(Path(__file__)),
        "commands_sha256": sha(output / "commands.json"),
        "runtime": {"version": version,
                    "engine_sha256": sha(runtime / "lib/agent_harness/workgraph/plan.py")},
        "readers": [reader_a, reader_b], "delta": delta_row, "stale_write": stale_row,
        "gate": {"before_exit": failed.returncode, "before_mark": "pending" if pending else "other",
                 "after_exit": passed.returncode, "after_mark": "done" if done else "other",
                 "before_tests_run": 3, "before_failures": 2, "after_tests_run": 3,
                 "tests_sha256_before": original_tests, "tests_sha256_after": sha(tests)},
        "isolation": {"disposable_home": home != Path.home(), "disposable_project": project != Path.cwd()},
        "limits": ["No native model turn", "No universal compliance claim",
                   "Byte suppression is measured here; historical native token evidence is separate"],
    }
    validate_receipt(receipt)
    (output / "commands.json").write_text(json.dumps(commands.events, indent=2) + "\n", encoding="utf-8")
    (output / "demo-proof.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("\nDEMO PASS | installed runtime " + version + " | 0 model calls", flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="new folder for fixture and evidence")
    parser.add_argument("--runtime", type=Path,
                        default=Path(os.environ.get("HARNESS_HOME", Path.home() / ".agent-harness")),
                        help="existing harness installation containing lib/agent_harness")
    args = parser.parse_args()
    runtime = args.runtime.expanduser().resolve()
    if not (runtime / "lib/agent_harness/workgraph/plan.py").is_file():
        parser.error("installed harness runtime missing; use --runtime with its installation directory")
    output = args.output.expanduser().resolve()
    if output.exists():
        parser.error("output folder already exists; choose a new name to preserve its evidence")
    output.mkdir(parents=True)
    try:
        run(output, runtime)
    except (OSError, ValueError, RuntimeError, queue.Empty, subprocess.SubprocessError) as error:
        message = normalize(str(error), output, runtime)
        failure = {"status": "FAIL", "error": type(error).__name__, "message": message}
        (output / "demo-proof.json").write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        print("DEMO FAIL " + message, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
