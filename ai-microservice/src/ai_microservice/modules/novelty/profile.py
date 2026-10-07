import re
from datetime import date, timedelta
from typing import Literal

from ai_microservice.llm import LLMClient
from ai_microservice.modules.novelty.prompts import PROFILE_SYSTEM
from ai_microservice.modules.novelty.schemas import ProfileExtraction, ProjectProfile

# Cabeçalho padrão dos dossiês do pacote: "Recorte de 32 semanas | Corte: 2025-08-18"
HEADER_RE = re.compile(r"Recorte de\s+(\d+)\s+semanas\s*\|\s*Corte:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)


class ProfileError(ValueError):
    pass


def resolve_start_date(
    corte: str | None, semanas: int | None, override: date | None
) -> tuple[date, Literal["calculada", "informada"]]:
    """Data de referência (T3 / NOV-W1): a informada pelo analista vale; senão, início = corte − semanas."""
    if override:
        return override, "informada"
    if corte and semanas:
        try:
            return date.fromisoformat(corte) - timedelta(weeks=semanas), "calculada"
        except ValueError as error:
            raise ProfileError(f"Data de corte inválida no dossiê: {corte!r}") from error
    raise ProfileError(
        "Não foi possível obter a data de início do projeto pelo dossiê; informe `data_inicio` (AAAA-MM-DD)."
    )


def build_documents_message(dossie: str, entrevista: str | None) -> str:
    message = f"<dossie>\n{dossie}\n</dossie>"
    if entrevista:
        message += f"\n\n<entrevista>\n{entrevista}\n</entrevista>"
    return message


async def extract_profile(
    llm: LLMClient, dossie: str, entrevista: str | None, data_inicio: date | None
) -> ProjectProfile:
    extraction = await llm.structured(
        [
            {"role": "system", "content": PROFILE_SYSTEM},
            {"role": "user", "content": build_documents_message(dossie, entrevista)},
        ],
        ProfileExtraction,
        role="extraction",
    )
    # O cabeçalho do dossiê, quando presente, é lido sem LLM: a data de referência tem de ser determinística.
    if match := HEADER_RE.search(dossie):
        extraction.recorte_semanas = int(match.group(1))
        extraction.corte = match.group(2)
        extraction.trecho_data = match.group(0)
    data_referencia, origem = resolve_start_date(extraction.corte, extraction.recorte_semanas, data_inicio)
    return ProjectProfile(
        **extraction.model_dump(), data_referencia=data_referencia, data_inicio_origem=origem
    )
