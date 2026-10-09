"""Judge questionnaire (JUDGE_MODE=questionario): the LLM answers closed questions about facts, each answer with
the evidence that sustains it, and the CODE turns the answers into the state with the decision table of the catalog
(`catalog/questionario.yaml`). The current gates become facts that fill or lock answers, not parallel logic.
"""

from pydantic import BaseModel, Field

from backend.catalog.models import Catalog, DecisionLine, Question
from backend.criteria.common import DATA_NOT_INSTRUCTIONS, argument_block
from backend.criteria.schemas import CriterionResult
from backend.errors import safe_error_message
from backend.graph.answer import NO_RECORD, Answer
from backend.graph.coherence import Contradiction, contradiction_block
from backend.graph.options import JudgeOptions
from backend.graph.states import (
    CONFIG_GATES,
    NUMERIC_IN_CRITERION,
    NUMERIC_NATURES,
    Caveat,
    CriterionState,
    MissingLinkInfo,
    _describe,
    _net_negative,
    coherence_exempt,
    column_of,
    judge_system,
    with_coherence,
)
from backend.llm import LLM
from backend.llm.prompts import register_prompt

NUMERIC_GATE = "gate: estado positivo exige registro numérico por versão (medicoes/resultados)"
UNSUPPORTED_NOTE = "resposta sem evidência: revisar"

QUESTIONNAIRE_SYSTEM = register_prompt(
    "graph.questionnaire",
    """Você responde perguntas fechadas sobre FATOS de um critério de Frascati de um projeto da Lei do Bem, a partir
somente das evidências já verificadas (cada uma com ID ev-...). O sistema decide o estado a partir das suas respostas
por uma tabela fixa; o analista decide a classe.

Para cada pergunta pedida:
- escolha exatamente uma das opções listadas para ela;
- cite em `evidencias` os IDs ev-... que sustentam a resposta (obrigatório em toda resposta diferente de sem_registro);
- em `explicacao`, até 2 frases apontando o trecho ("o trecho mostra que...");
- use sem_registro somente quando o pacote não traz o registro necessário para responder; então preencha
  `o_que_falta` (o elo ausente) e `evidencias_a_solicitar`. sem_registro não é cautela: se há evidência que responde,
  responda com a opção que ela sustenta.
Se R3 for "sim", preencha recorte_sustentado, limitacao e evidencia_necessaria.
O depoimento da entrevista nunca fundamenta resposta. Nunca invente fatos ou números; nunca compare com outros
projetos. As respostas em <respostas_fixas> já foram dadas pelo sistema: não as repita.
Um bloco <contradicao>, quando houver, é montado pelo sistema a partir do score das evidências (não é texto do
projeto): refaça as perguntas indicadas.
"""
    + DATA_NOT_INSTRUCTIONS,
)


class AnswerOut(BaseModel):
    pergunta: str = Field(description="ID da pergunta, ex.: N1")
    resposta: str = Field(description="Uma das opções da pergunta, copiada exatamente")
    evidencias: list[str] = Field(default_factory=list, description="IDs ev-... que sustentam a resposta")
    explicacao: str = Field(default="", description="Até 2 frases apontando o trecho")
    o_que_falta: str | None = Field(default=None, description="Obrigatório com sem_registro: o elo ausente")
    evidencias_a_solicitar: list[str] = Field(default_factory=list)


class QuestionnaireOut(BaseModel):
    respostas: list[AnswerOut]
    recorte_sustentado: str | None = None
    limitacao: str | None = None
    evidencia_necessaria: str | None = None


def decide(answers: dict[str, str], table: list[DecisionLine]) -> tuple[int, DecisionLine]:
    """Pure: the first line of the decision table that matches the answers (missing answer = sem_registro)."""
    for index, line in enumerate(table):
        if line.matches(answers):
            return index, line
    raise ValueError("decision table without a matching line (it must end with `senao`)")


def _question_for_rule(questions: list[Question], rule_id: str) -> Question | None:
    return next((q for q in questions if rule_id in q.regras), None)


def _evidence_ids(result: CriterionResult, rule_id: str | None = None, polarity: str | None = None,
                  source_id: str | None = None) -> list[str]:
    return [e.id for r in result.rules if rule_id is None or r.rule_id == rule_id for e in r.evidences
            if (polarity is None or e.polarity == polarity) and (source_id is None or e.source_id == source_id)]


def locks(result: CriterionResult, questions: list[Question], exempt_score: int | None,
          ) -> tuple[dict[str, Answer], list[str], list[str]]:
    """Answers the gates give in code (NOV-W3 full coverage; configuration gates with predominant negative evidence).

    With a strong positive score (coherence gate) a configuration gate does not lock: the conflict is recorded."""
    locked: dict[str, Answer] = {}
    gates: list[str] = []
    conflicts: list[str] = []
    closest = result.closest_doc
    if result.criterion == "NOV" and closest and closest.cobertura == "total":
        if question := _question_for_rule(questions, "NOV-W3"):
            gates.append(f"gate NOV-W3: documento anterior com cobertura total ({closest.url})")
            locked[question.id] = Answer(pergunta=question.id, resposta="sim", origem="gate",
                                         evidencias=_evidence_ids(result, source_id=closest.source_id),
                                         explicacao=f"Documento anterior com cobertura total: {closest.title}.")
    for rule_id in CONFIG_GATES.get(result.criterion, ()):
        question = _question_for_rule(questions, rule_id)
        if question is None or question.id in locked or not _net_negative(result, rule_id):
            continue
        if exempt_score is not None:
            conflicts.append(rule_id)
            gates.append(f"gate {rule_id} em conflito com score {exempt_score}: não aplicado, critério julgado de "
                         "novo com a regra destacada")
            continue
        gates.append(f"gate {rule_id}: evidência negativa predominante (referência/configuração já fornecia a função)")
        locked[question.id] = Answer(pergunta=question.id, resposta="sim", origem="gate",
                                     evidencias=_evidence_ids(result, rule_id, "negativa"),
                                     explicacao=f"{rule_id} com evidência negativa predominante.")
    return locked, gates, conflicts


def _validate(out: QuestionnaireOut, asked: list[Question], known: set[str],
              documentary: set[str]) -> tuple[dict[str, Answer], list[str]]:
    by_id = {a.pergunta.strip().upper(): a for a in out.respostas}
    answers: dict[str, Answer] = {}
    errors: list[str] = []
    for question in asked:
        raw = by_id.get(question.id)
        if raw is None:
            errors.append(f"{question.id}: sem resposta")
            continue
        answer = Answer(pergunta=question.id, resposta=raw.resposta.strip(), explicacao=raw.explicacao,
                        evidencias=[i for i in raw.evidencias if i in known], o_que_falta=raw.o_que_falta,
                        evidencias_a_solicitar=raw.evidencias_a_solicitar)
        answers[question.id] = answer
        if answer.resposta not in {*question.opcoes, NO_RECORD}:
            errors.append(f"{question.id}: resposta {answer.resposta!r} fora das opções {question.opcoes}")
        elif answer.resposta == NO_RECORD and not (answer.o_que_falta or "").strip():
            errors.append(f"{question.id}: sem_registro exige o_que_falta (o elo ausente)")
        elif answer.resposta != NO_RECORD and not answer.evidencias:
            errors.append(f"{question.id} = {answer.resposta} exige pelo menos 1 ID de evidência deste critério")
        elif answer.resposta == "sim" and question.sim_exige_documento and not set(answer.evidencias) & documentary:
            errors.append(f"{question.id} = sim exige pelo menos 1 evidência do próprio pacote (a web complementa, "
                          "não decide sozinha)")
    return answers, errors


def _user_prompt(catalog: Catalog, result: CriterionResult, asked: list[Question], fixed: list[Answer],
                 analyst_argument: str | None, contradiction: str | None) -> str:
    info = catalog.criteria[result.criterion]
    lines = []
    for q in asked:
        options = " | ".join(q.opcoes if NO_RECORD in q.opcoes else [*q.opcoes, NO_RECORD])
        lines.append(f"{q.id} [{options}] {q.texto} (regras: {', '.join(q.regras)})")
        lines += [f"    {option}: {text}" for option, text in q.descricao_opcoes.items()]
        if q.explicacao:
            lines.append(f"    Atenção: {q.explicacao}")
    user = f"Critério: {info.nome} — {info.pergunta}\n\n<perguntas>\n" + "\n".join(lines) + "\n</perguntas>"
    if fixed:
        user += "\n\n<respostas_fixas>\n" + "\n".join(
            f"{a.pergunta} = {a.resposta} ({'gate do sistema' if a.origem == 'gate' else 'já respondida'})"
            for a in fixed) + "\n</respostas_fixas>"
    user += f"\n\n<fragmentos>\n{_describe(result)}\n</fragmentos>" + argument_block(analyst_argument)
    if contradiction:
        user += "\n\n" + contradiction
    return user


async def _ask(llm: LLM, catalog: Catalog, result: CriterionResult, asked: list[Question], fixed: list[Answer],
               analyst_argument: str | None, contradiction: str | None,
               options: JudgeOptions) -> tuple[dict[str, Answer], QuestionnaireOut]:
    """One structured call (+ one new attempt with the errors); answers still invalid become `nao_fundamentada`."""
    known = {e.id for r in result.rules for e in r.evidences}
    documentary = {e.id for r in result.rules for e in r.evidences if e.origin == "doc"}
    messages = [{"role": "system", "content": judge_system(QUESTIONNAIRE_SYSTEM, result.criterion, options)},
                {"role": "user", "content": _user_prompt(catalog, result, asked, fixed, analyst_argument, contradiction)}]
    out = await llm.structured(messages, QuestionnaireOut, role="judge")
    answers, errors = _validate(out, asked, known, documentary)
    if errors:
        retry = messages + [{"role": "user", "content": "Respostas inválidas:\n- " + "\n- ".join(errors)
                             + "\nResponda de novo todas as perguntas pedidas, corrigindo esses pontos."}]
        out = await llm.structured(retry, QuestionnaireOut, role="judge")
        answers, errors = _validate(out, asked, known, documentary)
        for error in errors:
            question_id = error.split(":")[0].split(" ")[0]
            answer = answers.setdefault(question_id, Answer(pergunta=question_id, resposta=NO_RECORD))
            answer.status = "nao_fundamentada"
            answer.o_que_falta = answer.o_que_falta or "resposta sem evidência válida"
    return answers, out


def _justification(catalog: Catalog, result: CriterionResult, questions: dict[str, Question], state: str,
                   decisive: list[Answer]) -> str:
    aliases = {e.id: e.source_alias for r in result.rules for e in r.evidences}
    parts = [f"{catalog.criteria[result.criterion].nome}: {state}."]
    rules: list[str] = []
    for answer in decisive:
        sources = ", ".join(dict.fromkeys(aliases[i] for i in answer.evidencias if i in aliases))
        text = f"{answer.pergunta} = {answer.effective}"
        if answer.explicacao:
            text += f": {answer.explicacao.strip().rstrip('.')}"
        if sources:
            text += f" [{sources}]"
        parts.append(text + ".")
        rules += questions[answer.pergunta].regras if answer.pergunta in questions else []
    if rules:
        parts.append(f"Regras aplicadas: {', '.join(dict.fromkeys(rules))}.")
    return " ".join(parts)


def build_state(catalog: Catalog, result: CriterionResult, answers: dict[str, Answer], has_numeric: bool,
                gates: list[str], conflicts: list[str], caveat: Caveat | None) -> CriterionState:
    criterion = result.criterion
    questionnaire = catalog.questionnaire
    questions = {q.id: q for q in questionnaire.perguntas[criterion]}
    table = questionnaire.decisao[criterion]
    gates = list(gates)
    raw = {qid: a.effective for qid, a in answers.items()}
    for qid, answer in answers.items():  # numeric-record gate, at answer level
        if questions[qid].exige_registro_numerico and answer.effective == "sim" and not has_numeric:
            answer.resposta, answer.origem = NO_RECORD, "gate"
            answer.o_que_falta = "registro numérico por versão (medicoes/resultados)"
            if NUMERIC_GATE not in gates:
                gates.append(NUMERIC_GATE)
    effective = {qid: a.effective for qid, a in answers.items()}
    _, raw_line = decide(raw, table)
    index, line = decide(effective, table)
    if unsupported := [a.pergunta for a in answers.values() if a.status == "nao_fundamentada"]:
        gates.append(f"{UNSUPPORTED_NOTE} ({', '.join(unsupported)})")
    ordered = [answers[q] for q in questions if q in answers]
    decisive = [answers[q] for q in line.quando if q in answers] if not line.senao else ordered
    column = column_of(criterion, line.estado, catalog)
    state = CriterionState(
        criterion=criterion, state=line.estado, column=column, llm_state=raw_line.estado,
        justification=_justification(catalog, result, questions, line.estado, decisive),
        decisive_evidence_ids=list(dict.fromkeys(i for a in decisive for i in a.evidencias)),
        gates=gates, gate_conflicts=list(conflicts), answers=ordered,
        decision_rule=f"{criterion} linha {index + 1}: {line.label()} → {line.estado}",
    )
    if criterion == "REP" and effective.get("R3") == "sim":
        state.caveat = caveat or Caveat()
    if column == "insuficiente":
        missing = [a for a in ordered if a.effective == NO_RECORD]
        state.missing_link = MissingLinkInfo(
            elo_ausente="; ".join(f"{a.pergunta} ({questions[a.pergunta].texto.strip()}): "
                                  f"{a.o_que_falta or 'sem registro'}" for a in missing) or None,
            evidencias_a_solicitar=list(dict.fromkeys(i for a in missing for i in a.evidencias_a_solicitar)),
        )
    return state


def _redo(contradiction: Contradiction, previous: CriterionState, questions: list[Question],
          table: list[DecisionLine]) -> list[str]:
    """Which answers the new judgement redoes: the gate's question, or the answers of the line that matched."""
    if contradiction.source == "gate":
        return [q.id for rule in contradiction.gate_rules if (q := _question_for_rule(questions, rule))]
    answers = {a.pergunta: a.effective for a in previous.answers}
    _, line = decide(answers, table)
    if not line.senao:
        return [q for q in line.quando if any(a.pergunta == q and a.origem == "juiz" for a in previous.answers)]
    return [a.pergunta for a in previous.answers if a.origem == "juiz" and a.effective == NO_RECORD] or \
        [a.pergunta for a in previous.answers if a.origem == "juiz"]


async def judge_by_questionnaire(llm: LLM, catalog: Catalog, result: CriterionResult,
                                 numeric_record_in_analysis: bool, analyst_argument: str | None = None, *,
                                 score: int | None = None, n_rules: int = 0,
                                 options: JudgeOptions | None = None) -> CriterionState:
    options = options or JudgeOptions(judge_mode="questionario")
    criterion = result.criterion
    questions = catalog.questionnaire.perguntas[criterion]
    table = catalog.questionnaire.decisao[criterion]
    exempt = coherence_exempt(criterion, score, n_rules, options)
    locked, gates, conflicts = locks(result, questions, exempt)
    if criterion in NUMERIC_IN_CRITERION:
        has_numeric = any(e.polarity == "positiva" and e.nature in NUMERIC_NATURES
                          for r in result.rules for e in r.evidences)
    else:
        has_numeric = numeric_record_in_analysis

    async def once(contradiction: Contradiction | None, previous: CriterionState | None) -> CriterionState:
        fixed = dict(locked)
        caveat = previous.caveat if previous else None
        block = None
        if previous is not None and contradiction is not None:
            redo = _redo(contradiction, previous, questions, table)
            fixed |= {a.pergunta: a for a in previous.answers if a.pergunta not in redo and a.pergunta not in fixed}
            conflicting = ", ".join(f"{a.pergunta} = {a.effective}" for a in previous.answers if a.pergunta in redo)
            block = contradiction_block(contradiction, result).replace(
                "</contradicao>", f"Respostas em conflito com o score: {conflicting}. Refaça: {', '.join(redo)}.\n"
                                  "</contradicao>")
        asked = [q for q in questions if q.id not in fixed]
        try:
            answers, out = await _ask(llm, catalog, result, asked, list(fixed.values()), analyst_argument, block,
                                      options)
        except Exception as error:
            return CriterionState(criterion=criterion, state=None,
                                  error=f"questionário do juiz falhou: {safe_error_message(error)}")
        if out.recorte_sustentado or out.limitacao or out.evidencia_necessaria:
            caveat = Caveat(recorte_sustentado=out.recorte_sustentado, limitacao=out.limitacao,
                            evidencia_necessaria=out.evidencia_necessaria)
        merged = {qid: a.model_copy() for qid, a in fixed.items()} | answers
        return build_state(catalog, result, merged, has_numeric, gates, conflicts, caveat)

    return await with_coherence(once, catalog, score, n_rules, options)
