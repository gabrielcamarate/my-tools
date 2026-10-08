"""Install the upstream Claude Code compaction mod with the reviewed OpenRouter provider."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid

from .core import ROOT, ToolError, atomic_json, checked, read_json
from .pruner import build_env

NAME = "fast-jev-compaction"
PLUGIN = f"{NAME}@{NAME}"
PATCH = ROOT / "patches/fast-jev-compaction-openrouter.patch"
FLAG = "CLAUDE_CODE_ENABLE_FUNCTION_HOOKS"
SCOPE = {".claude-plugin/plugin.json", "hooks/README.md", "hooks/fast-jev.ts",
         "tests/hook.test.ts", "tests/openrouter-provider.test.ts"}
# What Claude Code loads: the hooks module and the library it imports.
RUNTIME = (".claude-plugin", "hooks", "src")


def provider_hash():
    return hashlib.sha256(PATCH.read_bytes()).hexdigest()


def apply_provider(source):
    paths = {line.split("\t")[-1] for line in checked(
        ["git", "apply", "--numstat", str(PATCH)]).splitlines()}
    if paths != SCOPE:
        raise ToolError("Patch excede o escopo de provedor revisado")
    checked(["git", "-C", str(source), "apply", "--check", str(PATCH)])
    checked(["git", "-C", str(source), "apply", str(PATCH)])


def hashes(path):
    source = Path(path) / "source"
    tracked = [p for p in checked(["git", "-C", str(source), "ls-files", "-z"]).split("\0") if p]
    files = [source / p for p in tracked + ["tests/openrouter-provider.test.ts"]]
    return {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files if p.is_file()}


def contract(source):
    try:
        package = json.loads((source / "package.json").read_text())
        plugin = json.loads((source / ".claude-plugin/plugin.json").read_text())
        marketplace = json.loads((source / ".claude-plugin/marketplace.json").read_text())
        hooks = json.loads((source / "hooks/hooks.json").read_text())
        valid = (package["name"] == NAME and package.get("dependencies", {}) == {}
                 and package["scripts"]["test"] == "vitest run"
                 and plugin["name"] == NAME and set(plugin) <= {"name", "version", "description", "license", "userConfig"}
                 and marketplace["name"] == NAME
                 and [(p["name"], p["source"]) for p in marketplace["plugins"]] == [(NAME, "./")]
                 and hooks == {"modules": ["./fast-jev.ts"]}
                 and plugin["userConfig"]["model"]["default"] == "typesafe/jev-1.13")
        if not valid:
            raise ToolError("Contrato do plugin mudou; revisão necessária")
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
    # Conflicting upstream changes stop installation before activation.
    apply_provider(source)
    contract(source)
    env = build_env()
    checked(["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"], cwd=source, env=env)
    atomic_json(Path(path) / "installation.json", {"schema_version": 1, "commit": commit,
        "repository": spec["repository"], "installer": spec["installer"],
        "provider_patch_sha256": provider_hash(), "hashes": hashes(path)})


def check(path, spec, commit, smoke=True):
    path = Path(path)
    record = read_json(path / "installation.json")
    if any(record.get(k) != expected for k, expected in (
        ("commit", commit), ("repository", spec["repository"]), ("installer", spec["installer"]),
        ("provider_patch_sha256", provider_hash()))):
        raise ToolError("Plugin não corresponde à origem/versão/instalador/patch")
    if hashes(path) != record.get("hashes"):
        raise ToolError("Fonte do plugin foi alterada")
    source = path / "source"
    contract(source)
    if smoke:
        with tempfile.TemporaryDirectory(prefix="my-tools-compaction-check-") as folder:
            # No credential and a scratch HOME: the provider and fallback tests stay offline.
            env = build_env()
            env["HOME"] = folder
            checked(["npm", "run", "typecheck"], cwd=source, env=env)
            checked(["npm", "test"], cwd=source, env=env, timeout=180)


def registry(manager):
    path = manager.home / "claude-plugins.json"
    value = read_json(path) if path.exists() else {"schema_version": 1, "tools": {}}
    if set(value) != {"schema_version", "tools"} or set(value["tools"]) - {NAME}:
        raise ToolError("Registro de plugins Claude inválido")
    return value


def client():
    try:
        value = json.loads(checked(["claude", "plugin", "list", "--json"]))
        return next((p for p in value if p.get("id") == PLUGIN), None)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ToolError("Resposta de plugins do Claude inválida") from exc


def runtime_files(root):
    root = Path(root)
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in RUNTIME for p in sorted((root / folder).rglob("*")) if p.is_file()}


def check_client(source):
    info = client()
    if not info or not info.get("enabled"):
        raise ToolError("Plugin não está instalado e habilitado no Claude Code")
    cached = Path(info.get("installPath", ""))
    if not cached.is_dir() or runtime_files(cached) != runtime_files(source):
        raise ToolError("Cache do Claude diverge da revisão aceita; execute integrate --apply")
    return info


def settings_path():
    return Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))) / "settings.json"


def enable_flag():
    """Opt in to function hooks; every other setting, hooks included, stays as it is."""
    path = settings_path()
    value = json.loads(path.read_text()) if path.exists() else {}
    env = value.setdefault("env", {})
    if not isinstance(env, dict):
        raise ToolError("Configuração env do Claude inválida")
    if env.get(FLAG) == "1":
        return
    env[FLAG] = "1"
    pending = path.with_name(f".settings-{uuid.uuid4().hex}.json")
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    os.chmod(pending, path.stat().st_mode & 0o777 if path.exists() else 0o600)
    os.replace(pending, path)


def integrate(manager, name, apply=False, bin_dir=None):
    if name != NAME or bin_dir is not None:
        raise ToolError("Plugin usa sua raiz gerenciada; --bin-dir é exclusivo de executáveis")
    manager.resolve(name)
    commit = manager.state()["tools"][name]["active"]
    source = manager.location(name, commit) / "source"
    value = registry(manager)
    old = value["tools"].get(name)
    if client() and not old:
        raise ToolError("Plugin já instalado fora do gestor; preservado")
    if apply:
        contract(source)
        markets = json.loads(checked(["claude", "plugin", "marketplace", "list", "--json"]))
        if any(m.get("name") == NAME for m in markets):
            if not old:
                raise ToolError("Marketplace já configurado fora do gestor; preservado")
            if client():
                checked(["claude", "plugin", "uninstall", PLUGIN, "--scope", "user"])
            checked(["claude", "plugin", "marketplace", "remove", NAME])
        checked(["claude", "plugin", "marketplace", "add", str(source)])
        checked(["claude", "plugin", "install", PLUGIN, "--scope", "user"])
        check_client(source)
        enable_flag()
        value["tools"][name] = {"source": str(source), "active": commit}
        atomic_json(manager.home / "claude-plugins.json", value)
    return {"tool": name, "active": commit, "plugin": PLUGIN, "root": str(source),
            "status": "integrated" if apply else "planned", "interface": "claude_code_function_hooks",
            "flag": FLAG, "credential": "OPENROUTER_API_KEY", "provider": "openrouter_decisions",
            "activation": "restart Claude Code or /reload-plugins"}


def diagnose(manager, name, commit):
    if name != NAME:
        return {}
    entry = registry(manager)["tools"].get(name)
    if not entry:
        return {}
    if entry["active"] != commit:
        raise ToolError("Plugin Claude usa outra revisão; execute integrate --apply")
    info = check_client(manager.location(name, commit) / "source")
    settings = json.loads(settings_path().read_text()) if settings_path().exists() else {}
    return {"claude_plugin": PLUGIN, "client_enabled": info.get("enabled"),
            "function_hooks_flag": settings.get("env", {}).get(FLAG) == "1",
            "server_rollout": "not verified offline", "requires_session_history_export": True,
            "provider": "openrouter_decisions"}
