"""Delivery checks for the bounded design, presentation and graph-memory refresh."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = {
    "clear-docs": ("web-design.md", "presentations.md"),
    "session-memory": ("graph-memory.md",),
}


def test_provenance_has_pins_and_explicit_adoption_decisions():
    data = json.loads((ROOT / "docs/skill-refresh-20261116.json").read_text())
    assert {row["repository"] for row in data["sources"]} == {
        "google-labs-code/design.md", "google-labs-code/stitch-skills",
        "anthropics/skills", "ModernRelay/omnigraph",
    }
    for row in data["sources"]:
        assert re.fullmatch(r"[a-f0-9]{40}", row["revision"])
        assert row["reviewed_paths"] and row["decision"] and row["license"]
    assert data["video"]["captions"] == "UNAVAILABLE"
    assert data["performance_improvement"] == "NOT_MEASURED"


def test_each_reference_is_reachable_from_its_skill():
    for skill, references in REFERENCES.items():
        folder = ROOT / "content/skills" / skill
        entry = (folder / "SKILL.md").read_text()
        targets = re.findall(r"\]\(([^)]+)\)", entry)
        for name in references:
            assert name in targets, (skill, name)
            assert (folder / name).is_file()
            assert len((folder / name).read_text()) > 0


@pytest.fixture(scope="module")
def installation(tmp_path_factory):
    home = tmp_path_factory.mktemp("skill-refresh-install")
    env = {k: v for k, v in os.environ.items() if not k.startswith("HARNESS_")}
    result = subprocess.run(
        [sys.executable, str(ROOT / "bin/harness"), "--home", str(home),
         "install", "--tools", "codex,copilot-vscode", "--yes"],
        capture_output=True, text=True, env=env, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return home


def test_normal_install_exposes_the_complete_updated_skills(installation):
    for skill, references in REFERENCES.items():
        for name in ("SKILL.md", *references):
            source = ROOT / "content/skills" / skill / name
            installed = installation / ".agents/skills" / skill / name
            assert installed.read_bytes() == source.read_bytes()
    for relative in (".codex/AGENTS.md", ".copilot/instructions/harness.instructions.md"):
        assert (installation / relative).is_file()


def test_entrypoints_keep_existing_skill_names_and_bounded_size():
    for skill in REFERENCES:
        text = (ROOT / "content/skills" / skill / "SKILL.md").read_text()
        assert re.search(r"^name: (.*)$", text, re.M).group(1) == skill
        assert len(text.splitlines()) <= 60
