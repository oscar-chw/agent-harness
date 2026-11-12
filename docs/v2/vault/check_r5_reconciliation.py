#!/usr/bin/env python3
"""Root-run metadata checks; no web fetch, source-truth or runtime qualification."""

import argparse
import copy
import hashlib
import json
import os
from collections import Counter
from pathlib import Path


AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
FILE = AREA / "r5-reconciliation-20261103.json"
R5_SHA = "889729914114582b17a2c85aa2e10f19c99337337812d49df73fd028641edaeb"
ORIGINALS = {
    "coverage-ledger.json": "e4713a40fbfd759e51052a46e29666605e307cd26828c6e165e04e87d36362ff",
    "README.md": "3da6d0f058c6f30dad974fd612d5ef3f98040a3f8ed2c662e1f3735ae989424d",
    "acceptance-cases.json": "dfc21103e64ae00d4bc9e6404aaa1481c440b18e8f11d020686be2574dac7343",
    "validate_coverage.py": "c2e6b3f61f71e2773671683a3f4a02e6e4de0f8ffc068dc12a7c4d3ccfe3448f",
}
REDACTION = {
    "scope": "DEPLOYMENT_PATHS_ONLY",
    "placeholder": "/Users/me/",
    "original_sha256": ORIGINALS["coverage-ledger.json"],
    "redacted_sha256": "350352a6a577e298f1a5f623075a88437ca034eb02f979a44c88317054376326",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(url):
    return url.rstrip("/")


def identity(url):
    return "url-sha256:" + sha(canonical(url).encode())


def path(name):
    candidate = Path(name)
    redacted_home = os.environ.get("HARNESS_REDACTED_HOME")
    if redacted_home and str(candidate).startswith(REDACTION["placeholder"]):
        candidate = Path(redacted_home) / str(candidate)[len(REDACTION["placeholder"]):]
    return candidate if candidate.is_absolute() else ROOT / candidate


def load(location):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result

    return json.loads(location.read_text(), object_pairs_hook=unique)


def validate(packet, base, manifest, receipts):
    require(packet["schema"] == "harness.source-reconciliation/v1", "schema")
    require(packet["claim_class"] == "ADDITIVE_LOCAL_METADATA_RECONCILIATION", "claim class")
    require(packet["base"]["preserved_artifacts"] == ORIGINALS, "original preservation anchors")
    redaction = packet["base"].get("deployment_path_redaction")
    if redaction is None:
        require(packet["base"]["sha256"] == ORIGINALS["coverage-ledger.json"], "base anchor")
    else:
        require(redaction == REDACTION, "unrecognized deployment-path redaction")
        require(packet["base"]["sha256"] == REDACTION["redacted_sha256"], "redacted base anchor")
    require(packet["r5"]["manifest_sha256"] == R5_SHA, "r5 manifest anchor")
    require(packet["r5"]["revision"] == manifest["revision"] == "2026.11.03.5", "revision")
    require(packet["r5"]["manifest_files"] == manifest["files"], "manifest file retention")
    require(packet["r5"]["manifest_file_records"] == len(manifest["files"]) == 17,
            "manifest file denominator")
    require(packet["r5"]["declared_source_bytes"] == sum(v["bytes"] for v in manifest["files"].values())
            == 134121, "manifest source bytes")
    base_rows = {s["source_id"]: s for s in base["sources"]}
    added = {s["source_id"]: s for s in packet["new_sources"]}
    require(len(base_rows) == 138 and len(added) == len(packet["new_sources"]) == 99, "source retention")
    require(not base_rows.keys() & added.keys(), "unqualified base identity merge")
    manifest_ids = {identity(u) for u in manifest["sources"]}
    source_reports = receipts["sources"]
    root_reports = receipts["root_sources"]
    pending_reports = receipts["pending_sources"]
    detailed_ids = {identity(s["resolved_url"]) for s in source_reports}
    detailed_ids.update(identity(s["url"]) for s in root_reports)
    aliases = {identity(s["requested_url"]) for s in source_reports} - manifest_ids
    pending_ids = {identity(s["url"]) for s in pending_reports}
    require(len(manifest_ids) == 94 and len(detailed_ids) == 22 and len(aliases) == 3
            and len(pending_ids) == 2, "raw receipt denominators")
    require(set(added) == manifest_ids | aliases | pending_ids, "missing/merged/additional identities")
    require(not manifest_ids & set(base_rows), "base/manifest overlap changed")
    manifest_membership = packet["manifest_membership"]
    require(len(manifest_membership) == 94, "manifest membership omitted")
    require([(r["source_id"], r["url"]) for r in manifest_membership]
            == [(identity(u), u) for u in manifest["sources"]], "manifest spelling/order changed")
    index = packet["source_index"]
    require(len(index) == len({r["source_id"] for r in index}) == 237, "index omission/duplicate")
    require({r["source_id"] for r in index} == base_rows.keys() | added.keys(), "index source union")
    for row in index:
        original = (base_rows | added)[row["source_id"]]
        require(row["canonical_url"] == original["canonical_url"], "index URL mismatch")
        require(row["source_id"] == identity(row["canonical_url"]), "index identity mismatch")
        retained = row["source_id"] in base_rows
        records = base["sources"] if retained else packet["new_sources"]
        position = next(i for i, value in enumerate(records) if value["source_id"] == row["source_id"])
        expected_input = packet["base"]["path"] if retained else "docs/v2/vault/r5-reconciliation-20261103.json"
        expected_pointer = ("/sources/" if retained else "/new_sources/") + str(position)
        require(row["record"] == {"input": expected_input, "json_pointer": expected_pointer},
                "source index points at the wrong record")
    require(len(packet["detailed_read_reports"]) == 22, "detailed report omission")
    for record, source in zip(packet["detailed_read_reports"], source_reports + root_reports):
        require(record["reported_record"] == source, "invented/changed read-depth receipt")
        require(record["source_id"] == identity(source.get("resolved_url", source.get("url"))),
                "detailed report assigned to wrong source")
        observation = added[record["source_id"]]["reading"]["observations"]
        require(len(observation) == 1 and observation[0]["read_depth_verbatim"] == source["read_depth"]
                and observation[0]["evidence"] == record["receipt"], "source observation changed")
    expected_edges = {
        (identity(s["requested_url"]), identity(s["resolved_url"])) for s in source_reports
        if canonical(s["requested_url"]) != canonical(s["resolved_url"])
    }
    require(len(packet["reported_redirect_relations"]) == 3, "redirect retention")
    require({(e["from"], e["to"]) for e in packet["reported_redirect_relations"]} == expected_edges,
            "redirect relation changed")
    for edge in packet["reported_redirect_relations"]:
        require(edge["identities_merged"] is False and edge["live_redirect_verified"] is False,
                "reported redirect promoted to live equivalence")
    require([r["reported_record"] for r in packet["pending_sources"]] == pending_reports,
            "pending source or failure overwritten")
    short_page_ids = {identity(s["url"]) for s in root_reports
                      if "full short accounting introduction" in s["read_depth"]}
    for source_id, source in added.items():
        require(source_id == identity(source["canonical_url"]), "added identity mismatch")
        require(source["exact_variants"] and all(identity(u) == source_id for u in source["exact_variants"]),
                "exact spelling lost or unqualified alias merged")
        require(source["worker_inspection"] == "LOCAL_METADATA_AND_REPORTED_READ_DEPTH_ONLY"
                and source["access"]["current"] == "NOT_ATTEMPTED", "primary-read overclaim")
        require(source["activation_allowed"] is False and source["primary_content_sha256"] is None,
                "activation or primary-content-pin overclaim")
        require(source["evaluation"] == {"status": "NOT_RUN", "receipts": []}, "efficacy overclaim")
        if source_id in detailed_ids:
            expected_depth = ("COMPLETE_SHORT_PAGE_TEXT_REPORTED" if source_id in short_page_ids
                              else "SELECTED_SCOPE_REPORTED")
            require(source["access"]["historical"] == "SUCCESS_REPORTED_AT_RESOLVED_URL",
                    "reported successful access missing")
            require(source["adoption"]["status"] == "AUTHORED_NOTE_USE_REPORTED"
                    and source["adoption"]["reported_uses"], "note use promoted or omitted")
        elif source_id in aliases:
            expected_depth = "CONTENT_REPORTED_AT_SEPARATE_RESOLVED_LOCATOR"
            require(source["access"]["historical"] == "REDIRECT_REPORTED", "alias access")
        elif source_id in pending_ids:
            report = next(s for s in pending_reports if identity(s["url"]) == source_id)
            expected_depth = "NOT_ANALYSED_REPORTED" if "NOT_ANALYSED" in report["status"] else "NOT_READ_REPORTED"
            require(source["access"]["historical"] == report["status"], "pending access failure lost")
        else:
            expected_depth = "NOT_ESTABLISHED_IN_SELECTED_R5_RECEIPTS"
            require(source["access"]["historical"] == "UNKNOWN", "manifest membership made a fetch")
        require(source["reading"]["status"] == expected_depth, "unsupported read-depth projection")
        if source_id not in detailed_ids:
            require(source["adoption"] == {"status": "NOT_ESTABLISHED", "reported_uses": []},
                    "unsupported adoption")
    target = next(s for s in base_rows.values() if s.get("transfer") and s["transfer"]["item"] == 15)
    require(len(packet["corrections"]) == 1, "unsupported full-post claim left current")
    correction = packet["corrections"][0]
    require(correction["source_id"] == target["source_id"] and correction["axis"] == "reading",
            "correction targets wrong identity/axis")
    require(correction["old_status"] == target["reading"]["status"] == "COMPLETE_POST_TEXT"
            and correction["replacement_status"] == "POST_TEXT_EXTENT_UNSPECIFIED",
            "unsupported complete-read label not corrected")
    require(correction["verified_primary_read"] is False and correction["acceptance_change"] is False
            and correction["access_or_activation_change"] is False, "correction widened authority")
    overrides = [r for r in index if r["reading_override"] is not None]
    require(len(overrides) == 1 and overrides[0]["source_id"] == target["source_id"]
            and overrides[0]["reading_override"]["json_pointer"] == "/corrections/0", "correction not applied")
    depths = Counter(correction["replacement_status"] if s["source_id"] == target["source_id"]
                     else s["reading"]["status"] for s in base_rows.values())
    depths.update(s["reading"]["status"] for s in added.values())
    transfer_depths = Counter(correction["replacement_status"] if s["source_id"] == target["source_id"]
                              else s["reading"]["status"] for s in base_rows.values() if s.get("transfer"))
    expected_summary = {
        "retained_identities": 138, "r5_manifest_identities": 94, "overlap_retained_manifest": 0,
        "new_resolved_or_manifest_identities": 94, "additional_requested_locator_identities": 3,
        "pending_outside_manifest_identities": 2, "new_identities": 99, "url_identities": 237,
        "manifest_urls_with_detailed_report": 22, "manifest_urls_without_depth_in_selected_r5_receipts": 72,
        "new_reported_redirect_relations": 3, "reported_primary_full_reads_this_worker": 0,
        "current_primary_fetches_this_worker": 0, "base_read_extent_corrections": 1,
        "current_projection_read_depths": dict(depths), "current_transfer_read_depths": dict(transfer_depths),
        "measured_efficacy_receipts_added": 0,
    }
    require(packet["summary"] == expected_summary, "summary diverges from independent input projection")
    return "PASS_METADATA_ONLY: 138 retained + 99 additions = 237 URL identities; item15 extent corrected"


def check_inputs(packet):
    pins = {p["path"]: p for p in packet["inputs"]}
    require(len(pins) == len(packet["inputs"]), "duplicate input pins")
    for pin in pins.values():
        require(sha(path(pin["path"]).read_bytes()) == pin["sha256"], "stale input: " + pin["path"])
    for name, expected in ORIGINALS.items():
        if name == "coverage-ledger.json" and packet["base"].get("deployment_path_redaction") is not None:
            expected = REDACTION["redacted_sha256"]
        require(sha((AREA / name).read_bytes()) == expected, "historical artifact changed: " + name)
    manifest_path = path(packet["r5"]["manifest"])
    require(sha(manifest_path.read_bytes()) == R5_SHA, "canonical r5 manifest changed")
    for name, metadata in packet["r5"]["manifest_files"].items():
        raw = (manifest_path.parent / name).read_bytes()
        require(len(raw) == metadata["bytes"] and sha(raw) == metadata["sha256"], "r5 file changed: " + name)


def negatives(packet, base, manifest, receipts):
    def mark_first_manifest_only_read(p):
        row = next(s for s in p["new_sources"] if s["reading"]["status"] == "NOT_ESTABLISHED_IN_SELECTED_R5_RECEIPTS")
        row["reading"]["status"] = "SELECTED_SCOPE_REPORTED"

    def mark_reel_read(p):
        row = next(s for s in p["new_sources"] if "DfNBVUroUTO" in s["canonical_url"])
        row["reading"]["status"] = "SELECTED_SCOPE_REPORTED"

    def mark_note_runtime_adoption(p):
        row = next(s for s in p["new_sources"] if s["adoption"]["status"] == "AUTHORED_NOTE_USE_REPORTED")
        row["adoption"]["status"] = "RUNTIME_ADOPTED"

    mutations = [
        ("omit retained identity", lambda p: p["source_index"].pop(0)),
        ("leave old full-post claim current", lambda p: p["corrections"].clear()),
        ("restore unsupported complete read", lambda p: p["corrections"][0].update(replacement_status="COMPLETE_POST_TEXT")),
        ("manifest membership becomes reading", mark_first_manifest_only_read),
        ("throttled reel becomes reading", mark_reel_read),
        ("merge requested and resolved", lambda p: p["reported_redirect_relations"][0].update(identities_merged=True)),
        ("notes become runtime adoption", mark_note_runtime_adoption),
        ("invent measured efficacy", lambda p: p["new_sources"][0]["evaluation"].update(status="PASS")),
        ("alter recorded read scope", lambda p: p["detailed_read_reports"][0]["reported_record"].update(read_depth="Full documentation read")),
        ("change preserved original anchor", lambda p: p["base"]["preserved_artifacts"].update({"README.md": "0" * 64})),
    ]
    for label, mutate in mutations:
        candidate = copy.deepcopy(packet)
        mutate(candidate)
        try:
            validate(candidate, base, manifest, receipts)
        except ValueError:
            print("REJECTED: " + label)
        else:
            raise ValueError("negative control survived: " + label)
    print(f"PASS: {len(mutations)} metadata mutants rejected; source truth and efficacy remain unverified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-inputs", action="store_true")
    parser.add_argument("--negative-controls", action="store_true")
    args = parser.parse_args()
    try:
        packet = load(FILE)
        base = load(path(packet["base"]["path"]))
        manifest = load(path(packet["r5"]["manifest"]))
        receipts = load(path(packet["r5"]["reference_sources"]))
        if args.check_inputs:
            check_inputs(packet)
        print(validate(packet, base, manifest, receipts))
        if args.negative_controls:
            negatives(packet, base, manifest, receipts)
    except (ValueError, KeyError, TypeError, StopIteration, OSError) as error:
        parser.exit(1, "FAIL_METADATA: " + str(error) + "\n")


if __name__ == "__main__":
    main()
