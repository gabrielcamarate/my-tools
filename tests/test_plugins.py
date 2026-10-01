"""Exercise plugin cache switches, rollback and recovery without private sessions."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from my_tools import plugins
from my_tools.core import ToolError


class PluginTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.first, self.second = "a" * 40, "b" * 40
        self.manager = SimpleNamespace(home=self.base / "storage",
            location=lambda name, commit: self.base / "storage/tools" / name / commit,
            resolve=lambda name: self.base / "storage/tools" / name / self.first,
            state=lambda: {"tools": {plugins.NAME: {"active": self.first}}})
        self.source = self.manager.location(plugins.NAME, self.first) / "source"
        self.other = self.manager.location(plugins.NAME, self.second) / "source"
        for source in (self.source, self.other):
            for name in ("dist/codex/run.js", "dist/codex/hook.js", ".codex-plugin/plugin.json",
                         "codex/hooks.json", "codex/skills/jev-pruner/SKILL.md"):
                file = source / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(source.parent.name)
        self.info = None
        self.market = None
        self.fail_add = False
        self.calls = []
        self.env = patch.dict("os.environ", {"CODEX_HOME": str(self.base / "codex")})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.command = patch("my_tools.plugins.checked", side_effect=self.codex)
        self.command.start()
        self.addCleanup(self.command.stop)
        self.contract = patch("my_tools.pruner.contract")
        self.contract.start()
        self.addCleanup(self.contract.stop)

    def codex(self, argv):
        self.calls.append(argv)
        args = argv[1:]
        if args == ["plugin", "list", "--json"]:
            return json.dumps({"installed": [self.info] if self.info else []})
        if args == ["plugin", "marketplace", "list", "--json"]:
            return json.dumps({"marketplaces": [{"name": plugins.MARKETPLACE}] if self.market else []})
        if args[:3] == ["plugin", "marketplace", "add"]:
            self.market = Path(args[3]).resolve()
        elif args[:3] == ["plugin", "marketplace", "remove"]:
            self.market = None
        elif args[:2] == ["plugin", "remove"]:
            if self.info:
                shutil.rmtree(plugins.cached_root(self.info))
            self.info = None
        elif args[:2] == ["plugin", "add"]:
            if self.fail_add and self.market == self.other:
                raise ToolError("synthetic installation failure")
            self.info = {"pluginId": plugins.PLUGIN, "version": "0.1.0", "installed": True,
                         "enabled": True, "source": {"path": str(self.market)}}
            shutil.copytree(self.market, plugins.cached_root(self.info))
        else:
            raise AssertionError(argv)
        return ""

    def enable(self):
        return plugins.integrate(self.manager, plugins.NAME, True)

    def test_cache_follows_version_and_rollback_with_unchanged_plugin_version(self):
        self.enable()
        plugins.synchronize(self.manager, plugins.NAME, self.second)
        plugins.check_client(self.other)
        plugins.synchronize(self.manager, plugins.NAME, self.first)
        plugins.check_client(self.source)
        self.assertEqual(plugins.registry(self.manager)["tools"][plugins.NAME]["active"], self.first)

    def test_failed_install_restores_previous_source_and_cached_files(self):
        self.enable()
        self.fail_add = True
        with self.assertRaises(ToolError):
            plugins.synchronize(self.manager, plugins.NAME, self.second)
        plugins.check_client(self.source)
        self.assertEqual(plugins.registry(self.manager)["tools"][plugins.NAME]["active"], self.first)

    def test_registry_write_failure_restores_cache_and_stable_link(self):
        self.enable()
        with patch("my_tools.plugins.atomic_json", side_effect=OSError("synthetic disk failure")):
            with self.assertRaises(OSError):
                plugins.synchronize(self.manager, plugins.NAME, self.second)
        plugins.check_client(self.source)
        link = Path(plugins.registry(self.manager)["tools"][plugins.NAME]["root"])
        self.assertEqual(link.resolve(), self.source)

    def test_first_registry_failure_removes_owned_plugin_and_marketplace(self):
        with patch("my_tools.plugins.atomic_json", side_effect=OSError("synthetic disk failure")):
            with self.assertRaises(OSError):
                self.enable()
        self.assertIsNone(self.info)
        self.assertIsNone(self.market)
        self.assertFalse((self.manager.home / "plugins/jev-pruner").is_symlink())

    def test_corrupted_cache_is_diagnosed_and_integrate_repairs_it(self):
        self.enable()
        (plugins.cached_root(self.info) / "dist/codex/run.js").write_text("tampered")
        with self.assertRaises(ToolError):
            plugins.diagnose(self.manager, plugins.NAME, self.first)
        self.enable()
        plugins.check_client(self.source)

    def test_foreign_marketplace_and_source_are_preserved(self):
        self.market = self.base / "foreign"
        with self.assertRaises(ToolError):
            self.enable()
        self.assertEqual(self.market, self.base / "foreign")
        self.market = None
        self.enable()
        self.info["source"]["path"] = str(self.base / "foreign")
        before = len(self.calls)
        with self.assertRaises(ToolError):
            plugins.synchronize(self.manager, plugins.NAME, self.second)
        self.assertFalse(any(c[1:3] == ["plugin", "remove"] for c in self.calls[before:]))

    def test_disabled_plugin_is_not_implicitly_reenabled(self):
        self.enable()
        self.info["enabled"] = False
        with self.assertRaises(ToolError):
            plugins.synchronize(self.manager, plugins.NAME, self.second)
        self.assertFalse(self.info["enabled"])
        self.assertEqual(self.market, self.source)


if __name__ == "__main__":
    unittest.main()
