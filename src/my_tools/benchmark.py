"""Compare measured, paired tasks. Missing token counts never become zero."""
import math

from .core import ToolError, read_json


def run(path, arm):
    data = read_json(path)
    if data.get("arm") != arm or not isinstance(data.get("environment"), dict):
        raise ToolError("Braço ou ambiente do benchmark inválido")
    environment = data["environment"]
    required = {"fixture_revision", "model", "reasoning", "acceptance"}
    if set(environment) != required or any(not isinstance(v, str) or not v.strip() for v in environment.values()):
        raise ToolError("Ambiente precisa identificar revisão, modelo, esforço e aceite")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ToolError("Benchmark sem casos")
    indexed = {}
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"] or case["id"] in indexed:
            raise ToolError("Caso inválido ou duplicado")
        if case.get("outcome") not in ("accepted", "failed", "blocked"):
            raise ToolError("Resultado precisa ser accepted, failed ou blocked")
        seconds = case.get("seconds")
        tokens = case.get("codex_total_tokens")
        recoveries = case.get("recoveries")
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            raise ToolError("Tempo precisa ser medido, finito e não negativo")
        if tokens is not None and (type(tokens) is not int or tokens < 0):
            raise ToolError("Tokens precisam ser inteiro medido ou null")
        if type(recoveries) is not int or recoveries < 0:
            raise ToolError("Recuperações precisam ser inteiro não negativo")
        indexed[case["id"]] = case
    return environment, indexed


def compare(baseline, candidate):
    env_a, a = run(baseline, "baseline")
    env_b, b = run(candidate, "candidate")
    if env_a != env_b or set(a) != set(b):
        raise ToolError("Comparação exige os mesmos casos e ambiente/aceite")
    def totals(cases):
        tokens = [c.get("codex_total_tokens") for c in cases.values()]
        return {"cases": len(cases), "accepted": sum(c["outcome"] == "accepted" for c in cases.values()),
                "failed": sum(c["outcome"] == "failed" for c in cases.values()),
                "blocked": sum(c["outcome"] == "blocked" for c in cases.values()),
                "seconds": sum(c["seconds"] for c in cases.values()),
                "recoveries": sum(c["recoveries"] for c in cases.values()),
                "codex_total_tokens": None if any(t is None for t in tokens) else sum(tokens)}
    base, cand = totals(a), totals(b)
    def delta(key):
        old, new = base[key], cand[key]
        return None if old is None or new is None or old == 0 else round((new - old) / old * 100, 2)
    return {"schema_version": 1, "baseline": base, "candidate": cand,
            "change_percent": {"seconds": delta("seconds"), "codex_total_tokens": delta("codex_total_tokens")},
            "quality_regression_cases": [key for key in a if a[key]["outcome"] == "accepted" and b[key]["outcome"] != "accepted"],
            "limits": "Descritivo; inclui falhas e bloqueios. Não prova significância, cota ou ganho geral."}
