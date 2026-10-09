"""Module 5: the report (parecer) is assembled from the analysis graph data. It decides nothing."""

import re
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from backend.analyses.models import Analysis
from backend.catalog.models import CRITERIA_ORDER, Catalog
from backend.criteria.schemas import EvidenceItem, SearchLogEntry
from backend.graph.classify import CLASS_LABELS
from backend.graph.states import Caveat, MissingLinkInfo
from backend.report.redact import ReportTexts

ANSWER_KEY_COLUMNS = [
    "projeto_id", "titulo", "classificacao", "justificativa", "limite", "fontes_decisivas", "divergencia_depoimento",
    *[f"{field}_{n}" for n in range(1, 6) for field in ("criterio", "estado", "justificativa", "fonte")],
]
EVIDENCE_REF_RE = re.compile(r"\[?(ev-[0-9a-f]{16})\]?")
GAP_STATUSES = ("na", "parcial", "nao_executada", "sem_evidencia")


class EvidenceRef(BaseModel):
    id: str
    regra: str
    fonte: str
    trecho: str
    polaridade: str
    natureza: str
    explicacao: str
    url: str | None = None
    data_publicacao: str | None = None


class RuleLine(BaseModel):
    regra: str
    titulo: str
    status: str
    motivo: str | None = None
    nota: int | None = None
    positivas: int = 0
    negativas: int = 0
    fontes_normativas: list[str] = Field(default_factory=list)


class AnswerLine(BaseModel):
    """Questionnaire mode: question → answer → evidence (what an auditor needs to redo the reasoning)."""

    pergunta: str
    texto: str
    resposta: str
    explicacao: str
    fontes: list[str] = Field(default_factory=list)
    origem: str = "juiz"
    o_que_falta: str | None = None


class CriterionSection(BaseModel):
    chave: str
    criterio: str
    estado: str | None
    justificativa: str
    fonte: str
    nota: int | None
    fonte_normativa: str
    gates: list[str] = Field(default_factory=list)
    regras: list[RuleLine] = Field(default_factory=list)
    respostas: list[AnswerLine] = Field(default_factory=list)
    regra_de_decisao: str | None = None


class Gap(BaseModel):
    regra: str
    status: str
    motivo: str


class AnalystDecisionInfo(BaseModel):
    outcome: str
    justification: str
    analyst_name: str
    decided_at: datetime


class Traceability(BaseModel):
    analysis_id: str
    version: int
    schema_version: str | None
    catalog_version: str | None
    models: dict[str, str | None]
    prompts: dict[str, str]
    file_hashes: dict[str, str]
    temperature: float
    regras_aplicadas: int


class Parecer(BaseModel):
    projeto_id: str
    titulo: str
    gerado_em: datetime
    classe_sugerida: str | None
    classificacao: str | None
    inconsistente: bool
    motivo_classe: str
    caminho_arvore: list[str] = Field(default_factory=list)
    incompleto: list[str] = Field(default_factory=list)
    resumo: str
    justificativa: str
    limite: str
    texto_gerado_por_llm: bool
    ressalva: Caveat | None = None
    elo_ausente: MissingLinkInfo | None = None
    criterios: list[CriterionSection]
    fontes_decisivas: list[str]
    evidencias_usadas: list[EvidenceRef]
    evidencias_contrarias: list[EvidenceRef]
    divergencias: list[str]
    elos_ausentes: list[str]
    lacunas: list[Gap]
    anexo_busca: list[SearchLogEntry]
    rastreabilidade: Traceability
    decisoes_analista: list[AnalystDecisionInfo] = Field(default_factory=list)


def _unique_divergences(divergences: list) -> list[str]:
    """One line per interview sentence and record, even when the sub-agent and CHK-DIVERG both recorded it."""
    from backend.checks.divergences import _normal, _same_sentence

    seen: list[tuple[str, str]] = []
    statements = []
    for divergence in divergences:
        quote = _normal(divergence.testimony_quote)
        if any(_same_sentence(quote, other) and record == divergence.record_fragment_id for other, record in seen):
            continue
        seen.append((quote, divergence.record_fragment_id))
        statements.append(divergence.statement)
    return list(dict.fromkeys(statements))


def _evidence_index(analysis: Analysis) -> dict[str, EvidenceItem]:
    return {e.id: e for result in analysis.criteria.values() for run in result.rules for e in run.evidences}


def replace_evidence_ids(text: str, index: dict[str, EvidenceItem]) -> str:
    return EVIDENCE_REF_RE.sub(lambda m: f"[{index[m.group(1)].source_alias}]" if m.group(1) in index else "", text)


def _ref(item: EvidenceItem) -> EvidenceRef:
    return EvidenceRef(id=item.id, regra=item.rule_id, fonte=item.source_alias, trecho=item.quote, polaridade=item.polarity,
                       natureza=item.nature, explicacao=item.explanation, url=item.url,
                       data_publicacao=str(item.published_date) if item.published_date else None)


def facts_for_text(catalog: Catalog, analysis: Analysis) -> tuple[str, str]:
    """What the report writer may use (facts) and the text numbers may come from (allowed source)."""
    index = _evidence_index(analysis)
    suggestion = analysis.suggestion
    lines = [f"Classe sugerida: {CLASS_LABELS.get(suggestion.suggested_class or '', 'sem classe automática')}"
             f" ({suggestion.reason})" if suggestion else "Classe sugerida: sem classe automática"]
    if suggestion and suggestion.inconsistent:
        lines.append("Combinação de estados fora dos padrões: revisar. Caminho: " + " → ".join(suggestion.path))
    for criterion in CRITERIA_ORDER:
        state = analysis.states.get(criterion)
        name = catalog.criteria[criterion].nome
        if state:
            lines.append(f"{name}: {state.state or 'não avaliado'} — {replace_evidence_ids(state.justification, index)}")
    if suggestion and suggestion.caveat:
        c = suggestion.caveat
        lines.append(f"Recorte sustentado: {c.recorte_sustentado}; limitação: {c.limitacao}; evidência necessária: {c.evidencia_necessaria}")
    if suggestion and suggestion.missing_link:
        lines.append(f"Elo ausente: {suggestion.missing_link.elo_ausente}; solicitar: {', '.join(suggestion.missing_link.evidencias_a_solicitar)}")
    for result in analysis.criteria.values():
        lines += [d.statement for d in result.divergences]
    allowed = "\n".join(e.quote for e in index.values())
    return "\n".join(lines), allowed


def template_texts(catalog: Catalog, analysis: Analysis) -> ReportTexts:
    suggestion = analysis.suggestion
    label = CLASS_LABELS.get(suggestion.suggested_class or "", "Sem classe automática") if suggestion else "Sem classe automática"
    states = "; ".join(
        f"{catalog.criteria[c].nome}: {analysis.states[c].state or 'não avaliado'}" for c in CRITERIA_ORDER if c in analysis.states
    )
    limit = ""
    if suggestion and suggestion.caveat:
        limit = f"{suggestion.caveat.limitacao or ''} Recorte sustentado: {suggestion.caveat.recorte_sustentado or '-'}."
    elif suggestion and suggestion.missing_link:
        limit = f"Elo ausente: {suggestion.missing_link.elo_ausente or '-'}."
    reason = suggestion.reason if suggestion else "critérios sem estado"
    return ReportTexts(
        resumo=f"{label} (sugestão do sistema; a decisão é do analista). {reason}.",
        justificativa=f"{label}: {reason}. {states}.",
        limite=limit.strip(),
        gerado_por_llm=False,
    )


def build_parecer(catalog: Catalog, analysis: Analysis, decisions: list[AnalystDecisionInfo] | None,
                  texts: ReportTexts | None = None, title: str | None = None, code: str | None = None) -> Parecer:
    report = analysis.report or {}
    if texts is None:
        texts = (ReportTexts(resumo=report["resumo"], justificativa=report["justificativa"], limite=report["limite"],
                             gerado_por_llm=report.get("texto_gerado_por_llm", False))
                 if report.get("resumo") else template_texts(catalog, analysis))
    index = _evidence_index(analysis)
    suggestion = analysis.suggestion
    sections, decisive_files, used, contrary, divergences, links, gaps, annex = [], [], [], [], [], [], [], []
    for criterion in CRITERIA_ORDER:
        info = catalog.criteria[criterion]
        result = analysis.criteria.get(criterion)
        state = analysis.states.get(criterion)
        scores = {s.rule_id: s for s in analysis.scores.get(criterion, [])}
        decisive = [index[i] for i in (state.decisive_evidence_ids if state else []) if i in index]
        evidences = [e for run in (result.rules if result else []) for e in run.evidences]
        # The answer-key "fonte" is a package file: decisive documentary evidence first, web only as last resort.
        ranked = [e for e in decisive if e.origin == "doc"] + [e for e in evidences if e.origin == "doc"] + decisive + evidences
        main_source = (ranked or [None])[0]
        for item in (e for e in decisive if e.origin == "doc"):
            decisive_files.append(item.source_alias.split("#")[0])
        justification = (replace_evidence_ids(state.justification, index) if state and state.state
                         else f"Critério não avaliado: {state.error if state else 'sem resultado'}")
        rules = []
        for run in result.rules if result else []:
            rule = catalog.get(run.rule_id)
            score = scores.get(run.rule_id)
            rules.append(RuleLine(regra=run.rule_id, titulo=rule.titulo if rule else run.rule_id, status=run.status,
                                  motivo=run.reason or run.note, nota=score.score if score else None,
                                  positivas=score.positive if score else 0, negativas=score.negative if score else 0,
                                  fontes_normativas=rule.fontes_normativas if rule else []))
            if run.status in GAP_STATUSES:
                gaps.append(Gap(regra=run.rule_id, status=run.status, motivo=run.reason or "-"))
        answers = []
        for answer in state.answers if state else []:
            question = catalog.questionnaire.question(criterion, answer.pergunta) if catalog.questionnaire else None
            answers.append(AnswerLine(
                pergunta=answer.pergunta, texto=question.texto.strip() if question else "", resposta=answer.effective,
                explicacao=answer.explicacao, origem=answer.origem, o_que_falta=answer.o_que_falta,
                fontes=list(dict.fromkeys(index[i].source_alias for i in answer.evidencias if i in index))))
        sections.append(CriterionSection(
            chave=criterion, criterio=info.nome, estado=state.state if state else None, justificativa=justification,
            fonte=main_source.source_alias if main_source else "", nota=analysis.criterion_scores.get(criterion),
            fonte_normativa=info.fonte_normativa, gates=state.gates if state else [], regras=rules,
            respostas=answers, regra_de_decisao=state.decision_rule if state else None))
        used += [_ref(e) for e in evidences if e.polarity == "positiva"]
        contrary += [_ref(e) for e in evidences if e.polarity == "negativa"]
        if result:
            divergences += [d for d in result.divergences]
            links += [f"{l.description} — solicitar: {l.evidence_to_request}" for l in result.missing_links]
            annex += result.search_log
    versions = analysis.versions
    return Parecer(
        projeto_id=code or report.get("projeto_id") or "",
        titulo=title or report.get("titulo") or "",
        gerado_em=datetime.now(UTC),
        classe_sugerida=suggestion.suggested_class if suggestion else None,
        classificacao=CLASS_LABELS.get(suggestion.suggested_class) if suggestion and suggestion.suggested_class else None,
        inconsistente=suggestion.inconsistent if suggestion else True,
        motivo_classe=suggestion.reason if suggestion else "sem classe automática",
        caminho_arvore=suggestion.path if suggestion else [],
        incompleto=suggestion.incomplete if suggestion else [],
        resumo=texts.resumo,
        justificativa=texts.justificativa,
        limite=texts.limite,
        texto_gerado_por_llm=texts.gerado_por_llm,
        ressalva=suggestion.caveat if suggestion else None,
        elo_ausente=suggestion.missing_link if suggestion else None,
        criterios=sections,
        fontes_decisivas=list(dict.fromkeys(decisive_files)),
        evidencias_usadas=used,
        evidencias_contrarias=contrary,
        divergencias=_unique_divergences(divergences),
        elos_ausentes=list(dict.fromkeys(links)),
        lacunas=gaps,
        anexo_busca=annex,
        rastreabilidade=Traceability(
            analysis_id=str(analysis.id), version=analysis.version, schema_version=versions.schema_version,
            catalog_version=versions.catalog_version, models=versions.models, prompts=versions.prompts,
            file_hashes=versions.file_hashes, temperature=versions.temperature,
            regras_aplicadas=sum(len(r.rules) for r in analysis.criteria.values()),
        ),
        decisoes_analista=decisions or [],
    )
