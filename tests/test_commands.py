"""Owned CLI/skill switching, persistence failures and recovery."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from my_tools.core import Manager, ToolError, atomic_json
from my_tools import commands, test_filter


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.manager = Manager(home=self.home / 'storage')
        self.first, self.second = '1' * 40, '2' * 40
        for commit in (self.first, self.second):
            cli, skill = commands.targets(self.manager, commit)
            cli.parent.mkdir(parents=True)
            cli.write_text('synthetic executable')
            skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_text('synthetic skill')
        self.entry = {'command': str(self.home / 'bin/jev-test-filter'),
                      'skill': str(self.home / 'skills/jev-test-filter'), 'active': self.first}
        commands.switch(self.manager, self.entry, self.first)
        atomic_json(self.manager.home / 'commands.json', {'schema_version': 1, 'tools': {commands.NAME: self.entry}})

    def assert_first(self):
        for key, dest in zip(('command', 'skill'), commands.targets(self.manager, self.first)):
            self.assertEqual(Path(self.entry[key]).resolve(), dest)

    def test_update_and_rollback_both_links(self):
        commands.synchronize(self.manager, commands.NAME, self.second)
        self.assertEqual(commands.registry(self.manager)['tools'][commands.NAME]['active'], self.second)
        commands.synchronize(self.manager, commands.NAME, self.first)
        self.assert_first()

    def test_registry_failure_restores_both_links_and_revision(self):
        with patch.object(commands, 'atomic_json', side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):
                commands.synchronize(self.manager, commands.NAME, self.second)
        self.assert_first()
        self.assertEqual(commands.registry(self.manager)['tools'][commands.NAME]['active'], self.first)

    def test_foreign_skill_preflight_preserves_command(self):
        link = Path(self.entry['skill'])
        link.unlink()
        link.mkdir()
        with self.assertRaises(ToolError):
            commands.synchronize(self.manager, commands.NAME, self.second)
        self.assertEqual(Path(self.entry['command']).resolve(), commands.targets(self.manager, self.first)[0])
        self.assertTrue(link.is_dir())

    def test_partial_switch_failure_restores_first_link(self):
        original = commands.replace_link
        failed = False
        def change(link, dest):
            nonlocal failed
            if link == Path(self.entry['skill']) and not failed:
                failed = True
                raise OSError('synthetic failure')
            original(link, dest)
        with patch.object(commands, 'replace_link', side_effect=change):
            with self.assertRaises(OSError):
                commands.synchronize(self.manager, commands.NAME, self.second)
        self.assert_first()

    def test_doctor_rejects_replaced_link(self):
        Path(self.entry['command']).unlink()
        with self.assertRaises(ToolError):
            commands.diagnose(self.manager, commands.NAME, self.first)

    def test_patch_conflict_leaves_source_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'src/jev.ts'
            path.parent.mkdir()
            path.write_text('conflicting provider')
            with self.assertRaises(ToolError):
                test_filter.apply_provider(folder)
            self.assertEqual(path.read_text(), 'conflicting provider')
            self.assertFalse((Path(folder) / 'src/provider.ts').exists())

    def test_controller_state_failure_restores_integrated_revision(self):
        self.manager.save({'schema_version': 1, 'tools': {commands.NAME: {
            'active': self.first, 'previous': None, 'accepted': [self.first, self.second], 'catalog_commit': self.first}}})
        with patch.object(test_filter, 'check'), patch.object(self.manager, 'save', side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):
                self.manager.activate(commands.NAME, self.second)
        self.assert_first()
        self.assertEqual(commands.registry(self.manager)['tools'][commands.NAME]['active'], self.first)


class BrowserCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.manager = Manager(home=self.home / 'storage')
        self.first, self.second = '1' * 40, '2' * 40
        for commit in (self.first, self.second):
            cli, mcp, skill = commands.targets(self.manager, commit, 'jev-browser')
            cli.parent.mkdir(parents=True)
            cli.write_text('synthetic executable')
            mcp.write_text('synthetic MCP executable')
            skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_text('synthetic skill')
        self.entry = {'command': str(self.home / 'bin/jev-browser'),
                      'mcp_command': str(self.home / 'bin/jev-browser-mcp'),
                      'skill': str(self.home / 'skills/jev-browser-playwright'), 'active': self.first}
        commands.switch(self.manager, self.entry, self.first, 'jev-browser')
        atomic_json(self.manager.home / 'commands.json', {'schema_version': 1, 'tools': {'jev-browser': self.entry}})

    def assert_revision(self, commit):
        for key, dest in zip(commands.FIELDS['jev-browser'], commands.targets(self.manager, commit, 'jev-browser')):
            self.assertEqual(Path(self.entry[key]).resolve(), dest)

    def test_update_and_rollback_three_links(self):
        commands.synchronize(self.manager, 'jev-browser', self.second)
        self.assert_revision(self.second)
        commands.synchronize(self.manager, 'jev-browser', self.first)
        self.assert_revision(self.first)

    def test_foreign_mcp_preserved_before_any_switch(self):
        link = Path(self.entry['mcp_command'])
        link.unlink()
        link.write_text('foreign tool')
        with self.assertRaises(ToolError):
            commands.synchronize(self.manager, 'jev-browser', self.second)
        self.assertEqual(link.read_text(), 'foreign tool')
        self.assertEqual(Path(self.entry['command']).resolve(), commands.targets(self.manager, self.first, 'jev-browser')[0])

    def test_registry_failure_restores_three_links(self):
        with patch.object(commands, 'atomic_json', side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):
                commands.synchronize(self.manager, 'jev-browser', self.second)
        self.assert_revision(self.first)
        self.assertEqual(commands.registry(self.manager)['tools']['jev-browser']['active'], self.first)

    def test_third_link_failure_restores_prior_two(self):
        original = commands.replace_link
        failed = False
        def replace(link, dest):
            nonlocal failed
            if link == Path(self.entry['skill']) and not failed:
                failed = True
                raise OSError('synthetic failure')
            original(link, dest)
        with patch.object(commands, 'replace_link', side_effect=replace):
            with self.assertRaises(OSError):
                commands.synchronize(self.manager, 'jev-browser', self.second)
        self.assert_revision(self.first)

    def test_controller_state_failure_restores_browser_links_and_registry(self):
        from my_tools import browser
        self.manager.save({'schema_version': 1, 'tools': {'jev-browser': {
            'active': self.first, 'previous': None, 'accepted': [self.first, self.second], 'catalog_commit': self.first}}})
        with patch.object(browser, 'check'), patch.object(self.manager, 'save', side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):
                self.manager.activate('jev-browser', self.second)
        self.assert_revision(self.first)
        self.assertEqual(commands.registry(self.manager)['tools']['jev-browser']['active'], self.first)

    def test_browser_patch_conflict_preserves_source(self):
        from my_tools import browser
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'src/decision.ts'
            path.parent.mkdir()
            path.write_text('conflicting provider')
            with self.assertRaises(ToolError):
                browser.apply_provider(folder)
            self.assertEqual(path.read_text(), 'conflicting provider')
            self.assertFalse((Path(folder) / 'src/provider.ts').exists())
