"""Official MCP handshake and failure-safe executable switches, offline."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from my_tools import native
from my_tools.core import ToolError, atomic_json


class NativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.first, self.second = "a" * 40, "b" * 40
        self.manager = SimpleNamespace(home=self.base / "storage",
            location=lambda name, commit: self.base / "source" / commit,
            resolve=lambda name: self.base / "source" / self.first,
            state=lambda: {"tools": {"siftr": {"active": self.first}}})
        self.link = self.base / "bin/siftr"
        self.make_exe(self.first)

    def make_exe(self, commit, tools=None):
        exe = native.executable(self.manager, "siftr", commit)
        exe.parent.mkdir(parents=True, exist_ok=True)
        names = sorted(native.MCP_TOOLS) if tools is None else tools
        exe.write_text(f'#!{sys.executable}\nimport json,sys\n'
            f'names={names!r}\n'
            'for line in sys.stdin:\n'
            ' m=json.loads(line)\n'
            ' if m.get("id") is not None:\n'
            '  result={"tools":[{"name":n} for n in names]} if m["method"]=="tools/list" else {}\n'
            '  print(json.dumps({"id":m["id"],"result":result}),flush=True)\n')
        exe.chmod(0o700)
        return exe

    def enable(self):
        return native.integrate(self.manager, "siftr", True, self.link.parent)

    def test_real_stdio_discovery_and_idempotent_official_link(self):
        result = self.enable()
        self.assertEqual(set(result["mcp_tools"]), native.MCP_TOOLS)
        self.assertEqual(self.link.resolve(), native.executable(self.manager, "siftr", self.first))
        self.enable()
        self.assertEqual(native.registry(self.manager)["tools"]["siftr"]["active"], self.first)

    def test_foreign_command_is_preserved_before_build(self):
        self.link.parent.mkdir()
        self.link.write_text("foreign")
        with patch("my_tools.native.prepare") as prepare, self.assertRaises(ToolError):
            self.enable()
        prepare.assert_not_called()
        self.assertEqual(self.link.read_text(), "foreign")

    def test_changed_mcp_contract_keeps_previous_link_and_record(self):
        self.enable()
        self.make_exe(self.second, ["unexpected"])
        with self.assertRaises(ToolError):
            native.synchronize(self.manager, "siftr", self.second)
        self.assertEqual(self.link.resolve(), native.executable(self.manager, "siftr", self.first))
        self.assertEqual(native.registry(self.manager)["tools"]["siftr"]["active"], self.first)

    def test_registry_write_failure_restores_previous_executable(self):
        self.enable()
        self.make_exe(self.second)
        with patch("my_tools.native.atomic_json", side_effect=OSError("fixture disk failure")):
            with self.assertRaises(OSError):
                native.synchronize(self.manager, "siftr", self.second)
        self.assertEqual(self.link.resolve(), native.executable(self.manager, "siftr", self.first))
        self.assertEqual(native.registry(self.manager)["tools"]["siftr"]["active"], self.first)

    def test_first_integration_write_failure_removes_only_owned_link(self):
        with patch("my_tools.native.atomic_json", side_effect=OSError("fixture disk failure")):
            with self.assertRaises(OSError):
                self.enable()
        self.assertFalse(self.link.is_symlink())

    def test_native_switch_and_rollback_keep_stable_command(self):
        self.enable()
        self.make_exe(self.second)
        native.synchronize(self.manager, "siftr", self.second)
        self.assertEqual(self.link.resolve(), native.executable(self.manager, "siftr", self.second))
        native.synchronize(self.manager, "siftr", self.first)
        self.assertEqual(self.link.resolve(), native.executable(self.manager, "siftr", self.first))

    def test_unintegrated_tools_do_not_install_native_runtime_on_update(self):
        with patch("my_tools.native.switch") as switch:
            native.synchronize(self.manager, "siftr", self.second)
        switch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
