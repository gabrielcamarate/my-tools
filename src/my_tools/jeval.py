"""Unmodified Jeval source, locked Python runtime and upstream skills."""
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import tomllib

from .core import ToolError, atomic_json, checked, read_json
from .pruner import build_env

SKILLS = ('jeval-handoff', 'jeval-instrument-service', 'jeval-labels-harvest',
          'jeval-calibration-audit', 'jeval-threshold-from-costs', 'jeval-drift-gate')


def uv():
    command = shutil.which('uv')
    if not command:
        raise ToolError('Jeval requer uv instalado pelo procedimento oficial')
    return command


def contract(source):
    data = tomllib.loads((source / 'pyproject.toml').read_text())['project']
    if (data['name'] != 'jeval-cli' or data['scripts'] != {'jeval': 'jeval.cli:main'}
            or data['requires-python'] != '>=3.10' or not (source / 'uv.lock').is_file()
            or set(data['dependencies']) != {'numpy>=1.26', 'pydantic>=2.6',
                                            'pyyaml>=6.0', 'typer>=0.12'}
            or any(not (source / 'skills' / name / 'SKILL.md').is_file() for name in SKILLS)):
        raise ToolError('Contrato Jeval mudou; revisão necessária')
    return data['version']


def hashes(path):
    source = Path(path) / 'source'
    if checked(['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=all']):
        raise ToolError('Fonte Jeval deve permanecer intacta, incluindo arquivos não rastreados')
    names = checked(['git', '-C', str(source), 'ls-files', '-z']).split('\0')
    return {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
            for name in sorted(filter(None, names))}


def sync(source, environment):
    env = build_env()
    env.update(UV_PROJECT_ENVIRONMENT=str(environment), UV_LINK_MODE='copy')
    checked([uv(), 'sync', '--project', str(source), '--frozen', '--no-dev',
             '--no-editable', '--python', '3.12'], env=env)
    return environment / 'bin/jeval'


def prepare(path, spec, commit):
    path = Path(path)
    source = path / 'source'
    checked(['git', 'init', '--quiet', str(source)])
    checked(['git', '-C', str(source), 'remote', 'add', 'origin', spec['repository']])
    checked(['git', '-C', str(source), 'fetch', '--quiet', '--depth', '1', 'origin', commit])
    checked(['git', '-C', str(source), 'checkout', '--quiet', '--detach', 'FETCH_HEAD'])
    if checked(['git', '-C', str(source), 'rev-parse', 'HEAD']) != commit:
        raise ToolError('Commit Jeval diverge do candidato')
    version = contract(source)
    atomic_json(path / 'installation.json', {'schema_version': 1, 'commit': commit,
        'repository': spec['repository'], 'installer': spec['installer'],
        'version': version, 'hashes': hashes(path)})


def check(path, spec, commit, smoke=True):
    path = Path(path)
    record = read_json(path / 'installation.json')
    if (any(record.get(k) != v for k, v in (('commit', commit),
            ('repository', spec['repository']), ('installer', spec['installer'])))
            or record.get('hashes') != hashes(path)
            or record.get('version') != contract(path / 'source')):
        raise ToolError('Fonte/origem Jeval foi alterada')
    if smoke:
        with tempfile.TemporaryDirectory(prefix='my-tools-jeval-check-') as folder:
            exe = sync(path / 'source', Path(folder) / 'venv')
            env = build_env()
            env.update(HOME=folder)
            if checked([str(exe), '--version'], env=env) != 'jeval ' + record['version']:
                raise ToolError('Versão da CLI Jeval diverge')
            checked([str(exe), 'demo', '--out-dir', str(Path(folder) / 'demo')], env=env)


def runtime_hashes(environment):
    # Include dependencies and entrypoints; omit mutable interpreter bytecode.
    return {str(p.relative_to(environment)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(environment.rglob('*'))
            if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts
            and p.suffix != '.pyc'}


def runtime(manager, commit, create=True):
    path = manager.location('jeval', commit)
    check(path, manager.spec('jeval'), commit, smoke=False)
    base = manager.home / 'native/jeval' / commit
    environment = base / 'venv'
    record = base / 'runtime.json'
    if record.exists():
        value = read_json(record)
        if value != {'schema_version': 1, 'commit': commit, 'source_hashes': hashes(path),
                     'runtime_hashes': runtime_hashes(environment)}:
            raise ToolError('Runtime Jeval alterado; integração preservada')
    elif create:
        # Build at its final absolute path: generated shebangs must survive activation.
        if environment.exists():
            raise ToolError('Runtime Jeval incompleto; diretório preservado para inspeção')
        try:
            exe = sync(path / 'source', environment)
            if checked([str(exe), '--version'], env=build_env()) != 'jeval ' + contract(path / 'source'):
                raise ToolError('CLI Jeval inválida')
            atomic_json(record, {'schema_version': 1, 'commit': commit, 'source_hashes': hashes(path),
                                'runtime_hashes': runtime_hashes(environment)})
        except BaseException:
            shutil.rmtree(environment, ignore_errors=True)
            raise
    else:
        raise ToolError('Runtime Jeval ausente')
    return environment / 'bin/jeval'


def registry(manager):
    path = manager.home / 'jeval.json'
    if not path.exists():
        return None
    entry = read_json(path)
    if set(entry) != {'schema_version', 'active', 'bin_dir', 'skills_dir', 'claude_dir'}:
        raise ToolError('Registro Jeval inválido')
    manager.location('jeval', entry['active'])
    if any(not isinstance(entry[k], str) or not Path(entry[k]).is_absolute()
           for k in ('bin_dir', 'skills_dir', 'claude_dir')):
        raise ToolError('Destinos Jeval precisam ser absolutos')
    return entry


def links(manager, entry, commit):
    source = manager.location('jeval', commit) / 'source'
    result = [(Path(entry['bin_dir']) / 'jeval',
               manager.home / 'native/jeval' / commit / 'venv/bin/jeval')]
    for name in SKILLS:
        skill = Path(entry['skills_dir']) / name
        result.extend([(skill, source / 'skills' / name),
                       (Path(entry['claude_dir']) / name, skill)])
    return result


def switch(manager, entry, commit):
    from .commands import replace_link, restore
    pairs = links(manager, entry, commit)
    changes = []
    # No runtime build or link mutation before all foreign targets are rejected.
    for link, target in pairs:
        old = None
        if link.exists() or link.is_symlink():
            owned = link.is_symlink() and (
                (link.parent == Path(entry['claude_dir']) and os.readlink(link) == str(target))
                or link.resolve().is_relative_to(manager.home / 'tools/jeval')
                or link.resolve().is_relative_to(manager.home / 'native/jeval'))
            if not owned:
                raise ToolError('CLI/skill Jeval externa preservada')
            old = os.readlink(link)
        changes.append((link, old))
    runtime(manager, commit)
    changed = []
    try:
        for (link, target), prior in zip(pairs, changes):
            if not target.exists():
                raise ToolError('CLI/skill Jeval oficial ausente')
            replace_link(link, target)
            changed.append(prior)
    except BaseException:
        restore(changed)
        raise
    return changes


def integrate(manager, name='jeval', apply=False, bin_dir=None):
    manager.resolve(name)
    commit = manager.state()['tools'][name]['active']
    entry = {'schema_version': 1, 'active': commit,
             'bin_dir': str(Path(bin_dir).expanduser().resolve() if bin_dir else Path.home() / '.local/bin'),
             'skills_dir': str(Path.home() / '.agents/skills'),
             'claude_dir': str(Path.home() / '.claude/skills')}
    old = registry(manager)
    if old and any(old[k] != entry[k] for k in ('bin_dir', 'skills_dir', 'claude_dir')):
        raise ToolError('Destinos Jeval já registrados; preserve a integração')
    if apply:
        from .commands import restore
        changes = switch(manager, entry, commit)
        try:
            atomic_json(manager.home / 'jeval.json', entry)
        except BaseException:
            restore(changes)
            raise
    return {'tool': name, 'active': commit, 'official_command': str(Path(entry['bin_dir']) / name),
            'official_skills': list(SKILLS), 'status': 'integrated' if apply else 'planned'}


def synchronize(manager, name, commit):
    entry = registry(manager)
    if entry:
        from .commands import restore
        updated = {**entry, 'active': commit}
        changes = switch(manager, updated, commit)
        try:
            atomic_json(manager.home / 'jeval.json', updated)
        except BaseException:
            restore(changes)
            raise


def diagnose(manager, name, commit):
    entry = registry(manager)
    if not entry:
        return {}
    if entry['active'] != commit or any(not link.is_symlink() or link.resolve() != target.resolve()
                                      for link, target in links(manager, entry, commit)):
        raise ToolError('Integração Jeval diverge da versão ativa')
    runtime(manager, commit, create=False)
    return {'official_command': str(Path(entry['bin_dir']) / name),
            'official_skills': list(SKILLS), 'credential_required': False,
            'hook_status': 'not_required', 'mcp_status': 'not_provided_upstream'}
