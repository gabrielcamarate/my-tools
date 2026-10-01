"""Explicit CLI; no global hooks and no automatic project adoption."""
import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .core import Manager, ToolError, setup, uninstall_launcher


def parser():
    p = argparse.ArgumentParser(prog="my-tools")
    p.add_argument("--version", action="version", version=__version__)
    commands = p.add_subparsers(dest="command", required=True)
    for name in ("setup", "uninstall"):
        sub = commands.add_parser(name)
        sub.add_argument("--bin-dir", type=Path)
        sub.add_argument("--apply", action="store_true")
    for name in ("status", "doctor"):
        commands.add_parser(name)
    sub = commands.add_parser("install")
    sub.add_argument("tool")
    sub = commands.add_parser("repair")
    sub.add_argument("tool", choices=["jev-pruner"])
    sub = commands.add_parser("integrate")
    sub.add_argument("tool", choices=["siftr", "jev-pruner", "jev-test-filter"])
    sub.add_argument("--apply", action="store_true")
    sub.add_argument("--bin-dir", type=Path)
    for name in ("outdated", "update"):
        sub = commands.add_parser(name)
        group = sub.add_mutually_exclusive_group(required=True)
        group.add_argument("tool", nargs="?")
        group.add_argument("--all", action="store_true")
        if name == "update":
            sub.add_argument("--accept", help="Aceitar explicitamente o SHA candidato de uma ferramenta")
    sub = commands.add_parser("rollback")
    sub.add_argument("tool")
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
        if args.command == "integrate":
            if args.tool == "jev-pruner":
                from .plugins import integrate
            elif args.tool == "jev-test-filter":
                from .commands import integrate
            else:
                from .native import integrate
            with manager.lock():
                emit(integrate(manager, args.tool, args.apply, args.bin_dir))
            return 0
        if args.command in ("doctor", "status"):
            result = manager.doctor(smoke=args.command == "doctor")
            result["runtime_scope"] = "local; desktop/cloud discovery must be verified separately"
            emit(result)
            return int(args.command == "doctor" and any(r["status"] != "ready_offline" for r in result["tools"]))
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
                        elif args.command == "repair":
                            from .pruner import rebuild
                            result = rebuild(manager)
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
