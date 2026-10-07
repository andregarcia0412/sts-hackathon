import asyncio
from collections.abc import Callable

from ai_microservice.llm import LLMClient
from ai_microservice.modules.novelty.prompts import JUDGE_SYSTEM
from ai_microservice.modules.novelty.schemas import (
    FRONTS,
    FrontResult,
    ProjectProfile,
    RuleJudgement,
    SourceDoc,
)
from ai_microservice.rules import Evidence, Rule, RuleStatus, RuleVerdict

# Regras que também olham fontes publicadas depois da data de referência
RULES_USING_LATER_SOURCES = {"NOV-W6"}


def _verdict(rule: Rule, status: RuleStatus, resumo: str, evidencias: list[Evidence] | None = None) -> RuleVerdict:
    return RuleVerdict(id=rule.id, titulo=rule.titulo, status=status, resumo=resumo, evidencias=evidencias or [])


def _check_reference_date(rule: Rule, profile: ProjectProfile, fronts: list[FrontResult]) -> RuleVerdict:
    docs = [doc for front in fronts for doc in front.fontes]
    later = sum(doc.anterior_a_referencia is False for doc in docs)
    undated = sum(doc.anterior_a_referencia is None for doc in docs)
    origem = "informada pelo analista" if profile.data_inicio_origem == "informada" else f'calculada de "{profile.trecho_data}"'
    return _verdict(
        rule,
        RuleStatus.ENQUADRA,
        f"Data de referência {profile.data_referencia.isoformat()} ({origem}). "
        f"{later} fonte(s) posterior(es) excluída(s) do estado da arte; {undated} sem data verificável.",
    )


def _check_three_fronts(rule: Rule, profile: ProjectProfile, fronts: list[FrontResult]) -> RuleVerdict:
    parts, missing = [], []
    for name in FRONTS:
        front = next((f for f in fronts if f.frente == name), None)
        ok_searches = [entry for entry in front.log if entry.erro is None] if front else []
        if not ok_searches:
            missing.append(name)
            continue
        bases = sorted({entry.base for entry in ok_searches})
        parts.append(f"{name} ({', '.join(bases)}: {len(ok_searches)} buscas, {len(front.fontes)} fontes)")
    if missing:
        return _verdict(rule, RuleStatus.NAO_ENQUADRA, f"Frente(s) sem busca concluída: {', '.join(missing)}.")
    return _verdict(rule, RuleStatus.ENQUADRA, "Busca feita nas três frentes: " + "; ".join(parts) + ".")


def _check_search_log(rule: Rule, profile: ProjectProfile, fronts: list[FrontResult]) -> RuleVerdict:
    log = [entry for front in fronts for entry in front.log]
    if not log:
        return _verdict(rule, RuleStatus.NAO_ENQUADRA, "Nenhuma busca registrada.")
    failed = sum(entry.erro is not None for entry in log)
    return _verdict(
        rule,
        RuleStatus.ENQUADRA,
        f"{len(log)} busca(s) registradas em `log_busca` com base, string exata, filtros, data/hora, "
        f"nº de resultados e fontes selecionadas/descartadas com motivo ({failed} com erro ou descartada).",
    )


PROCEDURAL_CHECKS: dict[str, Callable[[Rule, ProjectProfile, list[FrontResult]], RuleVerdict]] = {
    "NOV-W1": _check_reference_date,
    "NOV-W2": _check_three_fronts,
    "NOV-W8": _check_search_log,
}


def _describe(doc: SourceDoc) -> str:
    date = f"{doc.data_publicacao} ({doc.tipo_data or 'publicação'})" if doc.data_verificada else "sem data verificável"
    if doc.anterior_a_referencia is False:
        date += " — POSTERIOR à data de referência"
    lines = [f"[{doc.id}] frente={doc.frente} base={doc.base}", f"título: {doc.titulo}", f"data: {date}", f"url: {doc.url}"]
    if c := doc.comparacao:
        lines.append(
            f"comparação: cobertura={c.cobertura}; em_uso_no_setor={c.em_uso_no_setor}; "
            f"metodo_publico={c.metodo_publico}; o_que_o_projeto_tem_a_mais={c.o_que_o_projeto_tem_a_mais}; resumo={c.resumo}"
        )
    else:
        lines.append(f"trecho: {doc.trecho[:300]}")
    return "\n".join(lines)


async def judge_rule(llm: LLMClient, rule: Rule, profile: ProjectProfile, docs: list[SourceDoc]) -> RuleVerdict:
    candidates = [
        doc for doc in docs if rule.id in RULES_USING_LATER_SOURCES or doc.anterior_a_referencia is not False
    ]
    if not candidates:
        return _verdict(rule, RuleStatus.INCONCLUSIVO, "Nenhuma fonte recuperada para avaliar esta regra.")

    system = JUDGE_SYSTEM.format(
        rule_id=rule.id, titulo=rule.titulo, o_que_verificar=rule.o_que_verificar, como_julgar=rule.como_julgar or "-"
    )
    user = (
        f"Data de referência (início do projeto): {profile.data_referencia.isoformat()}\n"
        f"Elemento novo declarado: {profile.elemento_novo_declarado.texto}\n"
        f"Domínio/setor: {profile.dominio_setor.texto}\n\n"
        "Fontes recuperadas:\n\n" + "\n\n".join(_describe(doc) for doc in candidates)
    )
    try:
        judgement = await llm.structured(
            [{"role": "system", "content": system}, {"role": "user", "content": user}], RuleJudgement, role="judge"
        )
    except Exception as error:
        return _verdict(rule, RuleStatus.INCONCLUSIVO, f"Falha ao avaliar a regra: {type(error).__name__}.")

    # Regra T7: só vale evidência que aponta para uma fonte realmente recuperada.
    by_id = {doc.id: doc for doc in candidates}
    evidences = [
        Evidence(
            fonte_id=citation.fonte_id,
            titulo=by_id[citation.fonte_id].titulo,
            url=by_id[citation.fonte_id].url,
            data_publicacao=str(by_id[citation.fonte_id].data_publicacao or "") or None,
            frente=by_id[citation.fonte_id].frente,
            justificativa=citation.justificativa,
        )
        for citation in judgement.evidencias
        if citation.fonte_id in by_id
    ]
    status, resumo = judgement.status, judgement.resumo
    if not evidences and status != RuleStatus.INCONCLUSIVO:
        status = RuleStatus.INCONCLUSIVO
        resumo += " (Nenhuma fonte recuperada válida foi citada; veredito rebaixado para inconclusivo.)"
    return _verdict(rule, status, resumo, evidences)


async def evaluate_rules(
    llm: LLMClient, rules: list[Rule], profile: ProjectProfile, fronts: list[FrontResult]
) -> list[RuleVerdict]:
    docs = [doc for front in fronts for doc in front.fontes]

    async def evaluate(rule: Rule) -> RuleVerdict:
        if rule.evaluator == "procedural":
            return PROCEDURAL_CHECKS[rule.id](rule, profile, fronts)
        return await judge_rule(llm, rule, profile, docs)

    return list(await asyncio.gather(*(evaluate(rule) for rule in rules)))
