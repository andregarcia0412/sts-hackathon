"""Criterion state: suggested by an LLM judge over the evidence nodes, then forced by gates in code."""

from typing import Literal

from pydantic import BaseModel, Field

from backend.catalog.loader import get_catalog
from backend.catalog.models import Catalog
from backend.criteria.common import DATA_NOT_INSTRUCTIONS, argument_block
from backend.criteria.schemas import CriterionResult
from backend.errors import safe_error_message
from backend.llm import LLM
from backend.llm.prompts import register_prompt

Column = Literal["pd", "rotina", "insuficiente"]
NUMERIC_NATURES = {"registro_primario", "derivado"}
CONFIG_GATES = {"NOV": ("NOV-D4", "NOV-D10"), "CRI": ("CRI-D5",)}
# Novelty and creativity are proven by the method text; the numeric record may sit in other criteria.
NUMERIC_IN_CRITERION = {"INC", "SIS", "REP"}


class Caveat(BaseModel):
    recorte_sustentado: str | None = None
    limitacao: str | None = None
    evidencia_necessaria: str | None = None

    def complete(self) -> bool:
        return bool(self.recorte_sustentado and self.limitacao and self.evidencia_necessaria)


class MissingLinkInfo(BaseModel):
    elo_ausente: str | None = None
    evidencias_a_solicitar: list[str] = Field(default_factory=list)


class StateJudgeOut(BaseModel):
    estado: str = Field(description="Um dos estados do vocabulário, copiado exatamente")
    justificativa: str = Field(description="Até 4 frases, citando IDs de evidência entre colchetes")
    evidencias_decisivas: list[str] = Field(default_factory=list, description="IDs ev-... que decidem o estado")
    recorte_sustentado: str | None = None
    limitacao: str | None = None
    evidencia_necessaria: str | None = None
    elo_ausente: str | None = None
    evidencias_a_solicitar: list[str] = Field(default_factory=list)


class CriterionState(BaseModel):
    criterion: str
    state: str | None
    column: Column | None = None
    llm_state: str | None = None
    justification: str = ""
    decisive_evidence_ids: list[str] = Field(default_factory=list)
    gates: list[str] = Field(default_factory=list)
    caveat: Caveat | None = None
    missing_link: MissingLinkInfo | None = None
    error: str | None = None

    @classmethod
    def of(cls, criterion: str, state: str, **extra) -> "CriterionState":
        return cls(criterion=criterion, state=state, column=column_of(criterion, state), llm_state=state, **extra)


def column_of(criterion: str, state: str | None, catalog: Catalog | None = None) -> Column | None:
    vocabulary = (catalog or get_catalog()).criteria[criterion].estados
    if state in vocabulary.positivo:
        return "pd"
    if state == vocabulary.negativo:
        return "rotina"
    if state == vocabulary.indeterminado:
        return "insuficiente"
    return None


STATE_SYSTEM = register_prompt(
    "graph.state",
    """Você sugere o ESTADO de um critério de Frascati para um projeto da Lei do Bem, a partir somente das
evidências já verificadas (cada uma com ID ev-...). O analista decide; você sugere e justifica.

Escolha exatamente um estado do vocabulário:
- coluna P&D: o critério está demonstrado no recorte ensaiado;
- coluna rotina: a evidência permite concluir aplicação de técnica conhecida, configuração, integração,
  migração ou aceite (o mecanismo documentado decide, não o título);
- coluna insuficiente: falta informação essencial para verificar o núcleo alegado (plano, diagrama ou
  memorando sem execução registrada).
Para Transferência/reprodução: "DOCUMENTADA COM LIMITE" quando há lacuna técnica DENTRO da pretensão original
(hipótese não ensaiada, critério prévio não atingido) — preencha recorte_sustentado, limitacao e
evidencia_necessaria. Limite excluído desde o início não gera ressalva ("DOCUMENTADA NO ESCOPO").
Em estado da coluna insuficiente, preencha elo_ausente e evidencias_a_solicitar.
Justifique citando IDs de evidência; nunca invente fatos ou números. Divergências da entrevista mudam a
justificativa, não o estado. Nunca compare com outros projetos.
"""
    + DATA_NOT_INSTRUCTIONS,
)


def _describe(result: CriterionResult) -> str:
    lines = []
    for rule in result.rules:
        header = f"{rule.rule_id} [{rule.status}]" + (f" — {rule.reason}" if rule.reason else "")
        if rule.note:
            header += f" — {rule.note}"
        lines.append(header)
        for e in rule.evidences:
            lines.append(f'  [{e.id}] {e.polarity} fonte={e.source_alias} natureza={e.nature}: "{e.quote}" — {e.explanation}')
    for d in result.divergences:
        lines.append(f"Divergência: {d.statement}")
    for link in result.missing_links:
        lines.append(f"Elo ausente apontado: {link.description} (solicitar: {link.evidence_to_request})")
    if result.closest_doc:
        doc = result.closest_doc
        lines.append(f"Documento anterior mais próximo: {doc.title} ({doc.url}), cobertura {doc.cobertura}")
    return "\n".join(lines) or "(nenhuma regra executada)"


def _net_negative(result: CriterionResult, rule_id: str) -> bool:
    run = result.rule(rule_id)
    if run is None:
        return False
    sources_pos = {e.source_id for e in run.evidences if e.polarity == "positiva"}
    sources_neg = {e.source_id for e in run.evidences if e.polarity == "negativa"}
    return len(sources_neg) > len(sources_pos)


def apply_gates(state: CriterionState, result: CriterionResult, catalog: Catalog, numeric_in_analysis: bool) -> CriterionState:
    vocabulary = catalog.criteria[state.criterion].estados
    if state.criterion == "NOV" and result.closest_doc and result.closest_doc.cobertura == "total":
        state.gates.append(f"gate NOV-W3: documento anterior com cobertura total ({result.closest_doc.url})")
        state.state = vocabulary.negativo
    for rule_id in CONFIG_GATES.get(state.criterion, ()):
        if _net_negative(result, rule_id):
            state.gates.append(f"gate {rule_id}: evidência negativa predominante (referência/configuração já fornecia a função)")
            state.state = vocabulary.negativo
    if column_of(state.criterion, state.state, catalog) == "pd":
        if state.criterion in NUMERIC_IN_CRITERION:
            has_numeric = any(
                e.polarity == "positiva" and e.nature in NUMERIC_NATURES for r in result.rules for e in r.evidences
            )
        else:
            has_numeric = numeric_in_analysis
        if not has_numeric:
            state.gates.append("gate: estado positivo exige registro numérico por versão (medicoes/resultados)")
            state.state = vocabulary.indeterminado
    state.column = column_of(state.criterion, state.state, catalog)
    return state


async def judge_state(llm: LLM, catalog: Catalog, result: CriterionResult, numeric_record_in_analysis: bool,
                      analyst_argument: str | None = None) -> CriterionState:
    info = catalog.criteria[result.criterion]
    vocabulary = info.estados.all_states()
    user = (
        f"Critério: {info.nome} — {info.pergunta}\nVocabulário de estados: {' | '.join(vocabulary)}\n"
        f"(P&D: {', '.join(info.estados.positivo)}; rotina: {info.estados.negativo}; insuficiente: {info.estados.indeterminado})\n\n"
        f"<fragmentos>\n{_describe(result)}\n</fragmentos>"
    ) + argument_block(analyst_argument)
    try:
        out = await llm.structured(
            [{"role": "system", "content": STATE_SYSTEM}, {"role": "user", "content": user}], StateJudgeOut, role="judge"
        )
    except Exception as error:
        return CriterionState(criterion=result.criterion, state=None, error=f"juiz de estado falhou: {safe_error_message(error)}")
    chosen = out.estado.strip()
    if chosen not in vocabulary:
        return CriterionState(criterion=result.criterion, state=None, llm_state=chosen,
                              error=f"estado fora do vocabulário do gabarito: {chosen!r}")
    known = {e.id for r in result.rules for e in r.evidences}
    state = CriterionState(
        criterion=result.criterion,
        state=chosen,
        llm_state=chosen,
        justification=out.justificativa,
        decisive_evidence_ids=[i for i in out.evidencias_decisivas if i in known],
        caveat=Caveat(recorte_sustentado=out.recorte_sustentado, limitacao=out.limitacao,
                      evidencia_necessaria=out.evidencia_necessaria)
        if (out.recorte_sustentado or out.limitacao or out.evidencia_necessaria) else None,
        missing_link=MissingLinkInfo(elo_ausente=out.elo_ausente, evidencias_a_solicitar=out.evidencias_a_solicitar)
        if (out.elo_ausente or out.evidencias_a_solicitar) else None,
    )
    return apply_gates(state, result, catalog, numeric_record_in_analysis)


def numeric_record_in(results: dict[str, CriterionResult]) -> bool:
    return any(
        e.polarity == "positiva" and e.nature in NUMERIC_NATURES
        for result in results.values()
        for r in result.rules
        for e in r.evidences
    )
