"""Fetch and verify official Siftr source; no agent-call wrapper."""
import hashlib
import os
from pathlib import Path
import tempfile
import tomllib
import venv

from .core import ToolError, atomic_json, checked, read_json


def hashes(path):
    source = Path(path) / "source"
    files = sorted((source / "siftr").rglob("*.py"))
    files += [source / "pyproject.toml"]
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def offline_env(home):
    # Offline checks neither inherit credentials nor source local dotenv files.
    return {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(home),
            "XDG_CONFIG_HOME": str(Path(home) / ".config"), "PYTHONDONTWRITEBYTECODE": "1"}


def prepare(path, spec, commit):
    source = Path(path) / "source"
    checked(["git", "init", "--quiet", str(source)])
    checked(["git", "-C", str(source), "remote", "add", "origin", spec["repository"]])
    checked(["git", "-C", str(source), "fetch", "--quiet", "--depth", "1", "origin", commit])
    checked(["git", "-C", str(source), "checkout", "--quiet", "--detach", "FETCH_HEAD"])
    actual = checked(["git", "-C", str(source), "rev-parse", "HEAD"])
    if actual != commit:
        raise ToolError("Commit recebido diverge do candidato")
    with (source / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream).get("project", {})
    if project.get("dependencies") != [] or project.get("name") != "siftr":
        raise ToolError("Upstream mudou dependências/contrato de instalação; instalador precisa de revisão")
    venv.EnvBuilder(with_pip=False).create(Path(path) / "venv")
    atomic_json(Path(path) / "installation.json", {"schema_version": 1, "commit": commit,
                "repository": spec["repository"], "installer": spec["installer"], "hashes": hashes(path)})


def check(path, spec, commit, smoke=True):
    path = Path(path)
    record = read_json(path / "installation.json")
    if any(record.get(k) != expected for k, expected in
           (("commit", commit), ("repository", spec["repository"]), ("installer", spec["installer"]))):
        raise ToolError("Instalação não corresponde à origem/versão/instalador")
    if hashes(path) != record.get("hashes"):
        raise ToolError("Arquivos instalados foram alterados; candidato não pode ser usado")
    if not (path / "venv/bin/python").exists():
        raise ToolError("Runtime Python ausente")
    if not smoke:
        return
    with tempfile.TemporaryDirectory(prefix="my-tools-offline-") as temporary:
        env = offline_env(temporary)
        # Execute the upstream CLI unchanged, only for offline contract checks.
        probe = 'import sys; sys.path.insert(0, sys.argv.pop(1)); from siftr.cli import main; raise SystemExit(main())'
        argv = [str(path / "venv/bin/python"), "-I", "-c", probe, str(path / "source")]
        help_text = checked([*argv, "search", "--help"], cwd=temporary, env=env, timeout=30)
        if not all(word in help_text for word in ("query", "--json", "--top", "--glob")):
            raise ToolError("Contrato da CLI oficial mudou")
        checked([*argv, "--version"], cwd=temporary, env=env, timeout=30)
        # Disable Python socket transports before loading upstream tests. This is
        # an offline check, not a security sandbox against hostile upstream code.
        suite = '''import socket, sys, runpy
def blocked(*args, **kwargs):
    raise OSError("network disabled for offline check")
socket.socket.connect = blocked
socket.socket.connect_ex = blocked
socket.create_connection = blocked
sys.path.insert(0, ".")
sys.argv = ["unittest", "discover", "-s", "tests", "-t", "."]
runpy.run_module("unittest", run_name="__main__")
'''
        checked([str(path / "venv/bin/python"), "-I", "-c", suite],
                cwd=path / "source", env=env, timeout=120)

