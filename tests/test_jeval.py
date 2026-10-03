"""Version switching must preserve official commands, skills and foreign files."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from my_tools import commands, jeval
from my_tools.core import Manager, ToolError, atomic_json


class JevalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.manager = Manager(home=root / 'storage')
        self.a, self.b = '1' * 40, '2' * 40
        self.entry = {'schema_version': 1, 'active': self.a, 'bin_dir': str(root / 'bin'),
                      'skills_dir': str(root / 'skills'), 'claude_dir': str(root / 'claude')}
        for commit in (self.a, self.b):
            pairs = jeval.links(self.manager, self.entry, commit)
            pairs[0][1].parent.mkdir(parents=True)
            pairs[0][1].write_text('synthetic upstream entrypoint')
            for name in jeval.SKILLS:
                skill = self.manager.location('jeval', commit) / 'source/skills' / name
                skill.mkdir(parents=True)
                (skill / 'SKILL.md').write_text('synthetic skill')
        self.runtime = patch.object(jeval, 'runtime', return_value=None)
        self.runtime.start()
        self.addCleanup(self.runtime.stop)
        jeval.switch(self.manager, self.entry, self.a)
        atomic_json(self.manager.home / 'jeval.json', self.entry)

    def assert_active(self, commit):
        self.assertEqual(jeval.registry(self.manager)['active'], commit)
        for link, target in jeval.links(self.manager, self.entry, commit):
            self.assertEqual(link.resolve(), target.resolve())

    def test_all_thirteen_links_update_and_rollback(self):
        commands.synchronize(self.manager, 'jeval', self.b)
        self.assert_active(self.b)
        commands.synchronize(self.manager, 'jeval', self.a)
        self.assert_active(self.a)

    def test_persistence_failure_restores_all_links(self):
        with patch.object(jeval, 'atomic_json', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                jeval.synchronize(self.manager, 'jeval', self.b)
        self.assert_active(self.a)

    def test_foreign_last_skill_preserves_every_other_link(self):
        link = Path(self.entry['skills_dir']) / jeval.SKILLS[-1]
        link.unlink()
        link.mkdir()
        with self.assertRaises(ToolError):
            jeval.synchronize(self.manager, 'jeval', self.b)
        self.assertEqual(jeval.registry(self.manager)['active'], self.a)
        self.assertEqual((Path(self.entry['bin_dir']) / 'jeval').resolve(),
                         jeval.links(self.manager, self.entry, self.a)[0][1])
        self.assertTrue(link.is_dir())

    def test_partial_switch_failure_restores_prior_links(self):
        original = commands.replace_link
        count = 0
        def replace(link, target):
            nonlocal count
            count += 1
            if count == 9:
                raise OSError('link failure')
            return original(link, target)
        with patch.object(commands, 'replace_link', side_effect=replace):
            with self.assertRaises(OSError):
                jeval.synchronize(self.manager, 'jeval', self.b)
        self.assert_active(self.a)

    def test_runtime_failure_preserves_old_links(self):
        with patch.object(jeval, 'runtime', side_effect=ToolError('bad runtime')):
            with self.assertRaises(ToolError):
                jeval.synchronize(self.manager, 'jeval', self.b)
        self.assert_active(self.a)

    def test_doctor_rejects_missing_link(self):
        (Path(self.entry['claude_dir']) / jeval.SKILLS[-1]).unlink()
        with self.assertRaises(ToolError):
            jeval.diagnose(self.manager, 'jeval', self.a)

    def test_registry_rejects_relative_destination(self):
        atomic_json(self.manager.home / 'jeval.json', {**self.entry, 'bin_dir': 'relative'})
        with self.assertRaises(ToolError):
            jeval.registry(self.manager)

    def test_changed_runtime_rejected_without_switching_links(self):
        base = self.manager.home / 'native/jeval' / self.b
        env = base / 'venv'
        fingerprint = jeval.runtime_hashes(env)
        atomic_json(base / 'runtime.json', {'schema_version': 1, 'commit': self.b,
                    'source_hashes': {'fixture': 'hash'}, 'runtime_hashes': fingerprint})
        (env / 'bin/jeval').write_text('modified executable')
        self.runtime.stop()
        with patch.object(jeval, 'check'), patch.object(jeval, 'hashes', return_value={'fixture': 'hash'}):
            with self.assertRaises(ToolError):
                jeval.synchronize(self.manager, 'jeval', self.b)
        self.runtime.start()
        self.assert_active(self.a)

    def test_controller_state_failure_restores_all_links(self):
        state = {'schema_version': 1, 'tools': {'jeval': {
            'active': self.a, 'previous': None, 'accepted': [self.a]}}}
        self.manager.save(state)
        with patch.object(jeval, 'check'), patch.object(self.manager, 'save', side_effect=OSError('state failure')):
            with self.assertRaises(OSError):
                self.manager.activate('jeval', self.b)
        self.assert_active(self.a)
        self.assertEqual(self.manager.state()['tools']['jeval']['active'], self.a)
