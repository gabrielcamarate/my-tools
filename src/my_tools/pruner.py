"""Build and verify the upstream Codex plugin without rewriting its wrapper."""
import hashlib
import json
import os
from pathlib import Path
import tempfile

from .core import ToolError, atomic_json, checked, read_json


def build_env():
    # Do not give package scripts credentials or an actual conversation.
    return {k: v for k, v in os.environ.items() if k in (
        "PATH", "HOME", "TMPDIR", "SYSTEMROOT")}


def hashes(path):
    source = Path(path) / "source"
    tracked = checked(["git", "-C", str(source), "ls-files", "-z"]).split("\0")
    files = [source / p for p in tracked if p]
    files += sorted((source / "dist").rglob("*"))
    return {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files if p.is_file()}


def contract(source):
    try:
        package = json.loads((source / "package.json").read_text())
        plugin = json.loads((source / ".codex-plugin/plugin.json").read_text())
        marketplace = json.loads((source / ".agents/plugins/marketplace.json").read_text())
        hooks = json.loads((source / "codex/hooks.json").read_text())
        valid = (package["name"] == "fast-jev-output"
                 and package.get("dependencies", {}) == {}
                 and package["scripts"]["build"] == "tsc"
                 and package["scripts"]["test"] == "vitest run"
                 and plugin["name"] == "jev-pruner"
                 and plugin["skills"] == "./codex/skills"
                 and plugin["hooks"] == "./codex/hooks.json"
                 and marketplace["name"] == "jev-pruner-codex"
                 and marketplace["plugins"] == [{"name": "jev-pruner", "source": {
                     "source": "local", "path": "."}}]
                 and hooks == {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{
                     "type": "command", "command": 'node "${PLUGIN_ROOT}/dist/codex/hook.js"',
                     "timeout": 5}]}]}})
        if not valid:
            raise ToolError("Contrato do plugin mudou; revisão necessária")
        for file in ("dist/codex/run.js", "dist/codex/hook.js", "codex/skills/jev-pruner/SKILL.md"):
            if not (source / file).is_file():
                raise ToolError("Plugin oficial não foi compilado completamente")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ToolError("Contrato do plugin inválido") from exc


def prepare(path, spec, commit):
    source = Path(path) / "source"
    checked(["git", "init", "--quiet", str(source)])
    checked(["git", "-C", str(source), "remote", "add", "origin", spec["repository"]])
    checked(["git", "-C", str(source), "fetch", "--quiet", "--depth", "1", "origin", commit])
    checked(["git", "-C", str(source), "checkout", "--quiet", "--detach", "FETCH_HEAD"])
    if checked(["git", "-C", str(source), "rev-parse", "HEAD"]) != commit:
        raise ToolError("Commit recebido diverge do candidato")
    package = json.loads((source / "package.json").read_text())
    if package.get("scripts", {}).get("build") != "tsc" or package.get("dependencies", {}):
        raise ToolError("Contrato de compilação mudou; revisão necessária")
    env = build_env()
    checked(["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"], cwd=source, env=env)
    checked(["npm", "run", "build"], cwd=source, env=env)
    contract(source)
    atomic_json(Path(path) / "installation.json", {"schema_version": 1, "commit": commit,
        "repository": spec["repository"], "installer": spec["installer"], "hashes": hashes(path)})


def check(path, spec, commit, smoke=True):
    path = Path(path)
    record = read_json(path / "installation.json")
    if any(record.get(k) != expected for k, expected in (
        ("commit", commit), ("repository", spec["repository"]), ("installer", spec["installer"]))):
        raise ToolError("Plugin não corresponde à origem/versão/instalador")
    if hashes(path) != record.get("hashes"):
        raise ToolError("Fonte ou compilação do plugin foi alterada")
    source = path / "source"
    contract(source)
    if smoke:
        with tempfile.TemporaryDirectory(prefix="my-tools-pruner-check-") as folder:
            env = build_env()
            env.update(HOME=folder, CODEX_HOME=str(Path(folder) / ".codex"))
            checked(["npm", "run", "typecheck"], cwd=source, env=env)
            checked(["npm", "test", "--", "--maxWorkers=2", "--minWorkers=1"],
                    cwd=source, env=env, timeout=180)
            # Real official wrapper with no key/history: exact passthrough.
            output = checked(["node", str(source / "dist/codex/run.js"), "--", "node", "-e",
                              'process.stdout.write("official-pruner-offline")'], cwd=folder, env=env)
            if output != "official-pruner-offline":
                raise ToolError("Wrapper oficial não preservou a saída")
