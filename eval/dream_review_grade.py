"""Read-only quality replay for standalone and batched dream review."""
import argparse
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

from agent_harness.dream_candidates import MAX_CANDIDATES, review_packet
from agent_harness.presets import _read
from agent_harness.vault_sources import _unique_object

# Older corpora record only a binary verdict, so preserve their unknown subtype.
LABELS = {"support", "restatement", "stale_or_conflicting", "topic_only", "insufficient",
          "unclassified_negative", "ambiguous"}
DECISIONS = {"accept", "reject", "abstain"}
INPUT_LIMIT = 1024 * 1024


def _load(raw):
    return json.loads(raw, object_pairs_hook=_unique_object)


def _fields(value, names):
    return isinstance(value, dict) and set(value) == names


def _labels(freeze, expected_hash):
    raw = _read(Path(freeze), INPUT_LIMIT)
    if sha256(raw).hexdigest() != expected_hash:
        raise ValueError("label freeze hash does not match")
    frozen = _load(raw)
    if (not _fields(frozen, {"schema", "cases"}) or frozen["schema"] != "harness.dream-review-labels/v1"
            or not isinstance(frozen["cases"], list) or not 1 <= len(frozen["cases"]) <= MAX_CANDIDATES):
        raise ValueError("invalid frozen label manifest")
    labels = {}
    for row in frozen["cases"]:
        if (not _fields(row, {"id", "label", "lexical_selected"})
                or not isinstance(row["id"], str) or not isinstance(row["label"], str)
                or row["id"] in labels or row["label"] not in LABELS
                or type(row["lexical_selected"]) is not bool):
            raise ValueError("invalid or duplicate frozen label")
        labels[row["id"]] = row
    classes = {row["label"] for row in labels.values()}
    if "support" not in classes or not classes - {"support", "ambiguous"}:
        raise ValueError("frozen labels need both positive and negative cases")
    return labels


def _coverage(ids, expected):
    if (not isinstance(ids, list) or any(not isinstance(item, str) for item in ids)
            or len(ids) != len(set(ids)) or set(ids) != expected):
        raise ValueError("candidate coverage must be exact and unique")


def _arm(corpus, batches, labels, *, standalone):
    if not isinstance(batches, list) or not 1 <= len(batches) <= len(labels):
        raise ValueError("missing or invalid review packets")
    observed = {}
    for batch in batches:
        if not _fields(batch, {"candidate_ids", "packet_sha256", "decisions"}):
            raise ValueError("invalid review packet result")
        ids = batch["candidate_ids"]
        if (not isinstance(ids, list) or not ids or (standalone and len(ids) != 1)
                or any(not isinstance(identity, str) or identity not in labels or identity in observed
                       for identity in ids)):
            raise ValueError("candidate coverage must be exact and unique")
        _coverage(ids, set(ids))
        decisions = batch["decisions"]
        if not isinstance(decisions, list) or any(not isinstance(row, dict) for row in decisions):
            raise ValueError("invalid review decisions")
        _coverage([row.get("id") for row in decisions], set(ids))
        raw = review_packet(corpus, ids)
        if sha256(raw).hexdigest() != batch["packet_sha256"]:
            raise ValueError("review packet hash does not match the bound sources and order")
        packet = _load(raw)
        pages = packet["sources"]
        pairs = {row["id"]: row for row in packet["candidates"]}
        for row in decisions:
            identity, decision = row["id"], row.get("decision")
            if not isinstance(decision, str) or decision not in DECISIONS:
                raise ValueError("invalid review decision")
            if decision == "accept":
                if not _fields(row, {"id", "decision", "source_quote", "target_quote"}) or not all(
                    isinstance(row[key + "_quote"], str) and row[key + "_quote"].strip()
                    and row[key + "_quote"] in pages[pairs[identity][key]]["text"]
                    for key in ("source", "target")
                ):
                    raise ValueError("accepted link needs exact source and target quotations")
            elif not _fields(row, {"id", "decision"}):
                raise ValueError("invalid rejection or abstention")
            observed[identity] = decision == "accept"
    _coverage(list(observed), set(labels))
    return observed


def _measure(accepted, known, positive):
    selected = accepted & known
    true_positive = len(positive & selected)
    precision = Fraction(true_positive, len(selected) or 1)
    recall = Fraction(true_positive, len(positive))
    return {"tp": true_positive, "fp": len(selected) - true_positive,
            "fn": len(positive) - true_positive, "precision": precision, "recall": recall}



def _label_sets(labels):
    lexical = {identity for identity, row in labels.items() if row["lexical_selected"]}
    ambiguous = {identity for identity, row in labels.items() if row["label"] == "ambiguous"}
    positive = {identity for identity, row in labels.items() if row["label"] == "support"}
    return lexical, ambiguous, positive


def _minimum_precision(lexical_precision):
    return max(Fraction(4, 5), lexical_precision + Fraction(1, 10))


def precision_preflight(freeze, expected_hash):
    """Detect an unattainable precision gate before launching a reviewer."""
    labels = _labels(freeze, expected_hash)
    lexical, ambiguous, positive = _label_sets(labels)
    precision = _measure(lexical, set(labels) - ambiguous, positive)["precision"]
    minimum = _minimum_precision(precision)
    return {
        "status": "PRECISION_CEILING" if minimum > 1 else "WITHIN_PRECISION_RANGE",
        "label_freeze_sha256": expected_hash, "lexical_precision": float(precision),
        "required_precision": float(minimum), "maximum_precision": 1.0,
        "promotion": "NOT_GRANTED",
    }


def replay(corpus, freeze, expected_hash, results):
    labels = _labels(freeze, expected_hash)
    if not _fields(results, {"standalone", "batched"}):
        raise ValueError("both review arms are required")
    arms = {name: {identity for identity, yes in _arm(corpus, results[name], labels,
                                                     standalone=name == "standalone").items() if yes}
            for name in ("standalone", "batched")}
    if not any(len(batch["candidate_ids"]) > 1 for batch in results["batched"]):
        raise ValueError("batched arm needs at least one shared review packet")
    arms["lexical"], ambiguous, positive = _label_sets(labels)
    known = set(labels) - ambiguous
    scores = {name: _measure(accepted, known, positive) for name, accepted in arms.items()}
    regressions = ((arms["batched"] ^ positive) - (arms["standalone"] ^ positive)) & known
    accepted_ambiguous = arms["batched"] & ambiguous
    reasons = []
    if scores["batched"]["precision"] < _minimum_precision(scores["lexical"]["precision"]):
        reasons.append("precision_below_threshold")
    if scores["batched"]["recall"] < Fraction(1, 2):
        reasons.append("recall_below_threshold")
    if regressions:
        reasons.append("standalone_case_regression")
    if accepted_ambiguous:
        reasons.append("accepted_ambiguous_requires_adjudication")
    return {
        "quality_gate": "HOLD" if reasons else "PASS", "promotion": "NOT_GRANTED", "usage": "NOT_ASSESSED",
        "case_count": len(labels), "label_freeze_sha256": expected_hash, "reasons": reasons,
        "affected_decisions": sorted(regressions), "ambiguous_ids": sorted(ambiguous),
        "accepted_ambiguous_ids": sorted(accepted_ambiguous),
        "negative_acceptances": {
            name: {label: sum(labels[identity]["label"] == label for identity in accepted)
                   for label in sorted(LABELS - {"support", "ambiguous"})}
            for name, accepted in arms.items()
        },
        **{name: {key: float(value) if isinstance(value, Fraction) else value
                  for key, value in metrics.items()} for name, metrics in scores.items()},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path, nargs="?")
    parser.add_argument("freeze", type=Path, nargs="?")
    parser.add_argument("results", type=Path, nargs="?")
    parser.add_argument("--preflight-labels", type=Path, metavar="FREEZE",
                        help="check the frozen precision range before collecting responses")
    parser.add_argument("--freeze-sha256", required=True)
    args = parser.parse_args(argv)
    replay_inputs = (args.corpus, args.freeze, args.results)
    if args.preflight_labels is not None and any(replay_inputs):
        parser.error("--preflight-labels cannot be combined with corpus, freeze or results")
    if args.preflight_labels is None and not all(replay_inputs):
        parser.error("corpus, freeze and results are required for replay")
    try:
        if args.preflight_labels is not None:
            report = precision_preflight(args.preflight_labels, args.freeze_sha256)
            passed = report["status"] == "WITHIN_PRECISION_RANGE"
        else:
            report = replay(args.corpus, args.freeze, args.freeze_sha256, _load(_read(args.results, INPUT_LIMIT)))
            passed = report["quality_gate"] == "PASS"
    except (OSError, ValueError) as error:
        parser.exit(2, f"dream review evidence invalid: {error}\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
