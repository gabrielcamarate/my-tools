"""Publish the upstream CLI and complete skill; no operation wrapper."""
import os
from pathlib import Path
import uuid

from .core import ToolError, atomic_json, read_json

NAME = 'jev-test-filter'
FIELDS = {NAME: ('command', 'skill'), 'jev-browser': ('command', 'mcp_command', 'skill'), 'canny': ('command',)}
SKILLS = {NAME: NAME, 'jev-browser': 'jev-browser-playwright'}


def targets(manager, commit, name=NAME):
    source = manager.location(name, commit) / 'source'
    if name == 'canny':
        return [source / 'dist/cli.js']
    return ([source / 'dist/cli.js', source / 'dist/mcp-stdio.js', source / 'skills/jev-browser']
            if name == 'jev-browser' else [source / 'dist/cli.js', source / 'skills' / NAME])


def registry(manager):
    path = manager.home / 'commands.json'
    value = read_json(path) if path.exists() else {'schema_version': 1, 'tools': {}}
    if set(value) != {'schema_version', 'tools'} or value['schema_version'] != 1 or not isinstance(value['tools'], dict):
        raise ToolError('Registro de CLI inválido')
    for name, entry in value['tools'].items():
        if name not in FIELDS or not isinstance(entry, dict) or set(entry) not in (set(FIELDS[name]) | {'active'}, set(FIELDS[name]) | ({'active', 'claude_skill'} if name in SKILLS else {'active'})):
            raise ToolError('Registro de CLI inválido')
        manager.location(name, entry['active'])
        if any(not isinstance(entry[k], str) or not Path(entry[k]).is_absolute() for k in (*FIELDS[name], *(['claude_skill'] if 'claude_skill' in entry else []))):
            raise ToolError('Destinos da CLI precisam de caminhos absolutos')
    return value


def switch(manager, entry, commit, name=NAME):
    links = [Path(entry[k]) for k in FIELDS[name]]
    dests = targets(manager, commit, name)
    root = manager.home / 'tools' / name
    if 'claude_skill' in entry:
        links.append(Path(entry['claude_skill']))
        dests.append(Path(entry['skill']))
    previous = []
    # Preflight every destination before modifying any link.
    for link, dest in zip(links, dests):
        is_claude = 'claude_skill' in entry and link == Path(entry['claude_skill'])
        if not is_claude and not dest.exists():
            raise ToolError('CLI/skill oficial ausente')
        if link.exists() or link.is_symlink():
            owned = link.is_symlink() and (os.readlink(link) == entry['skill'] if is_claude else link.resolve().is_relative_to(root))
            if not owned:
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
    if name not in FIELDS:
        raise ToolError('CLI ainda não registrada')
    manager.resolve(name)
    commit = manager.state()['tools'][name]['active']
    folder = Path(bin_dir).expanduser().resolve() if bin_dir else Path.home() / '.local/bin'
    entry = {'command': str(folder / name), 'active': commit}
    if name in SKILLS:
        entry['skill'] = str(Path.home() / '.agents/skills' / SKILLS[name])
        entry['claude_skill'] = str(Path.home() / '.claude/skills' / SKILLS[name])
    if name == 'jev-browser':
        entry['mcp_command'] = str(folder / 'jev-browser-mcp')
    value = registry(manager)
    old = value['tools'].get(name)
    if old and any(old[k] != entry[k] for k in (*FIELDS[name], *(['claude_skill'] if 'claude_skill' in old else []))):
        raise ToolError('Destinos já registrados; preserve a integração existente')
    if apply:
        changes = switch(manager, entry, commit, name)
        value['tools'][name] = entry
        try:
            atomic_json(manager.home / 'commands.json', value)
        except BaseException:
            restore(changes)
            raise
    return {'tool': name, **entry, 'status': 'integrated' if apply else 'planned'}


def synchronize(manager, name, commit):
    if name not in FIELDS:
        return
    value = registry(manager)
    entry = value['tools'].get(name)
    if entry:
        changes = switch(manager, entry, commit, name)
        entry['active'] = commit
        try:
            atomic_json(manager.home / 'commands.json', value)
        except BaseException:
            restore(changes)
            raise


def diagnose(manager, name, commit):
    if name not in FIELDS:
        return {}
    entry = registry(manager)['tools'].get(name)
    if not entry:
        return {}
    if entry['active'] != commit or any(not Path(entry[k]).is_symlink()
            or Path(entry[k]).resolve() != dest.resolve()
            for k, dest in zip(FIELDS[name], targets(manager, commit, name))):
        raise ToolError('Integração CLI/skill diverge da revisão ativa')
    if 'claude_skill' in entry:
        link = Path(entry['claude_skill'])
        if not link.is_symlink() or os.readlink(link) != entry['skill'] or link.resolve() != Path(entry['skill']).resolve():
            raise ToolError('Skill Claude diverge do link gerenciado')
    if name == 'canny':
        return {'official_command': entry['command'], 'hook_status': 'project_activation_and_host_trust_not_verified'}
    return {'official_command': entry['command'], 'official_skill': entry['skill'],
            'claude_skill_status': 'linked' if 'claude_skill' in entry else 'not_registered',
            **({'official_claude_skill': entry['claude_skill']} if 'claude_skill' in entry else {}),
            **({'official_mcp_command': entry['mcp_command']} if name == 'jev-browser' else {})}
