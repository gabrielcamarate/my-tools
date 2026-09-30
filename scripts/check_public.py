"""Focused publication check; complements review and GitHub secret scanning."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
            re.compile(r"\bgithub_pat_[A-Za-z0-9_]{50,}\b"),
            re.compile(r"\bsk-or-v1-[a-f0-9]{32,}\b"),
            re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
            re.compile(r"/home/[A-Za-z0-9_-]+/")]


def main():
    paths = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    errors = []
    for name in filter(None, paths):
        path = ROOT / name
        if path.is_symlink():
            errors.append(f"Symlink versionado: {name}")
            continue
        if path.name == ".env" or path.name.startswith(".env.") or path.name in (".my-tools.json", "credentials.json"):
            errors.append(f"Configuração local versionada: {name}")
            continue
        try:
            text = path.read_text()
        except (UnicodeError, OSError):
            errors.append(f"Arquivo binário/ilegível requer revisão: {name}")
            continue
        if any(pattern.search(text) for pattern in PATTERNS):
            errors.append(f"Possível conteúdo privado: {name}")
    if (ROOT / "AGENTS.md").read_bytes() != (ROOT / "CLAUDE.md").read_bytes():
        errors.append("AGENTS/CLAUDE sem paridade")
    print("\n".join(errors) if errors else "Publicação: verificação focada passou")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
