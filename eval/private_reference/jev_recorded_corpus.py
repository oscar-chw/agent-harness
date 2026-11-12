"""tests for agent_harness.jev — the harness.jev-decision/v1 fail-closed contract.

Plan v3-jev-needle node 5; design docs/v3/jev-decision-records-20261111.md.
Every rule both directions: the intact record passes; each single defect
refuses with its named reason. Includes the REA-expressibility proof (the
Lever pattern-only decision as domain=dependency kind=choice) and the real
H6a retrofit record verified against the live tree.
"""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agent_harness import jev  # noqa: E402
from agent_harness import rea  # noqa: E402

REPO = Path(os.environ.get("HARNESS_RESEARCH_ROOT", Path(__file__).resolve().parents[2]))
REAL_RECORD = REPO / "docs" / "v3" / "jev" / "h6a-l2-candidacy-20261111.json"
REA_RECORD = REPO / "docs" / "v3" / "rea" / "lever-20261105.json"


def fixture(tmp_root):
    """A minimal VALID choice record; tmp_root holds the bound files."""
    with open(os.path.join(tmp_root, "evidence.md"), "wb") as fh:
        fh.write(b"# evidence\n")
    digest = hashlib.sha256(b"# evidence\n").hexdigest()
    with open(os.path.join(tmp_root, "receipt.json"), "wb") as fh:
        fh.write(b"{}")
    return {
        "schema": "harness.jev-decision/v1",
        "record_id": "jev-fixture-1",
        "created": "2026-11-11",
        "subject": {"name": "fixture", "question": "ship the candidate?"},
        "kind": "choice",
        "domain": "adoption",
        "options": ["ship", "hold", "reject"],
        "score_range": None,
        "verdict": "hold",
        "confidence": {"level": "medium", "basis": "two gated runs"},
        "policy": {"execute_at_or_above": "medium", "below": "escalate"},
        "scope": "the frozen fixture corpus only",
        "reversibility": "reversible",
        "authority": "plan fixture node 5 gate",
        "inputs": [{"ref": "evidence.md", "kind": "local-file",
                    "role": "the evidence", "digest": digest}],
        "receipts": ["receipt.json"],
        "unknowns": ["generalization unproven"],
        "links": {},
        "promotion": "NOT_GRANTED",
    }


class TestValidRecord(unittest.TestCase):
    def test_valid_record_validates_and_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = fixture(tmp)
            self.assertIs(jev.validate(record), record)
            self.assertTrue(jev.verify_bindings(record, tmp))

    def test_real_h6a_record_verifies_on_disk(self):
        self.assertTrue(REAL_RECORD.is_file())
        record = jev.verify_record(str(REAL_RECORD), str(REPO))
        self.assertEqual(record["verdict"], "ship-opt-in-default-off")
        self.assertEqual(record["domain"], "adoption")

    def test_boolean_and_score_kinds(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = fixture(tmp)
            record.update({"kind": "boolean", "options": [], "verdict": "YES"})
            self.assertIs(jev.validate(record), record)
            record.update({"kind": "score", "verdict": "0.8",
                           "score_range": {"min": 0.0, "max": 1.0}})
            self.assertIs(jev.validate(record), record)


class TestFailClosedRefusals(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.record = fixture(self.tmp.name)

    def refuse(self, needle):
        with self.assertRaises(jev.JevError) as ctx:
            jev.validate(self.record)
        self.assertIn(needle, str(ctx.exception))

    def test_missing_authority_refused(self):
        self.record["authority"] = "  "
        self.refuse("authority")

    def test_unbound_inputs_refused(self):
        self.record["inputs"] = []
        self.refuse("unbound inputs")

    def test_verdict_outside_enum_refused(self):
        self.record["verdict"] = "ship-it-anyway"
        self.refuse("outside the enum")

    def test_boolean_verdict_outside_enum_refused(self):
        self.record.update({"kind": "boolean", "options": [], "verdict": "MAYBE"})
        self.refuse("outside the enum")

    def test_score_verdict_outside_range_refused(self):
        self.record.update({"kind": "score", "options": [], "verdict": "1.5",
                            "score_range": {"min": 0.0, "max": 1.0}})
        self.refuse("outside the enum")

    def test_score_verdict_unparseable_refused(self):
        self.record.update({"kind": "score", "options": [], "verdict": "high",
                            "score_range": {"min": 0.0, "max": 1.0}})
        self.refuse("outside the enum")

    def test_choice_carries_no_score_range(self):
        self.record["score_range"] = {"min": 0, "max": 1}
        self.refuse("score_range")

    def test_invalid_confidence_level_refused(self):
        self.record["confidence"]["level"] = "very"
        self.refuse("confidence level")

    def test_policy_below_must_escalate(self):
        self.record["policy"]["below"] = "proceed-quietly"
        self.refuse("escalate")

    def test_invalid_reversibility_refused(self):
        self.record["reversibility"] = "maybe"
        self.refuse("reversibility")

    def test_empty_unknowns_refused(self):
        self.record["unknowns"] = []
        self.refuse("unknowns")

    def test_empty_receipts_refused(self):
        self.record["receipts"] = []
        self.refuse("receipt")

    def test_promotion_is_never_granted(self):
        self.record["promotion"] = "GRANTED"
        self.refuse("NOT_GRANTED")

    def test_wrong_schema_refused(self):
        self.record["schema"] = "harness.jev-decision/v0"
        self.refuse("unsupported record schema")

    def test_invalid_domain_refused(self):
        self.record["domain"] = "vibes"
        self.refuse("domain")

    def test_binding_escape_refused(self):
        self.record["inputs"][0]["ref"] = "../outside.md"
        self.refuse("must stay inside the repo")


class TestBindingVerification(unittest.TestCase):
    def test_input_hash_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = fixture(tmp)
            with open(os.path.join(tmp, "evidence.md"), "ab") as fh:
                fh.write(b"drift\n")
            with self.assertRaises(jev.JevError) as ctx:
                jev.verify_bindings(record, tmp)
            self.assertIn("hash mismatch", str(ctx.exception))

    def test_missing_receipt_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = fixture(tmp)
            os.unlink(os.path.join(tmp, "receipt.json"))
            with self.assertRaises(jev.JevError) as ctx:
                jev.verify_bindings(record, tmp)
            self.assertIn("receipt not found", str(ctx.exception))

    def test_verify_record_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = fixture(tmp)
            path = os.path.join(tmp, "record.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(record, fh)
            self.assertEqual(jev.verify_record(path, tmp)["record_id"], "jev-fixture-1")


class TestReaExpressibility(unittest.TestCase):
    def test_rea_lever_decision_as_jev_dependency_choice(self):
        """REA decisions are expressible as a JEV type: the Lever pattern-only
        decision encoded as domain=dependency kind=choice validates, with the
        REA record itself as the bound input (hash-chained consistency)."""
        rea_record = rea.verify_record(str(REA_RECORD), str(REPO))
        self.assertEqual(rea_record["decision"]["type"], "pattern-only")
        with tempfile.TemporaryDirectory() as tmp:
            base = fixture(tmp)
            rea_bytes = REAL_RECORD.read_bytes()
            with open(os.path.join(tmp, "rea-record.json"), "wb") as fh:
                fh.write(rea_bytes)
            base.update({
                "record_id": "jev-rea-lever-20261105",
                "subject": {"name": rea_record["subject"]["name"],
                            "question": "what does the harness do with github/lever?"},
                "domain": "dependency",
                "options": ["reuse", "adapter", "fork", "pattern-only",
                            "independent-build"],
                "verdict": rea_record["decision"]["type"],
                "inputs": [{"ref": "rea-record.json", "kind": "local-file",
                            "role": "the REA record carrying the full evidence",
                            "digest": hashlib.sha256(rea_bytes).hexdigest()}],
                "links": {"rea_record": {
                    "ref": "docs/v3/rea/lever-20261105.json",
                    "sha256": hashlib.sha256(rea_bytes).hexdigest()}},
            })
            self.assertIs(jev.validate(base), base)
            self.assertTrue(jev.verify_bindings(base, tmp))
            self.assertEqual(base["verdict"], "pattern-only")


if __name__ == "__main__":
    unittest.main()
