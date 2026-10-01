"""Pinned official Test Filter source; provider-only adaptation."""
import hashlib
import json
from pathlib import Path
import tempfile

from .core import ROOT, ToolError, atomic_json, checked, read_json
from .pruner import build_env

PATCH = ROOT / 'patches/jev-test-filter-openrouter.patch'
PATCH_PATHS = {'src/jev.ts', 'src/provider.ts', 'src/cli.ts', 'test/jev.test.ts',
               'test/cli.test.ts', 'test/openrouter-provider.test.ts',
               'skills/jev-test-filter/SKILL.md'}


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


def contract(source):
    package = json.loads((source / 'package.json').read_text())
    if (package.get('name') != 'jev-test-filter'
            or package.get('bin') != {'jev-test-filter': 'dist/cli.js'}
            or package.get('scripts', {}).get('test') != 'node --test "test/*.test.ts"'
            or package.get('scripts', {}).get('build') != 'tsc && node -e "require(\'fs\').chmodSync(\'dist/cli.js\', 0o755)"'
            or package.get('engines', {}).get('node') != '>=24'):
        raise ToolError('Contrato de Test Filter mudou; revisão necessária')
    for name in ('dist/cli.js', 'dist/jev.js', 'dist/provider.js',
                 'skills/jev-test-filter/SKILL.md', 'skills/jev-test-filter/references/runners.md',
                 'skills/jev-test-filter/references/ci.md'):
        if not (source / name).is_file():
            raise ToolError('CLI ou skill upstream incompleta')


def prepare(path, spec, commit):
    source = Path(path) / 'source'
    checked(['git', 'init', '--quiet', str(source)])
    checked(['git', '-C', str(source), 'remote', 'add', 'origin', spec['repository']])
    checked(['git', '-C', str(source), 'fetch', '--quiet', '--depth', '1', 'origin', commit])
    checked(['git', '-C', str(source), 'checkout', '--quiet', '--detach', 'FETCH_HEAD'])
    if checked(['git', '-C', str(source), 'rev-parse', 'HEAD']) != commit:
        raise ToolError('Commit recebido diverge do candidato')
    apply_provider(source)
    # Verify build script before executing any package script.
    package = json.loads((source / 'package.json').read_text())
    if package.get('scripts', {}).get('build') != 'tsc && node -e "require(\'fs\').chmodSync(\'dist/cli.js\', 0o755)"':
        raise ToolError('Contrato de compilação mudou; revisão necessária')
    env = build_env()
    checked(['pnpm', 'install', '--frozen-lockfile', '--ignore-scripts'], cwd=source, env=env)
    checked(['pnpm', 'run', 'build'], cwd=source, env=env)
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
        raise ToolError('Test Filter diverge da origem/versão/patch aceito')
    if record.get('hashes') != hashes(path):
        raise ToolError('Fonte ou compilação do Test Filter foi alterada')
    source = path / 'source'
    contract(source)
    if smoke:
        with tempfile.TemporaryDirectory(prefix='my-tools-test-filter-check-') as folder:
            env = build_env()
            env.update(HOME=folder, OPENROUTER_API_KEY='')
            checked(['pnpm', 'run', 'typecheck'], cwd=source, env=env)
            checked(['pnpm', 'test'], cwd=source, env=env)
            checked(['node', str(source / 'dist/cli.js'), '--help'], cwd=folder, env=env)
