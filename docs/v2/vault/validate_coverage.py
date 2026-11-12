#!/usr/bin/env python3
"""Validate this bounded documentation snapshot, never source truth or efficacy."""

import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AREA = Path(__file__).resolve().parent
DEPTHS = {
    "UNINSPECTED": 0, "TITLE_SNIPPET": 1, "METADATA_ONLY": 1,
    "SNIPPET_ONLY": 2, "CAPTION_FRAME": 3, "ABSTRACT_ONLY": 3,
    "SELECTED_SECTIONS": 4, "COMPLETE_POST_TEXT": 5,
    "COMPLETE_ARTICLE_TEXT": 5, "COMPLETE_IDEA_FILE": 5,
}
INVENTORY_SHA = "501dafcc17d404eed09fa999b8518097ee39c8840dcf74de5531ed0c57e4b6bc"
HANDOVER_SHA = "b3aa817acb40fb27105f549f3cf0ab49c17db145b71ce06cad34033e9d68be78"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result

    return json.loads(path.read_text(), object_pairs_hook=unique)


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def validate(ledger, cases, *, check_inputs=False):
    require(ledger["schema"] == "harness.source-coverage/v1", "ledger schema")
    require(ledger["claim_class"] == "BOUNDED_METADATA_RECONCILIATION", "claim boundary")
    inputs = {item["path"]: item for item in ledger["inputs"]}
    require(len(inputs) == len(ledger["inputs"]), "duplicate input pins")
    sources = ledger["sources"]
    require(len(sources) == 138, "bounded denominator must retain 138 identities")
    urls = [item["canonical_url"] for item in sources]
    identities = [item["source_id"] for item in sources]
    require(len(set(urls)) == len(urls), "canonical identity merge/duplicate")
    require(len(set(identities)) == len(identities), "duplicate source IDs")
    by_id = dict(zip(identities, sources))

    def evidence(ref):
        require(ref["input"] in inputs, "unbound evidence input")
        require(type(ref["start_line"]) is int and type(ref["end_line"]) is int
                and 1 <= ref["start_line"] <= ref["end_line"], "invalid evidence range")
        if check_inputs:
            lines = resolve(ref["input"]).read_text().splitlines()
            require(ref["end_line"] <= len(lines), "evidence range exceeds pinned input")

    transfer = []
    for item in sources:
        require(item["source_id"] == "url-sha256:" + sha(item["canonical_url"].encode()),
                "identity not bound to canonical URL")
        require(item["exact_variants"] and len(set(item["exact_variants"]))
                == len(item["exact_variants"]), "missing/duplicate exact variants")
        require(item["worker_inspection"] == "METADATA_AND_LOCAL_REVIEW_ONLY",
                "worker primary-read overclaim")
        require(item["activation_allowed"] is False, "activation authority overclaim")
        require(item["access"]["current"] == "NOT_ATTEMPTED", "current acquisition overclaim")
        require(item["access"]["historical"] in {
            "UNKNOWN", "SUCCESS_REPORTED", "INDEXED_OR_PARTIAL_REPORTED",
            "FAILED_REPORTED", "MIXED_REPORTS",
        }, "access enum")
        require(item["freshness"] == {"status": "NOT_REVALIDATED", "checked_date": None},
                "freshness overclaim")
        require(item["source_revision"]["content_sha256"] is None,
                "local report digest substituted for primary content")
        require(item["support"]["status"] in {
            "NOT_ESTABLISHED", "REPORTED_INTERPRETATION_ONLY", "REPORTED_CLAIM_CHECK",
        }, "unsupported verified support")
        require(item["adoption"]["status"] in {
            "NOT_ESTABLISHED", "PROPOSED_ONLY", "NONE_REPORTED",
        } and item["adoption"]["decision_ids"] == [], "unsupported adoption")
        require(item["evaluation"]["status"] in {
            "NOT_ESTABLISHED", "NOT_RUN_REPORTED",
        } and item["evaluation"]["receipt_ids"] == [], "unsupported evaluation")
        depth = item["reading"]["status"]
        require(depth in DEPTHS, "read-depth enum")
        observations = item["reading"]["observations"]
        if not observations:
            require(depth == "UNINSPECTED", "read depth without an observation")
        else:
            require(DEPTHS[depth] == max(DEPTHS[o["read_depth"]] for o in observations),
                    "aggregate read-depth unsupported by observations")
        for observation in observations:
            require(observation["kind"] == "HISTORICAL_LOCAL_REVIEW_REPORT",
                    "historical report promoted into fresh source verification")
            require(observation["extent_and_limit"], "read-depth scope missing")
            evidence(observation["evidence"])
        if item["transfer"]:
            old = item["transfer"]
            transfer.append(item)
            require(old["incoming_read_status"] == "UNREAD_UNVERIFIED", "original transfer overwritten")
            require(set(old["exact_variants"]) <= set(item["exact_variants"]), "lost original variants")
            require(old["provenance"]["input"] in inputs, "transfer input missing")
            if old["triage"] == "CROSS_PROJECT_RETAINED":
                require(item["scope"] == "CROSS_PROJECT_LEAD_ONLY", "cross-project widening")
    require(sorted(s["transfer"]["item"] for s in transfer) == list(range(1, 109)),
            "transfer item omission/duplication")
    require(sum(len(s["transfer"]["exact_variants"]) for s in transfer) == 110,
            "original exact variant denominator")
    require(Counter(s["transfer"]["classification"] for s in transfer)
            == {"U": 95, "E": 5, "R": 5, "M": 2, "Q": 1}, "classification retention")
    require(Counter(s["transfer"]["triage"] for s in transfer) == {
        "NEEDS_SOURCE_READ": 92, "PRIOR_RECORD_FOUND_RECONCILE_READ_DEPTH": 13,
        "CROSS_PROJECT_RETAINED": 3,
    }, "triage retention")
    summary = ledger["summary"]
    expected = {
        "source_identities": 138, "transfer_items": 108, "transfer_exact_variants": 110,
        "additional_identities": 30, "current_primary_fetches": 0, "current_primary_reads": 0,
        "reported_read_depth": dict(Counter(s["reading"]["status"] for s in sources)),
        "transfer_reported_read_depth": dict(Counter(s["reading"]["status"] for s in transfer)),
        "verified_source_to_claim_edges": 0, "complete_source_claim_implementation_eval_joins": 0,
        "reported_source_to_claim_edges": 3,
    }
    require(summary == expected, "summary not derived from retained records")
    claims = {claim["claim_id"]: claim for claim in ledger["claims"]}
    require(len(claims) == len(ledger["claims"]) == len(ledger["relations"]) == 3,
            "reported claim-check retention")
    for claim in claims.values():
        require(claim["source_id"] in by_id, "claim source missing")
        require(claim["verification"] == "HISTORICAL_LOCAL_REPORT_NOT_REVALIDATED",
                "claim verification overclaim")
        require(claim["support_status"] in {
            "SUPPORTED_REPORTED", "CONTRADICTED_REPORTED", "NOT_SUPPORTED_REPORTED",
        }, "claim support enum")
        evidence(claim["evidence"])
    for relation in ledger["relations"]:
        require(relation["source_id"] in by_id and relation["claim_id"] in claims,
                "dangling source-claim relation")
        require(relation["status"] == "REPORTED_NOT_REVALIDATED", "relation overclaim")
        require(relation["relation"] in {"supports", "contradicts", "does_not_support"},
                "relation enum")
        evidence(relation["evidence"])
    for source in sources:
        require(all(cid in claims and claims[cid]["source_id"] == source["source_id"]
                    for cid in source["support"]["claim_ids"]), "invalid support claim pointer")
    require(len(ledger["unresolved_leads"]) == 3, "unresolved lead retention")
    for lead in ledger["unresolved_leads"]:
        require(lead["identity"] == "UNRESOLVED" and lead["read_depth"] == "UNKNOWN",
                "unresolved lead fabricated")
        evidence(lead["evidence"])
    aggregate = ledger["historical_aggregates"]
    require(len(aggregate) == 1 and aggregate[0]["attempts"] == 15
            and aggregate[0]["item_mapping"] == "NOT_ESTABLISHED",
            "aggregate falsely assigned to individual rows")
    evidence(aggregate[0]["evidence"])
    require(cases["schema"] == "harness.vault-acceptance-cases/v1"
            and cases["status"] == "PROPOSED_NOT_RUN", "acceptance specification boundary")
    require(len(cases["cases"]) == len({c["case_id"] for c in cases["cases"]}) == 16,
            "case omission/duplicate")
    for case in cases["cases"]:
        require(case["status"] == "NOT_RUN" and case["response_receipt"] is None
                and case["usage_receipt"] is None and case["independent_oracle_frozen"] is False,
                "authored expected answer promoted to trial result")
        require(case["question"] and case["answer_requirements"] and case["must_not"]
                and case["supporting_sources"], "empty acceptance case")
        require(set(case["external_source_ids"]) <= set(by_id), "case source missing")
        for pointer in case["supporting_sources"]:
            require(1 <= pointer["start_line"] <= pointer["end_line"], "case span invalid")
            if check_inputs:
                path = resolve(pointer["path"])
                require(sha(path.read_bytes()) == pointer["sha256"], "case evidence changed: " + str(path))
                require(pointer["end_line"] <= len(path.read_text().splitlines()), "case span exceeds input")
    if check_inputs:
        for pin in inputs.values():
            require(sha(resolve(pin["path"]).read_bytes()) == pin["sha256"],
                    "changed input: " + pin["path"])
        original = next(pin for pin in inputs.values() if pin["path"].endswith("/inventory.json"))
        handover = next(pin for pin in inputs.values() if pin["path"].endswith("/HANDOVER.md"))
        require(original["sha256"] == INVENTORY_SHA and handover["sha256"] == HANDOVER_SHA,
                "original provenance anchor changed")
        inventory = load(resolve(original["path"]))
        for item in transfer:
            old = item["transfer"]
            row = inventory["items"][old["item"] - 1]
            raw = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
            require(old["provenance"]["row_sha256"] == sha(raw), "original row digest mismatch")
            require(item["canonical_url"] == row["canonical_url"], "original identity changed")
            require(old["provenance"]["json_pointer"] == "/items/" + str(old["item"] - 1),
                    "original item locator changed")
            for key in ("classification", "incoming_read_status", "triage", "exact_variants"):
                require(old[key] == row[key], "original field changed: " + key)
            require(old["prior_research_pointers"] == row["existing_research_refs"], "lost prior pointers")
    return "PASS_METADATA_ONLY: 138 identities; 108 transfer items/110 variants; 16 NOT_RUN cases"


def negative_controls(ledger, cases):
    mutations = [
        ("omitted identity", lambda l, c: l["sources"].pop()),
        ("lost original variant", lambda l, c: l["sources"][0]["transfer"]["exact_variants"].clear()),
        ("invented read", lambda l, c: l["sources"][0]["reading"].update(status="SELECTED_SECTIONS")),
        ("invented verification", lambda l, c: l["sources"][0]["support"].update(status="VERIFIED")),
        ("activation", lambda l, c: l["sources"][0].update(activation_allowed=True)),
        ("unbound span", lambda l, c: l["sources"][14]["reading"]["observations"][0]["evidence"].update(input="missing")),
        ("identity merge", lambda l, c: l["sources"][1].update(canonical_url=l["sources"][0]["canonical_url"])),
        ("fake trial pass", lambda l, c: c["cases"][0].update(status="PASS")),
    ]
    for name, mutate in mutations:
        left, right = copy.deepcopy(ledger), copy.deepcopy(cases)
        mutate(left, right)
        try:
            validate(left, right)
        except ValueError:
            print("REJECTED: " + name)
        else:
            raise ValueError("negative control survived: " + name)
    return len(mutations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-inputs", action="store_true",
                        help="Read only the already-authorized pinned local inputs; check bytes/spans")
    parser.add_argument("--negative-controls", action="store_true")
    args = parser.parse_args()
    try:
        ledger = load(AREA / "coverage-ledger.json")
        cases = load(AREA / "acceptance-cases.json")
        print(validate(ledger, cases, check_inputs=args.check_inputs))
        if args.negative_controls:
            count = negative_controls(ledger, cases)
            print(f"PASS: {count} metadata negative controls rejected; unchanged control valid")
    except (ValueError, KeyError, TypeError, StopIteration, OSError) as error:
        parser.exit(1, "FAIL_METADATA: " + str(error) + "\n")


if __name__ == "__main__":
    main()
