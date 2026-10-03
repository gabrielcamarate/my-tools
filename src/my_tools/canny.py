"""Pinned official Canny CLI and hooks; provider-only adaptation."""
import hashlib
import json
import os
import shutil
from pathlib import Path
import tempfile

from .core import ROOT, ToolError, atomic_json, checked, read_json
from .pruner import build_env

PATCH = ROOT / 'patches/canny-openrouter.patch'
PATCH_PATHS = {'src/jev.ts', 'src/provider.ts', 'src/cli.ts', 'test/jev.test.ts',
               'test/setup.ts', 'test/openrouter-provider.test.ts'}
PNPM = ['npx', '--yes', 'pnpm@12.4.1']


def provider_hash():
    return hashlib.sha256(PATCH.read_bytes()).hexdigest()


def apply_provider(source):
    paths = {line.split('\t')[-1] for line in checked(
        ['git', 'apply', '--numstat', str(PATCH)]).splitlines()}
    if paths != PATCH_PATHS:
        raise ToolError('Patch excede o escopo de provedor revisado')
    checked(['git', '-C', str(source), 'apply', '--check', str(PATCH)])
    checked(['git', '-C', str(source), 'apply', str(PATCH)])


def hashes(path):
    source = Path(path) / 'source'
    tracked = checked(['git', '-C', str(source), 'ls-files', '-z']).split('\0')
    names = set(filter(None, tracked)) | PATCH_PATHS
    files = [source / p for p in sorted(names)] + sorted((source / 'dist').rglob('*'))
    return {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files if p.is_file()}


def contract(source, compiled=True):
    package = json.loads((source / 'package.json').read_text())
    if (package.get('name') != 'canny-warden'
            or package.get('bin') != {'canny': 'dist/cli.js'}
            or package.get('scripts', {}).get('test') != 'vitest run'
            or package.get('scripts', {}).get('type-check') != 'tsc -p tsconfig.test.json'
            or package.get('scripts', {}).get('build') != 'tsc'
            or package.get('packageManager') != 'pnpm@12.4.1'
            or package.get('dependencies', {})
            or package.get('engines', {}).get('node') != '>=22'):
        raise ToolError('Contrato de Canny mudou; revisão necessária')
    if compiled:
        for name in ('dist/cli.js', 'dist/jev.js', 'dist/provider.js', 'dist/hook.js'):
            if not (source / name).is_file():
                raise ToolError('CLI/hooks upstream incompletos')


def prepare(path, spec, commit):
    source = Path(path) / 'source'
    checked(['git', 'init', '--quiet', str(source)])
    checked(['git', '-C', str(source), 'remote', 'add', 'origin', spec['repository']])
    checked(['git', '-C', str(source), 'fetch', '--quiet', '--depth', '1', 'origin', commit])
    checked(['git', '-C', str(source), 'checkout', '--quiet', '--detach', 'FETCH_HEAD'])
    if checked(['git', '-C', str(source), 'rev-parse', 'HEAD']) != commit:
        raise ToolError('Commit recebido diverge do candidato')
    apply_provider(source)
    contract(source, compiled=False)
    env = build_env()
    checked([*PNPM, 'install', '--frozen-lockfile', '--ignore-scripts'], cwd=source, env=env)
    checked([*PNPM, 'run', 'build'], cwd=source, env=env)
    (source / 'dist/cli.js').chmod(0o755)
    contract(source)
    atomic_json(Path(path) / 'installation.json', {'schema_version': 1, 'commit': commit,
        'repository': spec['repository'], 'installer': spec['installer'],
        'provider_patch_sha256': provider_hash(), 'hashes': hashes(path)})


def check(path, spec, commit, smoke=True):
    path = Path(path)
    record = read_json(path / 'installation.json')
    if any(record.get(k) != v for k, v in (('commit', commit),
            ('repository', spec['repository']), ('installer', spec['installer']),
            ('provider_patch_sha256', provider_hash()))):
        raise ToolError('Canny diverge da origem/versão/patch aceito')
    if record.get('hashes') != hashes(path):
        raise ToolError('Fonte ou compilação do Canny foi alterada')
    source = path / 'source'
    contract(source)
    if smoke:
        with tempfile.TemporaryDirectory(prefix='my-tools-canny-check-') as folder:
            env = build_env()
            env.update(HOME=folder, TMPDIR=folder, OPENROUTER_API_KEY='')
            # Upstream CLI tests exercise the no-Canny-on-PATH installation first.
            # Preserve access to build tools even when they share its directory.
            original_path = env.get('PATH', '')
            bins = Path(folder) / 'bin'
            bins.mkdir()
            for name in ('node', 'npx', 'pnpm', 'git', 'bash', 'sh'):
                exe = shutil.which(name, path=original_path)
                if exe:
                    (bins / name).symlink_to(exe)
            paths = [p for p in original_path.split(os.pathsep)
                     if p and not (Path(p) / 'canny').exists()]
            env['PATH'] = os.pathsep.join([str(bins), *paths])
            checked([*PNPM, 'run', 'type-check'], cwd=source, env=env)
            checked([*PNPM, 'test'], cwd=source, env=env)
            checked(['node', str(source / 'dist/cli.js')], cwd=folder, env=env)
