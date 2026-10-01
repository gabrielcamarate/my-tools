"""Manage the official Codex plugin through its own installation commands."""
import hashlib
import json
import os
from pathlib import Path
import uuid

from .core import ToolError, atomic_json, checked, read_json

NAME = "jev-pruner"
MARKETPLACE = "jev-pruner-codex"
PLUGIN = f"{NAME}@{MARKETPLACE}"


def registry(manager):
    path = manager.home / "plugins.json"
    value = read_json(path) if path.exists() else {"schema_version": 1, "tools": {}}
    if set(value) != {"schema_version", "tools"} or not isinstance(value["tools"], dict):
        raise ToolError("Registro de plugins inválido")
    for name, entry in value["tools"].items():
        if name != NAME or not isinstance(entry, dict) or set(entry) != {"root", "active"}:
            raise ToolError("Registro de plugins inválido")
        manager.location(name, entry["active"])
        if not isinstance(entry["root"], str) or not Path(entry["root"]).is_absolute():
            raise ToolError("Raiz do plugin precisa de caminho absoluto")
    return value


def client():
    try:
        value = json.loads(checked(["codex", "plugin", "list", "--json"]))
        return next((p for p in value["installed"] if p["pluginId"] == PLUGIN), None)
    except (ValueError, KeyError, TypeError) as exc:
        raise ToolError("Resposta de plugins do Codex inválida") from exc


def cached_root(info):
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    version = info.get("version")
    if not isinstance(version, str) or not version or Path(version).name != version:
        raise ToolError("Versão de cache do plugin inválida")
    return home / "plugins/cache" / MARKETPLACE / NAME / version


def ownership(source):
    info = client()
    if info:
        actual = info.get("source", {}).get("path")
        if not actual or Path(actual).resolve() != source.resolve():
            raise ToolError("Plugin do cliente aponta para outra fonte; preservado")
        if not info.get("enabled"):
            raise ToolError("Plugin desabilitado no cliente; reinstalação automática recusada")
    return info


def check_client(source):
    info = client()
    if not info or not info.get("installed"):
        raise ToolError("Plugin oficial não está instalado no Codex")
    actual = info.get("source", {}).get("path")
    if not actual or Path(actual).resolve() != source.resolve():
        raise ToolError("Plugin do cliente aponta para outra fonte")
    cached = cached_root(info)
    # Compare the executable closure and official skill/hooks, not only version 0.1.0.
    files = [p for p in (source / "dist").rglob("*") if p.is_file()]
    files += [source / p for p in (".codex-plugin/plugin.json", "codex/hooks.json",
                                  "codex/skills/jev-pruner/SKILL.md")]
    for p in files:
        target = cached / p.relative_to(source)
        if not target.is_file() or hashlib.sha256(p.read_bytes()).digest() != hashlib.sha256(target.read_bytes()).digest():
            raise ToolError("Cache do Codex diverge da revisão aceita; execute integrate --apply")
    return info


def switch(manager, commit, link):
    link = Path(link)
    if link.exists() or link.is_symlink():
        if not link.is_symlink() or not link.resolve().is_relative_to(manager.home / "tools" / NAME):
            raise ToolError("Raiz de plugin ocupada por instalação externa; preservada")
    source = manager.location(NAME, commit) / "source"
    from .pruner import contract
    contract(source)
    link.parent.mkdir(parents=True, exist_ok=True)
    pending = link.with_name(f".{NAME}-{uuid.uuid4().hex}")
    try:
        pending.symlink_to(source, target_is_directory=True)
        os.replace(pending, link)
    finally:
        pending.unlink(missing_ok=True)


def refresh(link):
    # Rebuild alone does not refresh Codex's installed cache. Follow upstream.
    if client():
        checked(["codex", "plugin", "remove", PLUGIN])
    markets = json.loads(checked(["codex", "plugin", "marketplace", "list", "--json"]))
    if any(m["name"] == MARKETPLACE for m in markets["marketplaces"]):
        # Codex canonicalizes symlinks. A new SHA is a different local source.
        checked(["codex", "plugin", "marketplace", "remove", MARKETPLACE])
    checked(["codex", "plugin", "marketplace", "add", str(link)])
    checked(["codex", "plugin", "add", PLUGIN])
    check_client(Path(link))


def transition(manager, commit, entry):
    link = Path(entry["root"])
    previous = entry["active"]
    switch(manager, commit, link)
    try:
        refresh(link)
    except BaseException:
        switch(manager, previous, link)
        refresh(link)
        raise


def integrate(manager, name, apply=False, bin_dir=None):
    if name != NAME or bin_dir is not None:
        raise ToolError("Plugin usa sua raiz gerenciada; --bin-dir é exclusivo de executáveis")
    manager.resolve(name)
    commit = manager.state()["tools"][name]["active"]
    value = registry(manager)
    old = value["tools"].get(name)
    link = manager.home / "plugins" / name
    info = client()
    if info and not old:
        raise ToolError("Plugin já instalado fora do gestor; preservado")
    if old and Path(old["root"]) != link:
        raise ToolError("Raiz registrada divergente; preserve a instalação")
    if not old:
        try:
            markets = json.loads(checked(["codex", "plugin", "marketplace", "list", "--json"]))
            if any(m["name"] == MARKETPLACE for m in markets["marketplaces"]):
                raise ToolError("Marketplace já configurado fora do gestor; preservado")
        except (ValueError, KeyError, TypeError) as exc:
            raise ToolError("Resposta de marketplaces inválida") from exc
    if apply:
        # Existing foreign sources must never be removed, even with a stale registry.
        if old and info:
            ownership(manager.location(name, old["active"]) / "source")
        switch(manager, commit, link)
        try:
            refresh(link)
            value["tools"][name] = {"root": str(link), "active": commit}
            atomic_json(manager.home / "plugins.json", value)
        except BaseException:
            if old:
                switch(manager, old["active"], link)
                refresh(link)
            else:
                if client():
                    checked(["codex", "plugin", "remove", PLUGIN])
                checked(["codex", "plugin", "marketplace", "remove", MARKETPLACE])
                link.unlink(missing_ok=True)
            raise
    return {"tool": name, "active": commit, "plugin": PLUGIN, "root": str(link),
            "status": "integrated" if apply else "planned", "interface": "official_codex_plugin",
            "hook_trust": "review in a new session", "credential": "TYPESAFE_API_KEY"}


def synchronize(manager, name, commit):
    entry = registry(manager)["tools"].get(name)
    if not entry:
        return
    value = registry(manager)
    entry = value["tools"][name]
    # Verify source ownership before calling remove/add.
    ownership(manager.location(name, entry["active"]) / "source")
    if entry["active"] == commit:
        check_client(manager.location(name, commit) / "source")
        return
    previous = entry["active"]
    transition(manager, commit, entry)
    entry["active"] = commit
    try:
        atomic_json(manager.home / "plugins.json", value)
    except BaseException:
        transition(manager, previous, entry)
        raise


def diagnose(manager, name, commit):
    entry = registry(manager)["tools"].get(name)
    if not entry:
        return {}
    source = manager.location(name, commit) / "source"
    if entry["active"] != commit or Path(entry["root"]).resolve() != source:
        raise ToolError("Estado de plugin diverge da revisão aceita; execute integrate --apply")
    info = check_client(source)
    return {"official_plugin": PLUGIN, "plugin_root": entry["root"],
            "client_enabled": info.get("enabled"), "hook_trust": "not verified",
            "requires_session_history_export": True}
