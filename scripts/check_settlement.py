#!/usr/bin/env python3
"""check_settlement.py — settlement-hook scan over plan/workgraph activity.

Plan v3-settlement-plugin-loop node 5; design
docs/v3/settlement-plugin-loop-design-20261111.md. Scans an EXPLICIT set of
plan files (fail-closed: no --plan is a usage error, a missing plan file is
exit 2) and proves every done-marked action has a closing receipt
(graph note + node record + re-derived gate signature).

    /usr/bin/python3 scripts/check_settlement.py --plan plan/<slug>.md [--plan ...]
                                                   [--out <document.json>]

Exit 0 = no failed action (settled and open listed); 1 = at least one
failed action; 2 = usage/internal error. UNKNOWN is never zero: one record
per parsed node, printed and (with --out) written.
"""
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_harness import settlement  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="settlement-hook scan over plan files")
    ap.add_argument("--plan", action="append", dest="plans", default=[],
                    metavar="PLAN", help="plan file to scan (repeatable, required)")
    ap.add_argument("--out", default=None, metavar="JSON",
                    help="write the settlement document here (default: stdout summary only)")
    args = ap.parse_args(argv)
    if not args.plans:
        print("ERROR: at least one --plan is required (an empty scan is not a settlement)")
        return 2
    plans = []
    for p in args.plans:
        path = p if os.path.isabs(p) else str(ROOT / p)
        if not os.path.isfile(path):
            print("ERROR: plan file not found: {}".format(p))
            return 2
        plans.append(path)
    try:
        document = settlement.scan(plans, datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    except settlement.SettlementError as exc:
        print("ERROR: scan failed closed: {}".format(exc))
        return 2
    counts = settlement.summarize(document)
    for rec in document["records"]:
        action = rec["action"]
        line = "  {} node {}: {}".format(
            os.path.basename(rec["plan"]["ref"]), action["node"], rec["status"])
        if rec["settled_by"]:
            line += " ({})".format(rec["settled_by"]["verification"])
        if rec["status"] == "failed":
            line += " — {}".format(rec["detail"])
        print(line)
    failed = [r for r in document["records"] if r["status"] == "failed"]
    if args.out:
        out_path = args.out if os.path.isabs(args.out) else str(ROOT / args.out)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        tmp = out_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(settlement.dumps(document))
        os.replace(tmp, out_path)  # atomic: all-or-nothing, the repo idiom
        print("document: {}".format(args.out))
    if failed:
        print("VERDICT: FAIL ({} failed, {} settled, {} open — unsettled ≠ settled)".format(
            len(failed), counts["settled"], counts["open"]))
        return 1
    print("VERDICT: PASS ({} settled, {} open, 0 failed across {} plan(s))".format(
        counts["settled"], counts["open"], len(plans)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
