import json

import pytest

from backend.extraction.agent import render_numbered
from backend.extraction.structure import deterministic_mapping
from backend.extraction.text import read_raw
from tests.factories import fake_file_mapping, synthetic_package

FIELDS = ("tipo", "linha_cabecalho", "coluna_id", "coluna_arquivo")


@pytest.mark.parametrize("incoming", [f for f in synthetic_package() if f.path != "notas_soltas.txt"],
                         ids=lambda f: f.path)
def test_deterministic_mapping_equals_what_the_agent_is_asked_to_produce(incoming):
    raw = read_raw(incoming.path, incoming.data)
    mapping, reason = deterministic_mapping(raw)
    assert reason is None
    expected = fake_file_mapping([{"role": "user", "content": render_numbered(raw)}])
    assert {f: getattr(mapping, f) for f in FIELDS} == {f: getattr(expected, f) for f in FIELDS}
    assert [(m.chave, m.linha, m.titulo) for m in mapping.secoes] == \
        [(m.chave, m.linha, m.titulo) for m in expected.secoes]


def test_the_name_of_the_file_does_not_matter():
    for incoming in synthetic_package():
        if incoming.path == "notas_soltas.txt":
            continue
        original, _ = deterministic_mapping(read_raw(incoming.path, incoming.data))
        suffix = incoming.path.rsplit(".", 1)[-1]
        renamed, _ = deterministic_mapping(read_raw(f"x.{suffix}", incoming.data))
        assert renamed.tipo == original.tipo


def test_xlsx_header_on_row_five_and_empty_cell_is_null():
    import io

    from openpyxl import Workbook

    from backend.extraction.slicer import slice_file

    book = Workbook()
    sheet = book.active
    sheet.append([])
    sheet.append(["PRJ90  Fila"])
    sheet.append(["Registro sintético."])
    sheet.append([])
    sheet.append(["ID da atividade", "Ciclo", "Resultado ou saída"])
    sheet.append(["PRJ90-ATV01", "C1", None])
    buffer = io.BytesIO()
    book.save(buffer)
    raw = read_raw("planilha.xlsx", buffer.getvalue())
    mapping, _ = deterministic_mapping(raw)
    assert (mapping.tipo, mapping.linha_cabecalho, mapping.coluna_id) == ("atividades", 5, "ID da atividade")
    [row] = slice_file(raw, mapping, "PRJ90", "PRJ90-EV03").fragments
    assert row.id == "PRJ90-ATV01" and row.data["Resultado ou saída"] is None


def test_unknown_or_incomplete_files_fall_back_to_the_agent():
    assert deterministic_mapping(read_raw("notas.txt", b"Anotacao solta sem estrutura."))[0] is None
    partial = "# PRJ90 — Método e referência\\n\\n## 1. Referência anterior\\n\\nx\\n\\n## 2. Mecanismo\\n\\ny\\n"
    mapping, reason = deterministic_mapping(read_raw("m.md", partial.encode()))
    assert mapping is None and "tipo não identificado" in reason
    config = json.dumps({"qualquer": 1}).encode()
    assert deterministic_mapping(read_raw("c.json", config))[0] is None


async def test_a_file_that_contradicts_the_inventory_goes_to_the_agent():
    from backend.extraction.agent import FileMapping
    from backend.extraction.pipeline import extract_project
    from backend.projects.importer import IncomingFile
    from tests.factories import extraction_handlers
    from tests.fakes import FakeLLM

    files = synthetic_package()
    inventory = next(f for f in files if f.path == "inventario_evidencias.csv")
    patched = inventory.data.decode().replace("PRJ90-EV07;PRJ90;Cronologia", "PRJ90-EV07;PRJ90;Medições")
    files = [f if f is not inventory else IncomingFile(path=f.path, data=patched.encode(), top_folder="PRJ90")
             for f in files]
    llm = FakeLLM(extraction_handlers())
    done = await extract_project(llm, files, code_hint="PRJ90")
    chronology = next(f for f in done.files if f.path == "evidencias/cronologia.csv")
    assert chronology.mapping_source == "agente" and "o inventário declara medicoes" in " ".join(chronology.notes)
    assert len(llm.calls_for(FileMapping)) == 2
