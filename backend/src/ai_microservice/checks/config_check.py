"""CHK-CONFIG (pre-pass) — a referência anterior já fornece a função? mecanismo é configuração?

Classificação final do §1/§2 é do especialista; aqui os fatos determinísticos:
- tipo da referência (manual/catálogo/dicionário/produto) por padrão de texto;
- verbos de configuração no mecanismo;
- flag de faixa suportada ("conforme faixa ... já admitida");
- data da referência (CR01/documento-inicial) vs. data de referência.
"""
from __future__ import annotations

import re

from ai_microservice.extraction.parsers import Fragment

_TIPO_PATTERNS = [
    (r"\bmanual\b", "manual"),
    (r"\bcatálogo\b|\bcatalogo\b", "catalogo"),
    (r"\bdicionário\b|\bdicionario\b", "dicionario"),
    (r"\bproduto contratado\b|\bcontratado\b", "produto_contratado"),
]

_VERBOS_CONFIG = [
    "configurar", "ativar", "cadastrar", "mapear", "ajustar", "parametrizar",
    "habilitar", "configuração", "customiz",
]

_FAIXA_RE = re.compile(r"faixa de [\d\w,–\- ]+\s*(?:s|segundos|ms|min)?\s*já admitida", re.I)
_ALGORITMO_NAO_MODIFICADO_RE = re.compile(r"nenhum algoritmo (?:do barramento )?foi modificado", re.I)


def run_chk_config(fragments: list[Fragment]) -> dict:
    metodo: dict[str, str] = {}
    for f in fragments:
        if f.artifact == "evidencias/metodo.md":
            secao = f.data.get("secao") if f.data else None
            if secao:
                metodo[str(secao)] = f.text

    s1 = metodo.get("1", "")
    s2 = metodo.get("2", "")

    tipo = None
    for pat, name in _TIPO_PATTERNS:
        if re.search(pat, s1, re.I):
            tipo = name
            break

    verbos = [v for v in _VERBOS_CONFIG if v in s2.lower()]
    faixa = bool(_FAIXA_RE.search(s2))
    algoritmo_intacto = bool(_ALGORITMO_NAO_MODIFICADO_RE.search(s2))

    funcao_ja_fornecida = bool(tipo and verbos)
    return {
        "referencia_anterior_tipo": tipo,
        "verbos_configuracao": verbos,
        "ajuste_dentro_da_faixa": faixa,
        "algoritmo_nao_modificado": algoritmo_intacto,
        "funcao_ja_fornecida": funcao_ja_fornecida,
        "s1_texto": s1,
        "s2_texto": s2,
    }