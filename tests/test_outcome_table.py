"""tests for scripts/build_outcome_table.py — the NEEDLE outcome table generator.

Plan v3-jev-needle node 6; design docs/v3/jev-decision-records-20261111.md §5.
Fixture registries in tmp roots only: the REAL registry's bindings are verified
by the node-6 master check, not here — verdict docs legitimately get dated
amendments (the H4/H6c precedent), and a unit-tier test against live doc bytes
would break unrelated workstreams on every amendment.

Both directions per rule: intact fixture generates all rows; a mutated verdict
doc fails generation; a missing receipt refuses (no silent row-skipping); a
registry dropped below the expected track set is caught; --check passes on
fresh outputs and fails on drifted outputs.
"""
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GENERATOR = REPO / "scripts" / "build_outcome_table.py"

_spec = importlib.util.spec_from_file_location("build_outcome_table", GENERATOR)
bot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bot)


def _write(root, rel, content):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(content)
    return hashlib.sha256(content).hexdigest()


def fixture_root(track_ids=("h1", "h2", "h3a", "h3b", "h4", "h5",
                            "h6a", "h6b", "h6c", "v2-node4")):
    """A tmp root with one bound doc per track and a matching registry."""
    tmp = tempfile.TemporaryDirectory()
    root = tmp.name
    tracks = []
    for tid in track_ids:
        doc_sha = _write(root, "docs/verdict-{}.md".format(tid),
                         ("# verdict {}\n".format(tid)).encode())
        rcpt_sha = _write(root, "work/receipt-{}.json".format(tid), b"{}")
        tracks.append({
            "id": tid, "title": "track " + tid, "plan": "plan/p.md",
            "hypothesis": "h " + tid, "criteria": "c " + tid,
            "key_numbers": [["checks", "1/1"]],
            "verdict": "CONFIRMED",
            "bindings": [
                {"path": "docs/verdict-{}.md".format(tid), "sha256": doc_sha},
                {"path": "work/receipt-{}.json".format(tid), "sha256": rcpt_sha},
            ],
        })
    registry = {"schema": "harness.outcome-tracks/v1", "created": "2026-11-11",
                "note": "fixture", "tracks": tracks}
    registry_path = os.path.join(root, "registry.json")
    with open(registry_path, "w", encoding="utf-8") as fh:
        json.dump(registry, fh)
    return tmp, root, registry_path


def run(argv):
    return bot.main(argv)


class TestGeneration(unittest.TestCase):
    def test_intact_fixture_generates_every_row(self):
        tmp, root, registry = fixture_root()
        self.addCleanup(tmp.cleanup)
        out_md = os.path.join(root, "out.md")
        out_json = os.path.join(root, "out.json")
        rc = run(["--root", root, "--registry", registry,
                  "--out-md", out_md, "--out-json", out_json])
        self.assertEqual(rc, 0)
        table = json.load(open(out_json))
        self.assertEqual([t["id"] for t in table["tracks"]],
                         list(bot.EXPECTED_TRACKS))  # absent rows are impossible
        self.assertEqual(table["schema"], "harness.outcome-table/v1")
        md = open(out_md).read()
        for tid in bot.EXPECTED_TRACKS:
            self.assertIn(tid, md)

    def test_check_mode_passes_on_fresh_outputs(self):
        tmp, root, registry = fixture_root()
        self.addCleanup(tmp.cleanup)
        out_md = os.path.join(root, "out.md")
        out_json = os.path.join(root, "out.json")
        base = ["--root", root, "--registry", registry,
                "--out-md", out_md, "--out-json", out_json]
        self.assertEqual(run(base), 0)
        self.assertEqual(run(base + ["--check"]), 0)

    def test_determinism_byte_identical_regeneration(self):
        tmp, root, registry = fixture_root()
        self.addCleanup(tmp.cleanup)
        out_md = os.path.join(root, "out.md")
        out_json = os.path.join(root, "out.json")
        base = ["--root", root, "--registry", registry,
                "--out-md", out_md, "--out-json", out_json]
        self.assertEqual(run(base), 0)
        first = open(out_md, "rb").read()
        self.assertEqual(run(base), 0)
        self.assertEqual(first, open(out_md, "rb").read())


class TestRefusals(unittest.TestCase):
    def test_mutated_verdict_doc_fails_generation(self):
        tmp, root, registry = fixture_root()
        self.addCleanup(tmp.cleanup)
        with open(os.path.join(root, "docs", "verdict-h4.md"), "ab") as fh:
            fh.write(b"tampered\n")
        rc = run(["--root", root, "--registry", registry,
                  "--out-md", os.path.join(root, "out.md"),
                  "--out-json", os.path.join(root, "out.json")])
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(os.path.join(root, "out.md")))  # all-or-nothing

    def test_missing_receipt_refuses_no_silent_skip(self):
        tmp, root, registry = fixture_root()
        self.addCleanup(tmp.cleanup)
        os.unlink(os.path.join(root, "work", "receipt-h6b.json"))
        rc = run(["--root", root, "--registry", registry,
                  "--out-md", os.path.join(root, "out.md"),
                  "--out-json", os.path.join(root, "out.json")])
        self.assertEqual(rc, 1)

    def test_missing_track_is_caught(self):
        tmp, root, registry = fixture_root()
        self.addCleanup(tmp.cleanup)
        data = json.load(open(registry))
        data["tracks"] = [t for t in data["tracks"] if t["id"] != "h5"]
        with open(registry, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        # dropping a track is not a registry-schema error — it is a row
        # completeness failure at build time
        rc = run(["--root", root, "--registry", registry,
                  "--out-md", os.path.join(root, "out.md"),
                  "--out-json", os.path.join(root, "out.json")])
        self.assertEqual(rc, 1)

    def test_check_mode_fails_on_drifted_output(self):
        tmp, root, registry = fixture_root()
        self.addCleanup(tmp.cleanup)
        out_md = os.path.join(root, "out.md")
        out_json = os.path.join(root, "out.json")
        base = ["--root", root, "--registry", registry,
                "--out-md", out_md, "--out-json", out_json]
        self.assertEqual(run(base), 0)
        with open(out_md, "a", encoding="utf-8") as fh:
            fh.write("hand edit\n")
        self.assertEqual(run(base + ["--check"]), 1)

    def test_registry_with_unbound_track_refused(self):
        tmp, root, registry = fixture_root()
        self.addCleanup(tmp.cleanup)
        data = json.load(open(registry))
        data["tracks"][0]["bindings"] = []
        with open(registry, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        with self.assertRaises(bot.TableError) as ctx:
            bot.load_registry(registry)
        self.assertIn("binds no evidence", str(ctx.exception))

    def test_binding_path_escape_refused(self):
        tmp, root, registry = fixture_root()
        self.addCleanup(tmp.cleanup)
        data = json.load(open(registry))
        data["tracks"][0]["bindings"][0]["path"] = "../outside.md"
        with open(registry, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        with self.assertRaises(bot.TableError) as ctx:
            bot.load_registry(registry)
        self.assertIn("must stay inside the repo", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
