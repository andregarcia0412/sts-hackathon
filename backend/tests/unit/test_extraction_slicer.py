import json

from backend.extraction.agent import FileMapping, SectionMark
from backend.extraction.slicer import slice_file
from backend.extraction.text import read_raw

MD = "# Título\n\nPreâmbulo.\n\n## 1. Ref\n\nTexto um.\n\n## 2. Mec\n\nTexto dois.\nRODAPÉ\n"


def test_document_sections_between_headings_with_preamble_and_ignored_lines():
    raw = read_raw("evidencias/metodo.md", MD.encode())
    mapping = FileMapping(
        tipo="metodo",
        justificativa="",
        secoes=[SectionMark(chave="1", linha=5, titulo="## 1. Ref"), SectionMark(chave="2", linha=9, titulo="## 2. Mec")],
        linhas_ignorar=[12],
    )
    result = slice_file(raw, mapping, code="PRJ90", evidence_id="PRJ90-EV06")
    by_anchor = {f.anchor: f for f in result.fragments}
    assert by_anchor["1"].text == "Texto um."
    assert by_anchor["2"].text == "Texto dois."
    assert by_anchor["cabecalho"].text == "# Título\nPreâmbulo."
    assert by_anchor["1"].id == "PRJ90-EV06#1"
    assert by_anchor["1"].alias == "evidencias/metodo.md#1"
    assert by_anchor["1"].nature == "sintese"
    assert by_anchor["2"].line == 9
    assert result.missing_sections == ["3", "4", "5", "6", "7"]


def test_heading_with_wrong_line_is_found_by_title():
    raw = read_raw("evidencias/metodo.md", MD.encode())
    mapping = FileMapping(tipo="metodo", justificativa="", secoes=[SectionMark(chave="1", linha=2, titulo="## 1. Ref")])
    result = slice_file(raw, mapping, code="PRJ90", evidence_id="E")
    assert any(f.anchor == "1" and f.text.startswith("Texto um.") for f in result.fragments)


def test_invented_heading_is_dropped_never_trusted():
    raw = read_raw("evidencias/metodo.md", MD.encode())
    mapping = FileMapping(tipo="metodo", justificativa="", secoes=[SectionMark(chave="3", linha=7, titulo="## 3. Inventado")])
    result = slice_file(raw, mapping, code="PRJ90", evidence_id="E")
    assert "3" not in {f.anchor for f in result.fragments}
    assert result.rejected_marks == ["3"]


def test_table_rows_become_fragments_with_null_for_empty_cells():
    csv = "﻿registro_id;ensaio_id;valor;numerador\nPRJ90-S01-M001;PRJ90-S01;;150\nPRJ90-S01-M002;PRJ90-S01;0;\n"
    raw = read_raw("evidencias/medicoes.csv", csv.encode())
    mapping = FileMapping(tipo="medicoes", justificativa="", linha_cabecalho=1, coluna_id="registro_id")
    result = slice_file(raw, mapping, code="PRJ90", evidence_id="PRJ90-EV08")
    first, second = result.fragments
    assert first.id == "PRJ90-S01-M001"
    assert first.alias == "evidencias/medicoes.csv#PRJ90-S01-M001"
    assert first.text == "PRJ90-S01-M001;PRJ90-S01;;150"
    assert first.data == {"registro_id": "PRJ90-S01-M001", "ensaio_id": "PRJ90-S01", "valor": None, "numerador": "150"}
    assert second.data["valor"] == "0"  # zero is a value, empty is null
    assert first.nature == "registro_primario"
    assert first.line == 2


def test_table_header_on_later_row_and_rows_without_id():
    text = "Planilha\n\n\nNota\nid;desc\n;sem id\nA2;ok\n"
    raw = read_raw("atividades.csv", text.encode())
    mapping = FileMapping(tipo="atividades", justificativa="", linha_cabecalho=5, coluna_id="id")
    result = slice_file(raw, mapping, code="PRJ90", evidence_id="PRJ90-EV03")
    assert [f.id for f in result.fragments] == ["PRJ90-EV03#L6", "A2"]


def test_json_top_level_keys_become_fragments():
    raw = read_raw("evidencias/configuracao.json", json.dumps({"parametros": {"a": None}, "versoes": ["v1"]}).encode())
    result = slice_file(raw, FileMapping(tipo="configuracao", justificativa=""), code="PRJ90", evidence_id="PRJ90-EV05")
    by_anchor = {f.anchor: f for f in result.fragments}
    assert by_anchor["parametros"].text == '{"a": null}'
    assert by_anchor["parametros"].id == "PRJ90-EV05#parametros"
    assert by_anchor["versoes"].nature == "registro_primario"


def test_interview_is_testimony():
    raw = read_raw("e.md", "1. Pergunta?\nResposta.\n".encode())
    mapping = FileMapping(tipo="entrevista", justificativa="", secoes=[SectionMark(chave="conclusao", linha=1, titulo="1. Pergunta?")])
    [fragment] = slice_file(raw, mapping, code="P", evidence_id="P-EV10").fragments
    assert fragment.nature == "depoimento"
    assert fragment.text == "Resposta."


def test_unknown_file_is_one_fragment():
    raw = read_raw("x.txt", b"linha 1\nlinha 2")
    result = slice_file(raw, FileMapping(tipo="desconhecido", justificativa=""), code="P", evidence_id="P-x")
    assert [f.text for f in result.fragments] == ["linha 1\nlinha 2"]
