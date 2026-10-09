"""Report stage of the pipeline: texts written by the LLM (gated), document assembled from the graph data."""

from typing import Any

from backend.catalog.models import Catalog
from backend.extraction.schema import CanonicalProject
from backend.llm import LLM
from backend.report.builder import build_parecer, facts_for_text, template_texts
from backend.report.redact import redact


async def generate_report(llm: LLM, catalog: Catalog, analysis, canonical: CanonicalProject) -> dict[str, Any]:
    facts, allowed = facts_for_text(catalog, analysis)
    texts = await redact(llm, facts, allowed, fallback=template_texts(catalog, analysis))
    parecer = build_parecer(catalog, analysis, None, texts=texts, title=canonical.context.title,
                            code=canonical.project_code)
    return parecer.model_dump(mode="json")
