"""Failure recovery and moving installed versions, without providers or credentials."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import struct
import shutil
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'experiments/codex-jev/manage.py'
SPEC = importlib.util.spec_from_file_location('jev_management', PATH)
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)


class ManagedEngineTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.state = self.root / 'state'
        self.state.mkdir()
        self.source = self.root / 'source'
        self.official = self.root / 'official/codex'
        self.official.parent.mkdir()
        self.write_engine(self.official)
        self.engine = self.source / 'target/release/codex'
        self.engine.parent.mkdir(parents=True)
        self.write_engine(self.engine)
        for name in ('target/release/codex-code-mode-host', 'lab-runtime/node_modules/@oven/bun-linux-x64/bin/bun', 'jev/codex-jev-compact.ts', 'jev/lib/index.ts'):
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('synthetic fixture')

    def write_engine(self, path, version='0.162.0', extra=''):
        path.write_text('#!/bin/sh\necho "codex-cli ' + version + '"\n' + extra)
        path.chmod(0o700)

    def accept(self):
        with patch.object(manager, 'validate'):
            manager.accept(self.state, 'cli', self.source, self.official)

    def test_success_records_full_runtime_integrity(self):
        self.accept()
        record = manager.load(self.state)['cli']
        self.assertTrue(manager.matches(record, self.official))
        (self.source / 'jev/lib/index.ts').write_text('modified after validation')
        self.assertFalse(manager.matches(record, self.official))

    def test_failed_validation_preserves_accepted_pointer(self):
        self.accept()
        before = (self.state / 'accepted.json').read_bytes()
        with patch.object(manager, 'validate', side_effect=RuntimeError('native fallback failed')):
            with self.assertRaisesRegex(RuntimeError, 'fallback failed'):
                manager.accept(self.state, 'cli', self.source, self.official)
        self.assertEqual((self.state / 'accepted.json').read_bytes(), before)

    def test_package_update_during_validation_is_not_activated(self):
        def update(*_):
            self.write_engine(self.official, '0.163.0')
        with patch.object(manager, 'validate', side_effect=update):
            with self.assertRaisesRegex(RuntimeError, 'changed during validation'):
                manager.accept(self.state, 'cli', self.source, self.official)
        self.assertFalse((self.state / 'accepted.json').exists())

    def test_runtime_change_during_validation_is_not_activated(self):
        def change(*_):
            (self.source / 'jev/lib/index.ts').write_text('unvalidated replacement')
        with patch.object(manager, 'validate', side_effect=change):
            with self.assertRaisesRegex(RuntimeError, 'runtime changed'):
                manager.accept(self.state, 'cli', self.source, self.official)
        self.assertFalse((self.state / 'accepted.json').exists())

    def test_extra_javascript_cannot_shadow_accepted_typescript(self):
        self.accept()
        (self.source / 'jev/lib/index.js').write_text('foreign runtime')
        self.assertFalse(manager.matches(manager.load(self.state)['cli'], self.official))

    def test_same_version_package_replacement_invalidates_acceptance(self):
        self.accept()
        self.write_engine(self.official, extra='# new official package\n')
        self.assertFalse(manager.matches(manager.load(self.state)['cli'], self.official))

    def test_maintenance_patch_update_requires_new_acceptance(self):
        self.accept()
        with patch.object(manager, 'patch_signature', return_value='new-maintenance-patch'):
            self.assertFalse(manager.matches(manager.load(self.state)['cli'], self.official))

    def test_patch_update_during_validation_does_not_publish_pointer(self):
        with patch.object(manager, 'patch_signature', return_value='old-patch') as signature:
            def change(*_):
                signature.return_value = 'new-patch'
            with patch.object(manager, 'validate', side_effect=change):
                with self.assertRaisesRegex(RuntimeError, 'patch changed'):
                    manager.accept(self.state, 'cli', self.source, self.official)
        self.assertFalse((self.state / 'accepted.json').exists())

    def test_stale_launch_uses_updated_official_engine_without_jev(self):
        self.accept()
        self.write_engine(self.official, '0.163.0')
        with patch.object(manager, 'official', return_value=self.official), patch.dict(os.environ, {'CODEX_JEV_COMPACT': 'foreign-helper'}), patch.object(os, 'execve') as execute:
            manager.launch(self.state, 'cli', ['--version'])
        binary, arguments, env = execute.call_args.args
        self.assertEqual(binary, self.official)
        self.assertNotIn('CODEX_JEV_COMPACT', env)
        self.assertEqual(arguments, [str(self.official), '--version'])

    def test_new_acceptance_preserves_helper_used_by_running_engine(self):
        self.accept()
        with patch.object(manager, 'official', return_value=self.official), patch.object(os, 'execve') as execute:
            manager.launch(self.state, 'cli', [])
            old = Path(execute.call_args.args[2]['CODEX_JEV_COMPACT'])
            old_bytes = old.read_bytes()
            new_source = self.root / 'new-source'
            shutil.copytree(self.source, new_source)
            with patch.object(manager, 'validate'):
                manager.accept(self.state, 'cli', new_source, self.official)
            manager.launch(self.state, 'cli', [])
            new = Path(execute.call_args.args[2]['CODEX_JEV_COMPACT'])
        self.assertNotEqual(old, new)
        self.assertEqual(old.read_bytes(), old_bytes)
        self.assertIn(str(self.source), old.read_text())
        self.assertIn(str(new_source), new.read_text())

    def test_desktop_has_separate_renderer_and_engine_profiles(self):
        self.accept()
        records = manager.load(self.state)
        records['desktop'] = records['cli']
        manager.atomic_json(self.state / 'accepted.json', records)
        with patch.object(manager, 'official', return_value=self.official), patch.object(manager, 'desktop_interface', return_value='verified-bundle'), patch.object(manager.shutil, 'which', return_value='/synthetic/chatgpt'), patch.object(os, 'execve') as execute:
            manager.launch(self.state, 'desktop', [])
        _, arguments, env = execute.call_args.args
        self.assertEqual(env['CODEX_CLI_PATH'], str(self.engine))
        self.assertEqual(env['CODEX_HOME'], str(self.state / 'desktop-codex'))
        self.assertEqual(env['CODEX_ELECTRON_USER_DATA_PATH'], str(self.state / 'desktop-renderer'))
        self.assertIn('--user-data-dir=' + env['CODEX_ELECTRON_USER_DATA_PATH'], arguments)

    def test_unsupported_desktop_update_invalidates_jev(self):
        self.accept()
        record = manager.load(self.state)['cli']
        record['desktop_bundle_sha256'] = 'previous-bundle'
        with patch.object(manager, 'desktop_interface', side_effect=RuntimeError('override removed')):
            self.assertFalse(manager.matches(record, self.official))

    def test_desktop_bundle_requires_both_native_overrides(self):
        bundle = self.official.parent / 'app.asar'
        def write_bundle(script):
            data = script.encode()
            index = json.dumps({'files': {'.vite': {'files': {'build': {'files': {
                'main-fixture.js': {'offset': '0', 'size': len(data)}
            }}}}}}).encode()
            bundle.write_bytes(struct.pack('<4I', 4, len(index) + 8, len(index) + 4, len(index)) + index + data)
        write_bundle('rawValue:e.CODEX_CLI_PATH; CODEX_ELECTRON_USER_DATA_PATH')
        self.assertEqual(manager.desktop_interface(self.official), manager.digest(bundle))
        write_bundle('rawValue:e.CODEX_CLI_PATH;')
        with self.assertRaisesRegex(RuntimeError, 'not verified'):
            manager.desktop_interface(self.official)

    def test_unsupported_desktop_profile_does_not_attach_to_main_app(self):
        with patch.object(manager, 'official', return_value=self.official), patch.object(manager, 'desktop_interface', side_effect=RuntimeError('override removed')), patch.object(os, 'execve') as execute:
            with self.assertRaisesRegex(RuntimeError, 'override removed'):
                manager.launch(self.state, 'desktop', [])
        execute.assert_not_called()

    def test_no_rebuild_for_identical_installed_package(self):
        self.accept()
        with patch.object(manager, 'official', return_value=self.official), patch.object(manager, 'run', wraps=manager.run) as commands:
            manager.prepare(self.state, 'cli')
        self.assertFalse(any(call.args[0][0] in ('cargo', 'git', 'npm') for call in commands.call_args_list))

    def test_renderer_only_update_revalidates_without_rebuilding_engine(self):
        self.accept()
        records = manager.load(self.state)
        records['desktop'] = {**records['cli'], 'desktop_bundle_sha256': 'old-bundle'}
        manager.atomic_json(self.state / 'accepted.json', records)
        with patch.object(manager, 'official', return_value=self.official), patch.object(manager, 'desktop_interface', return_value='new-bundle'), patch.object(manager, 'validate'), patch.object(manager, 'run', wraps=manager.run) as commands:
            manager.prepare(self.state, 'desktop')
        self.assertEqual(manager.load(self.state)['desktop']['source'], str(self.source))
        self.assertEqual(manager.load(self.state)['desktop']['desktop_bundle_sha256'], 'new-bundle')
        self.assertFalse(any(call.args[0][0] in ('cargo', 'git', 'npm') for call in commands.call_args_list))

    def test_refuses_unrecognized_versions(self):
        self.official.write_text('#!/bin/sh\necho "unknown vendor version"\n')
        with self.assertRaisesRegex(RuntimeError, 'Unrecognized'):
            manager.version(self.official)

    def test_lock_normalization_changes_only_workspace_versions(self):
        root = self.root / 'release/codex-rs'
        root.mkdir(parents=True)
        (root / 'Cargo.toml').write_text('[workspace.package]\nversion = "0.162.0-alpha.2"\n')
        (root / 'Cargo.lock').write_text('version = 4\n[[package]]\nname = "codex-core"\nversion = "0.0.0"\n[[package]]\nname = "external"\nversion = "0.0.0"\nsource = "registry+https://example.invalid"\nchecksum = "sentinel"\n')
        manager.normalize_release_lock(root.parent)
        import tomllib
        packages = tomllib.loads((root / 'Cargo.lock').read_text())['package']
        self.assertEqual(packages[0]['version'], '0.162.0-alpha.2')
        self.assertEqual(packages[1]['version'], '0.0.0')
        self.assertEqual(packages[1]['checksum'], 'sentinel')

    def test_patch_selection_uses_actual_api_and_refuses_unknown_layout(self):
        path = self.source / 'codex-rs/core/src/compact_remote_v2.rs'
        path.parent.mkdir(parents=True)
        for parameters, expected in (
            ('replacement_step_context: Context, world_state: World', 'integration.patch'),
            ('fallback_step_context: Context, initial_context_injection: Injection', 'integration-alpha.patch'),
        ):
            with self.subTest(expected=expected):
                path.write_text('async fn run_remote_compact_task_inner_impl(' + parameters + ') -> CodexResult<()> {}')
                self.assertEqual(manager.integration_variant(self.source, require_source=True), expected)
        path.write_text('async fn run_remote_compact_task_inner_impl(new_protocol: Protocol) -> CodexResult<()> {}')
        with self.assertRaisesRegex(RuntimeError, 'Unrecognized compaction API'):
            manager.integration_variant(self.source, require_source=True)

    def test_cli_failure_does_not_skip_desktop_update(self):
        calls = []
        def prepare(_state, target):
            calls.append(target)
            if target == 'cli':
                raise RuntimeError('patch conflict')
        with patch.object(manager, 'prepare', side_effect=prepare), patch('sys.argv', ['manage.py', '--state', str(self.state), 'update']), patch.dict(os.environ):
            with self.assertRaisesRegex(RuntimeError, 'patch conflict'):
                manager.main()
        self.assertEqual(calls, ['cli', 'desktop'])
        self.assertTrue((self.state / 'last-failure-cli.json').exists())


class InstallerOwnershipTests(unittest.TestCase):
    def test_foreign_desktop_entry_blocks_all_mutations(self):
        spec = importlib.util.spec_from_file_location('jev_installer', PATH.parent / 'install.py')
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            desktop = home / '.local/share/applications/chatgpt-jev.desktop'
            desktop.parent.mkdir(parents=True)
            desktop.write_text('foreign desktop sentinel')
            with self.assertRaisesRegex(RuntimeError, 'unowned'):
                installer.install(home)
            self.assertFalse((home / '.local/bin/codex-jev').exists())
            self.assertEqual(desktop.read_text(), 'foreign desktop sentinel')

    def test_install_is_idempotent_and_does_not_override_official_entry(self):
        spec = importlib.util.spec_from_file_location('jev_installer', PATH.parent / 'install.py')
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            official = home / '.local/share/applications/chatgpt.desktop'
            official.parent.mkdir(parents=True)
            official.write_text('official sentinel')
            installer.install(home)
            installer.install(home)
            self.assertEqual(official.read_text(), 'official sentinel')
            hook = home / '.config/omarchy/hooks/post-update.d/codex-jev-update.hook'
            self.assertIn('systemd-run --user', hook.read_text())
            self.assertIn('is-active --quiet', hook.read_text())


if __name__ == '__main__':
    unittest.main()
