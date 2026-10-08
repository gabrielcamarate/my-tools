"""Claude Code compaction mod: reviewed patch scope, contract and settings preservation."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from my_tools import compaction
from my_tools.core import ToolError


class ProviderPatchTests(unittest.TestCase):
    def test_patch_stays_within_the_provider_scope(self):
        stat = compaction.checked(["git", "apply", "--numstat", str(compaction.PATCH)])
        self.assertEqual({line.split("\t")[-1] for line in stat.splitlines()}, compaction.SCOPE)
        text = compaction.PATCH.read_text()
        self.assertIn("https://openrouter.ai/api/alpha/decisions", text)
        self.assertNotIn("src/compact.ts", text)

    def test_out_of_scope_patch_is_refused_before_applying(self):
        with patch("my_tools.compaction.checked", return_value="1\t1\tsrc/compact.ts") as run:
            with self.assertRaises(ToolError):
                compaction.apply_provider(Path("/nonexistent"))
        self.assertEqual(run.call_count, 1)


class ContractTests(unittest.TestCase):
    def write(self, root, hooks):
        files = {"package.json": {"name": compaction.NAME, "scripts": {"test": "vitest run"}},
                 ".claude-plugin/plugin.json": {"name": compaction.NAME, "version": "0.3.0",
                     "userConfig": {"model": {"default": "typesafe/jev-1.13"}}},
                 ".claude-plugin/marketplace.json": {"name": compaction.NAME, "plugins": [
                     {"name": compaction.NAME, "source": "./"}]},
                 "hooks/hooks.json": hooks}
        for name, value in files.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(json.dumps(value))

    def test_accepts_the_reviewed_shape_and_refuses_new_modules(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.write(root, {"modules": ["./fast-jev.ts"]})
            compaction.contract(root)
            self.write(root, {"modules": ["./fast-jev.ts", "./other.ts"]})
            with self.assertRaises(ToolError):
                compaction.contract(root)


class SettingsTests(unittest.TestCase):
    def test_flag_is_added_without_touching_existing_hooks(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            original = {"hooks": {"PreCompact": [{"hooks": [{"type": "command", "command": "ai-memory hook"}]}]},
                        "env": {"OTHER": "x"}, "includeCoAuthoredBy": False}
            path.write_text(json.dumps(original))
            os.chmod(path, 0o600)
            with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": folder}):
                compaction.enable_flag()
                compaction.enable_flag()
            value = json.loads(path.read_text())
            self.assertEqual(value["hooks"], original["hooks"])
            self.assertEqual(value["env"], {"OTHER": "x", compaction.FLAG: "1"})
            self.assertFalse(value["includeCoAuthoredBy"])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()), ["settings.json"])


if __name__ == "__main__":
    unittest.main()
