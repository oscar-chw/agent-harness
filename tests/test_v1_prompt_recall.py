"""Fresh subprocess hook tests; these do not assert that a native app fires hooks."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from . import test_memory_transport as transport
from .test_memory_transport import seed

lab = transport.lab

SRC = Path(__file__).resolve().parents[1] / "src"


def prompt(lab, text, *, project=None, session="turns"):
    home, projects = lab
    env = {k: v for k, v in os.environ.items() if not k.startswith("HARNESS_")}
    env.update(HOME=str(home), HARNESS_HOME=str(home / "harness"),
               PYTHONPATH=str(SRC), HARNESS_PROJECT=str(projects[0]))
    data = {"prompt": text, "session_id": session,
            "cwd": str(project if project is not None else projects[1])}
    result = subprocess.run([sys.executable, "-m", "agent_harness.cli", "_hook-prompt"],
                            input=json.dumps(data), text=True, capture_output=True,
                            env=env, cwd=projects[0], timeout=10)
    assert result.returncode == 0, result.stderr
    return result


def test_event_project_controls_automatic_context_not_launcher(lab):
    launcher, alpha, bravo = lab[1]
    for project, day in ((launcher, "Monday"), (alpha, "Tuesday"), (bravo, "Friday")):
        seed(lab, project, "The release cutoff is " + day + ".")
    out = prompt(lab, "release cutoff", project=alpha).stdout
    assert "Tuesday" in out
    assert "Monday" not in out and "Friday" not in out
    other = prompt(lab, "release cutoff", project=bravo).stdout
    assert "Friday" in other and "Tuesday" not in other


def test_unchanged_warm_context_is_suppressed_but_a_new_session_recalls(lab):
    seed(lab, lab[1][1], "Release checks require the turquoise checklist.", scope="user")
    assert "turquoise" in prompt(lab, "release checks").stdout
    assert prompt(lab, "release checks").stdout == ""
    assert "turquoise" in prompt(lab, "release checks", session="new").stdout


@pytest.mark.parametrize('sessions', [('run/a', 'run_a'), ('a'*120+'b', 'a'*120+'c')])
def test_distinct_session_names_never_share_suppression(lab, sessions):
    seed(lab, lab[1][1], 'Release checks require the turquoise checklist.')
    assert 'turquoise' in prompt(lab, 'release checks', session=sessions[0]).stdout
    assert 'turquoise' in prompt(lab, 'release checks', session=sessions[1]).stdout


def test_return_to_a_prior_fact_is_still_a_new_update(lab):
    identity = seed(lab, lab[1][1], 'Release cutoff is Tuesday.', scope='user')
    source = lab[0] / 'harness/memory/user' / (identity + '.json')
    for day in ('Tuesday', 'Friday', 'Tuesday'):
        item = json.loads(source.read_text())
        item['text'] = 'Release cutoff is ' + day + '.'
        source.write_text(json.dumps(item))
        assert day in prompt(lab, 'release cutoff').stdout


def test_changed_record_is_recalled_in_same_session_even_with_preserved_mtime(lab):
    identity = seed(lab, lab[1][1], "Release cutoff is Tuesday.", scope="user")
    assert "Tuesday" in prompt(lab, "release cutoff").stdout
    source = lab[0] / "harness/memory/user" / (identity + ".json")
    previous = source.stat()
    record = json.loads(source.read_text())
    record["text"] = "Release cutoff is Friday."
    source.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    os.utime(source, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    corrected = prompt(lab, "release cutoff").stdout
    assert "Friday" in corrected and "Tuesday" not in corrected
    assert prompt(lab, "release cutoff").stdout == ""


def test_forgotten_recalled_fact_warns_the_same_session_without_replaying_old_text(lab):
    project = lab[1][1]
    identity = seed(lab, project, "Release cutoff is Tuesday.", scope="project")
    assert "Tuesday" in prompt(lab, "release cutoff").stdout
    memory = transport.Memory(home=lab[0] / "harness", project=project)
    try:
        assert memory.mem_forget(identity)["ok"] is True
    finally:
        memory.close()
    warning = prompt(lab, "release cutoff").stdout
    assert identity in warning and "no longer active" in warning
    assert "Tuesday" not in warning
    assert prompt(lab, "release cutoff").stdout == ""
    assert prompt(lab, "release cutoff", session="new").stdout == ""
    seed(lab, project, "Release cutoff is Friday.", scope="project")
    corrected = prompt(lab, "release cutoff").stdout
    assert "Friday" in corrected and "Tuesday" not in corrected


def test_forgotten_recalled_lesson_warns_without_replaying_its_fix(lab):
    project = lab[1][1]
    memory = transport.Memory(home=lab[0] / "harness", project=project)
    try:
        identity = memory.lesson_add("Stale release cutoff", "Use the turquoise checklist",
                                     "release cutoff")['id']
    finally:
        memory.close()
    assert "turquoise" in prompt(lab, "release cutoff").stdout
    memory = transport.Memory(home=lab[0] / "harness", project=project)
    try:
        assert memory.mem_forget(identity)["ok"] is True
    finally:
        memory.close()
    warning = prompt(lab, "release cutoff").stdout
    assert identity in warning and "no longer active" in warning
    assert "turquoise" not in warning


def test_full_constraint_survives_when_it_fits_packet(lab):
    fact = "Archive recovery policy: " + "retain the validated checkpoint; " * 12 + "Never delete raw inputs."
    seed(lab, lab[1][1], fact, scope="user")
    out = prompt(lab, "archive recovery policy").stdout
    assert fact in out
    assert "Never delete raw inputs." in out


def test_oversized_match_is_explicit_and_not_claimed_as_delivered(lab):
    identity = seed(lab, lab[1][1], "Archive recovery policy: " + "retain " * 300, scope="user")
    out = prompt(lab, "archive recovery policy").stdout
    assert identity in out and "omitted" in out.lower()
    assert "mem_search" in out
    assert len(out.encode()) <= 1200


def test_unrelated_prompt_does_not_load_memory(lab):
    seed(lab, lab[1][1], "Release checks require the turquoise checklist.", scope="user")
    assert prompt(lab, "write a haiku about autumn leaves").stdout == ""


def test_invalid_event_scope_does_not_silently_fall_back(lab):
    seed(lab, lab[1][0], "Release cutoff is secret-launcher-value.")
    out = prompt(lab, "release cutoff", project=Path("relative-project"))
    assert out.stdout == ""
    assert "scope" in out.stderr.lower()
    assert "secret-launcher-value" not in out.stderr


@pytest.mark.parametrize("payload", [123, ["private-prompt"], {"text": "private-prompt"}])
def test_malformed_prompt_does_not_crash_or_echo_content(lab, payload):
    out = prompt(lab, payload)
    assert out.stdout == ""
    assert "unavailable" in out.stderr and "Traceback" not in out.stderr
    assert "private-prompt" not in out.stderr
