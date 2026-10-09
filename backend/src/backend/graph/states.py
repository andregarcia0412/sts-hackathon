"""Criterion state: suggested by an LLM judge over the evidence nodes, then forced by gates in code."""

from collections.abc import Awaitable, Callable
from typing import Literal

from pydantic import BaseModel, Field

from backend.catalog.loader import get_catalog
from backend.catalog.models import Catalog
from backend.criteria.common import DATA_NOT_INSTRUCTIONS, argument_block
from backend.criteria.schemas import CriterionResult
from backend.errors import safe_error_message
from backend.graph.answer import Answer
from backend.graph.coherence import (
    CONFLICT_NOTE,
    CORE,
    Coherence,
    Contradiction,
    check_coherence,
    contradiction_block,
    forced_state,
    strength_of,
)
from backend.graph.options import JudgeOptions
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
    gate_conflicts: list[str] = Field(default_factory=list)  # configuration gates not applied: strong positive score
    coherence: Coherence | None = None
    answers: list[Answer] = Field(default_factory=list)  # questionnaire mode: the judge's answers
    decision_rule: str | None = None  # questionnaire mode: the line of the decision table that matched

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
Um bloco <contradicao>, quando houver, é montado pelo sistema a partir do score das evidências (não é texto do
projeto): reavalie o estado escolhendo entre as opções que ele indica.
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


def apply_gates(state: CriterionState, result: CriterionResult, catalog: Catalog, numeric_in_analysis: bool,
                exempt_score: int | None = None) -> CriterionState:
    """Forces the state in code. `exempt_score` (coherence gate): a strong positive score keeps the configuration
    gates from forcing the negative column; the conflict is recorded and the criterion is judged again."""
    vocabulary = catalog.criteria[state.criterion].estados
    if state.criterion == "NOV" and result.closest_doc and result.closest_doc.cobertura == "total":
        state.gates.append(f"gate NOV-W3: documento anterior com cobertura total ({result.closest_doc.url})")
        state.state = vocabulary.negativo
    for rule_id in CONFIG_GATES.get(state.criterion, ()):
        if not _net_negative(result, rule_id):
            continue
        if exempt_score is not None:
            if rule_id not in state.gate_conflicts:
                state.gate_conflicts.append(rule_id)
                state.gates.append(f"gate {rule_id} em conflito com score {exempt_score}: não aplicado, critério "
                                   "julgado de novo com a regra destacada")
            continue
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


async def _judge_once(llm: LLM, catalog: Catalog, result: CriterionResult, numeric_record_in_analysis: bool,
                      analyst_argument: str | None, contradiction: Contradiction | None,
                      exempt_score: int | None) -> CriterionState:
    info = catalog.criteria[result.criterion]
    vocabulary = info.estados.all_states()
    user = (
        f"Critério: {info.nome} — {info.pergunta}\nVocabulário de estados: {' | '.join(vocabulary)}\n"
        f"(P&D: {', '.join(info.estados.positivo)}; rotina: {info.estados.negativo}; insuficiente: {info.estados.indeterminado})\n\n"
        f"<fragmentos>\n{_describe(result)}\n</fragmentos>"
    ) + argument_block(analyst_argument)
    if contradiction is not None:
        user += "\n\n" + contradiction_block(contradiction, result)
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
    return apply_gates(state, result, catalog, numeric_record_in_analysis, exempt_score)


def _contradiction(state: CriterionState, score: int | None, n_rules: int, catalog: Catalog, options: JudgeOptions,
                   include_gate_conflicts: bool = True) -> Contradiction | None:
    llm_column = column_of(state.criterion, state.llm_state, catalog) if state.llm_state else None
    return check_coherence(state.criterion, state.state, state.column, llm_column, state.gate_conflicts, score,
                           n_rules, catalog, options, include_gate_conflicts)


JudgeOnce = Callable[[Contradiction | None, CriterionState | None], Awaitable[CriterionState]]


def coherence_exempt(criterion: str, score: int | None, n_rules: int, options: JudgeOptions) -> int | None:
    """The score that keeps the configuration gates from forcing (coherence gate active, strong positive score)."""
    if options.coherence_mode == "off" or criterion not in CORE:
        return None
    return score if strength_of(score, n_rules, options) == "forte_positivo" else None


async def with_coherence(judge_once: JudgeOnce, catalog: Catalog, score: int | None, n_rules: int,
                         options: JudgeOptions) -> CriterionState:
    """Coherence gate around one judgement (state judge or questionnaire): at most one new judgement per criterion,
    and the code never picks the state from the score (except `force`, a re-judge-only diagnostic ceiling)."""
    first = await judge_once(None, None)
    if options.coherence_mode == "off" or first.state is None:
        return first
    contradiction = _contradiction(first, score, n_rules, catalog, options)
    if contradiction is None:
        return first
    record = Coherence(score=contradiction.score, rules_with_evidence=contradiction.rules_with_evidence,
                       strength=contradiction.strength, original_state=first.state,
                       original_source=contradiction.source, choices=contradiction.choices, status="incoerente")
    if options.coherence_mode == "force" and (forced := forced_state(contradiction, catalog)):
        first.gates.append(f"coerência (diagnóstico force): estado ajustado de {first.state} para {forced}")
        first.state, first.column = forced, column_of(first.criterion, forced, catalog)
        record.status = "resolvida"
    elif options.coherence_mode == "reask":
        second = await judge_once(contradiction, first)
        record.rejudged = True
        if second.state is not None:
            if _contradiction(second, score, n_rules, catalog, options, include_gate_conflicts=False) is None:
                record.status = "resolvida"
            first = second
    if record.status == "incoerente":
        first.gates.append(CONFLICT_NOTE)
    first.coherence = record
    return first


async def judge_state(llm: LLM, catalog: Catalog, result: CriterionResult, numeric_record_in_analysis: bool,
                      analyst_argument: str | None = None, *, score: int | None = None, n_rules: int = 0,
                      options: JudgeOptions | None = None) -> CriterionState:
    """The LLM suggests the state, gates force it in code, and the coherence gate checks it against the score."""
    options = options or JudgeOptions()
    exempt = coherence_exempt(result.criterion, score, n_rules, options)

    async def once(contradiction: Contradiction | None, _previous: CriterionState | None) -> CriterionState:
        return await _judge_once(llm, catalog, result, numeric_record_in_analysis, analyst_argument, contradiction,
                                 exempt)

    return await with_coherence(once, catalog, score, n_rules, options)


def numeric_record_in(results: dict[str, CriterionResult]) -> bool:
    return any(
        e.polarity == "positiva" and e.nature in NUMERIC_NATURES
        for result in results.values()
        for r in result.rules
        for e in r.evidences
    )
