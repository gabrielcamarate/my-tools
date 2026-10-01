"""Pinned upstream Playwright SDK, CLI and MCP; transport-only provider patch."""
import hashlib
import json
from pathlib import Path
import tempfile

from .core import ROOT, ToolError, atomic_json, checked, read_json
from .pruner import build_env

PATCH = ROOT / 'patches/jev-browser-openrouter.patch'
PATCH_PATHS = {'src/decision.ts', 'src/provider.ts', 'test/decision.test.mjs',
               'test/openrouter-provider.test.mjs', 'skills/jev-browser/SKILL.md'}
BUILD = 'tsc && esbuild src/dom.ts --bundle --platform=browser --format=iife --global-name=JevDOM --outfile=dist/dom.bundle.cjs'
PREBUILD = 'node --input-type=module -e "import { rmSync } from \'node:fs\'; rmSync(\'dist\', { recursive: true, force: true });"'


def provider_hash():
    return hashlib.sha256(PATCH.read_bytes()).hexdigest()


def apply_provider(source):
    paths = {line.split('\t')[-1] for line in checked(['git', 'apply', '--numstat', str(PATCH)]).splitlines()}
    if paths != PATCH_PATHS:
        raise ToolError('Patch excede transporte/testes/orientação de provedor revisados')
    checked(['git', '-C', str(source), 'apply', '--check', str(PATCH)])
    checked(['git', '-C', str(source), 'apply', str(PATCH)])


def hashes(path):
    source = Path(path) / 'source'
    names = set(filter(None, checked(['git', '-C', str(source), 'ls-files', '-z']).split('\0'))) | PATCH_PATHS
    files = [source / p for p in sorted(names)] + sorted((source / 'dist').rglob('*'))
    return {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}


def contract(source, compiled=True):
    package = json.loads((source / 'package.json').read_text())
    if (package.get('name') != '@tontoko/jev-browser'
            or package.get('bin') != {'jev-browser': 'dist/cli.js', 'jev-browser-mcp': 'dist/mcp-stdio.js'}
            or package.get('scripts', {}).get('build') != BUILD
            or package.get('scripts', {}).get('prebuild') != PREBUILD
            or package.get('engines', {}).get('node') != '>=22.15.0'):
        raise ToolError('Contrato upstream de Browser mudou; revisão necessária')
    names = ['skills/jev-browser/SKILL.md', 'docs/screen-review.md', 'LICENSE']
    if compiled:
        names += ['dist/cli.js', 'dist/mcp-stdio.js', 'dist/index.js', 'dist/provider.js', 'dist/dom.bundle.cjs']
    if any(not (source / name).is_file() for name in names):
        raise ToolError('Interface oficial Browser incompleta')
    if compiled and any(not ((source / name).stat().st_mode & 0o111) for name in ('dist/cli.js', 'dist/mcp-stdio.js')):
        raise ToolError('Entrypoint oficial sem permissão de execução')


def prepare(path, spec, commit):
    source = Path(path) / 'source'
    checked(['git', 'init', '--quiet', str(source)])
    checked(['git', '-C', str(source), 'remote', 'add', 'origin', spec['repository']])
    checked(['git', '-C', str(source), 'fetch', '--quiet', '--depth', '1', 'origin', commit])
    checked(['git', '-C', str(source), 'checkout', '--quiet', '--detach', 'FETCH_HEAD'])
    if checked(['git', '-C', str(source), 'rev-parse', 'HEAD']) != commit:
        raise ToolError('SHA recebido diverge do candidato')
    apply_provider(source)
    contract(source, compiled=False)
    env = build_env()
    checked(['npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund'], cwd=source, env=env)
    checked(['npm', 'run', 'build'], cwd=source, env=env)
    for name in ('dist/cli.js', 'dist/mcp-stdio.js'):
        (source / name).chmod(0o755)
    contract(source)
    atomic_json(Path(path) / 'installation.json', {'schema_version': 1, 'commit': commit,
        'repository': spec['repository'], 'installer': spec['installer'],
        'provider_patch_sha256': provider_hash(), 'hashes': hashes(path)})


def check(path, spec, commit, smoke=True):
    path = Path(path)
    record = read_json(path / 'installation.json')
    if any(record.get(k) != v for k, v in (('commit', commit), ('repository', spec['repository']),
            ('installer', spec['installer']), ('provider_patch_sha256', provider_hash()))):
        raise ToolError('Browser diverge da origem/versão/patch aceito')
    if record.get('hashes') != hashes(path):
        raise ToolError('Fonte ou compilação Browser alterada')
    source = path / 'source'
    contract(source)
    if smoke:
        with tempfile.TemporaryDirectory(prefix='my-tools-browser-check-') as folder:
            env = build_env()
            env.update(HOME=folder, OPENROUTER_API_KEY='')
            checked(['node', '--test', 'test/decision.test.mjs', 'test/openrouter-provider.test.mjs'], cwd=source, env=env)
            checked(['node', str(source / 'dist/cli.js'), '--help'], cwd=folder, env=env)
            checked(['node', str(ROOT / 'scripts/check_browser_mcp.mjs'), str(source)], cwd=folder, env=env)
