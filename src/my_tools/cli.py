"""Explicit CLI; no global hooks and no automatic project adoption."""
import argparse
import getpass
import json
from pathlib import Path
import sys

from . import __version__
from .core import (Manager, ToolError, atomic_json, project_config, project_root,
                   setup, uninstall_launcher)


def parser():
    p = argparse.ArgumentParser(prog="my-tools")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--project", type=Path)
    commands = p.add_subparsers(dest="command", required=True)
    for name in ("setup", "uninstall"):
        sub = commands.add_parser(name)
        sub.add_argument("--bin-dir", type=Path)
        sub.add_argument("--apply", action="store_true")
    for name in ("status", "doctor"):
        commands.add_parser(name)
    sub = commands.add_parser("init")
    sub.add_argument("--profile", choices=["minimal", "search-experimental"], default="minimal")
    sub = commands.add_parser("enable")
    sub.add_argument("capability", choices=["search"])
    sub.add_argument("--provider", choices=["siftr"], default="siftr")
    sub.add_argument("--allow-remote", action="store_true")
    sub.add_argument("--pin", default="approved", help="approved ou SHA completo instalado")
    sub = commands.add_parser("disable")
    sub.add_argument("capability", choices=["search"])
    sub = commands.add_parser("install")
    sub.add_argument("tool")
    for name in ("outdated", "update"):
        sub = commands.add_parser(name)
        group = sub.add_mutually_exclusive_group(required=True)
        group.add_argument("tool", nargs="?")
        group.add_argument("--all", action="store_true")
        if name == "update":
            sub.add_argument("--accept", help="Aceitar explicitamente o SHA candidato de uma ferramenta")
    sub = commands.add_parser("rollback")
    sub.add_argument("tool")
    sub = commands.add_parser("search")
    sub.add_argument("query")
    sub.add_argument("--top", type=int, default=10)
    sub.add_argument("--json", action="store_true")
    sub.add_argument("--stats", action="store_true")
    sub.add_argument("--glob", action="append", help="Limitar caminhos elegíveis; repetível, ex.: 'src/*.ts'")
    sub = commands.add_parser("auth")
    sub.add_argument("operation", choices=["set", "remove"])
    sub.add_argument("--provider", required=True, choices=["openrouter", "typesafe"])
    sub = commands.add_parser("compare")
    sub.add_argument("baseline", type=Path)
    sub.add_argument("candidate", type=Path)
    return p


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command in ("setup", "uninstall"):
            operation = setup if args.command == "setup" else uninstall_launcher
            emit(operation(bin_dir=args.bin_dir, apply=args.apply))
            return 0
        if args.command == "compare":
            from .benchmark import compare
            emit(compare(args.baseline, args.candidate))
            return 0
        manager = Manager()
        if args.command == "auth":
            from .credentials import clear, save
            if args.operation == "set":
                if not sys.stdin.isatty():
                    raise ToolError("Execute auth set em um terminal interativo; a chave será solicitada sem eco")
                key = getpass.getpass(f"Chave {args.provider} (oculta): ")
                with manager.lock():
                    save(manager.home, args.provider, key)
                del key
            else:
                with manager.lock():
                    clear(manager.home, args.provider)
            emit({"status": "saved_local" if args.operation == "set" else "removed_local", "provider": args.provider})
            return 0
        root = project_root(args.project or Path.cwd())
        if args.command == "init" and args.project is not None:
            # An explicitly named nested fixture/project gets its own boundary.
            root = args.project.expanduser().resolve()
            if not root.is_dir():
                raise ToolError("Projeto precisa ser diretório existente")
        if args.command in ("doctor", "status"):
            result = manager.doctor(smoke=args.command == "doctor")
            config_path = root / ".my-tools.json"
            result["project_config"] = project_config(root) if config_path.exists() else None
            result["runtime_scope"] = "local; desktop/cloud discovery must be verified separately"
            emit(result)
            return int(args.command == "doctor" and any(r["status"] != "ready_offline" for r in result["tools"]))
        if args.command == "init":
            path = root / ".my-tools.json"
            if path.exists() or path.is_symlink():
                raise ToolError("Configuração já existe; preservada")
            from .core import read_json
            profile = read_json(manager.root / "profiles" / f"{args.profile}.json")
            atomic_json(path, profile)
            emit({"status": "initialized", "profile": args.profile, "enabled": "none"})
        elif args.command in ("enable", "disable"):
            config = project_config(root)
            if args.command == "enable":
                manager.resolve(args.provider, args.pin)
                config["capabilities"][args.capability] = {"provider": args.provider, "version": args.pin,
                     "enabled": True, "allow_remote_data": args.allow_remote}
            elif args.capability in config["capabilities"]:
                config["capabilities"][args.capability]["enabled"] = False
                config["capabilities"][args.capability]["allow_remote_data"] = False
            atomic_json(root / ".my-tools.json", config)
            emit(config)
        elif args.command == "search":
            if not args.query.strip() or args.query.startswith("-") or not 1 <= args.top <= 100:
                raise ToolError("Consulta vazia/opção ou top fora de 1..100")
            if args.glob and any(not pattern.strip() or pattern.startswith(("-", "/"))
                                 or ".." in pattern.replace("\\", "/").split("/")
                                 or any(c in pattern for c in ("\n", "\r", "\x00")) for pattern in args.glob):
                raise ToolError("Use globs relativos, não vazios e sem travessia de diretórios")
            config = project_config(root)
            entry = config["capabilities"].get("search", {})
            if not entry.get("enabled"):
                raise ToolError("Busca desabilitada neste projeto")
            if not entry.get("allow_remote_data"):
                raise ToolError("Envio remoto não habilitado para este projeto; reveja o escopo antes de enable --allow-remote")
            path = manager.resolve(entry["provider"], entry["version"])
            from .credentials import effective
            env, _ = effective(manager.home)
            from .siftr import search
            return search(path, root, args.query, args.top, args.json, args.stats, env=env, globs=args.glob)
        else:
            names = list(manager.tools) if getattr(args, "all", False) else [args.tool]
            if getattr(args, "accept", None) and getattr(args, "all", False):
                raise ToolError("--accept exige uma única ferramenta e seu SHA completo")
            rows = []
            with manager.lock():
                for name in names:
                    try:
                        if args.command == "install":
                            result = manager.install(name)
                        elif args.command == "outdated":
                            result = manager.discover(name)
                        elif args.command == "update":
                            result = manager.update(name, args.accept)
                        else:
                            result = manager.rollback(name)
                        rows.append(result)
                    except ToolError as exc:
                        rows.append({"tool": name, "status": "failed", "reason": str(exc)})
            emit({"tools": rows})
            if any(r.get("status") == "failed" for r in rows):
                return 1
            if any(r.get("status") == "review_required" for r in rows):
                return 2
        return 0
    except (ToolError, OSError, ValueError, KeyError) as exc:
        message = str(exc) if isinstance(exc, ToolError) else "Arquivo/estado inválido ou operação indisponível"
        print(f"my-tools: {message}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
