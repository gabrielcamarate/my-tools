"""Install owned launchers and an Omarchy post-update hook, preserving third parties."""
import argparse
from pathlib import Path
import shlex
import subprocess
import sys

HERE = Path(__file__).resolve().parent
MARKER = '# my-tools: codex-jev-managed-v1'


def owned_write(path, text, executable=False):
    if path.is_symlink() or (path.exists() and MARKER not in path.read_text()):
        raise RuntimeError(f'Refusing to replace an unowned file: {path.name}')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.pending')
    if temporary.exists() or temporary.is_symlink():
        raise RuntimeError('Pending installer file requires reconciliation')
    temporary.write_text(text)
    temporary.chmod(0o700 if executable else 0o600)
    temporary.replace(path)


def install(home):
    manager = shlex.quote(str(HERE / 'manage.py'))
    destinations = [home / '.local/bin/codex-jev', home / '.local/bin/chatgpt-jev', home / '.local/share/applications/chatgpt-jev.desktop', home / '.config/omarchy/hooks/post-update.d/codex-jev-update.hook']
    for path in destinations:
        if path.is_symlink() or (path.exists() and MARKER not in path.read_text()):
            raise RuntimeError(f'Refusing to replace an unowned file: {path.name}')
        pending = path.with_name(path.name + '.pending')
        if pending.exists() or pending.is_symlink():
            raise RuntimeError('Pending installer file requires reconciliation')
    for command, target in (('codex-jev', 'cli'), ('chatgpt-jev', 'desktop')):
        path = home / '.local/bin' / command
        owned_write(path, '#!/bin/sh\n' + MARKER + '\nexec python3 ' + manager + ' launch --target ' + target + ' -- "$@"\n', True)
    desktop = home / '.local/share/applications/chatgpt-jev.desktop'
    command = str(home / '.local/bin/chatgpt-jev').replace('"', '\\"')
    owned_write(desktop, '[Desktop Entry]\n' + MARKER + '\nName=ChatGPT (Jev)\nComment=Experimental Jev compaction, separate technical conversations\nExec="' + command + '" %U\nIcon=chatgpt\nType=Application\nTerminal=false\nCategories=Utility;Development;\n')
    hook = home / '.config/omarchy/hooks/post-update.d/codex-jev-update.hook'
    # systemd owns the background job and its logs. No timers, polling or duplicate builds.
    owned_write(hook, '#!/bin/sh\n' + MARKER + '\nif systemctl --user is-active --quiet codex-jev-update.service; then\n  echo "Jev update already running"\n  exit 0\nfi\nexec systemd-run --user --collect --unit=codex-jev-update --description="Validate Codex Jev after Omarchy update" -p Nice=10 -p CPUQuota=200% -p MemoryMax=16G python3 ' + manager + ' update --target all\n', True)
    print('Installed codex-jev, chatgpt-jev, separate Desktop entry and post-update hook.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not args.apply:
        print('Preview: two owned launchers, a separate Desktop entry, one Omarchy post-update hook. Official app/CLI are unchanged.')
    else:
        install(Path.home())
