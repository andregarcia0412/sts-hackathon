import json

from openpyxl import Workbook

from backend.extraction.text import read_raw
from tests.factories import DOSSIE_LINES, make_pdf


def test_csv_strips_bom_and_keeps_lines():
    raw = read_raw("x.csv", "﻿a;b\n1;\n".encode())
    assert raw.format == "table"
    assert raw.lines == ["a;b", "1;"]


def test_pdf_lines_and_pages():
    raw = read_raw("d.pdf", make_pdf(DOSSIE_LINES))
    assert raw.format == "pdf"
    assert "Pergunta registrada" in raw.lines
    assert set(raw.line_pages) == {1}
    assert len(raw.line_pages) == len(raw.lines)


def test_xlsx_rows_rendered_with_semicolons_and_trailing_blanks_trimmed(tmp_path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Titulo", None, None])
    sheet.append([])
    sheet.append(["id", "valor", None])
    sheet.append(["A1", 3, None])
    path = tmp_path / "a.xlsx"
    workbook.save(path)
    raw = read_raw("a.xlsx", path.read_bytes())
    assert raw.format == "table"
    assert raw.lines == ["Titulo", "", "id;valor", "A1;3"]


def test_json_is_parsed_and_lines_kept():
    raw = read_raw("c.json", json.dumps({"a": 1}).encode())
    assert raw.format == "json"
    assert raw.json_data == {"a": 1}


def test_invalid_json_keeps_text_and_records_error():
    raw = read_raw("c.json", b"{oops")
    assert raw.json_data is None
    assert raw.error


def test_markdown_and_binary():
    assert read_raw("m.md", "# t\nx".encode()).lines == ["# t", "x"]
    binary = read_raw("img.png", b"\x89PNG\r\n\x1a\n\x00\x00")
    assert binary.format == "binary"
    assert binary.lines == []


def test_sha256_recorded():
    assert len(read_raw("m.md", b"x").sha256) == 64
