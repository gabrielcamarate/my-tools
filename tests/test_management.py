"""Real local Git repositories and isolated runtimes; no keys or API calls."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from my_tools.core import Manager, ToolError, ROOT, atomic_json, checked, project_config, project_root, setup, uninstall_launcher
from my_tools import cli
from my_tools import __version__
from my_tools.siftr import command


FAKE = '''import sys, json, os
def load_env():
    raise RuntimeError("dotenv loading must be disabled by the adapter")
def main():
    load_env()
    args = sys.argv[1:]
    if "--help" in args:
        print("query --json --top --glob")
    elif "--version" in args:
        print("siftr fixture")
    elif args[1] == "EXIT7":
        print("fixture stderr", file=sys.stderr)
        return 7
    else:
        print(json.dumps({"query": args[1], "root": args[2], "args": args[3:]}))
    return 0
'''


class ManagementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="my-tools-test-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repository = self.base / "upstream"
        self.repository.mkdir()
        self.git("init", "--quiet")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.repository / "siftr").mkdir()
        (self.repository / "siftr/__init__.py").write_text("")
        (self.repository / "siftr/cli.py").write_text(FAKE)
        (self.repository / "pyproject.toml").write_text('[project]\nname="siftr"\ndependencies=[]\n')
        (self.repository / "tests").mkdir()
        (self.repository / "tests/__init__.py").write_text("")
        (self.repository / "tests/test_offline.py").write_text('''import socket, unittest
class Offline(unittest.TestCase):
    def test_transport_blocked(self):
        with self.assertRaises(OSError):
            socket.create_connection(("example.invalid", 443))
''')
        self.first = self.commit("initial")
        self.git("branch", "-M", "main")
        self.manager = Manager(home=self.base / "storage")
        # Local fixture transport is injected only in tests, not accepted by catalog validation.
        self.manager.tools["siftr"]["repository"] = str(self.repository)
        self.manager.tools["siftr"]["approved_commit"] = self.first
        self.project = self.base / "project"
        self.project.mkdir()
        (self.project / ".git").mkdir()

    def git(self, *args):
        return checked(["git", "-C", str(self.repository), *args])

    def commit(self, message):
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", message)
        return self.git("rev-parse", "HEAD")

    def next(self, bad=False):
        (self.repository / "siftr/cli.py").write_text(FAKE.replace("query --json --top", "broken contract") if bad else FAKE + "\n# next revision\n")
        return self.commit("next")

    def invoke(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with patch("my_tools.cli.Manager", return_value=self.manager), redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["--project", str(self.project), *args])
        return code, out.getvalue(), err.getvalue()

    def test_install_is_idempotent_and_runtime_relocates(self):
        self.manager.install("siftr")
        self.manager.install("siftr")
        entry = self.manager.state()["tools"]["siftr"]
        self.assertEqual(entry["active"], self.first)
        self.assertIsNone(entry["previous"])
        self.assertEqual(self.manager.doctor()["tools"][0]["status"], "ready_offline")

    def test_unreviewed_update_does_not_change_active_or_allow_pin(self):
        self.manager.install("siftr")
        second = self.next()
        result = self.manager.update("siftr")
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["active"], self.first)
        with self.assertRaises(ToolError):
            self.manager.resolve("siftr", second)

    def test_accept_update_rollback_and_project_pin(self):
        self.manager.install("siftr")
        second = self.next()
        self.manager.update("siftr", accept=second)
        self.manager.install("siftr")
        self.assertEqual(self.manager.resolve("siftr", self.first).name, self.first)
        self.assertEqual(self.manager.update("siftr")["status"], "current")
        self.assertEqual(self.manager.state()["tools"]["siftr"]["active"], second)
        self.manager.rollback("siftr")
        self.assertEqual(self.manager.state()["tools"]["siftr"]["active"], self.first)
        self.assertEqual(self.manager.resolve("siftr", second).name, second)

    def test_accepted_revision_is_not_reset_when_newer_candidate_appears(self):
        self.manager.install("siftr")
        second = self.next()
        self.manager.update("siftr", accept=second)
        (self.repository / "siftr/cli.py").write_text(FAKE + "\n# third revision\n")
        third = self.commit("third")
        result = self.manager.update("siftr")
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["prepared"], third)
        self.assertEqual(self.manager.state()["tools"]["siftr"]["active"], second)

    def test_rollback_refuses_broken_previous_runtime(self):
        self.manager.install("siftr")
        second = self.next()
        self.manager.update("siftr", accept=second)
        (self.manager.location("siftr", self.first) / "runner.py").write_text("broken")
        with self.assertRaises(ToolError):
            self.manager.rollback("siftr")
        self.assertEqual(self.manager.state()["tools"]["siftr"]["active"], second)

    def test_failed_state_write_keeps_previous_active(self):
        self.manager.install("siftr")
        second = self.next()
        with patch("my_tools.core.atomic_json", side_effect=OSError("simulated disk error")):
            with self.assertRaises(OSError):
                self.manager.update("siftr", accept=second)
        self.assertEqual(self.manager.state()["tools"]["siftr"]["active"], self.first)

    def test_failed_candidate_keeps_active_and_removes_staging(self):
        self.manager.install("siftr")
        second = self.next(bad=True)
        with self.assertRaises(ToolError):
            self.manager.update("siftr", accept=second)
        self.assertEqual(self.manager.state()["tools"]["siftr"]["active"], self.first)
        self.assertFalse(self.manager.location("siftr", second).exists())
        self.assertFalse(list((self.manager.home / "tools/siftr").glob(".staging-*")))

    def test_upstream_changed_between_review_and_apply_is_rejected(self):
        self.manager.install("siftr")
        second = self.next()
        with self.assertRaises(ToolError):
            self.manager.update("siftr", accept=self.first)
        self.assertEqual(self.manager.state()["tools"]["siftr"]["active"], self.first)

    def test_catalog_approval_activates_without_manual_accept(self):
        self.manager.install("siftr")
        second = self.next()
        self.manager.tools["siftr"]["approved_commit"] = second
        self.assertEqual(self.manager.update("siftr")["status"], "updated")
        self.assertEqual(self.manager.state()["tools"]["siftr"]["active"], second)

    def test_annotated_stable_tag_precedes_branch_and_prerelease(self):
        self.git("tag", "-a", "v1.2.3", "-m", "stable")
        second = self.next()
        self.git("tag", "v2.0.0-rc1")
        result = self.manager.discover("siftr")
        self.assertEqual(result["latest"], self.first)
        self.assertEqual(result["ref"], "refs/tags/v1.2.3")

    def test_modified_runtime_source_is_rejected(self):
        self.manager.install("siftr")
        path = self.manager.location("siftr", self.first)
        (path / "source/siftr/cli.py").write_text("tampered")
        with self.assertRaises(ToolError):
            self.manager.resolve("siftr")

    def test_dependency_change_requires_adapter_review(self):
        self.manager.install("siftr")
        (self.repository / "pyproject.toml").write_text('[project]\nname="siftr"\ndependencies=["unexpected"]\n')
        second = self.commit("dependencies")
        with self.assertRaises(ToolError):
            self.manager.update("siftr", accept=second)
        self.assertEqual(self.manager.state()["tools"]["siftr"]["active"], self.first)

    def test_launcher_preserves_foreign_file_and_uninstall_only_owned(self):
        folder = self.base / "bin"
        folder.mkdir()
        target = folder / "my-tools"
        target.write_text("foreign")
        with self.assertRaises(ToolError):
            setup(bin_dir=folder, apply=True)
        uninstall_launcher(bin_dir=folder, apply=True)
        self.assertEqual(target.read_text(), "foreign")
        target.unlink()
        self.assertEqual(setup(bin_dir=folder)["status"], "planned")
        self.assertFalse(target.exists())
        setup(bin_dir=folder, apply=True)
        result = subprocess.run([sys.executable, str(target), "--version"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), __version__)
        uninstall_launcher(bin_dir=folder, apply=True)
        self.assertFalse(target.exists())

    def test_project_boundaries_include_worktree_git_file(self):
        atomic_json(self.base / ".my-tools.json", {"schema_version": 1, "capabilities": {}})
        child = self.project / "src"
        child.mkdir()
        self.assertEqual(project_root(child), self.project)
        (self.project / ".git").rmdir()
        (self.project / ".git").write_text("gitdir: ../worktree")
        self.assertEqual(project_root(child), self.project)

    def test_project_init_enable_disable_and_remote_opt_in(self):
        self.manager.install("siftr")
        self.assertEqual(self.invoke("init")[0], 0)
        before = (self.project / ".my-tools.json").read_text()
        self.assertEqual(self.invoke("init")[0], 2)
        self.assertEqual((self.project / ".my-tools.json").read_text(), before)
        self.assertEqual(self.invoke("enable", "search")[0], 0)
        with patch("my_tools.siftr.search") as operation:
            self.assertEqual(self.invoke("search", "question")[0], 2)
            operation.assert_not_called()
        self.assertEqual(self.invoke("enable", "search", "--allow-remote", "--pin", self.first)[0], 0)
        with patch("my_tools.siftr.search", return_value=7) as operation:
            self.assertEqual(self.invoke("search", "question", "--json")[0], 7)
            self.assertEqual(operation.call_args.args[1], self.project)
        self.assertEqual(self.invoke("disable", "search")[0], 0)
        self.assertEqual(self.invoke("search", "question")[0], 2)

    def test_explicit_nested_init_creates_separate_config(self):
        fixture = self.project / "fixture"
        fixture.mkdir()
        with patch("my_tools.cli.Manager", return_value=self.manager), redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["--project", str(fixture), "init"]), 0)
        self.assertTrue((fixture / ".my-tools.json").exists())
        self.assertFalse((self.project / ".my-tools.json").exists())
        self.assertEqual(project_root(fixture), fixture)

    def test_unknown_project_fields_are_not_echoed(self):
        atomic_json(self.project / ".my-tools.json", {"schema_version": 1, "capabilities": {}, "private": "do not echo"})
        code, out, err = self.invoke("status")
        self.assertEqual(code, 2)
        self.assertNotIn("do not echo", out + err)

    def test_update_all_reports_failure_and_continues_other_tools(self):
        self.manager.tools["second"] = self.manager.tools["siftr"].copy()
        with patch.object(self.manager, "update", side_effect=[ToolError("failed fixture"), {"tool": "second", "status": "current"}]):
            code, out, _ = self.invoke("update", "--all")
        self.assertEqual(code, 1)
        self.assertEqual([r["status"] for r in json.loads(out)["tools"]], ["failed", "current"])

    def test_search_keeps_json_and_exit_code_without_shell_interpolation(self):
        self.manager.install("siftr")
        path = self.manager.resolve("siftr")
        query = 'literal $(touch SHOULD_NOT_EXIST); `echo unsafe`'
        result = subprocess.run(command(path, ["search", query, str(self.project), "--json"]), cwd=self.project,
                                capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout)["query"], query)
        self.assertFalse((self.project / "SHOULD_NOT_EXIST").exists())
        result = subprocess.run(command(path, ["search", "EXIT7", str(self.project)]), capture_output=True)
        self.assertEqual(result.returncode, 7)
        self.assertIn(b"fixture stderr", result.stderr)

    def test_search_scope_reaches_runtime_as_separate_literal_arguments(self):
        self.manager.install("siftr")
        self.invoke("init")
        self.invoke("enable", "search", "--allow-remote")
        from my_tools.siftr import search
        path = self.manager.resolve("siftr")
        output = self.base / "output.json"
        original = subprocess.run
        with output.open("w") as stdout:
            # Real adapter process; the fixture records the upstream arguments.
            with patch("my_tools.siftr.subprocess.run", wraps=subprocess.run) as operation:
                operation.side_effect = lambda *a, **kw: original(*a, **kw, stdout=stdout)
                code = search(path, self.project, "question", globs=["src/*.ts", "tests/* $(touch SHOULD_NOT_EXIST)"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.read_text())["args"],
                         ["--top", "10", "--glob", "src/*.ts", "--glob", "tests/* $(touch SHOULD_NOT_EXIST)"])
        self.assertFalse((self.project / "SHOULD_NOT_EXIST").exists())
        with patch("my_tools.siftr.search", return_value=0) as operation:
            self.assertEqual(self.invoke("search", "question", "--glob", "src/*.ts", "--glob", "tests/*.ts")[0], 0)
            self.assertEqual(operation.call_args.kwargs["globs"], ["src/*.ts", "tests/*.ts"])

    def test_invalid_search_scopes_never_start_adapter(self):
        with patch("my_tools.siftr.search") as operation:
            for pattern in ("", " ", "/private/*", "../*", "src/../*", "src\n*"):
                self.assertEqual(self.invoke("search", "question", "--glob", pattern)[0], 2)
            operation.assert_not_called()

    def test_controller_save_failure_restores_registered_native_version(self):
        self.manager.install("siftr")
        second = self.next()
        self.manager.prepare("siftr", second)
        with patch("my_tools.native.synchronize") as sync:
            with patch.object(self.manager, "save", side_effect=OSError("fixture disk failure")):
                with self.assertRaises(OSError):
                    self.manager.activate("siftr", second)
        self.assertEqual([call.args[2] for call in sync.call_args_list], [second, self.first])
        self.assertEqual(self.manager.state()["tools"]["siftr"]["active"], self.first)

    def test_doctor_reports_divergence_after_failed_native_compensation(self):
        self.manager.install("siftr")
        second = self.next()
        atomic_json(self.manager.home / "native.json", {"schema_version": 1, "tools": {
            "siftr": {"active": second, "command": str(self.base / "bin/siftr")}}})
        row = self.manager.doctor(smoke=False)["tools"][0]
        self.assertEqual(row["status"], "not_ready")
        self.assertIn("diverge", row["reason"])

    def test_saved_scope_is_default_and_cannot_be_widened_by_search(self):
        self.manager.install("siftr")
        self.invoke("init")
        self.assertEqual(self.invoke("enable", "search", "--allow-remote", "--glob", "src/*.ts", "--glob", "tests/*.ts")[0], 0)
        with patch("my_tools.siftr.search", return_value=0) as operation:
            self.assertEqual(self.invoke("search", "question")[0], 0)
            self.assertEqual(operation.call_args.kwargs["globs"], ["src/*.ts", "tests/*.ts"])
            self.assertEqual(self.invoke("search", "question", "--glob", "tests/*.ts")[0], 0)
            self.assertEqual(operation.call_args.kwargs["globs"], ["tests/*.ts"])
            operation.reset_mock()
            self.assertEqual(self.invoke("search", "question", "--glob", "*")[0], 2)
            operation.assert_not_called()
        self.invoke("disable", "search")
        self.invoke("enable", "search", "--allow-remote")
        self.assertEqual(project_config(self.project)["capabilities"]["search"]["globs"], ["src/*.ts", "tests/*.ts"])

    def test_invalid_saved_scopes_fail_before_runtime_and_preserve_config(self):
        self.invoke("init")
        before = (self.project / ".my-tools.json").read_bytes()
        with patch.object(self.manager, "resolve") as resolve:
            self.assertEqual(self.invoke("enable", "search", "--allow-remote", "--glob", "../*")[0], 2)
            resolve.assert_not_called()
        self.assertEqual((self.project / ".my-tools.json").read_bytes(), before)
        for globs in ([], "src/*.ts", [None], ["/private/*"], ["src/../*"], ["\\private\\*"]):
            atomic_json(self.project / ".my-tools.json", {"schema_version": 1, "capabilities": {
                "search": {"provider": "siftr", "version": "approved", "enabled": True,
                           "allow_remote_data": True, "globs": globs}}})
            with patch("my_tools.siftr.search") as operation:
                self.assertEqual(self.invoke("search", "question")[0], 2)
                operation.assert_not_called()

    def test_update_all_pending_exit_and_accept_all_rejected(self):
        self.manager.install("siftr")
        second = self.next()
        self.assertEqual(self.invoke("update", "--all")[0], 2)
        self.assertEqual(self.invoke("update", "--all", "--accept", second)[0], 2)
        self.assertEqual(self.manager.state()["tools"]["siftr"]["active"], self.first)

    def test_corrupt_state_fails_closed(self):
        atomic_json(self.manager.home / "state.json", {"schema_version": 1, "tools": {"siftr": "invalid"}})
        with self.assertRaises(ToolError):
            self.manager.state()

    def test_mutations_are_exclusive(self):
        with self.manager.lock():
            with self.assertRaises(ToolError):
                with Manager(home=self.manager.home).lock():
                    pass

    def test_project_config_symlink_is_not_modified(self):
        foreign = self.base / "foreign.json"
        atomic_json(foreign, {"schema_version": 1, "capabilities": {}})
        (self.project / ".my-tools.json").symlink_to(foreign)
        self.assertEqual(self.invoke("disable", "search")[0], 2)
        self.assertEqual(json.loads(foreign.read_text())["capabilities"], {})


if __name__ == "__main__":
    unittest.main()
