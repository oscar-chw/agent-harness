"""Regression coverage for exact qualification and positive admission decisions."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from agent_harness import plugin_loop
from tests.test_plugin_loop import ROOT, LoopFixture, _sha


class CapabilityBindingTest(unittest.TestCase):
    def test_hold_is_recorded_as_refused_even_when_the_candidate_selects_it(self):
        fx = LoopFixture(self, verdict="hold", admit_verdict="hold")
        path = fx.root / "candidate.json"
        path.write_text(json.dumps(fx.candidate))
        result = subprocess.run([sys.executable, str(ROOT / "scripts/admit_capability.py"),
                                 "--root", str(fx.root), "--candidate", path.name,
                                 "--registry", "registry.json"],
                                capture_output=True, text=True, timeout=15)
        registry = plugin_loop.load_registry(str(fx.root / "registry.json"))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual([(row["status"], row["verdict"], row["promotion"])
                          for row in registry["entries"]], [("refused", "hold", "NOT_GRANTED")])

    def test_reject_cannot_be_the_admitting_verdict(self):
        fx = LoopFixture(self, verdict="reject", admit_verdict="reject")
        self.assertEqual(fx.admit()["status"], "refused")

    def test_decision_without_binding_to_qualification_refuses(self):
        fx = LoopFixture(self)
        decision = json.loads(fx.jev_path.read_text())
        decision["inputs"] = decision["inputs"][1:]
        fx.jev_path.write_text(json.dumps(decision))
        fx.refresh_candidate()
        entry = fx.admit()
        self.assertEqual(entry["status"], "refused")
        self.assertIn("qualification", entry["detail"])

    def test_decision_for_another_valid_qualification_refuses(self):
        fx = LoopFixture(self)
        other = fx.root / "docs" / "other-rea.json"
        qualification = json.loads(fx.rea_path.read_text())
        qualification["record_id"] = "rea-another-qualification"
        other.write_text(json.dumps(qualification))
        fx.candidate["rea"] = {"ref": "docs/other-rea.json", "sha256": _sha(other)}
        entry = fx.admit()
        self.assertEqual(entry["status"], "refused")
        self.assertIn("qualification", entry["detail"])

    def test_decision_is_validated_from_the_same_bytes_that_were_hashed(self):
        fx = LoopFixture(self)
        with patch("builtins.open", wraps=open) as opened:
            self.assertEqual(fx.admit()["status"], "admitted")
        reads = [call for call in opened.call_args_list if Path(call.args[0]) == fx.jev_path.resolve()]
        self.assertEqual(len(reads), 1)

    def test_pattern_only_decision_admits_original_kind_only(self):
        fx = LoopFixture(self, verdict="adopt-pattern-only", admit_verdict="adopt-pattern-only")
        record = json.loads(fx.jev_path.read_text())
        record["options"][0] = "adopt-pattern-only"
        fx.jev_path.write_text(json.dumps(record))
        fx.refresh_candidate()
        self.assertEqual(fx.admit()["status"], "admitted")
        fx.candidate["kind"] = "skill"
        self.assertEqual(fx.admit()["status"], "refused")
