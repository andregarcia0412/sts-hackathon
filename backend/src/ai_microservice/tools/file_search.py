"""Tool buscar_em_arquivos — busca em fragmentos por artefato, seção e termo."""
from __future__ import annotations

from ai_microservice.extraction.parsers import Fragment


def search_fragments(
    fragments: list[Fragment],
    artefato: str | None = None,
    secao: str | None = None,
    termo: str | None = None,
) -> list[Fragment]:
    """Filtragem determinística; termo é case-insensitive substring."""
    out = []
    for f in fragments:
        if artefato and f.artifact != artefato:
            continue
        if secao:
            anchor_sect = f.anchor.split("#")[-1]
            if anchor_sect != secao and not anchor_sect.endswith(f"p{secao}"):
                continue
        if termo:
            if termo.lower() not in (f.text or "").lower():
                continue
        out.append(f)
    return out


def fragment_to_tool_text(f: Fragment, max_chars: int = 2000) -> str:
    """Representação do fragmento para o contexto do agente (dado, não instrução)."""
    text = (f.text or "")[:max_chars]
    return f"[FRAGMENTO {f.anchor} | natureza={f.nature}]\n<<<CONTEUDO\n{text}\nCONTEUDO>>>"


TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "buscar_em_arquivos",
        "description": (
            "Busca fragmentos citáveis do pacote do projeto. Retorna âncora estável "
            "(ex.: evidencias/metodo.md#2, dossie_projeto.pdf#p1), natureza e o texto literal. "
            "Use antes de citar qualquer documento."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "artefato": {
                    "type": "string",
                    "description": "Arquivo completo com caminho relativo (ex.: evidencias/metodo.md). Opcional.",
                },
                "secao": {
                    "type": "string",
                    "description": "Seção/âncora específica (ex.: 2 para metodo.md#2, p1 para página 1 do PDF). Opcional.",
                },
                "termo": {
                    "type": "string",
                    "description": "Termo para filtrar fragmentos que contenham o texto. Opcional.",
                },
            },
            "required": [],
        },
    },
}