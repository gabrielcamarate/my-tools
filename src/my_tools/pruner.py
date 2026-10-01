"""Build and verify the upstream Codex plugin without rewriting its wrapper."""
import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path
import tempfile

from .core import ROOT, ToolError, atomic_json, checked, read_json

PATCH = ROOT / "patches/jev-pruner-openrouter.patch"


def provider_hash():
    return hashlib.sha256(PATCH.read_bytes()).hexdigest()


def apply_provider(source):
    paths = {line.split("\t")[-1] for line in checked(
        ["git", "apply", "--numstat", str(PATCH)]).splitlines()}
    if paths != {"src/codex/run.ts", "src/codex/prune.ts", "src/codex/provider.ts",
                 "codex/skills/jev-pruner/SKILL.md", "tests/codex.test.ts",
                 "tests/codex-boundaries.test.ts", "tests/openrouter-provider.test.ts"}:
        raise ToolError("Patch excede o escopo de provedor revisado")
    checked(["git", "-C", str(source), "apply", "--check", str(PATCH)])
    checked(["git", "-C", str(source), "apply", str(PATCH)])


def build_env():
    # Do not give package scripts credentials or an actual conversation.
    return {k: v for k, v in os.environ.items() if k in (
        "PATH", "HOME", "TMPDIR", "SYSTEMROOT")}


def hashes(path):
    source = Path(path) / "source"
    tracked = checked(["git", "-C", str(source), "ls-files", "-z"]).split("\0")
    files = [source / p for p in tracked if p]
    files += [source / p for p in ("src/codex/provider.ts", "tests/openrouter-provider.test.ts")
              if p not in tracked]
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
    # Conflicting upstream changes stop installation before activation.
    apply_provider(source)
    checked(["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"], cwd=source, env=env)
    checked(["npm", "run", "build"], cwd=source, env=env)
    contract(source)
    atomic_json(Path(path) / "installation.json", {"schema_version": 1, "commit": commit,
        "repository": spec["repository"], "installer": spec["installer"],
        "provider_patch_sha256": provider_hash(), "hashes": hashes(path)})


def check(path, spec, commit, smoke=True, verify_provider=True):
    path = Path(path)
    record = read_json(path / "installation.json")
    if any(record.get(k) != expected for k, expected in (
        ("commit", commit), ("repository", spec["repository"]), ("installer", spec["installer"]))):
        raise ToolError("Plugin não corresponde à origem/versão/instalador")
    if hashes(path) != record.get("hashes"):
        raise ToolError("Fonte ou compilação do plugin foi alterada")
    if verify_provider and record.get("provider_patch_sha256") != provider_hash():
        raise ToolError("Ajuste de provedor pendente; execute repair jev-pruner")
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


def rebuild(manager):
    """Repair the same upstream SHA, restoring source/cache on failure."""
    from . import plugins
    name = plugins.NAME
    commit = manager.state()["tools"].get(name, {}).get("active")
    if not commit:
        raise ToolError("Instale o plugin antes de reparar")
    target = manager.location(name, commit)
    spec = manager.spec(name)
    check(target, spec, commit, smoke=False, verify_provider=False)
    entry = plugins.registry(manager)["tools"].get(name)
    if entry:
        plugins.ownership(target / "source")
    stage = target.with_name(f".repair-{uuid.uuid4().hex}")
    backup = target.with_name(f".previous-{uuid.uuid4().hex}")
    stage.mkdir(mode=0o700)
    replaced = False
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
        check(target, spec, commit, smoke=False)
        if entry:
            plugins.refresh(Path(entry["root"]))
    except BaseException:
        if replaced:
            shutil.rmtree(target)
            os.replace(backup, target)
            if entry:
                plugins.refresh(Path(entry["root"]))
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(backup)
    return {"tool": name, "active": commit, "status": "repaired",
            "provider_patch_sha256": provider_hash()}
