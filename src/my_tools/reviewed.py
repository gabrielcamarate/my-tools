"""Reviewed official CLIs: common lifecycle, individual provider-only patches."""
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

from .core import ROOT, ToolError, atomic_json, checked, read_json
from .pruner import build_env
from . import jeval


def interface(spec):
    value = spec['interface']
    if value['kind'] not in {'npm', 'pnpm', 'bun', 'python', 'rust'}:
        raise ToolError('Interface não revisada')
    for path in [value['manifest'], *value['commands'].values(), *value['skills'], *value['patch_paths']]:
        if Path(path).is_absolute() or '..' in Path(path).parts:
            raise ToolError('Caminho de interface inválido')
    return value


def patch_path(spec):
    return ROOT / 'patches' / (next(iter(interface(spec)['commands'])) + '-openrouter.patch')


def contract(source, spec):
    value = interface(spec)
    if hashlib.sha256((source / value['manifest']).read_bytes()).hexdigest() != value['manifest_sha256']:
        raise ToolError('Manifesto/dependências mudaram; revisão necessária')
    if any(not (source / path / 'SKILL.md').is_file() for path in value['skills']):
        raise ToolError('Skill upstream ausente')


def hashes(path, spec):
    source = Path(path) / 'source'
    names = set(filter(None, checked(['git', '-C', str(source), 'ls-files', '-z']).split('\0')))
    names.update(interface(spec)['patch_paths'])
    for base in ('dist', 'packages/core/dist', 'packages/cli/dist'):
        names.update(str(p.relative_to(source)) for p in (source / base).rglob('*') if p.is_file())
    if interface(spec)['kind'] == 'rust':
        names.update(interface(spec)['commands'].values())
    return {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
            for name in sorted(names) if (source / name).is_file()}


def toolchain(kind):
    if kind == 'rust':
        try:
            cargo = checked(['mise', 'where', 'rust@1.90.0'])
        except ToolError as exc:
            raise ToolError('Instale Rust 1.90.0 pelo mise, sem alterar versões globais') from exc
        return ['mise', 'exec', 'rust@1.90.0', '--', 'cargo']
    return ['npx', '--yes', 'bun@1.3.5'] if kind == 'bun' else ['npx', '--yes', 'pnpm@10.32.1']


def build(source, spec):
    kind = interface(spec)['kind']
    env = build_env()
    if kind == 'python':
        return
    if kind == 'rust':
        cargo = toolchain(kind)
        checked([*cargo, 'build', '--locked', '--release'], cwd=source, env=env, timeout=600)
    elif kind == 'bun':
        bun = toolchain(kind)
        checked([*bun, 'install', '--frozen-lockfile', '--ignore-scripts'], cwd=source, env=env)
        # Upstream build scripts invoke bun themselves. Expose this pinned executable only.
        bun_exe = checked(['npx', '--yes', '--package', 'bun@1.3.5', 'which', 'bun'], env=env)
        env['PATH'] = str(Path(bun_exe).parent) + os.pathsep + env['PATH']
        checked([*bun, 'run', 'build'], cwd=source, env=env)
    else:
        install = ['npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund'] if kind == 'npm' else [*toolchain(kind), 'install', '--frozen-lockfile', '--ignore-scripts']
        checked(install, cwd=source, env=env)
        checked(['npm', 'run', 'build'], cwd=source, env=env)
    for path in interface(spec)['commands'].values():
        target = source / path
        if not target.is_file():
            raise ToolError('Entrypoint upstream não foi produzido')
        target.chmod(target.stat().st_mode | 0o111)


def prepare(path, spec, commit):
    path = Path(path)
    source = path / 'source'
    checked(['git', 'init', '--quiet', str(source)])
    checked(['git', '-C', str(source), 'remote', 'add', 'origin', spec['repository']])
    checked(['git', '-C', str(source), 'fetch', '--quiet', '--depth', '1', 'origin', commit])
    checked(['git', '-C', str(source), 'checkout', '--quiet', '--detach', 'FETCH_HEAD'])
    if checked(['git', '-C', str(source), 'rev-parse', 'HEAD']) != commit:
        raise ToolError('Origem recebida diverge')
    contract(source, spec)
    patch = patch_path(spec)
    paths = sorted(line.split('\t')[-1] for line in checked(['git', 'apply', '--numstat', str(patch)]).splitlines())
    if paths != interface(spec)['patch_paths']:
        raise ToolError('Patch excede o escopo de provedor revisado')
    checked(['git', '-C', str(source), 'apply', '--check', str(patch)])
    checked(['git', '-C', str(source), 'apply', str(patch)])
    build(source, spec)
    atomic_json(path / 'installation.json', {'schema_version': 1, 'commit': commit,
        'repository': spec['repository'], 'installer': spec['installer'],
        'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(), 'hashes': hashes(path, spec)})


def python_sync(source, environment):
    env = build_env()
    if (source / 'uv.lock').exists():
        env.update(UV_PROJECT_ENVIRONMENT=str(environment), UV_LINK_MODE='copy')
        checked([jeval.uv(), 'sync', '--project', str(source), '--frozen', '--no-dev',
                 '--no-editable', '--python', '3.12'], env=env)
    else:
        # SemDecide has no runtime dependencies; install only the pinned local source.
        checked([jeval.uv(), 'venv', '--python', '3.12', str(environment)], env=env)
        checked([jeval.uv(), 'pip', 'install', '--python', str(environment / 'bin/python'),
                 '--no-deps', str(source)], env=env)


def check(path, spec, commit, smoke=True):
    path = Path(path)
    record = read_json(path / 'installation.json')
    expected = {'commit': commit, 'repository': spec['repository'], 'installer': spec['installer'],
                'patch_sha256': hashlib.sha256(patch_path(spec).read_bytes()).hexdigest(),
                'hashes': hashes(path, spec)}
    if any(record.get(k) != v for k, v in expected.items()):
        raise ToolError('Fonte/compilação/provedor diverge da revisão aceita')
    contract(path / 'source', spec)
    if smoke:
        with tempfile.TemporaryDirectory(prefix='my-tools-offline-check-') as folder:
            env = build_env()
            env.update(HOME=folder)
            for name, target in interface(spec)['commands'].items():
                if interface(spec)['kind'] == 'python':
                    runtime = Path(folder) / 'venv'
                    python_sync(path / 'source', runtime)
                    exe = runtime / 'bin' / target
                else:
                    exe = path / 'source' / target
                checked([str(exe), '--help'], env=env, cwd=folder, timeout=30)


def registry(manager):
    path = manager.home / 'interfaces.json'
    value = read_json(path) if path.exists() else {'schema_version': 1, 'tools': {}}
    if set(value) != {'schema_version', 'tools'} or not isinstance(value['tools'], dict):
        raise ToolError('Registro de interfaces inválido')
    for name, entry in value['tools'].items():
        if manager.spec(name)['installer'] != 'reviewed-source-v1' or set(entry) != {'active', 'bin_dir', 'skills_dir', 'claude_dir'}:
            raise ToolError('Registro de interface inválido')
        manager.location(name, entry['active'])
        if any(not isinstance(entry[k], str) or not Path(entry[k]).is_absolute() for k in ('bin_dir', 'skills_dir', 'claude_dir')):
            raise ToolError('Destinos precisam ser absolutos')
    return value


def runtime(manager, name, commit, create=True):
    spec = manager.spec(name)
    path = manager.location(name, commit)
    check(path, spec, commit, smoke=False)
    if interface(spec)['kind'] != 'python':
        return path / 'source'
    base = manager.home / 'native' / name / commit
    env = base / 'venv'
    record = base / 'runtime.json'
    if record.exists():
        if read_json(record) != {'schema_version': 1, 'hashes': jeval.runtime_hashes(env)}:
            raise ToolError('Runtime Python diverge; preserve para diagnóstico')
    elif create:
        if env.exists():
            raise ToolError('Runtime Python incompleto preservado')
        try:
            python_sync(path / 'source', env)
            atomic_json(record, {'schema_version': 1, 'hashes': jeval.runtime_hashes(env)})
        except BaseException:
            shutil.rmtree(env, ignore_errors=True)
            raise
    else:
        raise ToolError('Runtime Python ausente')
    return env / 'bin'


def links(manager, name, entry, commit):
    spec = manager.spec(name)
    source = manager.location(name, commit) / 'source'
    base = manager.home / 'native' / name / commit / 'venv/bin' if interface(spec)['kind'] == 'python' else source
    pairs = [(Path(entry['bin_dir']) / cmd, base / target) for cmd, target in interface(spec)['commands'].items()]
    for path in interface(spec)['skills']:
        skill = Path(entry['skills_dir']) / Path(path).name
        pairs += [(skill, source / path), (Path(entry['claude_dir']) / skill.name, skill)]
    return pairs


def switch(manager, name, entry, commit):
    from .commands import replace_link, restore
    pairs = links(manager, name, entry, commit)
    previous = []
    for link, target in pairs:
        old = None
        if link.exists() or link.is_symlink():
            if not link.is_symlink() or not (
                (link.parent == Path(entry['claude_dir']) and os.readlink(link) == str(target))
                or link.resolve().is_relative_to(manager.home / 'tools' / name)
                or link.resolve().is_relative_to(manager.home / 'native' / name)):
                raise ToolError('CLI/skill externa preservada')
            old = os.readlink(link)
        previous.append((link, old))
    runtime(manager, name, commit)
    changed = []
    try:
        for (link, target), prior in zip(pairs, previous):
            if not target.exists():
                raise ToolError('Interface upstream ausente')
            replace_link(link, target)
            changed.append(prior)
    except BaseException:
        restore(changed)
        raise
    return previous


def integrate(manager, name, apply=False, bin_dir=None):
    manager.resolve(name)
    commit = manager.state()['tools'][name]['active']
    entry = {'active': commit,
             'bin_dir': str(Path(bin_dir).expanduser().resolve() if bin_dir else Path.home() / '.local/bin'),
             'skills_dir': str(Path.home() / '.agents/skills'), 'claude_dir': str(Path.home() / '.claude/skills')}
    value = registry(manager)
    old = value['tools'].get(name)
    if old and any(old[k] != entry[k] for k in ('bin_dir', 'skills_dir', 'claude_dir')):
        raise ToolError('Destinos já registrados')
    if apply:
        from .commands import restore
        changes = switch(manager, name, entry, commit)
        value['tools'][name] = entry
        try:
            atomic_json(manager.home / 'interfaces.json', value)
        except BaseException:
            restore(changes)
            raise
    return {'tool': name, 'active': commit, 'commands': list(interface(manager.spec(name))['commands']),
            'skills': [Path(p).name for p in interface(manager.spec(name))['skills']],
            'status': 'integrated' if apply else 'planned'}


def synchronize(manager, name, commit):
    value = registry(manager)
    old = value['tools'].get(name)
    if old:
        from .commands import restore
        updated = {**old, 'active': commit}
        changes = switch(manager, name, updated, commit)
        value['tools'][name] = updated
        try:
            atomic_json(manager.home / 'interfaces.json', value)
        except BaseException:
            restore(changes)
            raise


def diagnose(manager, name, commit):
    entry = registry(manager)['tools'].get(name)
    if not entry:
        return {}
    if entry['active'] != commit or any(not link.is_symlink() or link.resolve() != target.resolve()
                                      for link, target in links(manager, name, entry, commit)):
        raise ToolError('Interface diverge do ativo')
    runtime(manager, name, commit, create=False)
    return {'official_commands': list(interface(manager.spec(name))['commands']),
            'official_skills': [Path(p).name for p in interface(manager.spec(name))['skills']],
            'hook_status': 'optional_not_enabled' if name in {'jev-axi', 'jev-spec', 'snifftest'} else 'not_required',
            'mcp_status': 'not_registered_by_cli_integration'}


def repair(manager, name):
    """Rebuild the active pinned source; retain the original on any failed stage."""
    import uuid
    commit = manager.state()['tools'].get(name, {}).get('active')
    if not commit:
        raise ToolError('Instale a ferramenta antes de reparar')
    spec = manager.spec(name)
    target = manager.location(name, commit)
    record = read_json(target / 'installation.json')
    if record.get('hashes') != hashes(target, spec):
        raise ToolError('Fonte modificada preservada; reparo recusado')
    stage = target.with_name('.repair-' + uuid.uuid4().hex)
    backup = target.with_name('.previous-' + uuid.uuid4().hex)
    native = manager.home / 'native' / name / commit
    native_backup = native.with_name('.previous-' + uuid.uuid4().hex)
    stage.mkdir(mode=0o700)
    replaced = False
    moved_native = False
    had_native = native.exists()
    try:
        prepare(stage, spec, commit)
        check(stage, spec, commit)
        os.replace(target, backup)
        try:
            os.replace(stage, target)
        except BaseException:
            os.replace(backup, target)
            raise
        replaced = True
        if interface(spec)['kind'] == 'python' and native.exists():
            os.replace(native, native_backup)
            moved_native = True
        synchronize(manager, name, commit)
    except BaseException:
        if replaced:
            shutil.rmtree(target)
            os.replace(backup, target)
            if interface(spec)['kind'] == 'python' and (moved_native or not had_native):
                shutil.rmtree(native, ignore_errors=True)
            if moved_native:
                os.replace(native_backup, native)
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(backup)
    if moved_native:
        shutil.rmtree(native_backup)
    return {'tool': name, 'active': commit, 'status': 'repaired'}
