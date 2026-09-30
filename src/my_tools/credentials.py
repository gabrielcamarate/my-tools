"""Local credentials, never CLI arguments or diagnostic output."""
import os
from pathlib import Path
import stat

from .core import ToolError, atomic_json, read_json

PROVIDERS = {"openrouter": "OPENROUTER_API_KEY", "typesafe": "TYPESAFE_API_KEY"}


def stored(home):
    path = Path(home) / "credentials.json"
    if not path.exists() and not path.is_symlink():
        return {}
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ToolError("Cadastro de credenciais precisa ser arquivo próprio com permissão 600")
    data = read_json(path)
    values = data.get("credentials")
    if set(data) != {"schema_version", "credentials"} or not isinstance(values, dict):
        raise ToolError("Cadastro de credenciais inválido")
    if set(values) - set(PROVIDERS.values()) or any(not isinstance(v, str) or not v or any(c.isspace() for c in v) for v in values.values()):
        raise ToolError("Cadastro de credenciais inválido")
    return values


def save(home, provider, key):
    if provider not in PROVIDERS or not key or any(c.isspace() for c in key):
        raise ToolError("Provider ou chave inválidos")
    values = stored(home)
    values[PROVIDERS[provider]] = key
    atomic_json(Path(home) / "credentials.json", {"schema_version": 1, "credentials": values})


def clear(home, provider):
    values = stored(home)
    values.pop(PROVIDERS[provider], None)
    atomic_json(Path(home) / "credentials.json", {"schema_version": 1, "credentials": values})


def effective(home):
    environment = os.environ.copy()
    # Explicit process credentials take precedence as a group. Do not inject a
    # stored OpenRouter key ahead of an explicit TypeSafe key chosen by the user.
    if any(environment.get(name) for name in PROVIDERS.values()):
        return environment, "environment"
    values = stored(home)
    environment.update(values)
    return environment, "local_store" if values else "none"
