"""Install official entrypoints; never translate or proxy their tool calls."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import json
import uuid

from .core import ToolError, atomic_json, checked, read_json

MCP_TOOLS = {"semantic_search", "focused_read", "pick_relevant", "filter_output"}


def registry(manager):
    path = manager.home / "native.json"
    value = read_json(path) if path.exists() else {"schema_version": 1, "tools": {}}
    if set(value) != {"schema_version", "tools"} or not isinstance(value["tools"], dict):
        raise ToolError("Registro nativo inválido")
    for name, entry in value["tools"].items():
        if name != "siftr" or not isinstance(entry, dict) or set(entry) != {"command", "active"}:
            raise ToolError("Registro nativo inválido")
        manager.location(name, entry["active"])
        if not isinstance(entry["command"], str) or not Path(entry["command"]).is_absolute():
            raise ToolError("Comando nativo precisa de caminho absoluto")
    return value


def executable(manager, name, commit):
    manager.location(name, commit)  # validate tool and SHA
    return manager.home / "native" / name / commit / "tools" / name / "bin" / name


def check(exe):
    if not exe.is_file():
        raise ToolError("Executável oficial ausente")
    with tempfile.TemporaryDirectory(prefix="my-tools-mcp-check-") as folder:
        from .siftr import offline_env
        env = offline_env(folder)
        messages = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}]
        result = subprocess.run([str(exe), "mcp"], input="".join(json.dumps(m) + "\n" for m in messages),
                                capture_output=True, text=True, cwd=folder, env=env, timeout=15)
        if result.returncode:
            raise ToolError("MCP oficial falhou na descoberta offline")
        try:
            replies = [json.loads(line) for line in result.stdout.splitlines()]
            tools = next(r["result"]["tools"] for r in replies if r.get("id") == 2)
            if {t["name"] for t in tools} != MCP_TOOLS:
                raise ToolError("Contrato de ferramentas MCP mudou; revisão necessária")
        except (ValueError, KeyError, StopIteration, TypeError) as exc:
            raise ToolError("Resposta de descoberta MCP inválida") from exc
    return sorted(MCP_TOOLS)


def prepare(manager, name, commit):
    source = manager.location(name, commit) / "source"
    exe = executable(manager, name, commit)
    if exe.exists():
        check(exe)
        return exe
    uv = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
    if not Path(uv).is_file():
        raise ToolError("Instale uv pelo procedimento oficial antes de integrate")
    base = exe.parents[3]
    env = os.environ.copy()
    for key in ("OPENROUTER_API_KEY", "TYPESAFE_API_KEY"):
        env.pop(key, None)
    env.update(UV_TOOL_DIR=str(base / "tools"), UV_TOOL_BIN_DIR=str(base / "bin"),
               UV_NO_MODIFY_PATH="1")
    # Same official installer operation, using the accepted local source rather
    # than an unpinned main.zip. uv generates the upstream siftr entrypoint.
    checked([uv, "tool", "install", "--python", "3.12", str(source)], env=env, timeout=180)
    check(exe)
    return exe


def switch(manager, name, commit, link):
    link = Path(link)
    native_root = manager.home / "native" / name
    if link.exists() or link.is_symlink():
        if not link.is_symlink() or not link.resolve().is_relative_to(native_root):
            raise ToolError("Comando ocupado por instalação externa; preservado")
    exe = prepare(manager, name, commit)
    link.parent.mkdir(parents=True, exist_ok=True)
    temporary = link.with_name(f".{name}-{uuid.uuid4().hex}")
    try:
        temporary.symlink_to(exe)
        os.replace(temporary, link)
    finally:
        temporary.unlink(missing_ok=True)
    return exe


def integrate(manager, name, apply=False, bin_dir=None):
    if name != "siftr":
        raise ToolError("Integração nativa ainda não registrada para esta ferramenta")
    manager.resolve(name)
    commit = manager.state()["tools"][name]["active"]
    folder = Path(bin_dir).expanduser().resolve() if bin_dir else Path.home() / ".local/bin"
    link = folder / name
    value = registry(manager)
    old = value["tools"].get(name)
    if old and Path(old["command"]) != link:
        raise ToolError("Destino nativo já registrado; preserve o comando existente")
    if apply:
        exe = switch(manager, name, commit, link)
        value["tools"][name] = {"command": str(link), "active": commit}
        try:
            atomic_json(manager.home / "native.json", value)
        except BaseException:
            if old:
                switch(manager, name, old["active"], link)
            elif link.is_symlink() and link.resolve() == exe.resolve():
                link.unlink()
            raise
    return {"tool": name, "active": commit, "command": str(link), "args": ["mcp"],
            "status": "integrated" if apply else "planned", "mcp_tools": sorted(MCP_TOOLS)}


def synchronize(manager, name, commit):
    value = registry(manager)
    entry = value["tools"].get(name)
    if entry:
        previous = entry["active"]
        switch(manager, name, commit, entry["command"])
        entry["active"] = commit
        try:
            atomic_json(manager.home / "native.json", value)
        except BaseException:
            switch(manager, name, previous, entry["command"])
            raise
