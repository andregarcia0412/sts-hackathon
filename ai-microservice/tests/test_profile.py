from datetime import date

import pytest

from ai_microservice.modules.novelty.profile import ProfileError, extract_profile, resolve_start_date
from ai_microservice.modules.novelty.schemas import CampoComOrigem, ProfileExtraction
from tests.fakes import FakeLLM

PRJ21_HEADER = (
    "PRJ21 | Isolamento dinâmico de serviços lentos\n"
    "Equipe: Plataforma de Serviços | Recorte de 32 semanas | Corte: 2025-08-18\n"
)


def extraction(**overrides) -> ProfileExtraction:
    field = CampoComOrigem(texto="x", origem="dossie")
    data = dict(
        titulo="t",
        elemento_novo_declarado=field,
        problema_tecnico=field,
        dominio_setor=field,
        referencia_anterior_declarada=field,
        corte=None,
        recorte_semanas=None,
        trecho_data="",
        palavras_chave_pt=[],
        palavras_chave_en=[],
        termos_sensiveis=[],
    )
    return ProfileExtraction(**(data | overrides))


def test_start_date_is_cut_minus_weeks():
    assert resolve_start_date("2025-08-18", 32, None) == (date(2025, 1, 6), "calculada")


def test_informed_start_date_wins():
    assert resolve_start_date("2025-08-18", 32, date(2024, 12, 1)) == (date(2024, 12, 1), "informada")


def test_without_any_date_it_fails():
    with pytest.raises(ProfileError):
        resolve_start_date(None, None, None)


async def test_header_is_read_without_trusting_the_llm():
    llm = FakeLLM({ProfileExtraction: lambda _: extraction(corte="2030-01-01", recorte_semanas=1)})
    profile = await extract_profile(llm, PRJ21_HEADER + "Contexto...", "entrevista", None)
    assert profile.data_referencia == date(2025, 1, 6)
    assert profile.trecho_data == "Recorte de 32 semanas | Corte: 2025-08-18"


async def test_interview_is_sent_in_its_own_block():
    llm = FakeLLM({ProfileExtraction: lambda _: extraction(corte="2025-08-18", recorte_semanas=32)})
    await extract_profile(llm, "dossiê", "depoimento", None)
    user_message = llm.calls[0][1][-1]["content"]
    assert "<dossie>\ndossiê\n</dossie>" in user_message
    assert "<entrevista>\ndepoimento\n</entrevista>" in user_message
