"""tests for agent_harness.rea — the harness.rea-record/v1 fail-closed contract.

Plan v3-rea-support node 5; design docs/v3/rea-support-design-20261111.md.
Every rule is tested in both directions: the intact record passes, and each
single introduced defect refuses with its named reason.
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_harness import rea  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
REAL_RECORD = REPO / "docs" / "v3" / "rea" / "lever-20261105.json"
DOC_SHA = "6bcb18ea3241f3f9d94c0043f03debb4ba3810e38f8ab60be5ddb41caa51d852"


def fixture(tmp_root):
    """A minimal VALID record; tmp_root holds the one bound local file."""
    doc = os.path.join(tmp_root, "notes.md")
    with open(doc, "wb") as fh:
        fh.write(b"# reading note\n")
    digest = hashlib.sha256(b"# reading note\n").hexdigest()
    os.makedirs(os.path.join(tmp_root, "plan"), exist_ok=True)
    with open(os.path.join(tmp_root, "plan", "p.md"), "wb") as fh:
        fh.write(b"# plan\n")
    return {
        "schema": "harness.rea-record/v1",
        "record_id": "rea-fixture-1",
        "created": "2026-11-11",
        "subject": {
            "name": "up/stream",
            "source_locator": "https://example.invalid/up/stream",
            "version_pin": "abc1234",
            "version_label": "pinned commit abc1234",
        },
        "license": {
            "spdx": "MIT",
            "holder": "Example",
            "evidence": {"url": None, "doc_ref": None, "doc_sha256": None,
                         "file_sha256": "b" * 64},
        },
        "lawfulness": {"basis": "public license-bearing repository, owner-authorized reading"},
        "reading_scope": {"read": ["README"], "not_read": ["runtime behavior"]},
        "evidence_bindings": [
            {"ref": "notes.md", "kind": "local-file", "role": "reading note",
             "digest": digest},
            {"ref": "upstream:up/stream@abc1234", "kind": "upstream-pin",
             "role": "analyzed source", "digest": "abc1234"},
        ],
        "claims": [
            {"id": "c1", "statement": "The README documents a router.",
             "basis": "observed", "observation_class": "documented", "reasoning": None,
             "evidence": [{"ref": "notes.md", "sha256": digest, "note": "README section"}],
             "covers": []},
            {"id": "c2", "statement": "The pattern probably transfers.",
             "basis": "inferred", "observation_class": None,
             "reasoning": "prompt-level procedure, not code", "evidence": [],
             "covers": []},
        ],
        "unknowns": ["runtime behavior unexercised"],
        "decision": {"type": "pattern-only", "summary": "Adapt the pattern locally.",
                     "evidence": ["c1"], "paraphrase_only": True, "code_copied": False},
        "integration": {"referenced_by": ["plan/p.md"]},
        "promotion": "NOT_GRANTED",
    }


class TestValidRecord(unittest.TestCase):
    def test_valid_record_validates_and_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = fixture(tmp)
            self.assertIs(rea.validate(record), record)
            self.assertTrue(rea.verify_bindings(record, tmp))

    def test_real_example_record_valid(self):
        """The Lever retroactive record stays continuously verified by CI."""
        self.assertTrue(REAL_RECORD.is_file())
        record = rea.verify_record(str(REAL_RECORD), str(REPO))
        self.assertEqual(record["decision"]["type"], "pattern-only")


class TestIntakeRefusals(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.record = fixture(self.tmp.name)

    def refuse(self, needle):
        with self.assertRaises(rea.ReaError) as ctx:
            rea.validate(self.record)
        self.assertIn(needle, str(ctx.exception))

    def test_missing_license_spdx_refused(self):
        self.record["license"]["spdx"] = ""
        self.refuse("license spdx")

    def test_missing_license_holder_refused(self):
        del self.record["license"]["holder"]
        self.refuse("license")

    def test_license_evidence_needs_one_real_form(self):
        self.record["license"]["evidence"] = {"url": None, "doc_ref": None,
                                              "doc_sha256": None, "file_sha256": None}
        self.refuse("license evidence")

    def test_unpinned_source_refused(self):
        self.record["subject"]["version_pin"] = ""
        self.refuse("unpinned source version")

    def test_latest_is_not_a_pin(self):
        self.record["subject"]["version_pin"] = "latest"
        self.refuse("unpinned source version")

    def test_no_bindings_refused_as_unhash_bound(self):
        self.record["evidence_bindings"] = []
        self.refuse("unhash-bound source")

    def test_missing_lawfulness_refused(self):
        self.record["lawfulness"]["basis"] = " "
        self.refuse("lawfulness basis")

    def test_empty_reading_scope_refused(self):
        self.record["reading_scope"]["read"] = []
        self.refuse("reading scope read")


class TestClaimDiscipline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.record = fixture(self.tmp.name)

    def refuse(self, needle):
        with self.assertRaises(rea.ReaError) as ctx:
            rea.validate(self.record)
        self.assertIn(needle, str(ctx.exception))

    def test_inference_presented_as_observed_refused(self):
        # flip the inferred claim to observed WITHOUT adding bound evidence
        self.record["claims"][1]["basis"] = "observed"
        self.record["claims"][1]["observation_class"] = "documented"
        self.record["claims"][1]["reasoning"] = None
        self.refuse("inference presented as observed")

    def test_observed_claim_with_unbound_evidence_refused(self):
        self.record["claims"][0]["evidence"][0]["sha256"] = "c" * 64
        self.refuse("inference presented as observed")

    def test_observed_claim_needs_observation_class(self):
        self.record["claims"][0]["observation_class"] = None
        self.refuse("observation class")

    def test_inferred_claim_may_not_claim_observation_class(self):
        self.record["claims"][1]["observation_class"] = "measured"
        self.refuse("may not claim an observation class")

    def test_inferred_claim_carries_no_evidence(self):
        digest = self.record["evidence_bindings"][0]["digest"]
        self.record["claims"][1]["evidence"] = [
            {"ref": "notes.md", "sha256": digest, "note": "x"}]
        self.refuse("only observed claims bind evidence")

    def test_empty_unknowns_refused(self):
        self.record["unknowns"] = []
        self.refuse("unknowns")

    def test_duplicate_claim_id_refused(self):
        self.record["claims"].append(deepcopy(self.record["claims"][0]))
        self.refuse("duplicate claim id")

    def test_duplicate_binding_ref_refused(self):
        self.record["evidence_bindings"].append(
            deepcopy(self.record["evidence_bindings"][0]))
        self.refuse("duplicate binding ref")

    def test_binding_escape_refused(self):
        self.record["evidence_bindings"][0]["ref"] = "../outside.md"
        self.refuse("must stay inside the repo")


class TestDecisionRequirements(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.record = fixture(self.tmp.name)

    def refuse(self, needle):
        with self.assertRaises(rea.ReaError) as ctx:
            rea.validate(self.record)
        self.assertIn(needle, str(ctx.exception))

    def test_pattern_only_requires_no_copied_code(self):
        self.record["decision"]["code_copied"] = True
        self.refuse("code_copied")

    def test_reuse_requires_used_surface_coverage(self):
        self.record["decision"] = {
            "type": "reuse", "summary": "use it", "evidence": ["c1"],
            "license_compatible": True, "used_surface": ["router"],
            "integration_cost": "small"}
        self.refuse("used surface element")

    def test_reuse_passes_with_source_observed_coverage(self):
        self.record["claims"][0]["observation_class"] = "source-observed"
        self.record["claims"][0]["covers"] = ["router"]
        self.record["decision"] = {
            "type": "reuse", "summary": "use it", "evidence": ["c1"],
            "license_compatible": True, "used_surface": ["router"],
            "integration_cost": "small"}
        self.assertIs(rea.validate(self.record), self.record)

    def test_documented_alone_does_not_cover_reuse_surface(self):
        self.record["claims"][0]["covers"] = ["router"]  # class stays "documented"
        self.record["decision"] = {
            "type": "reuse", "summary": "use it", "evidence": ["c1"],
            "license_compatible": True, "used_surface": ["router"],
            "integration_cost": "small"}
        self.refuse("used surface element")

    def test_adapter_requires_boundary_map(self):
        self.record["claims"][0]["observation_class"] = "source-observed"
        self.record["claims"][0]["covers"] = ["router"]
        self.record["decision"] = {
            "type": "adapter", "summary": "wrap it", "evidence": ["c1"],
            "license_compatible": True, "used_surface": ["router"],
            "integration_cost": "small", "boundary_map": []}
        self.refuse("boundary map")

    def test_fork_requires_maintenance_budget(self):
        self.record["decision"] = {
            "type": "fork", "summary": "fork it", "evidence": ["c1"],
            "license_permits_fork": True, "fork_reason": "upstream stalled",
            "maintenance_budget": ""}
        self.refuse("maintenance budget")

    def test_independent_build_requires_prior_exposure(self):
        self.record["decision"] = {
            "type": "independent-build", "summary": "build our own",
            "evidence": ["c1"], "prior_exposure": "", "rationale": "small design space"}
        self.refuse("prior exposure")

    def test_decision_citing_unknown_claim_refused(self):
        self.record["decision"]["evidence"] = ["c9"]
        self.refuse("unknown claim id")

    def test_promotion_is_never_granted(self):
        self.record["promotion"] = "GRANTED"
        self.refuse("NOT_GRANTED")

    def test_wrong_schema_refused(self):
        self.record["schema"] = "harness.rea-record/v0"
        self.refuse("unsupported record schema")


class TestBindingVerification(unittest.TestCase):
    def test_hash_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = fixture(tmp)
            with open(os.path.join(tmp, "notes.md"), "ab") as fh:
                fh.write(b"tampered\n")
            with self.assertRaises(rea.ReaError) as ctx:
                rea.verify_bindings(record, tmp)
            self.assertIn("hash mismatch", str(ctx.exception))

    def test_missing_bound_file_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = fixture(tmp)
            os.unlink(os.path.join(tmp, "notes.md"))
            with self.assertRaises(rea.ReaError) as ctx:
                rea.verify_bindings(record, tmp)
            self.assertIn("not found on disk", str(ctx.exception))

    def test_missing_referenced_plan_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = fixture(tmp)
            shutil.rmtree(os.path.join(tmp, "plan"))
            with self.assertRaises(rea.ReaError) as ctx:
                rea.verify_bindings(record, tmp)
            self.assertIn("referenced_by", str(ctx.exception))

    def test_verify_record_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = fixture(tmp)
            path = os.path.join(tmp, "record.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(record, fh)
            self.assertEqual(rea.verify_record(path, tmp)["record_id"], "rea-fixture-1")


if __name__ == "__main__":
    unittest.main()
