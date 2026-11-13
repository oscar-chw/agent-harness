"""Check the interview pack and observations, independently of the demo runner."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

REQUIRED_FILES = ("demo.py", "check_pack.py", "build_guide.py", "architecture.svg", "architecture.pdf",
                  "architecture.mmd", "guide.html", "technical-notes.md", "README.md", "deployment-status.md",
                  "recorded-demo-proof.json", "recorded-commands.json", "capability-catalog.json",
                  "capability-catalog.md", "recorded-reader-a.txt", "recorded-reader-b.txt",
                  "recorded-reader-update.txt")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_receipt(row):
    require(row.get("schema") == "harness.interview-demo/v1", "wrong receipt schema")
    require(row.get("status") == "PASS", "demo did not pass")
    require(type(row.get("model_calls")) is int and row["model_calls"] == 0,
            "this deterministic demo must use zero model calls")
    runtime = row.get("runtime", {})
    require(bool(runtime.get("version")), "runtime version missing")
    require(bool(re.fullmatch(r"[a-f0-9]{64}", runtime.get("engine_sha256", ""))),
            "engine binding missing")
    require(bool(re.fullmatch(r"[a-f0-9]{64}", row.get("commands_sha256", ""))),
            "command log binding missing")
    readers = row.get("readers", [])
    require(len(readers) == 2, "two cold processes required")
    require(all(type(r.get("pid")) is int and r["pid"] > 0 for r in readers), "invalid process ids")
    require(readers[0]["pid"] != readers[1]["pid"], "reader processes must be distinct")
    require(all(r.get("cold_pickup") is True and r.get("unchanged_board_bytes") == 0
                for r in readers), "cold or quiet delivery failed")
    delta = row.get("delta", {})
    require(delta.get("first_bytes", 0) > 0 and delta.get("repeat_bytes") == 0
            and delta.get("contains_next_step") is True, "changed delivery is missing or repeats")
    gate = row.get("gate", {})
    require(gate.get("before_exit") == 1 and gate.get("before_mark") == "pending",
            "broken code must fail and remain pending")
    require(gate.get("after_exit") == 0 and gate.get("after_mark") == "done",
            "fixed code must pass and settle")
    require(gate.get("before_tests_run") == 3 and gate.get("before_failures") == 2
            and gate.get("after_tests_run") == 3, "actual acceptance-test execution missing")
    require(bool(re.fullmatch(r"[a-f0-9]{64}", gate.get("tests_sha256_before", "")))
            and gate["tests_sha256_before"] == gate.get("tests_sha256_after"),
            "acceptance tests changed")
    stale = row.get("stale_write", {})
    require(type(stale.get("exit")) is int and stale["exit"] != 0
            and stale.get("version_before") == stale.get("version_after")
            and stale.get("summary_preserved") is True
            and stale.get("version_conflict_observed") is True, "stale-version rejection missing")
    require(row.get("isolation", {}).get("disposable_home") is True
            and row.get("isolation", {}).get("disposable_project") is True,
            "isolation observations missing")
    require(len(row.get("limits", [])) >= 2, "scope limits missing")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof", type=Path)
    parser.add_argument("--visual-proof", type=Path)
    parser.add_argument("--bundle", type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    for name in REQUIRED_FILES:
        require((here / name).is_file(), "missing pack member " + name)
    diagram = ET.parse(here / "architecture.svg").getroot()
    labels = " ".join(diagram.itertext())
    for label in ("Shared task board", "Work graph", "Source-backed memory", "Evaluation"):
        require(label in labels, "architecture component missing " + label)
    guide = (here / "guide.html").read_text()
    require("10.68%" in guide and "4 paired" in guide and "held" in guide.lower(),
            "evidence scope missing")
    require("https://cdn" not in guide and '<script src="http' not in guide,
            "the interview guide must work offline")
    if args.proof:
        receipt = json.loads(args.proof.read_text())
        validate_receipt(receipt)
        require(receipt.get("demo_sha256") == hashlib.sha256((here / "demo.py").read_bytes()).hexdigest(),
                "receipt belongs to different demo code")
    if args.visual_proof:
        visual = json.loads(args.visual_proof.read_text())
        require(visual.get("status") == "PASS" and visual.get("tabs") == 5
                and visual.get("technical_answers") == 18
                and visual.get("recorded_failure_and_recovery_replay") is True
                and visual.get("keyboard_navigation") is True
                and visual.get("desktop_width") == 1440 and visual.get("mobile_width") == 390
                and visual.get("console_errors") == [], "browser evidence missing or failed")
    if args.bundle:
        with zipfile.ZipFile(args.bundle) as archive:
            sums = archive.read("interview-v3/SHA256SUMS").decode().splitlines()
            require(bool(sums), "bundle has no content manifest")
            for line in sums:
                digest, name = line.split("  ", 1)
                require(Path(name).name == name, "invalid bundle member path")
                content = archive.read("interview-v3/" + name)
                require(hashlib.sha256(content).hexdigest() == digest, "bundle hash mismatch " + name)
                require((here / name).read_bytes() == content, "bundle differs from source " + name)
            require({name.split("  ", 1)[1] for name in sums} == set(REQUIRED_FILES),
                    "bundle lacks required deliverables")
            require(set(archive.namelist()) == {"interview-v3/" + name for name in REQUIRED_FILES}
                    | {"interview-v3/SHA256SUMS"}, "bundle contains unexpected members")
    print("PASS interview pack" + (" and observed demo receipt" if args.proof else " structure"))


if __name__ == "__main__":
    main()
