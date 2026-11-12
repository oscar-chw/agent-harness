#!/usr/bin/env python3
"""admit_capability.py — run one capability through the plugin admission loop.

Plan v3-settlement-plugin-loop node 6; design
docs/v3/settlement-plugin-loop-design-20261111.md. Loads a
`harness.plugin-candidate/v1` descriptor, runs the fail-closed loop
(qualification → typed decision → admission), and records the outcome —
admitted OR refused — in a `harness.plugin-registry/v1` registry
(atomic write; refusals are first-class auditable entries).

    /usr/bin/python3 scripts/admit_capability.py --candidate <candidate.json>
                                                 --registry <registry.json>

Exit 0 = admitted (or already admitted with identical bindings); 1 =
refused (the refusal is still registered); 2 = usage/internal error
(fail-closed).
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_harness import plugin_loop  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="plugin admission loop for one capability")
    ap.add_argument("--candidate", required=True, help="candidate descriptor (repo-relative)")
    ap.add_argument("--registry", required=True, help="registry file (repo-relative)")
    ap.add_argument("--root", default=str(ROOT),
                    help="root the candidate's refs resolve under (default: this repo; "
                    "controls point it at a tmp skeleton)")
    args = ap.parse_args(argv)

    root = str(Path(args.root).resolve())
    candidate_path = args.candidate if os.path.isabs(args.candidate) else os.path.join(root, args.candidate)
    registry_path = (args.registry if os.path.isabs(args.registry)
                     else os.path.join(root, args.registry))
    if not os.path.isfile(candidate_path):
        print("ERROR: candidate not found: {}".format(args.candidate))
        return 2
    try:
        with open(candidate_path, "r", encoding="utf-8") as fh:
            candidate = json.load(fh)
        candidate = plugin_loop.validate_candidate(candidate)
        registry = plugin_loop.load_registry(registry_path)
    except (OSError, ValueError) as exc:
        print("ERROR: failed closed: {}".format(exc))
        return 2

    entry = plugin_loop.admit(candidate, root,
                              datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    try:
        registry, appended = plugin_loop.append_entry(registry, entry)
        plugin_loop.write_registry(registry_path, registry)
    except plugin_loop.PluginLoopError as exc:
        print("ERROR: registry refused the entry: {}".format(exc))
        return 2

    print("{}: {} ({}){}".format(entry["status"].upper(), entry["name"], entry["kind"],
                                 "" if appended else " — already registered, unchanged"))
    print("  rea: {} sha256 {}…".format(entry["rea"]["ref"], entry["rea"]["sha256"][:12]))
    print("  jev: {} sha256 {}…".format(entry["jev"]["ref"], entry["jev"]["sha256"][:12]))
    print("  {}".format(entry["detail"]))
    if entry["status"] == "admitted":
        print("VERDICT: PASS (admitted with full receipts; promotion NOT_GRANTED)")
        return 0
    print("VERDICT: FAIL (admission refused; the refusal is registered)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
