import csv
import io

import pytest
from pypdf import PdfReader

from backend.analyses.orchestrator import AnalysisService
from backend.catalog.loader import get_catalog
from backend.config import Settings
from backend.projects.service import create_project
from backend.report.builder import ANSWER_KEY_COLUMNS, build_parecer
from backend.report.export import answer_key_row, to_csv
from backend.report.pdf import render_pdf
from backend.report.redact import ReportTextOut, numbers_gate
from tests.factories import fake_providers, full_handlers, synthetic_package
from tests.fakes import FakeLLM


@pytest.fixture
async def analysis(db):
    project = await create_project("o", "PRJ90 fila", synthetic_package())
    service = AnalysisService(FakeLLM(full_handlers()), fake_providers, Settings(_env_file=None, ollama_model="m"), get_catalog())
    return await service.run(str((await service.create(project)).id))


def test_answer_key_has_27_columns():
    assert len(ANSWER_KEY_COLUMNS) == 27
    assert ANSWER_KEY_COLUMNS[:7] == ["projeto_id", "titulo", "classificacao", "justificativa", "limite",
                                      "fontes_decisivas", "divergencia_depoimento"]
    assert ANSWER_KEY_COLUMNS[-4:] == ["criterio_5", "estado_5", "justificativa_5", "fonte_5"]


async def test_report_is_stored_by_the_pipeline(analysis):
    report = analysis.report
    assert report["classificacao"] == "Elegível"
    assert report["projeto_id"] == "PRJ90"
    assert [c["criterio"] for c in report["criterios"]] == [
        "Novidade", "Criatividade técnica", "Incerteza tecnológica", "Sistematicidade", "Transferência/reprodução"]


async def test_row_in_answer_key_schema(analysis):
    row = answer_key_row(build_parecer(get_catalog(), analysis, None))
    assert list(row) == ANSWER_KEY_COLUMNS
    assert row["classificacao"] == "Elegível"
    assert row["estado_3"] == "INVESTIGADA"
    assert row["fonte_1"] == "evidencias/metodo.md#1"  # documentary source preferred over the web one
    assert row["fonte_3"] == "evidencias/resultados.csv#PRJ90-S02"
    assert "https://" not in row["fontes_decisivas"]
    assert "evidencias/resultados.csv" in row["fontes_decisivas"]
    assert row["divergencia_depoimento"].startswith('A entrevista afirma "acertou todos os 200 lotes"')
    assert "ev-" not in row["justificativa_1"]  # evidence ids are replaced by their source


async def test_gaps_list_na_partial_and_rules_without_evidence(analysis):
    parecer = build_parecer(get_catalog(), analysis, None)
    gaps = {g.regra: g for g in parecer.lacunas}
    assert gaps["SIS-D4"].status == "na" and gaps["SIS-D4"].motivo
    assert gaps["CRI-D3"].status == "parcial"
    assert any(g.status == "sem_evidencia" for g in parecer.lacunas)


async def test_web_annex_and_traceability(analysis):
    parecer = build_parecer(get_catalog(), analysis, None)
    assert parecer.anexo_busca and parecer.anexo_busca[0].sanitized_query
    assert parecer.rastreabilidade.catalog_version == get_catalog().versao
    assert parecer.rastreabilidade.models["report"] == "fake-report"


def test_numbers_gate_drops_sentences_with_unknown_numbers():
    text = "A versão final acertou 196 de 200 lotes. A taxa chegou a 99,5%. Há divergência."
    assert numbers_gate(text, allowed_source="196;200 lotes") == "A versão final acertou 196 de 200 lotes. Há divergência."


async def test_redaction_fallback_when_llm_fails(db):
    project = await create_project("o", "PRJ90", synthetic_package())
    handlers = full_handlers() | {ReportTextOut: RuntimeError("down")}
    service = AnalysisService(FakeLLM(handlers), fake_providers, Settings(_env_file=None, ollama_model="m"), get_catalog())
    analysis = await service.run(str((await service.create(project)).id))
    assert analysis.report["justificativa"].startswith("Elegível")
    assert analysis.report["texto_gerado_por_llm"] is False


async def test_csv_export_matches_answer_key_format(analysis):
    content = to_csv([answer_key_row(build_parecer(get_catalog(), analysis, None))])
    assert content.startswith("﻿projeto_id;titulo;classificacao")
    rows = list(csv.DictReader(io.StringIO(content.lstrip("﻿")), delimiter=";"))
    assert rows[0]["estado_5"] == "DOCUMENTADA NO ESCOPO"


async def test_pdf_has_summary_and_decision_trail(analysis):
    from datetime import UTC, datetime

    from backend.report.builder import AnalystDecisionInfo

    decision = AnalystDecisionInfo(outcome="not_eligible", justification="Discordo: falta comparador.",
                                   analyst_name="Ana", decided_at=datetime(2026, 10, 9, tzinfo=UTC))
    pdf = render_pdf(build_parecer(get_catalog(), analysis, [decision]))
    assert pdf.startswith(b"%PDF")
    text = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "Elegível" in text
    assert "Não elegível" in text and "Ana" in text  # analyst decision shown next to the suggestion
    assert "A entrevista afirma" in text
