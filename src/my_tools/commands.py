"""Publish the upstream CLI and complete skill; no operation wrapper."""
import os
from pathlib import Path
import uuid

from .core import ToolError, atomic_json, read_json

NAME = 'jev-test-filter'


def targets(manager, commit):
    source = manager.location(NAME, commit) / 'source'
    return [source / 'dist/cli.js', source / 'skills' / NAME]


def registry(manager):
    path = manager.home / 'commands.json'
    value = read_json(path) if path.exists() else {'schema_version': 1, 'tools': {}}
    if set(value) != {'schema_version', 'tools'} or value['schema_version'] != 1 or not isinstance(value['tools'], dict):
        raise ToolError('Registro de CLI inválido')
    for name, entry in value['tools'].items():
        if name != NAME or not isinstance(entry, dict) or set(entry) != {'command', 'skill', 'active'}:
            raise ToolError('Registro de CLI inválido')
        manager.location(name, entry['active'])
        if any(not isinstance(entry[k], str) or not Path(entry[k]).is_absolute() for k in ('command', 'skill')):
            raise ToolError('Destinos da CLI precisam de caminhos absolutos')
    return value


def switch(manager, entry, commit):
    links = [Path(entry[k]) for k in ('command', 'skill')]
    dests = targets(manager, commit)
    root = manager.home / 'tools' / NAME
    previous = []
    # Preflight every destination before modifying either one.
    for link, dest in zip(links, dests):
        if not dest.exists():
            raise ToolError('CLI/skill oficial ausente')
        if link.exists() or link.is_symlink():
            if not link.is_symlink() or not link.resolve().is_relative_to(root):
                raise ToolError('CLI/skill ocupada por instalação externa; preservada')
            previous.append(os.readlink(link))
        else:
            previous.append(None)
    changed = []
    try:
        for link, dest, old in zip(links, dests, previous):
            replace_link(link, dest)
            changed.append((link, old))
    except BaseException:
        restore(changed)
        raise
    return list(zip(links, previous))


def replace_link(link, dest):
    link.parent.mkdir(parents=True, exist_ok=True)
    temp = link.with_name(f'.{NAME}-{uuid.uuid4().hex}')
    try:
        temp.symlink_to(dest)
        os.replace(temp, link)
    finally:
        temp.unlink(missing_ok=True)


def restore(changes):
    for link, old in reversed(changes):
        if old is None:
            link.unlink(missing_ok=True)
        else:
            replace_link(link, old)


def integrate(manager, name, apply=False, bin_dir=None):
    if name != NAME:
        raise ToolError('CLI ainda não registrada')
    manager.resolve(name)
    commit = manager.state()['tools'][name]['active']
    folder = Path(bin_dir).expanduser().resolve() if bin_dir else Path.home() / '.local/bin'
    entry = {'command': str(folder / NAME), 'skill': str(Path.home() / '.agents/skills' / NAME), 'active': commit}
    value = registry(manager)
    old = value['tools'].get(name)
    if old and any(old[k] != entry[k] for k in ('command', 'skill')):
        raise ToolError('Destinos já registrados; preserve a integração existente')
    if apply:
        changes = switch(manager, entry, commit)
        value['tools'][name] = entry
        try:
            atomic_json(manager.home / 'commands.json', value)
        except BaseException:
            restore(changes)
            raise
    return {'tool': name, **entry, 'status': 'integrated' if apply else 'planned'}


def synchronize(manager, name, commit):
    if name != NAME:
        return
    value = registry(manager)
    entry = value['tools'].get(name)
    if entry:
        changes = switch(manager, entry, commit)
        entry['active'] = commit
        try:
            atomic_json(manager.home / 'commands.json', value)
        except BaseException:
            restore(changes)
            raise


def diagnose(manager, name, commit):
    if name != NAME:
        return {}
    entry = registry(manager)['tools'].get(name)
    if not entry:
        return {}
    if entry['active'] != commit or any(not Path(entry[k]).is_symlink()
            or Path(entry[k]).resolve() != dest.resolve()
            for k, dest in zip(('command', 'skill'), targets(manager, commit))):
        raise ToolError('Integração CLI/skill diverge da revisão ativa')
    return {'official_command': entry['command'], 'official_skill': entry['skill']}
