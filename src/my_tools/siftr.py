"""Adapter for Siftr's dependency-free Python CLI, pinned to Git commits."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib
import venv

from .core import ToolError, atomic_json, checked, read_json


BOOTSTRAP = '''import sys
from pathlib import Path
import os
if os.environ.get("MY_TOOLS_OFFLINE_CHECK") == "1":
    import socket
    def blocked(*args, **kwargs):
        raise OSError("network disabled for offline check")
    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    socket.create_connection = blocked
sys.path.insert(0, str(Path(__file__).resolve().parent / "source"))
from siftr import cli
# Credentials must come from the process environment. Never read project .env files.
cli.load_env = lambda: None
raise SystemExit(cli.main())
'''


def command(path, args):
    return [str(Path(path) / "venv/bin/python"), "-I", str(Path(path) / "runner.py"), *args]


def hashes(path):
    files = [Path(path) / "runner.py"]
    files += sorted((Path(path) / "source/siftr").rglob("*.py"))
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def offline_env(home):
    # Offline checks neither inherit credentials nor source local dotenv files.
    return {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(home),
            "XDG_CONFIG_HOME": str(Path(home) / ".config"), "PYTHONDONTWRITEBYTECODE": "1",
            "MY_TOOLS_OFFLINE_CHECK": "1"}


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
        raise ToolError("Upstream mudou dependências/contrato de instalação; adaptador precisa de revisão")
    venv.EnvBuilder(with_pip=False).create(Path(path) / "venv")
    (Path(path) / "runner.py").write_text(BOOTSTRAP)
    atomic_json(Path(path) / "installation.json", {"schema_version": 1, "commit": commit,
                "repository": spec["repository"], "adapter": spec["adapter"], "hashes": hashes(path)})


def check(path, spec, commit, smoke=True):
    path = Path(path)
    record = read_json(path / "installation.json")
    if any(record.get(k) != expected for k, expected in
           (("commit", commit), ("repository", spec["repository"]), ("adapter", spec["adapter"]))):
        raise ToolError("Instalação não corresponde à origem/versão/adaptador")
    if hashes(path) != record.get("hashes"):
        raise ToolError("Arquivos instalados foram alterados; candidato não pode ser usado")
    if not (path / "venv/bin/python").exists():
        raise ToolError("Runtime Python ausente")
    if not smoke:
        return
    with tempfile.TemporaryDirectory(prefix="my-tools-offline-") as temporary:
        env = offline_env(temporary)
        help_text = checked(command(path, ["search", "--help"]), cwd=temporary, env=env, timeout=30)
        if not all(word in help_text for word in ("query", "--json", "--top")):
            raise ToolError("Contrato do comando search mudou")
        checked(command(path, ["--version"]), cwd=temporary, env=env, timeout=30)
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


def search(path, root, query, top=10, json_output=False, stats=False):
    args = ["search", query, str(root), "--top", str(top)]
    if json_output:
        args.append("--json")
    if stats:
        args.append("--stats")
    try:
        return subprocess.run(command(path, args), cwd=root, check=False).returncode
    except OSError as exc:
        raise ToolError("Não foi possível iniciar Siftr") from exc
