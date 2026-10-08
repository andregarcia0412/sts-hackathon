"""CHK-ESCOPO (pre-pass) — limite da conclusão: excluído desde o início × lacuna na pretensão.

Fatos determinísticos: flags ..._executado: false no configuracao.json,
menção explícita de limite no §6/§7. Leitura fina (dentro/fora da pretensão) é do especialista.
"""
from __future__ import annotations

from ai_microservice.extraction.parsers import Fragment


def _find_executado_false(obj, prefix=""):
    out: list[dict] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else k
            if k.endswith("_executado") and v is False:
                out.append({"chave": key})
            out.extend(_find_executado_false(v, key))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(_find_executado_false(v, f"{prefix}[{i}]"))
    return out


def run_chk_escopo(fragments: list[Fragment]) -> dict:
    config: dict = {}
    metodo: dict[str, str] = {}
    revisao = ""
    for f in fragments:
        if f.artifact == "evidencias/configuracao.json" and f.data and "projeto_id" in f.data:
            config = f.data
        elif f.artifact == "evidencias/metodo.md" and f.data and f.data.get("secao") in ("6", "7"):
            metodo[str(f.data["secao"])] = f.text
        elif f.artifact == "evidencias/revisao_tecnica.md":
            revisao = f.text

    flags = _find_executado_false(config)
    limite_declarado = bool(metodo.get("6"))
    return {
        "flags_executado_false": flags,
        "limite_declarado_secao6": limite_declarado,
        "s6_texto": metodo.get("6", ""),
        "s7_texto": metodo.get("7", ""),
        "revisao_tecnica_texto": revisao,
    }