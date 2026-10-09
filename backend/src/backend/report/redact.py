"""The LLM only writes prose from the graph fields; a numbers gate drops any sentence with a number that is
not in those fields (principle 3: numbers are copied, never recomputed or invented)."""

import logging
import re

from pydantic import BaseModel, Field

from backend.criteria.common import DATA_NOT_INSTRUCTIONS
from backend.errors import safe_error_message
from backend.llm import LLM
from backend.llm.prompts import register_prompt

logger = logging.getLogger(__name__)
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


class ReportTextOut(BaseModel):
    resumo: str = Field(description="3 a 5 linhas: classe, por quê e o que falta")
    justificativa: str = Field(description="Justificativa da classe sugerida")
    limite: str = Field(description="Limite da conclusão (recorte, limitação ou elo ausente)")


class ReportTexts(BaseModel):
    resumo: str
    justificativa: str
    limite: str
    gerado_por_llm: bool


REPORT_SYSTEM = register_prompt(
    "report.text",
    """Você redige o parecer de enquadramento na Lei do Bem para um analista que não conhece a norma a fundo.
Use SOMENTE os fatos recebidos: não acrescente fatos, não recalcule nem arredonde números, não cite
fontes que não estão na lista. Linguagem simples e direta, em português. A classe é uma SUGESTÃO do
sistema; a decisão é do analista. Divergências entre entrevista e registro devem ser mencionadas.
"""
    + DATA_NOT_INSTRUCTIONS,
)


def _numbers(text: str) -> set[str]:
    return {n.replace(",", ".") for n in NUMBER_RE.findall(text)}


def numbers_gate(text: str, allowed_source: str) -> str:
    allowed = _numbers(allowed_source)
    kept = [s for s in SENTENCE_RE.split(text.strip()) if _numbers(s) <= allowed]
    return " ".join(kept).strip()


async def redact(llm: LLM, facts: str, allowed_source: str, fallback: ReportTexts) -> ReportTexts:
    try:
        out = await llm.structured(
            [{"role": "system", "content": REPORT_SYSTEM}, {"role": "user", "content": f"<fragmentos>\n{facts}\n</fragmentos>"}],
            ReportTextOut,
            role="report",
        )
    except Exception as error:  # the report never blocks on prose: the template text is used instead
        logger.warning("report text generation failed, using template: %s", safe_error_message(error))
        return fallback
    source = facts + "\n" + allowed_source
    return ReportTexts(
        resumo=numbers_gate(out.resumo, source) or fallback.resumo,
        justificativa=numbers_gate(out.justificativa, source) or fallback.justificativa,
        limite=numbers_gate(out.limite, source) or fallback.limite,
        gerado_por_llm=True,
    )
