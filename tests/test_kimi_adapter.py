"""Kimi Code adapter: shared harness access without changing other Kimi settings."""
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_harness import installer as I  # noqa: E402
from agent_harness.adapters import all_adapters  # noqa: E402
from agent_harness.adapters.base import Ctx  # noqa: E402

RULES = "# Rules\n\nUse the shared harness.\n"


class KimiAdapterTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.hh = self.home / ".agent-harness"
        self.content = self.hh / "content"
        skill = self.content / "skills" / "demo"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: demo\ndescription: Demo\n---\n")
        (self.content / "routing.toml").write_text(
            'efforts = ["low", "high"]\nceiling = "high"\n'
            '[tiers.deep]\nwhen = "hard work"\nbrief = "Check it."\neffort = "high"\n')
        self.cmd = ["python3", str(self.hh / "lib" / "agent_harness" / "mcp" / "server.py")]
        self.env = mock.patch.dict(os.environ, {"PATH": str(self.bin)})
        self.env.start()
        os.environ.pop("KIMI_CODE_HOME", None)
        self.addCleanup(self.env.stop)
        self.addCleanup(self._tmp.cleanup)

    def ctx(self, project=None):
        return Ctx(home=self.home, harness_home=self.hh, content=self.content, profile={},
                   rules=RULES, mcp_cmd=self.cmd, scope="project" if project else "user", project=project)

    def adapter(self):
        adapters = all_adapters()
        self.assertIn("kimi", adapters)
        return adapters["kimi"]

    def by_path(self, changes):
        for change in changes:
            self.assertTrue(change.path.is_absolute())
            self.assertTrue(str(change.path).startswith(str(self.root)), change.path)
            self.assertTrue(change.note)
        return {change.path: change for change in changes}

    def test_registry_detects_kimi_without_changing_existing_order(self):
        names = list(all_adapters())
        self.assertIn("kimi", names)
        self.assertEqual([name for name in names if name != "kimi"],
                         ["claude-code", "codex", "copilot-vscode", "cursor", "gemini", "agents-md",
                          "claude-desktop", "jupyter-ai"])
        self.assertEqual(len(names), len(set(names)))

    def test_user_plan_shares_rules_mcp_skills_hooks_and_tiers(self):
        kimi = self.home / ".kimi-code"
        kimi.mkdir()
        (kimi / "mcp.json").write_text(json.dumps({
            "mcpServers": {"other": {"command": "other-server"}}, "userKey": {"keep": True}}))
        changes = self.by_path(self.adapter().plan(self.ctx()))
        self.assertEqual(changes[kimi / "AGENTS.md"].content, RULES)
        mcp = changes[kimi / "mcp.json"]
        self.assertEqual(mcp.kind, "merge-json")
        self.assertEqual(set(mcp.content["mcpServers"]), {"other", "harness"})
        self.assertEqual(mcp.content["mcpServers"]["harness"],
                         {"command": "python3", "args": self.cmd[1:]})
        self.assertNotIn("type", mcp.content["mcpServers"]["harness"])
        self.assertNotIn("userKey", mcp.content)
        self.assertIn(self.home / ".agents" / "skills" / "demo", changes)
        config = changes[kimi / "config.toml"]
        self.assertEqual(config.kind, "merge-toml")
        self.assertTrue(any(hook["event"] == "PreToolUse" for hook in config.content["+"]["hooks"]))
        self.assertIn(kimi / "agents" / "harness-deep.md", changes)
        self.assertNotIn(kimi / "settings.json", changes)

    def test_project_plan_uses_kimi_project_files(self):
        project = self.root / "project"
        project.mkdir()
        changes = self.by_path(self.adapter().plan(self.ctx(project)))
        self.assertEqual(changes[project / ".kimi-code" / "AGENTS.md"].content, RULES)
        self.assertIn(project / ".kimi-code" / "mcp.json", changes)
        self.assertIn(project / ".agents" / "skills" / "demo", changes)
        self.assertNotIn(self.home / ".kimi-code" / "mcp.json", changes)

    def test_kimi_code_home_moves_user_config_but_not_shared_skills(self):
        custom = self.root / "custom-kimi"
        custom.mkdir()
        with mock.patch.dict(os.environ, {"KIMI_CODE_HOME": str(custom)}):
            changes = self.by_path(self.adapter().plan(self.ctx()))
            self.assertIn(custom / "AGENTS.md", changes)
            self.assertIn(custom / "mcp.json", changes)
            self.assertTrue(self.adapter().detect(self.ctx()))
        self.assertIn(self.home / ".agents" / "skills" / "demo", changes)
        self.assertNotIn(self.home / ".kimi-code" / "mcp.json", changes)

    def test_invalid_mcp_json_is_refused_not_replaced(self):
        kimi = self.home / ".kimi-code"
        kimi.mkdir()
        bad = "{not json"
        path = kimi / "mcp.json"
        path.write_text(bad)
        adapter = self.adapter()
        changes = self.by_path(adapter.plan(self.ctx()))
        self.assertNotIn(path, changes)
        self.assertTrue(any("refused" in note and str(path) in note for note in adapter.notes(self.ctx())))
        self.assertEqual(path.read_text(), bad)

    def test_detects_cli_or_default_config_directory(self):
        adapter = self.adapter()
        self.assertFalse(adapter.detect(self.ctx()))
        executable = self.bin / "kimi"
        executable.write_text("#!/bin/sh\n")
        executable.chmod(executable.stat().st_mode | stat.S_IEXEC)
        self.assertTrue(adapter.detect(self.ctx()))
        executable.unlink()
        self.assertFalse(adapter.detect(self.ctx()))
        (self.home / ".kimi-code").mkdir()
        self.assertTrue(adapter.detect(self.ctx()))

    def test_existing_connection_options_survive_reinstall(self):
        kimi = self.home / ".kimi-code"
        kimi.mkdir()
        project = self.root / "project"
        project.mkdir()
        (kimi / "mcp.json").write_text(json.dumps({"mcpServers": {"harness": {
            "command": "old", "args": ["old"], "cwd": str(project), "enabled": False,
            "env": {"CUSTOM_SETTING": "keep"}}}}))
        changes = self.by_path(self.adapter().plan(self.ctx()))
        harness = changes[kimi / "mcp.json"].content["mcpServers"]["harness"]
        self.assertEqual(harness["command"], "python3")
        self.assertEqual(harness["args"], self.cmd[1:])
        self.assertEqual(harness["cwd"], str(project))
        self.assertIs(harness["enabled"], False)
        self.assertEqual(harness["env"]["CUSTOM_SETTING"], "keep")

    def test_install_and_uninstall_restore_existing_kimi_files(self):
        kimi = self.home / ".kimi-code"
        kimi.mkdir()
        rules = kimi / "AGENTS.md"
        mcp = kimi / "mcp.json"
        rules.write_text("my own rules\n")
        mcp.write_text('{"mcpServers":{"other":{"command":"other-server"}}}\n')
        changes = self.adapter().plan(self.ctx())
        state = I.apply(self.hh, [("kimi", changes)], {}, [self.home])
        I.save_state(self.hh, state)
        configured = json.loads(mcp.read_text())
        self.assertEqual(set(configured["mcpServers"]), {"other", "harness"})
        self.assertEqual(rules.read_text(), RULES)
        I.uninstall(self.hh, lambda _line: None)
        self.assertEqual(rules.read_text(), "my own rules\n")
        self.assertEqual(mcp.read_text(), '{"mcpServers":{"other":{"command":"other-server"}}}\n')


if __name__ == "__main__":
    unittest.main()
