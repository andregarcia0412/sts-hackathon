from datetime import date

import pytest

from backend.extraction.agent import FileMapping
from backend.extraction.pipeline import extract_project
from tests.factories import extraction_handlers, fake_file_mapping, synthetic_package
from tests.fakes import FakeLLM


@pytest.fixture
async def canonical():
    return await extract_project(FakeLLM(extraction_handlers()), synthetic_package(), code_hint="PRJ90")


async def test_only_unrecognized_files_go_through_the_agent(canonical):
    llm = FakeLLM(extraction_handlers())
    done = await extract_project(llm, synthetic_package(), code_hint="PRJ90")
    [call] = llm.calls_for(FileMapping)  # the known files are mapped by code; only the loose note needs the agent
    assert "notas_soltas.txt" in call[-1]["content"]
    sources = {f.path: f.mapping_source for f in done.files}
    assert sources.pop("notas_soltas.txt") == "agente" and set(sources.values()) == {"deterministico"}
    assert any("mapeado pelo agente" in note for f in done.files for note in f.notes)


async def test_files_classified_by_content_with_evidence_ids(canonical):
    by_path = {f.path: f for f in canonical.files}
    assert by_path["evidencias/metodo.md"].file_type == "metodo"
    assert by_path["evidencias/metodo.md"].evidence_id == "PRJ90-EV06"
    assert by_path["dossie_projeto.pdf"].file_type == "dossie"
    assert by_path["dossie_projeto.pdf"].missing_sections == []
    assert by_path["notas_soltas.txt"].status == "pendente_validacao"
    assert by_path["evidencias/configuracao.json"].file_type == "configuracao"
    assert all(len(f.sha256) == 64 for f in canonical.files)


async def test_fragments_are_verbatim_and_citable(canonical):
    method = canonical.fragment("PRJ90-EV06#2")
    assert method.alias == "evidencias/metodo.md#2"
    assert method.text.startswith("Ordenar lotes por grafo de dependência")
    assert canonical.fragment("PRJ90-S02-M001").data["numerador"] == "196"
    assert canonical.fragment("PRJ90-S02").nature == "derivado"
    question = canonical.fragment("PRJ90-EV01#pergunta_registrada")
    assert question.page == 1
    assert question.text == "Como ordenar lotes sem violar a precedencia contabil?"


async def test_interview_fragments_are_testimony(canonical):
    interview = canonical.fragments_of("entrevista")
    assert {f.anchor for f in interview} >= {"conclusao", "situacao", "condicao_do_registro"}
    assert all(f.nature == "depoimento" for f in interview)


async def test_context_points_to_existing_fragments_and_copies_their_text(canonical):
    ctx = canonical.context
    assert ctx.elemento_novo.fragment_ids == ["PRJ90-EV06#2"]
    assert ctx.elemento_novo.text == canonical.fragment("PRJ90-EV06#2").text
    assert ctx.barreira.fragment_ids == ["PRJ90-EV01#contexto"]  # invented id dropped
    assert "Time Conciliacao" in ctx.termos_sensiveis
    assert "PRJ90" in ctx.termos_sensiveis


async def test_reference_date_comes_from_dossier_header(canonical):
    ctx = canonical.context
    assert ctx.corte == date(2025, 3, 17)
    assert ctx.recorte_semanas == 10
    assert ctx.data_referencia == date(2025, 1, 6)
    assert ctx.data_referencia_origem == "cabecalho"
    assert ctx.data_referencia_fragmento == "PRJ90-EV01#cabecalho"
    assert ctx.team == "Time Conciliacao"


async def test_fragment_ids_are_unique(canonical):
    ids = [f.id for f in canonical.fragments]
    assert len(ids) == len(set(ids))


async def test_agent_failure_on_one_file_does_not_stop_extraction():
    def flaky(messages):
        if "notas_soltas" in messages[-1]["content"]:
            raise RuntimeError("model down")
        return fake_file_mapping(messages)

    handlers = extraction_handlers() | {FileMapping: flaky}
    canonical = await extract_project(FakeLLM(handlers), synthetic_package(), code_hint="PRJ90")
    notes = next(f for f in canonical.files if f.path == "notas_soltas.txt")
    assert notes.status == "nao_extraido"
    assert notes.notes


async def test_reference_date_override_wins():
    canonical = await extract_project(
        FakeLLM(extraction_handlers()), synthetic_package(), code_hint="PRJ90", reference_date=date(2024, 12, 1)
    )
    assert canonical.context.data_referencia == date(2024, 12, 1)
    assert canonical.context.data_referencia_origem == "informada"
