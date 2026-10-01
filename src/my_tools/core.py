"""Storage and installation. Upstream code is never evaluated in the controller."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid


ROOT = Path(__file__).resolve().parents[2]
SHA = re.compile(r"[0-9a-f]{40}")
NAME = re.compile(r"[a-z][a-z0-9-]{0,63}")


class ToolError(Exception):
    pass


def read_json(path):
    try:
        value = json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise ToolError(f"JSON ausente ou inválido: {Path(path).name}") from exc
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ToolError("Formato incompatível; esperado schema_version=1")
    return value


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ToolError("Recusando substituir arquivo de estado/configuração simbólico")
    fd, temporary = tempfile.mkstemp(prefix=".my-tools-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def checked(argv, *, cwd=None, env=None, timeout=180):
    try:
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True,
                                text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ToolError(f"Falha ou timeout ao executar {Path(str(argv[0])).name}") from exc
    if result.returncode:
        # Third-party output can contain credentials. Do not echo it into diagnostics.
        raise ToolError(f"{Path(str(argv[0])).name} terminou com código {result.returncode}")
    return result.stdout.strip()


def catalog(root=ROOT):
    tools = read_json(Path(root) / "tools.json").get("tools")
    if not isinstance(tools, dict) or not tools:
        raise ToolError("Catálogo vazio ou inválido")
    for name, spec in tools.items():
        if not NAME.fullmatch(name) or not isinstance(spec, dict):
            raise ToolError("Nome ou descrição de ferramenta inválido")
        if not SHA.fullmatch(spec.get("approved_commit", "")):
            raise ToolError("Commit aprovado precisa ser SHA completo")
        if not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.git", spec.get("repository", "")):
            raise ToolError("Origem precisa ser repositório GitHub HTTPS sem credenciais")
        if spec.get("adapter") != "siftr-v1" or spec.get("capability") != "search":
            raise ToolError("Adaptador/capacidade ainda não suportado")
        if not re.fullmatch(r"[A-Za-z0-9_./-]+", spec.get("branch", "")) or ".." in spec["branch"]:
            raise ToolError("Branch inválida")
    return tools


class Manager:
    def __init__(self, root=ROOT, home=None):
        self.root = Path(root).resolve()
        location = home or os.environ.get("MY_TOOLS_HOME")
        self.home = Path(location).expanduser().resolve() if location else Path.home() / ".local/share/my-tools"
        self.tools = catalog(self.root)

    @contextmanager
    def lock(self):
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.home / ".lock").open("a") as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ToolError("Outra alteração de my-tools está em andamento") from exc
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def state(self):
        path = self.home / "state.json"
        if not path.exists():
            return {"schema_version": 1, "tools": {}}
        value = read_json(path)
        if not isinstance(value.get("tools"), dict):
            raise ToolError("Estado inválido")
        for name, entry in value["tools"].items():
            self.spec(name)
            if not isinstance(entry, dict) or not isinstance(entry.get("active"), str) or not SHA.fullmatch(entry["active"]):
                raise ToolError("Versão ativa inválida")
            if entry.get("previous") is not None and (not isinstance(entry["previous"], str) or not SHA.fullmatch(entry["previous"])):
                raise ToolError("Versão anterior inválida")
            approved = entry.get("accepted", [])
            if not isinstance(approved, list) or any(not isinstance(s, str) or not SHA.fullmatch(s) for s in approved):
                raise ToolError("Histórico de aceitação inválido")
        return value

    def save(self, state):
        atomic_json(self.home / "state.json", state)

    def spec(self, name):
        if name not in self.tools:
            raise ToolError("Ferramenta não consta do catálogo")
        return self.tools[name]

    def location(self, name, commit):
        self.spec(name)
        if not isinstance(commit, str) or not SHA.fullmatch(commit):
            raise ToolError("Versão precisa ser SHA completo")
        return self.home / "tools" / name / commit

    def prepare(self, name, commit):
        from .adapters import ADAPTERS
        spec = self.spec(name)
        adapter = ADAPTERS[spec["adapter"]]
        target = self.location(name, commit)
        if target.exists():
            adapter.check(target, spec, commit)
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        stage = target.parent / f".staging-{uuid.uuid4().hex}"
        stage.mkdir(mode=0o700)
        try:
            adapter.prepare(stage, spec, commit)
            adapter.check(stage, spec, commit)
            os.replace(stage, target)
            # Proves the runtime survives moving out of staging.
            adapter.check(target, spec, commit)
        except BaseException:
            shutil.rmtree(stage, ignore_errors=True)
            # A published but invalid candidate never becomes active.
            if target.exists():
                shutil.rmtree(target)
            raise
        return target

    def activate(self, name, commit, from_catalog=False):
        from .adapters import ADAPTERS
        spec = self.spec(name)
        ADAPTERS[spec["adapter"]].check(self.location(name, commit), spec, commit)
        state = self.state()
        old = state["tools"].get(name, {})
        accepted = list(dict.fromkeys([*old.get("accepted", []), commit]))
        state["tools"][name] = {"active": commit,
            "previous": old.get("active") if old.get("active") != commit else old.get("previous"),
            "accepted": accepted,
            "catalog_commit": self.spec(name)["approved_commit"] if from_catalog else old.get("catalog_commit")}
        from .native import synchronize
        # Prepare/check the official entrypoint before publishing the new SHA.
        synchronize(self, name, commit)
        try:
            self.save(state)
        except BaseException:
            if old.get("active"):
                synchronize(self, name, old["active"])
            raise

    def install(self, name):
        active = self.state()["tools"].get(name, {}).get("active")
        if active:
            self.resolve(name)
            return {"tool": name, "active": active, "status": "installed"}
        commit = self.spec(name)["approved_commit"]
        self.prepare(name, commit)
        self.activate(name, commit, from_catalog=True)
        return {"tool": name, "active": commit, "status": "installed"}

    def discover(self, name):
        spec = self.spec(name)
        tags = checked(["git", "ls-remote", "--tags", spec["repository"]])
        versions = {}
        peeled = {}
        for line in tags.splitlines():
            commit, ref = line.split()
            if ref.endswith("^{}"):
                peeled[ref[:-3]] = commit
            match = re.fullmatch(r"refs/tags/v?(\d+)\.(\d+)\.(\d+)", ref)
            if match:
                versions[tuple(map(int, match.groups()))] = (commit, ref)
        if versions:
            commit, ref = versions[max(versions)]
            commit = peeled.get(ref, commit)
        else:
            ref = "refs/heads/" + spec["branch"]
            lines = checked(["git", "ls-remote", spec["repository"], ref]).splitlines()
            if len(lines) != 1:
                raise ToolError("Não foi possível identificar a revisão upstream")
            commit = lines[0].split()[0]
        if not SHA.fullmatch(commit):
            raise ToolError("Upstream devolveu revisão inválida")
        active = self.state()["tools"].get(name, {}).get("active")
        return {"tool": name, "active": active, "approved": spec["approved_commit"],
                "latest": commit, "ref": ref, "update_available": commit != active}

    def update(self, name, accept=None):
        candidate = self.discover(name)
        commit = candidate["latest"]
        if accept is not None and accept != commit:
            raise ToolError("Upstream mudou ou SHA aceito não é o candidato; consulte outdated novamente")
        approved = self.spec(name)["approved_commit"]
        if commit == self.state()["tools"].get(name, {}).get("active"):
            return {**candidate, "status": "current"}
        self.prepare(name, commit)
        if commit != approved and accept is None:
            # A revised catalog can advance its approved baseline. Re-running update
            # must not undo a newer revision explicitly accepted by this user.
            entry = self.state()["tools"].get(name, {})
            if entry.get("catalog_commit") != approved:
                self.prepare(name, approved)
                self.activate(name, approved, from_catalog=True)
            return {**candidate, "status": "review_required", "prepared": commit,
                    "active": self.state()["tools"].get(name, {}).get("active")}
        self.activate(name, commit, from_catalog=commit == approved)
        return {**candidate, "status": "updated", "active": commit}

    def rollback(self, name):
        self.spec(name)
        previous = self.state()["tools"].get(name, {}).get("previous")
        if not previous:
            raise ToolError("Não há versão anterior para restaurar")
        self.activate(name, previous)
        return {"tool": name, "active": previous, "status": "rolled_back"}

    def resolve(self, name, version="approved"):
        entry = self.state()["tools"].get(name, {})
        if version == "approved":
            version = entry.get("active")
            if not version:
                raise ToolError("Ferramenta não instalada; execute install")
        if version not in entry.get("accepted", []):
            raise ToolError("Candidato preparado ainda não foi aceito; não pode ser fixado no projeto")
        path = self.location(name, version)
        from .adapters import ADAPTERS
        spec = self.spec(name)
        ADAPTERS[spec["adapter"]].check(path, spec, version, smoke=False)
        return path

    def doctor(self, smoke=True):
        from .adapters import ADAPTERS
        from .credentials import effective
        effective_env, credential_source = effective(self.home)
        rows = []
        state = self.state()
        for name, spec in self.tools.items():
            entry = state["tools"].get(name, {})
            row = {"tool": name, "active": entry.get("active"),
                   "previous": entry.get("previous"), "adoption": spec["status"],
                   "credential_in_environment": any(bool(os.environ.get(k)) for k in spec["credential_environment"])}
            row["credential_available"] = any(bool(effective_env.get(k)) for k in spec["credential_environment"])
            row["credential_source"] = credential_source
            try:
                path = self.resolve(name)
                ADAPTERS[spec["adapter"]].check(path, spec, entry["active"], smoke=smoke)
                from . import native
                official = native.registry(self)["tools"].get(name)
                if official:
                    exe = native.executable(self, name, entry["active"])
                    if (official["active"] != entry["active"] or not exe.is_file()
                            or Path(official["command"]).resolve() != exe):
                        raise ToolError("Estado nativo diverge da versão ativa; execute integrate --apply para reconciliar")
                    if smoke:
                        native.check(exe)
                    row["official_command"] = official["command"]
                    row["mcp_tools"] = sorted(native.MCP_TOOLS)
                row["status"] = "ready_offline"
            except ToolError as exc:
                row.update(status="not_ready", reason=str(exc))
            rows.append(row)
        return {"schema_version": 1, "tools": rows}


def project_root(start):
    here = Path(start).expanduser().resolve()
    if not here.is_dir():
        raise ToolError("Projeto precisa ser diretório existente")
    for folder in (here, *here.parents):
        if (folder / ".my-tools.json").exists():
            return folder
        if (folder / ".git").exists():
            return folder
    return here


def validate_globs(patterns):
    if not isinstance(patterns, list) or not patterns or any(
        not isinstance(pattern, str) or not pattern.strip()
        or pattern.startswith(("-", "/", "\\"))
        or ".." in pattern.replace("\\", "/").split("/")
        or any(c in pattern for c in ("\n", "\r", "\x00"))
        for pattern in patterns
    ):
        raise ToolError("Use uma lista não vazia de globs relativos e sem travessia de diretórios")
    return patterns


def project_config(root):
    path = Path(root) / ".my-tools.json"
    if path.is_symlink():
        raise ToolError("Configuração do projeto precisa ser arquivo próprio")
    value = read_json(path)
    if set(value) != {"schema_version", "capabilities"}:
        raise ToolError("Configuração contém campos desconhecidos; não coloque credenciais aqui")
    capabilities = value.get("capabilities")
    if not isinstance(capabilities, dict) or set(capabilities) - {"search"}:
        raise ToolError("Capacidades inválidas")
    for entry in capabilities.values():
        if not isinstance(entry, dict) or entry.get("provider") != "siftr":
            raise ToolError("Provider inválido")
        required = {"provider", "version", "enabled", "allow_remote_data"}
        if not required <= set(entry) or set(entry) - required - {"globs"}:
            raise ToolError("Configuração da capacidade contém campos desconhecidos")
        if "globs" in entry:
            validate_globs(entry["globs"])
        if type(entry.get("enabled")) is not bool or type(entry.get("allow_remote_data")) is not bool:
            raise ToolError("enabled e allow_remote_data precisam ser booleanos")
        version = entry.get("version")
        if version != "approved" and (not isinstance(version, str) or not SHA.fullmatch(version)):
            raise ToolError("Versão do projeto inválida")
    return value


def setup(root=ROOT, bin_dir=None, apply=False):
    source = Path(root).resolve() / "bin/my-tools"
    destination = Path(bin_dir).expanduser().resolve() if bin_dir else Path.home() / ".local/bin"
    link = destination / "my-tools"
    owned = link.is_symlink() and link.resolve() == source
    if (link.exists() or link.is_symlink()) and not owned:
        raise ToolError("Destino ocupado por outro programa; preservado")
    if apply and not owned:
        destination.mkdir(parents=True, exist_ok=True)
        link.symlink_to(source)
    return {"command": str(link), "status": "linked" if owned or apply else "planned",
            "path_required": str(destination)}


def uninstall_launcher(root=ROOT, bin_dir=None, apply=False):
    source = Path(root).resolve() / "bin/my-tools"
    destination = Path(bin_dir).expanduser().resolve() if bin_dir else Path.home() / ".local/bin"
    link = destination / "my-tools"
    owned = link.is_symlink() and link.resolve() == source
    if owned and apply:
        link.unlink()
    return {"status": "removed" if owned and apply else "planned" if owned else "preserved"}
