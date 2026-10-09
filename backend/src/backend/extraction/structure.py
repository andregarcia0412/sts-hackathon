"""Deterministic mapping of the known package files (spec 05): the same `FileMapping` the extraction agent
produces, without the LLM. The type comes from the CONTENT (header columns, JSON keys, headings), never from the
file name. Anything not recognized with confidence falls back to the agent (`None` + the reason)."""

import re
import unicodedata

from backend.extraction.agent import FileMapping, SectionMark
from backend.extraction.schema import REQUIRED_SECTIONS, SECTION_KEYS
from backend.extraction.text import RawFile

HEADER_SCAN_LINES = 10
# (type, required header columns (normalized), id column, file column) — checked in this order
TABLE_SIGNATURES = (
    ("inventario", {"id_evidencia", "arquivo"}, "id_evidencia", "arquivo"),
    ("medicoes", {"registro_id", "ensaio_id"}, "registro_id", None),
    ("resultados", {"ensaio_id", "operacao", "base_de_calculo"}, "ensaio_id", None),
    ("cronologia", {"evento_id", "data"}, "evento_id", None),
    ("atividades", {"id_atividade"}, "id_atividade", None),
    ("atividades", {"id_da_atividade"}, "id_da_atividade", None),  # the XLSX header, on row 5
    ("entradas", {"entrada_id"}, "entrada_id", None),
    ("observacoes", {"observacao_id"}, "observacao_id", None),
)
CONFIG_KEYS = {"parametros", "versoes_registradas", "ensaios"}
FOOTER_RE = re.compile(r"^massa inteiramente fict", re.I)
PAGE_RE = re.compile(r"^\s*\d{1,3}\s*$")
DOSSIER_HEADINGS = {"contexto": "contexto", "pergunta registrada": "pergunta_registrada",
                    "referencia anterior": "referencia_anterior", "trabalho documentado": "trabalho_documentado",
                    "limite da conclusao": "limite_da_conclusao", "localizacao da prova": "localizacao_da_prova"}
RECORD_HEADINGS = {"mecanismo e comparacao": "mecanismo_e_comparacao", "desenho e criterios": "desenho_e_criterios",
                   "resultados recalculaveis": "resultados_recalculaveis",
                   "recortes de observacao": "recortes_de_observacao", "limite tecnico": "limite_tecnico",
                   "proveniencia": "proveniencia"}
# The interview questions come shuffled: the key comes from the meaning of the question.
INTERVIEW_QUESTIONS = (("qual situacao", "situacao"), ("qual ocorrencia", "ocorrencia"),
                       ("o que a equipe fez", "mecanismo"), ("que ponto ficou", "continuidade"),
                       ("como foi organizada", "verificacao"), ("como ficou a conclusao", "conclusao"),
                       ("que alternativas", "alternativas"))
NUMBERED_QUESTION_RE = re.compile(r"^\s*\d+\.\s+(.*\?)\s*$")


def plain(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(folded.lower().strip().lstrip("#").split())


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", plain(text)).strip("_")


def _cells(line: str) -> list[str]:
    separator = ";" if line.count(";") >= line.count(",") else ","
    return [cell.strip().lstrip("﻿") for cell in line.split(separator)]


def _table(raw: RawFile) -> FileMapping | None:
    for number, line in enumerate(raw.lines[:HEADER_SCAN_LINES], start=1):
        cells = _cells(line)
        names = {slug(c): c for c in cells if c}
        for kind, required, id_column, file_column in TABLE_SIGNATURES:
            if required <= set(names):
                return FileMapping(tipo=kind, justificativa=f"cabeçalho de colunas: {', '.join(sorted(required))}",
                                   linha_cabecalho=number, coluna_id=names[id_column],
                                   coluna_arquivo=names.get(file_column) if file_column else None)
    return None


def _ignored(raw: RawFile) -> list[int]:
    return [n for n, line in enumerate(raw.lines, start=1) if FOOTER_RE.match(line.strip()) or PAGE_RE.match(line)]


def _marks(raw: RawFile, headings: dict[str, str]) -> list[SectionMark]:
    marks, seen = [], set()
    for number, line in enumerate(raw.lines, start=1):
        key = headings.get(plain(line))
        if key and key not in seen:
            seen.add(key)
            marks.append(SectionMark(chave=key, linha=number, titulo=line.strip()))
    return marks


def _interview(raw: RawFile) -> list[SectionMark]:
    marks, seen = [], set()
    for number, line in enumerate(raw.lines, start=1):
        text = plain(line)
        key = None
        if match := NUMBERED_QUESTION_RE.match(line):
            question = plain(match.group(1))
            key = next((k for prefix, k in INTERVIEW_QUESTIONS if question.startswith(prefix)), None)
        elif text == "condicao do registro":
            key = "condicao_do_registro"
        if key and key not in seen:
            seen.add(key)
            marks.append(SectionMark(chave=key, linha=number, titulo=line.strip()))
    return marks


def _markdown(raw: RawFile) -> FileMapping | None:
    headings = [(n, line) for n, line in enumerate(raw.lines, start=1) if line.startswith("## ")]
    numbered = [(n, line, m.group(1)) for n, line in headings if (m := re.match(r"##\s+(\d)\.\s", line))]
    if {key for _, _, key in numbered} >= set(SECTION_KEYS["metodo"]):
        marks = [SectionMark(chave=key, linha=n, titulo=line.strip()) for n, line, key in numbered]
        return FileMapping(tipo="metodo", justificativa="seções numeradas 1–7", secoes=marks)
    title = plain(raw.lines[0]) if raw.lines else ""
    if headings and "revisao tecnica" in title:
        known = SECTION_KEYS["revisao"]
        marks = []
        for n, line in headings:
            name = slug(line[3:])
            key = next((k for k in known if name.startswith(k)), name)
            marks.append(SectionMark(chave=key, linha=n, titulo=line.strip()))
        return FileMapping(tipo="revisao", justificativa="registro de revisão técnica", secoes=marks)
    return None


def _pdf(raw: RawFile) -> FileMapping | None:
    head = " ".join(plain(line) for line in raw.lines[:8])
    ignore = _ignored(raw)
    if "entrevista tecnica" in head:
        return FileMapping(tipo="entrevista", justificativa="perguntas da entrevista", secoes=_interview(raw),
                           linhas_ignorar=ignore)
    if re.search(r"recorte de \d+ semanas", head):
        return FileMapping(tipo="dossie", justificativa="cabeçalho com recorte e corte",
                           secoes=_marks(raw, DOSSIER_HEADINGS), linhas_ignorar=ignore)
    if "registro tecnico" in head:
        return FileMapping(tipo="registro_tecnico", justificativa="registro técnico",
                           secoes=_marks(raw, RECORD_HEADINGS), linhas_ignorar=ignore)
    return None


def deterministic_mapping(raw: RawFile) -> tuple[FileMapping | None, str | None]:
    """(mapping, None) when the file is recognized with confidence; (None, reason) to fall back to the agent."""
    if raw.format == "table":
        mapping = _table(raw)
    elif raw.format == "json":
        data = raw.json_data
        recognized = isinstance(data, dict) and "projeto_id" in data and CONFIG_KEYS & set(data)
        mapping = FileMapping(tipo="configuracao", justificativa="chaves de topo") if recognized else None
    elif raw.format == "text":
        mapping = _markdown(raw)
    elif raw.format == "pdf":
        mapping = _pdf(raw)
    else:
        mapping = None
    if mapping is None:
        return None, "tipo não identificado pelo conteúdo"
    required = REQUIRED_SECTIONS.get(mapping.tipo)
    if required and len(mapping.secoes) < required:
        return None, f"{mapping.tipo}: {len(mapping.secoes)} de {required} seções obrigatórias"
    return mapping, None


# Inventory "tipo" column → file type, to cross-check what was identified by content.
INVENTORY_TYPES = {"dossie": "dossie", "registro tecnico": "registro_tecnico", "atividades": "atividades",
                   "inventario": "inventario", "configuracao": "configuracao", "metodo": "metodo",
                   "cronologia": "cronologia", "medicoes": "medicoes", "resultados": "resultados",
                   "entrevista": "entrevista", "entradas": "entradas", "observacoes": "observacoes",
                   "revisao tecnica": "revisao"}
