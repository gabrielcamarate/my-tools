import json
import io
from contextlib import redirect_stdout, redirect_stderr
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from my_tools.credentials import save, stored, effective, clear
from my_tools.core import ToolError
from my_tools.core import Manager
from my_tools import cli


class CredentialsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)

    def test_persistent_storage_permissions_and_removal(self):
        save(self.home, "openrouter", "synthetic-fixture-key")
        self.assertEqual((self.home / "credentials.json").stat().st_mode & 0o777, 0o600)
        with patch.dict(os.environ, {}, clear=True):
            env, source = effective(self.home)
        self.assertEqual(source, "local_store")
        self.assertEqual(env["OPENROUTER_API_KEY"], "synthetic-fixture-key")
        clear(self.home, "openrouter")
        self.assertEqual(stored(self.home), {})

    def test_explicit_typesafe_environment_overrides_stored_openrouter(self):
        save(self.home, "openrouter", "stored-fixture")
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "explicit-fixture"}, clear=True):
            env, source = effective(self.home)
        self.assertEqual(source, "environment")
        self.assertNotIn("OPENROUTER_API_KEY", env)

    def test_group_readable_file_is_rejected(self):
        save(self.home, "openrouter", "fixture-key")
        (self.home / "credentials.json").chmod(0o644)
        with self.assertRaises(ToolError):
            stored(self.home)

    def test_symlink_is_rejected_without_modifying_target(self):
        target = self.home / "foreign"
        target.write_text("foreign")
        (self.home / "credentials.json").symlink_to(target)
        with self.assertRaises(ToolError):
            save(self.home, "openrouter", "fixture-key")
        self.assertEqual(target.read_text(), "foreign")

    def test_noninteractive_prompt_is_rejected(self):
        with patch("my_tools.cli.Manager"), patch("sys.stdin.isatty", return_value=False), patch("my_tools.cli.getpass.getpass") as prompt:
            self.assertEqual(cli.main(["auth", "set", "--provider", "openrouter"]), 2)
            prompt.assert_not_called()

    def test_unknown_fields_and_whitespace_key_rejected(self):
        for key in ("", "contains whitespace"):
            with self.assertRaises(ToolError):
                save(self.home, "openrouter", key)

    def test_interactive_cli_never_echoes_key(self):
        manager = Manager(home=self.home)
        out, err = io.StringIO(), io.StringIO()
        with patch("my_tools.cli.Manager", return_value=manager), patch("sys.stdin.isatty", return_value=True), patch("my_tools.cli.getpass.getpass", return_value="synthetic-private-value"), redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(cli.main(["auth", "set", "--provider", "openrouter"]), 0)
        self.assertNotIn("synthetic-private-value", out.getvalue() + err.getvalue())
        self.assertEqual(stored(self.home)["OPENROUTER_API_KEY"], "synthetic-private-value")

    def test_diagnostics_only_report_availability_and_source(self):
        save(self.home, "openrouter", "synthetic-private-value")
        with patch.dict(os.environ, {}, clear=True):
            result = Manager(home=self.home).doctor(smoke=False)
        self.assertTrue(result["tools"][0]["credential_available"])
        self.assertFalse(result["tools"][0]["credential_in_environment"])
        self.assertEqual(result["tools"][0]["credential_source"], "local_store")
        self.assertNotIn("synthetic-private-value", json.dumps(result))
