"""Module 1: the project package becomes the canonical JSON."""

import asyncio
import logging
import re
from datetime import date, timedelta
from pathlib import PurePosixPath

from backend.errors import safe_error_message
from backend.extraction.agent import ContextOut, FileMapping, extract_context_ids, map_file
from backend.extraction.schema import (
    PREAMBLE_KEY,
    CanonicalProject,
    ContextField,
    ExtractedFile,
    Fragment,
    ProjectContext,
)
from backend.extraction.slicer import slice_file
from backend.extraction.text import RawFile, read_raw
from backend.llm import LLM
from backend.projects.importer import IncomingFile

logger = logging.getLogger(__name__)

# Standard dossier header: "Equipe: X | Recorte de 32 semanas | Corte: 2025-08-18"
HEADER_RE = re.compile(r"Recorte de\s+(\d+)\s+semanas\s*\|\s*Corte:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
TEAM_RE = re.compile(r"Equipe(?: fictícia| ficticia)?:\s*([^|\n]+)", re.IGNORECASE)
CODE_RE = re.compile(r"\bPRJ\d+\b")
CONTEXT_SOURCES = {"dossie", "metodo", "registro_tecnico"}
CONTEXT_ROWS = 3


async def _map(llm: LLM, raw: RawFile) -> tuple[FileMapping | None, list[str]]:
    """Maps a file; retries once when a heading cannot be found verbatim."""
    if raw.format == "binary":
        return None, ["arquivo binário sem texto"]
    notes: list[str] = []
    try:
        mapping = await map_file(llm, raw)
        probe = slice_file(raw, mapping, code="", evidence_id="probe")
        if probe.rejected_marks:
            notes.append(f"títulos não encontrados literalmente: {', '.join(probe.rejected_marks)}; nova tentativa")
            mapping = await map_file(
                llm,
                raw,
                feedback="Os títulos destas chaves não existem literalmente no arquivo: "
                f"{', '.join(probe.rejected_marks)}. Copie o título exatamente como aparece na linha.",
            )
        return mapping, notes
    except Exception as error:
        return None, [f"agente extrator falhou: {safe_error_message(error)}"]


def _evidence_ids(raw: RawFile, mapping: FileMapping, code: str) -> tuple[dict[str, str], str | None]:
    """path -> EV id from the inventory, plus the project code it declares."""
    result = slice_file(raw, mapping, code=code, evidence_id=f"{code}-inventario")
    by_path, declared = {}, None
    for fragment in result.fragments:
        data = fragment.data or {}
        path = data.get(mapping.coluna_arquivo or "arquivo")
        evidence = data.get(mapping.coluna_id or "id_evidencia")
        if path and evidence:
            by_path[path.strip()] = evidence.strip()
        declared = declared or data.get("projeto_id")
    return by_path, declared


def _default_evidence_id(code: str, path: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "-", PurePosixPath(path).stem).strip("-")
    return f"{code}-{stem}"


def _field(ids: list[str], index: dict[str, Fragment]) -> ContextField:
    valid = [i for i in dict.fromkeys(ids) if i in index]
    return ContextField(text="\n".join(index[i].text for i in valid) or None, fragment_ids=valid)


def _context_fragments(fragments: list[Fragment]) -> list[Fragment]:
    selected = [f for f in fragments if f.file_type in CONTEXT_SOURCES]
    selected += [f for f in fragments if f.file_type == "atividades"][:CONTEXT_ROWS]
    return selected


def _reference_date(fragments: list[Fragment], ctx: ContextOut | None) -> dict:
    for fragment in fragments:
        if fragment.file_type == "dossie" and fragment.anchor == PREAMBLE_KEY and (m := HEADER_RE.search(fragment.text)):
            weeks, cut = int(m.group(1)), date.fromisoformat(m.group(2))
            return {
                "corte": cut,
                "recorte_semanas": weeks,
                "data_referencia": cut - timedelta(weeks=weeks),
                "data_referencia_origem": "cabecalho",
                "data_referencia_fragmento": fragment.id,
            }
    if ctx and ctx.corte and ctx.recorte_semanas:
        try:
            cut = date.fromisoformat(ctx.corte)
        except ValueError:
            return {}
        return {
            "corte": cut,
            "recorte_semanas": ctx.recorte_semanas,
            "data_referencia": cut - timedelta(weeks=ctx.recorte_semanas),
            "data_referencia_origem": "llm",
        }
    return {}


async def _build_context(llm: LLM, fragments: list[Fragment], code: str, reference_date: date | None) -> ProjectContext:
    index = {f.id: f for f in fragments}
    try:
        ctx: ContextOut | None = await extract_context_ids(llm, _context_fragments(fragments))
    except Exception as error:
        logger.warning("context extraction failed: %s", safe_error_message(error))
        ctx = None
    header = next((f.text for f in fragments if f.file_type == "dossie" and f.anchor == PREAMBLE_KEY), "")
    team = (m.group(1).strip() if (m := TEAM_RE.search(header)) else None) or (ctx.equipe if ctx else None)
    sensitive = list(dict.fromkeys([*(ctx.termos_sensiveis if ctx else []), *([team] if team else []), code]))
    context = ProjectContext(
        title=ctx.titulo if ctx else None,
        team=team,
        elemento_novo=_field(ctx.elemento_novo if ctx else [], index),
        referencia_anterior=_field(ctx.referencia_anterior if ctx else [], index),
        barreira=_field(ctx.barreira if ctx else [], index),
        pergunta=_field(ctx.pergunta if ctx else [], index),
        produtos_citados=ctx.produtos_citados if ctx else [],
        termos_sensiveis=sensitive,
        palavras_chave_pt=ctx.palavras_chave_pt if ctx else [],
        palavras_chave_en=ctx.palavras_chave_en if ctx else [],
        **_reference_date(fragments, ctx),
    )
    if reference_date:
        context.data_referencia = reference_date
        context.data_referencia_origem = "informada"
        context.data_referencia_fragmento = None
    return context


async def extract_project(
    llm: LLM,
    files: list[IncomingFile],
    code_hint: str | None = None,
    reference_date: date | None = None,
) -> CanonicalProject:
    raws = await asyncio.gather(*(asyncio.to_thread(read_raw, f.path, f.data) for f in files))
    mapped = await asyncio.gather(*(_map(llm, raw) for raw in raws))

    code = code_hint or "PRJ"
    evidence_by_path: dict[str, str] = {}
    for raw, (mapping, _) in zip(raws, mapped, strict=True):
        if mapping and mapping.tipo == "inventario":
            evidence_by_path, declared = _evidence_ids(raw, mapping, code)
            code = code_hint or declared or code
    if code == "PRJ":
        code = next((m.group(0) for raw in raws for m in [CODE_RE.search(raw.text[:500])] if m), code)

    extracted: list[ExtractedFile] = []
    fragments: list[Fragment] = []
    taken: set[str] = set()
    for raw, (mapping, notes) in zip(raws, mapped, strict=True):
        evidence_id = evidence_by_path.get(raw.path) or _default_evidence_id(code, raw.path)
        if mapping is None:
            extracted.append(
                ExtractedFile(path=raw.path, sha256=raw.sha256, file_type="desconhecido", evidence_id=evidence_id,
                              status="nao_extraido", notes=notes)
            )
            continue
        result = slice_file(raw, mapping, code=code, evidence_id=evidence_id)
        for fragment in result.fragments:
            if fragment.id in taken:  # same row in two files (e.g. atividades.xlsx and .csv)
                fragment.id = f"{fragment.id}@{evidence_id}"
            taken.add(fragment.id)
        fragments += result.fragments
        if result.rejected_marks:
            notes = [*notes, f"títulos descartados: {', '.join(result.rejected_marks)}"]
        if raw.error:
            notes = [*notes, raw.error]
        extracted.append(
            ExtractedFile(
                path=raw.path,
                sha256=raw.sha256,
                file_type=mapping.tipo,
                evidence_id=evidence_id,
                status="pendente_validacao" if mapping.tipo == "desconhecido" else "reconhecido",
                missing_sections=result.missing_sections,
                notes=notes,
                fragment_count=len(result.fragments),
            )
        )
    context = await _build_context(llm, fragments, code, reference_date)
    return CanonicalProject(project_code=code, files=extracted, fragments=fragments, context=context)
