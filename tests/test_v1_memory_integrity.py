"""Critical meaning survives ingestion and cold stdio recall; no model calls."""
import json

import pytest

from . import test_memory_transport as transport
from .test_memory_transport import exchange, value

lab = transport.lab


@pytest.mark.parametrize("before,after", [
    ("The production data pipeline must delete the original input files after a successful verified import.",
     "The production data pipeline must not delete the original input files after a successful verified import."),
    ("The alpha staging service accepts client connections using the configured database port 5433 for testing.",
     "The alpha staging service accepts client connections using the configured database port 5434 for testing."),
    ("Alice reviews Bob before the release while the integration tests run on the staging server.",
     "Bob reviews Alice before the release while the integration tests run on the staging server."),
    ("The release deadline for the shared alpha service is Monday at 10:00 UTC after the final review.",
     "The release deadline for the shared alpha service is Tuesday at 10:00 UTC after the final review."),
    ("The permitted lower temperature bound for the laboratory sensor calibration is -5 degrees.",
     "The permitted lower temperature bound for the laboratory sensor calibration is 5 degrees."),
    ("The archive warning threshold is .5.", "The archive warning threshold is 5."),
    ("PATH is the environment variable to update.", "path is the environment variable to update."),
])
def test_changed_meaning_is_not_discarded_as_a_duplicate(lab, before, after):
    project = str(lab[1][1])
    first, second = [value(r) for r in exchange(lab, [
        ("mem_add", {"text": text, "scope": "project", "project": project})
        for text in (before, after)])]
    assert second["duplicate"] is False
    assert second["id"] != first["id"]
    # Both originals remain exactly recoverable; this test does not adjudicate truth
    # or pretend that a new fact automatically supersedes an old one.
    cold = value(exchange(lab, [("mem_search", {
        "query": before, "k": 10, "project": project})])[0])
    assert {r["text"] for r in cold} == {before, after}
    records = lab[0] / "harness" / "memory" / "project"
    assert json.loads((records / (first["id"] + ".json")).read_text())["text"] == before


def test_formatting_only_repetition_still_deduplicates(lab):
    project = str(lab[1][1])
    first, repeat = [value(r) for r in exchange(lab, [
        ("mem_add", {"text": text, "scope": "project", "project": project})
        for text in ("The staging database lives on the second server, port 5433.",
                     "the staging database lives on the second server port 5433")])]
    assert repeat["duplicate"] is True
    assert repeat["id"] == first["id"]
