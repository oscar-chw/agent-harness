"""tests for agent_harness.settlement — the harness.settlement-record/v1
fail-closed settlement-hook contract.

Plan v3-settlement-plugin-loop node 5; design
docs/v3/settlement-plugin-loop-design-20261111.md. Fixture plans in tmp
roots with signatures computed by the workgraph's own gate_signature, plus
one live-tree smoke test over the real v3 plans (the perpetual guard: zero
failed actions). Every rule both directions: an intact action settles; each
broken chain fails with its named reason.
"""
import getpass
import json
import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_harness import settlement  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def gate_artifacts(blob, secs=2, ts="2026-11-11T00:00:00Z"):
    """Build (note_line, record_text) for a synthetic gate output, using the
    workgraph's own signature and tail derivation so the fixtures exercise
    the real formats."""
    body = blob.strip() or "(no output)"
    sig = settlement.gate_signature(blob)
    lines = [l.strip() for l in blob.strip().split("\n") if l.strip()]
    tail = " / ".join(lines[-3:])[:400] if lines else "(no output)"
    note = "      {} exit 0 in {}s [{}] — {}".format(ts, secs, sig, tail)
    record = ("# Node 1 — fixture\n\nplan: fixture\ngate: `true`\nctx: (none)\n\n"
              "## Attempt {} — tester@host — {}s — exit 0\n\n```\n{}\n```\n".format(ts, secs, body))
    return note, record


def plan_text(node1_lines, mark1="x", node2=True):
    lines = ["## goal: fixture", ""]
    lines.append("- [{}] 1. done node | gate: true".format(mark1))
    lines.extend(node1_lines)
    if node2:
        lines.append("- [ ] 2. open node | gate: true")
    return "\n".join(lines) + "\n"


class Fixture:
    """A tmp plan tree: plan/fixture.md + plan/fixture/01-*.md."""

    def __init__(self, tc, note=None, record=None, mark1="x", node2=True):
        tc.addCleanup(self._cleanup)
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        (root / "plan" / "fixture").mkdir(parents=True)
        self.plan = root / "plan" / "fixture.md"
        self.plan.write_text(plan_text([note] if note else [], mark1=mark1, node2=node2),
                             encoding="utf-8")
        if record is not None:
            (root / "plan" / "fixture" / "01-done-node.md").write_text(record, encoding="utf-8")

    def _cleanup(self):
        self._tmp.cleanup()

    def scan(self):
        return settlement.scan([str(self.plan)], "2026-11-11")


class SettlementTest(unittest.TestCase):

    def test_intact_action_settles_direct(self):
        note, record = gate_artifacts("tests passed\nall green\n")
        doc = Fixture(self, note, record).scan()
        self.assertEqual(len(doc["records"]), 2)  # one record per node: UNKNOWN is never zero
        rec = doc["records"][0]
        self.assertEqual(rec["status"], "settled")
        self.assertEqual(rec["settled_by"]["verification"], "direct")
        self.assertEqual(rec["expected_receipts"], ["graph-note", "node-record"])
        self.assertEqual(doc["records"][1]["status"], "open")
        counts = settlement.summarize(doc)
        self.assertEqual(counts, {"settled": 1, "open": 1, "failed": 0})

    def test_fabricated_done_without_receipts_fails(self):
        doc = Fixture(self, note=None, record=None, mark1="x").scan()
        rec = doc["records"][0]
        self.assertEqual(rec["status"], "failed")
        self.assertIn("fabricated", rec["detail"])
        self.assertIsNone(rec["settled_by"])

    def test_open_node_is_listed_never_failed(self):
        doc = Fixture(self, mark1=" ", node2=False).scan()
        self.assertEqual(doc["records"][0]["status"], "open")

    def test_missing_record_file_fails(self):
        note, _record = gate_artifacts("ok\n")
        doc = Fixture(self, note, record=None).scan()
        rec = doc["records"][0]
        self.assertEqual(rec["status"], "failed")
        self.assertIn("record file missing", rec["detail"])

    def test_sigless_exit_note_fails_unverifiable(self):
        note = "      2026-11-11T00:00:00Z exit 0 in 2s — tests passed"
        _n, record = gate_artifacts("tests passed\n")
        doc = Fixture(self, note, record).scan()
        rec = doc["records"][0]
        self.assertEqual(rec["status"], "failed")
        self.assertIn("no signature", rec["detail"])

    def test_tampered_body_fails_signature_check(self):
        note, record = gate_artifacts("line one\nline two\nline three\nline four\nline five\n")
        # tamper a line OUTSIDE the last-three-lines tail so only the
        # signature can catch it
        tampered = record.replace("line two", "line two FORGED")
        doc = Fixture(self, note, tampered).scan()
        rec = doc["records"][0]
        self.assertEqual(rec["status"], "failed")
        self.assertIn("signature mismatch", rec["detail"])

    def test_tampered_tail_fails_tail_check(self):
        note, record = gate_artifacts("head\nmiddle\ntail line\n")
        tampered = record.replace("tail line", "forged tail")
        doc = Fixture(self, note, tampered).scan()
        rec = doc["records"][0]
        self.assertEqual(rec["status"], "failed")
        self.assertIn("tail", rec["detail"])

    def test_newer_applied_failure_under_done_mark_fails(self):
        note, record = gate_artifacts("ok\n")
        later = "      2026-11-11T01:00:00Z exit 1 in 3s [deadbeef] — boom failed"
        doc = Fixture(self, None, record)
        doc.plan.write_text(plan_text([note, later]), encoding="utf-8")
        rec = doc.scan()["records"][0]
        self.assertEqual(rec["status"], "failed")
        self.assertIn("newer applied failure", rec["detail"])

    def test_reclaim_note_after_success_is_benign(self):
        note, record = gate_artifacts("ok\n")
        reclaim = ("      2026-11-11T01:00:00Z gate ran to exit 1 in 3s but the node "
                   "had been re-claimed by other — result NOT applied")
        doc = Fixture(self, None, record)
        doc.plan.write_text(plan_text([note, reclaim]), encoding="utf-8")
        self.assertEqual(doc.scan()["records"][0]["status"], "settled")

    def test_secs_mismatch_fails(self):
        note, record = gate_artifacts("ok\n", secs=2)
        record = record.replace("— 2s —", "— 9s —")
        doc = Fixture(self, note, record).scan()
        rec = doc["records"][0]
        self.assertEqual(rec["status"], "failed")
        self.assertIn("duration mismatch", rec["detail"])

    def test_no_applied_attempt_fails(self):
        note, record = gate_artifacts("ok\n")
        record = record.replace("exit 0", "exit 0 (NOT APPLIED: node was re-claimed)")
        doc = Fixture(self, note, record).scan()
        rec = doc["records"][0]
        self.assertEqual(rec["status"], "failed")
        self.assertIn("no applied gate attempt", rec["detail"])

    def test_inverse_redaction_settles_post_signing_hygiene_redaction(self):
        home = os.path.expanduser("~")
        blob = "receipt: {}/runs/run-1.json\nverdict: OK\n".format(home)
        sig = settlement.gate_signature(blob)
        body = blob.strip().replace(home, "/Users/me")  # post-gate sed redaction
        lines = [l.strip() for l in body.split("\n") if l.strip()]
        tail = " / ".join(lines[-3:])[:400]
        note = "      2026-11-11T00:00:00Z exit 0 in 2s [{}] — {}".format(sig, tail)
        record = ("# Node 1 — fixture\n\nplan: fixture\ngate: `true`\nctx: (none)\n\n"
                  "## Attempt 2026-11-11T00:00:00Z — agent@redacted-host — 2s — exit 0"
                  "\n\n```\n{}\n```\n".format(body))
        doc = Fixture(self, note, record).scan()
        rec = doc["records"][0]
        self.assertEqual(rec["status"], "settled")
        self.assertEqual(rec["settled_by"]["verification"], "inverse-redacted")
        self.assertEqual(settlement._inverse_redact("agent@"), getpass.getuser() + "@")
        self.assertEqual(settlement._inverse_redact("redacted-host"), socket.gethostname())

    def test_empty_scan_refuses(self):
        with self.assertRaises(settlement.SettlementError):
            settlement.scan([], "2026-11-11")

    def test_unrecognized_mark_fails_closed(self):
        with self.assertRaises(settlement.SettlementError):
            settlement.parse_plan("- [~] 1. weird node | gate: true\n")

    def test_missing_plan_file_fails_closed(self):
        with self.assertRaises(settlement.SettlementError):
            settlement.scan_plan("/nonexistent/plan/nope.md")

    def test_document_schema_and_serialisation(self):
        note, record = gate_artifacts("ok\n")
        doc = Fixture(self, note, record).scan()
        self.assertEqual(doc["schema"], "harness.settlement-record/v1")
        parsed = json.loads(settlement.dumps(doc))
        self.assertEqual(parsed["checked_at"], "2026-11-11")
        self.assertEqual(len(parsed["records"]), 2)



if __name__ == "__main__":
    unittest.main()
