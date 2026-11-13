"""Keep the public catalogue tied to the actual shipped surfaces."""
import json
from pathlib import Path
import subprocess
import sys

from agent_harness.adapters import names
from agent_harness.mcp.server import TOOLS

ROOT = Path(__file__).resolve().parents[1]


def test_catalogue_names_every_shipped_surface():
    catalog = json.loads((ROOT / "docs/CAPABILITIES.json").read_text())
    assert {row["name"] for row in catalog["mcp_tools"]} == {row["name"] for row in TOOLS}
    assert {row["name"] for row in catalog["skills"]} == {
        p.parent.name for p in (ROOT / "content/skills").glob("*/SKILL.md")}
    assert set(catalog["adapters"]) == set(names())
    assert set(catalog["templates"]) == {p.name for p in (ROOT / "content/templates").iterdir() if p.is_file()}
    assert next(row for row in catalog["mcp_tools"] if row["name"] == "run_checks")["exposure"] == "opt-in"
    assert next(row for row in catalog["mcp_tools"] if row["name"] == "op_state")["exposure"] == "default"


def test_generated_catalogue_has_no_source_drift():
    result = subprocess.run([sys.executable, str(ROOT / "scripts/build_capability_catalog.py"), "--check"],
                            cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
