"""A local coverage report describes evidence declarations, never certifies them."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def source(url, *, transferred=False, depth="UNINSPECTED"):
    return {
        "source_id": "url-sha256:" + hashlib.sha256(url.encode()).hexdigest(),
        "canonical_url": url,
        "transfer": {"incoming_read_status": "UNREAD_UNVERIFIED",
                     "exact_variants": [url, url + "/"]} if transferred else None,
        "reading": {"status": depth, "observations": []},
        "access": {"current": "NOT_ATTEMPTED", "historical": "UNKNOWN"},
        "source_revision": {"content_sha256": None},
        "adoption": {"status": "NOT_ESTABLISHED", "decision_ids": []},
        "evaluation": {"status": "NOT_ESTABLISHED", "receipt_ids": []},
    }


def ledger():
    return {"schema": "harness.source-coverage/v1", "as_of": "2026-11-02",
            "claim_class": "BOUNDED_METADATA_RECONCILIATION",
            "denominator_boundary": "Only the explicitly selected historical snapshot.",
            "summary": {"source_identities": 999, "current_primary_reads": 999},
            "sources": [source("https://example.com/a", transferred=True),
                        source("https://example.com/b", depth="SNIPPET_ONLY")]}


def write(tmp_path, value=None):
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(ledger() if value is None else value))
    return path


def cli(path, *args):
    return subprocess.run([sys.executable, str(ROOT / "bin/harness"),
                           "source-coverage", "--ledger", str(path), *args],
                          env={"PATH": os.defpath, "HOME": str(path.parent),
                               "HARNESS_HOME": str(path.parent / "hh"),
                               "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
                          capture_output=True, text=True, timeout=10)


def query(path, **kwargs):
    from agent_harness.source_coverage import coverage_report
    return coverage_report(path, **kwargs)


def test_cli_recomputes_selected_ledger_counts_without_certifying_reads(tmp_path):
    path = write(tmp_path)
    result = cli(path)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["denominator"] == {"identities": 2, "transferred_identities": 1,
                                     "transfer_exact_variants": 2, "additional_identities": 1}
    assert report["reported"]["incoming_transfer_status"] == {"UNREAD_UNVERIFIED": 1}
    assert report["reported"]["read_depth"] == {"UNINSPECTED": 1, "SNIPPET_ONLY": 1}
    assert report["reported"]["current_access"] == {"NOT_ATTEMPTED": 2}
    assert report["declared_summary"]["current_primary_reads"] == 999
    assert report["evidence_verification"] == "NOT_RUN"
    assert report["corrections"] == "NOT_APPLIED; selected ledger only"
    assert "not current knowledge or a complete corpus" in report["scope"]
    assert report["ledger_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert not (tmp_path / "hh").exists()


def test_exact_source_lookup_keeps_scope_and_unknowns(tmp_path):
    path = write(tmp_path)
    report = query(path, source_id="https://example.com/a")
    row = report["source"]
    assert row["pointer"] == "/sources/0"
    assert row["reported"]["reading"]["status"] == "UNINSPECTED"
    assert row["reported"]["transfer"]["incoming_read_status"] == "UNREAD_UNVERIFIED"
    assert query(path, source_id=row["source_id"])["source"] == row
    with pytest.raises(ValueError, match="not present"):
        query(path, source_id="example.com/a")


def test_only_selected_ledger_is_read_no_bound_inputs_or_url_fetches(tmp_path, monkeypatch):
    value = ledger()
    value["inputs"] = [{"path": "DO_NOT_READ_PRIVATE_HISTORY", "sha256": "a" * 64}]
    path = write(tmp_path, value)
    before = path.read_bytes()
    original = os.open

    def selected_only(name, *args, **kwargs):
        assert Path(name) == path
        return original(name, *args, **kwargs)

    monkeypatch.setattr(os, "open", selected_only)
    result = query(path)
    assert result["evidence_verification"] == "NOT_RUN"
    assert "DO_NOT_READ_PRIVATE_HISTORY" not in json.dumps(result)
    assert path.read_bytes() == before


def test_record_delta_changes_only_its_reported_axis(tmp_path):
    path = write(tmp_path)
    before = query(path)
    value = ledger()
    value["sources"][0]["adoption"] = {"status": "USE_REPORTED", "decision_ids": ["d-1"]}
    path.write_text(json.dumps(value))
    after = query(path)
    assert after["reported"]["adoption"] == {"USE_REPORTED": 1, "NOT_ESTABLISHED": 1}
    assert after["reported"]["evaluation"] == before["reported"]["evaluation"]
    assert after["reported"]["read_depth"] == before["reported"]["read_depth"]
    assert after["evidence_verification"] == "NOT_RUN"
    assert after["ledger_sha256"] != before["ledger_sha256"]


@pytest.mark.parametrize("mutate", [
    lambda x: x.update(schema="unknown"),
    lambda x: x.pop("sources"),
    lambda x: x.update(sources={}),
    lambda x: x["sources"].append(copy.deepcopy(x["sources"][0])),
    lambda x: x["sources"][0].update(source_id="wrong"),
    lambda x: x["sources"][0].update(reading=None),
    lambda x: x["sources"][0]["access"].update(current=1),
    lambda x: x["sources"][0]["transfer"].update(exact_variants=["duplicate", "duplicate"]),
])
def test_malformed_records_are_errors_not_empty_success(tmp_path, mutate):
    value = ledger()
    mutate(value)
    with pytest.raises(ValueError):
        query(write(tmp_path, value))


@pytest.mark.parametrize("body", ['{"schema":"x","schema":"y"}', '{"bad":NaN}', '{broken'])
def test_invalid_json_and_duplicate_keys_fail_closed(tmp_path, body):
    path = tmp_path / "ledger.json"
    path.write_text(body)
    with pytest.raises(ValueError):
        query(path)
    result = cli(path)
    assert result.returncode == 2
    assert result.stdout == "" and "source-coverage" in result.stderr


def test_empty_selected_scope_is_explicit_not_verified(tmp_path):
    value = ledger()
    value["sources"] = []
    report = query(write(tmp_path, value))
    assert report["denominator"]["identities"] == 0
    assert report["evidence_verification"] == "NOT_RUN"


def test_missing_symlink_and_oversize_are_refused(tmp_path):
    with pytest.raises(ValueError):
        query(tmp_path / "missing.json")
    with pytest.raises(ValueError):
        query(tmp_path)
    target = write(tmp_path)
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(ValueError):
        query(link)
    large = tmp_path / "large.json"
    large.write_bytes(b" " * (2 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="limit"):
        query(large)


def test_real_ledger_stays_a_bounded_historical_projection():
    path = ROOT / "docs/v2/vault/coverage-ledger.json"
    result = query(path)
    assert result["denominator"] == {"identities": 138, "transferred_identities": 108,
                                     "transfer_exact_variants": 110, "additional_identities": 30}
    assert result["reported"]["incoming_transfer_status"] == {"UNREAD_UNVERIFIED": 108}
    assert result["reported"]["primary_hashes_present"] == 0
    assert result["evidence_verification"] == "NOT_RUN"
    assert result["corrections"] == "NOT_APPLIED; selected ledger only"


def reconciliation(tmp_path):
    value = ledger()
    value["sources"][0]["reading"]["status"] = "COMPLETE_POST_TEXT"
    base = write(tmp_path, value)
    extra = source("https://example.com/new", depth="SELECTED_SCOPE_REPORTED")
    extra["primary_content_sha256"] = extra.pop("source_revision")["content_sha256"]
    extra.pop("transfer")
    key = value["sources"][0]["source_id"]
    packet = {
        "schema": "harness.source-reconciliation/v1", "as_of": "2026-11-03",
        "base": {"path": "ledger.json", "sha256": hashlib.sha256(base.read_bytes()).hexdigest()},
        "new_sources": [extra], "summary": {"url_identities": 999},
        "corrections": [{"correction_id": "extent-1", "source_id": key, "axis": "reading",
                         "old_status": "COMPLETE_POST_TEXT", "replacement_status": "POST_TEXT_EXTENT_UNSPECIFIED",
                         "verified_primary_read": False, "acceptance_change": False,
                         "access_or_activation_change": False,
                         "original_preserved": {"input": "ledger.json", "json_pointer": "/sources/0/reading"}}],
        "source_index": [
            {"source_id": row["source_id"], "canonical_url": row["canonical_url"],
             "record": {"input": "ledger.json", "json_pointer": "/sources/" + str(i)},
             "reading_override": {"input": "reconciliation.json", "json_pointer": "/corrections/0"} if i == 0 else None}
            for i, row in enumerate(value["sources"])
        ] + [{"source_id": extra["source_id"], "canonical_url": extra["canonical_url"],
              "record": {"input": "reconciliation.json", "json_pointer": "/new_sources/0"},
              "reading_override": None}],
    }
    path = tmp_path / "reconciliation.json"
    path.write_text(json.dumps(packet))
    return base, path, packet


def test_explicit_reconciliation_corrects_projection_without_rewriting_history(tmp_path):
    base, path, _ = reconciliation(tmp_path)
    before = base.read_bytes(), path.read_bytes()
    result = query(base, reconciliation=path, source_id="https://example.com/a")
    assert result["denominator"] == {"identities": 3, "transferred_identities": 1,
                                     "transfer_exact_variants": 2, "additional_identities": 2}
    assert result["reported"]["transfer_read_depth"] == {"POST_TEXT_EXTENT_UNSPECIFIED": 1}
    assert result["source"]["original_reading_status"] == "COMPLETE_POST_TEXT"
    assert result["source"]["reported"]["reading"]["status"] == "POST_TEXT_EXTENT_UNSPECIFIED"
    assert result["source"]["container_sha256"] == result["ledger_sha256"]
    assert result["reconciliation_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result["evidence_verification"] == "NOT_RUN"
    assert result["base_denominator_boundary"] == ledger()["denominator_boundary"]
    assert result["denominator_boundary"] != result["base_denominator_boundary"]
    assert result["base_claim_class"] == "BOUNDED_METADATA_RECONCILIATION"
    assert result["claim_class"] == "SELECTED_LOCAL_METADATA_PROJECTION"
    assert before == (base.read_bytes(), path.read_bytes())
    assert query(base)["reported"]["transfer_read_depth"] == {"COMPLETE_POST_TEXT": 1}
    extra = query(base, reconciliation=path, source_id="https://example.com/new")
    assert extra["source"]["pointer"] == "/new_sources/0"
    assert extra["source"]["container_sha256"] == result["reconciliation_sha256"]
    actual = cli(base, "--reconciliation", str(path))
    assert actual.returncode == 0, actual.stderr
    assert json.loads(actual.stdout)["denominator"] == result["denominator"]


@pytest.mark.parametrize("mutate", [
    lambda x: x["base"].update(sha256="a" * 64),
    lambda x: x["source_index"].pop(),
    lambda x: x["source_index"][0]["record"].update(json_pointer="/sources/1"),
    lambda x: x["corrections"][0].update(old_status="SNIPPET_ONLY"),
    lambda x: x["corrections"][0].update(verified_primary_read=True),
    lambda x: x["corrections"][0].update(axis="access"),
    lambda x: x["source_index"][0].update(reading_override=None),
    lambda x: x["source_index"][1].update(reading_override={"input": "reconciliation.json", "json_pointer": "/corrections/0"}),
])
def test_stale_misbound_or_authority_widening_reconciliation_fails(tmp_path, mutate):
    base, path, packet = reconciliation(tmp_path)
    mutate(packet)
    path.write_text(json.dumps(packet))
    with pytest.raises(ValueError):
        query(base, reconciliation=path)


def test_actual_r5_union_applies_recorded_extent_correction():
    base = ROOT / "docs/v2/vault/coverage-ledger.json"
    extra = ROOT / "docs/v2/vault/r5-reconciliation-20261103.json"
    result = query(base, reconciliation=extra)
    assert result["denominator"] == {"identities": 237, "transferred_identities": 108,
                                     "transfer_exact_variants": 110, "additional_identities": 129}
    assert result["reported"]["transfer_read_depth"] == {
        "UNINSPECTED": 98, "SNIPPET_ONLY": 7, "TITLE_SNIPPET": 1,
        "METADATA_ONLY": 1, "POST_TEXT_EXTENT_UNSPECIFIED": 1}
    assert result["reported"]["primary_hashes_present"] == 0
    assert result["evidence_verification"] == "NOT_RUN"


@pytest.mark.parametrize("status", [None, "", 1, {}])
def test_reconciliation_cannot_hide_invalid_original_read_label(tmp_path, status):
    base, path, packet = reconciliation(tmp_path)
    value = json.loads(base.read_text())
    if status is None:
        value["sources"][0]["reading"].pop("status")
        packet["corrections"][0].pop("old_status")
    else:
        value["sources"][0]["reading"]["status"] = status
        packet["corrections"][0]["old_status"] = status
    base.write_text(json.dumps(value))
    packet["base"]["sha256"] = hashlib.sha256(base.read_bytes()).hexdigest()
    path.write_text(json.dumps(packet))
    with pytest.raises(ValueError, match="original reading"):
        query(base, reconciliation=path)
    result = cli(base, "--reconciliation", str(path))
    assert result.returncode == 2 and result.stdout == ""
    assert "Traceback" not in result.stderr


def test_reconciliation_reads_only_two_explicit_files(tmp_path, monkeypatch):
    base, path, _ = reconciliation(tmp_path)
    original = os.open
    seen = set()

    def selected_only(name, *args, **kwargs):
        assert Path(name) in (base, path), "linked evidence must not be opened"
        seen.add(Path(name))
        return original(name, *args, **kwargs)

    monkeypatch.setattr(os, "open", selected_only)
    assert query(base, reconciliation=path)["denominator"]["identities"] == 3
    assert seen == {base, path}


def test_report_refuses_excess_output_instead_of_silent_truncation(tmp_path):
    value = ledger()
    value["sources"] = [source("https://example.com/" + str(i), depth="x" * 200 + str(i))
                        for i in range(250)]
    with pytest.raises(ValueError, match="output limit"):
        query(write(tmp_path, value))
