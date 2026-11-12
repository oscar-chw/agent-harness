"""tests for agent_harness.plugin_loop — the fail-closed plugin admission loop.

Plan v3-settlement-plugin-loop node 6; design
docs/v3/settlement-plugin-loop-design-20261111.md. Fixture REA/JEV records
in tmp roots (validated by the real rea/jev modules), plus one live-tree
test re-running the real Lever candidate against the repo. Every stage both
directions: intact admits with full receipts; no REA record refuses; no JEV
adoption decision refuses; below-threshold confidence escalates and never
auto-admits; drifted bytes refuse.
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_harness import plugin_loop  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LEVER_CANDIDATE = ROOT / "docs" / "v3" / "plugin-candidates" / "lever-pattern-20261111.json"
LEVER_REGISTRY = ROOT / "docs" / "v3" / "plugin-registry-20261111.json"


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class LoopFixture:
    """A tmp root holding a minimal but VALID REA record, JEV record and
    candidate descriptor (all three validated by the real modules)."""

    def __init__(self, tc, verdict="adopt", level="high", threshold="medium",
                 domain="adoption", jev_name="fixture-cap", admit_verdict="adopt"):
        tc.addCleanup(self._cleanup)
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "docs").mkdir()
        evidence = self.root / "docs" / "evidence.md"
        evidence.write_text("pinned reading note\n", encoding="utf-8")
        receipt = self.root / "docs" / "receipt.json"
        receipt.write_text("{}\n", encoding="utf-8")
        digest = _sha(evidence)

        self.rea_path = self.root / "docs" / "rea.json"
        rea_record = {
            "schema": "harness.rea-record/v1",
            "record_id": "rea-fixture-20261111",
            "created": "2026-11-11",
            "subject": {"name": "fixture-upstream",
                        "source_locator": "https://example.invalid/fixture",
                        "version_pin": "abc1234", "version_label": "fixture pin"},
            "license": {"spdx": "MIT", "holder": "Fixture Holder",
                        "evidence": {"url": "https://example.invalid/fixture/LICENSE",
                                     "doc_ref": "docs/evidence.md",
                                     "doc_sha256": digest, "file_sha256": None}},
            "lawfulness": {"basis": "public license-bearing fixture; owner-authorized"},
            "reading_scope": {"read": ["pinned README"], "not_read": ["runtime behavior"]},
            "evidence_bindings": [
                {"ref": "docs/evidence.md", "kind": "local-file",
                 "role": "reading note", "digest": digest},
                {"ref": "upstream:fixture@abc1234", "kind": "upstream-pin",
                 "role": "source pin", "digest": "abc1234"}],
            "claims": [{"id": "c1", "statement": "a documented fixture claim",
                        "basis": "observed", "observation_class": "documented",
                        "reasoning": None,
                        "evidence": [{"ref": "docs/evidence.md", "sha256": digest,
                                      "note": "D: README paragraph"}],
                        "covers": []}],
            "unknowns": ["runtime behavior unexercised"],
            "decision": {"type": "pattern-only", "summary": "adapt the pattern only",
                         "evidence": ["c1"], "paraphrase_only": True,
                         "code_copied": False},
            "integration": {"referenced_by": []},
            "promotion": "NOT_GRANTED"}
        self.rea_path.write_text(json.dumps(rea_record, indent=2) + "\n", encoding="utf-8")

        self.jev_path = self.root / "docs" / "jev.json"
        jev_record = {
            "schema": "harness.jev-decision/v1",
            "record_id": "jev-fixture-20261111",
            "created": "2026-11-11",
            "subject": {"name": jev_name,
                        "question": "Adopt the fixture capability?"},
            "kind": "choice", "domain": domain,
            "options": ["adopt", "hold", "reject"], "score_range": None,
            "verdict": verdict,
            "confidence": {"level": level, "basis": "fixture evidence verified"},
            "policy": {"execute_at_or_above": threshold, "below": "escalate"},
            "scope": "repo-local fixture", "reversibility": "reversible",
            "authority": "fixture gate, plan v3-settlement-plugin-loop tests",
            "inputs": [{"ref": "docs/evidence.md", "kind": "local-file",
                        "role": "the qualification evidence", "digest": digest}],
            "receipts": ["docs/receipt.json"],
            "unknowns": ["fixture unknown"],
            "links": {}, "promotion": "NOT_GRANTED"}
        self.jev_path.write_text(json.dumps(jev_record, indent=2) + "\n", encoding="utf-8")

        self.candidate = {
            "schema": "harness.plugin-candidate/v1",
            "name": "fixture-cap", "kind": "pattern",
            "rea": {"ref": "docs/rea.json", "sha256": _sha(self.rea_path)},
            "jev": {"ref": "docs/jev.json", "sha256": _sha(self.jev_path)},
            "admit_verdict": admit_verdict}

    def _cleanup(self):
        self._tmp.cleanup()

    def refresh_candidate(self):
        """Re-bind after mutating a record on disk (the honest amendment path)."""
        self.candidate["rea"]["sha256"] = _sha(self.rea_path)
        self.candidate["jev"]["sha256"] = _sha(self.jev_path)

    def admit(self):
        return plugin_loop.admit(self.candidate, str(self.root), "2026-11-11")


class PluginLoopTest(unittest.TestCase):

    def test_intact_pipeline_admits_with_full_receipts(self):
        fx = LoopFixture(self)
        entry = fx.admit()
        self.assertEqual(entry["status"], "admitted")
        self.assertEqual(entry["verdict"], "adopt")
        self.assertEqual(entry["confidence"], "high")
        self.assertEqual(entry["rea"]["sha256"], _sha(fx.rea_path))
        self.assertEqual(entry["jev"]["sha256"], _sha(fx.jev_path))
        self.assertEqual(entry["promotion"], "NOT_GRANTED")
        self.assertEqual(entry["schema"], "harness.plugin-admission/v1")
        self.assertEqual(entry["admitted_at"], "2026-11-11")

    def test_malformed_candidate_raises(self):
        with self.assertRaises(plugin_loop.PluginLoopError):
            plugin_loop.validate_candidate({"schema": "harness.plugin-candidate/v1"})

    def test_admission_without_rea_record_refuses(self):
        fx = LoopFixture(self)
        fx.rea_path.unlink()
        entry = fx.admit()
        self.assertEqual(entry["status"], "refused")
        self.assertIn("qualification refused", entry["detail"])

    def test_rea_hash_drift_refuses(self):
        fx = LoopFixture(self)
        with open(fx.rea_path, "a", encoding="utf-8") as fh:
            fh.write("\n")
        entry = fx.admit()  # candidate still binds the pre-drift bytes
        self.assertEqual(entry["status"], "refused")
        self.assertIn("hash drift", entry["detail"])

    def test_rea_internally_invalid_refuses(self):
        fx = LoopFixture(self)
        record = json.loads(fx.rea_path.read_text(encoding="utf-8"))
        record["unknowns"] = []  # UNKNOWN is never zero
        fx.rea_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        fx.refresh_candidate()  # bytes match; the RECORD is invalid
        entry = fx.admit()
        self.assertEqual(entry["status"], "refused")
        self.assertIn("qualification refused", entry["detail"])

    def test_admission_without_jev_decision_refuses(self):
        fx = LoopFixture(self)
        fx.jev_path.unlink()
        entry = fx.admit()
        self.assertEqual(entry["status"], "refused")
        self.assertIn("typed decision refused", entry["detail"])

    def test_jev_wrong_domain_refuses(self):
        fx = LoopFixture(self, domain="hypothesis")
        fx.refresh_candidate()
        entry = fx.admit()
        self.assertEqual(entry["status"], "refused")
        self.assertIn("adoption", entry["detail"])

    def test_jev_subject_mismatch_refuses(self):
        fx = LoopFixture(self, jev_name="some-other-capability")
        fx.refresh_candidate()
        entry = fx.admit()
        self.assertEqual(entry["status"], "refused")
        self.assertIn("not this capability", entry["detail"])

    def test_verdict_mismatch_refuses(self):
        fx = LoopFixture(self, verdict="hold")
        fx.refresh_candidate()
        entry = fx.admit()
        self.assertEqual(entry["status"], "refused")
        self.assertIn("not the admitting verdict", entry["detail"])

    def test_below_threshold_escalates_never_admits(self):
        fx = LoopFixture(self, level="low", threshold="medium")
        fx.refresh_candidate()
        entry = fx.admit()
        self.assertEqual(entry["status"], "refused")
        self.assertIn("ESCALATED", entry["detail"])
        self.assertIn("never auto-admitted", entry["detail"])
        self.assertIsNone(entry["admitted_at"])

    def test_threshold_equality_admits(self):
        fx = LoopFixture(self, level="medium", threshold="medium")
        fx.refresh_candidate()
        self.assertEqual(fx.admit()["status"], "admitted")

    def test_registry_round_trip_and_duplicate_rules(self):
        fx = LoopFixture(self)
        entry = fx.admit()
        registry = plugin_loop.load_registry(str(fx.root / "registry.json"))
        registry, appended = plugin_loop.append_entry(registry, entry)
        self.assertTrue(appended)
        path = fx.root / "registry.json"
        plugin_loop.write_registry(str(path), registry)
        loaded = plugin_loop.load_registry(str(path))
        self.assertEqual(loaded["schema"], "harness.plugin-registry/v1")
        self.assertEqual(len(loaded["entries"]), 1)
        # identical re-admission is idempotent (gates re-run)
        _registry, again = plugin_loop.append_entry(loaded, entry)
        self.assertFalse(again)
        # a changed binding under the same name refuses
        changed = dict(entry, rea={"ref": "docs/rea.json", "sha256": "0" * 64})
        with self.assertRaises(plugin_loop.PluginLoopError):
            plugin_loop.append_entry(loaded, changed)

    def test_malformed_registry_raises(self):
        fx = LoopFixture(self)
        bad = fx.root / "bad.json"
        bad.write_text('{"schema": "something-else"}\n', encoding="utf-8")
        with self.assertRaises(plugin_loop.PluginLoopError):
            plugin_loop.load_registry(str(bad))

    def test_real_lever_candidate_admits_against_live_tree(self):
        """The retroactive example: the Lever pattern capability, REA-qualified
        by docs/v3/rea/lever-20261105.json, decided by
        docs/v3/jev/lever-pattern-adoption-20261111.json."""
        candidate = json.loads(LEVER_CANDIDATE.read_text(encoding="utf-8"))
        entry = plugin_loop.admit(candidate, str(ROOT), "2026-11-11")
        self.assertEqual(entry["status"], "admitted")
        self.assertEqual(entry["name"], "lever-experiment-contract-pattern")
        registry = plugin_loop.load_registry(str(LEVER_REGISTRY))
        matches = [e for e in registry["entries"]
                   if e["name"] == "lever-experiment-contract-pattern"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["status"], "admitted")
        self.assertEqual(matches[0]["rea"]["sha256"], entry["rea"]["sha256"])
        self.assertEqual(matches[0]["jev"]["sha256"], entry["jev"]["sha256"])


if __name__ == "__main__":
    unittest.main()
