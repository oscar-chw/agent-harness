"""Replay a named immutable reasoning run; simulation always exits nonzero."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
if len(sys.argv) != 2:
    raise SystemExit("usage: check_reasoning_outcome.py RUN_DIRECTORY")
module = runpy.run_path(str(ROOT / "eval/reasoning_iteration.py"))
raise SystemExit(module["main"](["check", sys.argv[1]]))
