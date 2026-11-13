"""A published walkthrough must keep its declared depth and resolvable references."""
from pathlib import Path
import re
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[1]


def check_links(text, page):
    for target in re.findall(r"\]\(([^)]+)\)", text):
        if target.startswith(("https://", "http://", "#")):
            continue
        path = (page.parent / unquote(target.split("#", 1)[0])).resolve()
        assert path.is_relative_to(ROOT), "link escapes repository"
        assert path.exists(), "missing local link " + target


@pytest.mark.parametrize("name", ["framework", "memory", "methodology", "philosophy"])
def test_each_direction_has_an_explanation_example_and_boundaries(name):
    page = ROOT / "docs/walkthrough" / (name + ".md")
    text = page.read_text()
    for heading in ("## Mechanism", "## Example", "## Tradeoffs", "## Evidence and limits", "## Implementation"):
        assert heading in text, (name, heading)
    check_links(text, page)


def test_walkthrough_link_check_rejects_a_missing_source():
    page = ROOT / "docs/walkthrough/README.md"
    check_links("[source](framework.md)", page)
    with pytest.raises(AssertionError, match="missing local link"):
        check_links("[source](missing-implementation.py)", page)
