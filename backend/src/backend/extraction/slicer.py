"""Applies the agent's mapping to the verbatim file: sections and rows become citable fragments."""

import csv
import io
import json
import re
from dataclasses import dataclass, field

from backend.extraction.agent import FileMapping, SectionMark
from backend.extraction.schema import NATURE_BY_TYPE, PREAMBLE_KEY, REQUIRED_SECTIONS, SECTION_KEYS, Fragment
from backend.extraction.text import RawFile

WHOLE_FILE_ANCHOR = "texto"


@dataclass
class SliceResult:
    fragments: list[Fragment] = field(default_factory=list)
    missing_sections: list[str] = field(default_factory=list)
    rejected_marks: list[str] = field(default_factory=list)


def _norm_heading(text: str) -> str:
    return " ".join(text.strip().lstrip("#").split()).casefold()


def _locate(raw: RawFile, mark: SectionMark) -> int | None:
    """Line (1-based) of a heading, trusting the title over the line number; None when invented."""
    wanted = _norm_heading(mark.titulo)
    if not wanted:
        return None
    if 1 <= mark.linha <= len(raw.lines) and _norm_heading(raw.lines[mark.linha - 1]) == wanted:
        return mark.linha
    matches = [n for n, line in enumerate(raw.lines, start=1) if _norm_heading(line) == wanted]
    return matches[0] if matches else None


def _body(raw: RawFile, start: int, end: int, ignore: set[int]) -> str:
    """Lines start..end (1-based, inclusive), without blank or ignored lines."""
    kept = [raw.lines[n - 1].strip() for n in range(start, end + 1) if n not in ignore and raw.lines[n - 1].strip()]
    return "\n".join(kept)


def _page(raw: RawFile, line: int) -> int | None:
    return raw.line_pages[line - 1] if raw.line_pages and 0 < line <= len(raw.line_pages) else None


def _fragment(raw: RawFile, mapping: FileMapping, evidence_id: str, anchor: str, text: str, line: int | None,
              data=None, fragment_id: str | None = None) -> Fragment:
    return Fragment(
        id=fragment_id or f"{evidence_id}#{anchor}",
        alias=f"{raw.path}#{anchor}",
        file=raw.path,
        file_type=mapping.tipo,
        anchor=anchor,
        page=_page(raw, line) if line else None,
        line=line,
        text=text,
        nature=NATURE_BY_TYPE[mapping.tipo],
        data=data,
    )


def _slice_document(raw: RawFile, mapping: FileMapping, evidence_id: str) -> SliceResult:
    result = SliceResult()
    located: dict[str, int] = {}
    for mark in mapping.secoes:
        line = _locate(raw, mark)
        if line is None:
            result.rejected_marks.append(mark.chave)
        elif mark.chave not in located:
            located[mark.chave] = line
    ignore = set(mapping.linhas_ignorar)
    ordered = sorted(located.items(), key=lambda item: item[1])
    if ordered:
        preamble = _body(raw, 1, ordered[0][1] - 1, ignore)
        if preamble:
            result.fragments.append(_fragment(raw, mapping, evidence_id, PREAMBLE_KEY, preamble, 1))
        for index, (key, line) in enumerate(ordered):
            end = ordered[index + 1][1] - 1 if index + 1 < len(ordered) else len(raw.lines)
            text = _body(raw, line + 1, end, ignore)
            if text:
                result.fragments.append(_fragment(raw, mapping, evidence_id, key, text, line))
    elif text := _body(raw, 1, len(raw.lines), ignore):
        result.fragments.append(_fragment(raw, mapping, evidence_id, WHOLE_FILE_ANCHOR, text, 1))
    if mapping.tipo in REQUIRED_SECTIONS:
        present = {f.anchor for f in result.fragments}
        result.missing_sections = [key for key in SECTION_KEYS[mapping.tipo] if key not in present][
            : len(SECTION_KEYS[mapping.tipo])
        ]
        if mapping.tipo == "entrevista":
            result.missing_sections = [k for k in result.missing_sections if k != "condicao_do_registro"]
    return result


def _delimiter(header: str) -> str:
    return ";" if header.count(";") >= header.count(",") else ","


def _slice_table(raw: RawFile, mapping: FileMapping, evidence_id: str) -> SliceResult:
    result = SliceResult()
    header_line = mapping.linha_cabecalho if mapping.linha_cabecalho and mapping.linha_cabecalho <= len(raw.lines) else 1
    if not raw.lines:
        return result
    delimiter = _delimiter(raw.lines[header_line - 1])
    columns = [c.strip().lstrip("﻿") for c in next(csv.reader([raw.lines[header_line - 1]], delimiter=delimiter))]
    body_lines = raw.lines[header_line:]
    reader = csv.reader(io.StringIO("\n".join(body_lines)), delimiter=delimiter)
    previous_end = 0
    seen: set[str] = set()
    for cells in reader:
        start, previous_end = previous_end + 1, reader.line_num
        line = header_line + start
        text = "\n".join(body_lines[start - 1 : previous_end])
        if not any(cell.strip() for cell in cells):
            continue
        data = {col: (cells[i] if i < len(cells) and cells[i].strip() != "" else None) for i, col in enumerate(columns)}
        row_id = data.get(mapping.coluna_id) if mapping.coluna_id else None
        if row_id and row_id not in seen:
            seen.add(row_id)
            anchor, fragment_id = row_id, row_id
        else:
            anchor, fragment_id = f"L{line}", f"{evidence_id}#L{line}"
        result.fragments.append(
            _fragment(raw, mapping, evidence_id, anchor, text, line, data=data, fragment_id=fragment_id)
        )
    return result


def _slice_json(raw: RawFile, mapping: FileMapping, evidence_id: str) -> SliceResult:
    if not isinstance(raw.json_data, dict):
        return _whole(raw, mapping, evidence_id)
    result = SliceResult()
    for key, value in raw.json_data.items():
        anchor = re.sub(r"\s+", "_", str(key))
        result.fragments.append(_fragment(raw, mapping, evidence_id, anchor, json.dumps(value, ensure_ascii=False), None))
    return result


def _whole(raw: RawFile, mapping: FileMapping, evidence_id: str) -> SliceResult:
    text = raw.text.strip()
    return SliceResult(fragments=[_fragment(raw, mapping, evidence_id, WHOLE_FILE_ANCHOR, text, 1)] if text else [])


def slice_file(raw: RawFile, mapping: FileMapping, code: str, evidence_id: str) -> SliceResult:
    if mapping.tipo == "desconhecido":
        return _whole(raw, mapping, evidence_id)
    if raw.format == "json" and raw.json_data is not None:
        return _slice_json(raw, mapping, evidence_id)
    if raw.format == "table" or mapping.linha_cabecalho:
        return _slice_table(raw, mapping, evidence_id)
    return _slice_document(raw, mapping, evidence_id)
