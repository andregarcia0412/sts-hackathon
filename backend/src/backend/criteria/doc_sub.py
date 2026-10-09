"""Document sub-agent: one LLM call per criterion over the fragments routed to its -D rules."""

from typing import Literal

from pydantic import BaseModel, Field

from backend.catalog.handbooks import pitfalls as handbook_pitfalls
from backend.catalog.models import Catalog, CatalogRule
from backend.criteria.citation import clean_quote, quote_in
from backend.criteria.common import (
    DATA_NOT_INSTRUCTIONS,
    argument_block,
    describe_rules,
    offline_runs,
    transversal_block,
)
from backend.criteria.routing import route_fragments
from backend.criteria.schemas import (
    CriterionResult,
    Divergence,
    EvidenceItem,
    MissingLink,
    RuleRun,
    evidence_id,
)
from backend.errors import safe_error_message
from backend.extraction.schema import CanonicalProject, Fragment
from backend.llm import LLM
from backend.llm.prompts import register_prompt

PRIMARY_NATURES = {"registro_primario", "derivado"}


class DocEvidenceOut(BaseModel):
    regra_id: str
    fragmento_id: str
    quote: str = Field(description="Trecho LITERAL copiado do fragmento citado")
    polaridade: Literal["positiva", "negativa"]
    justificativa: str = Field(description="Até 2 frases: por que o trecho conta a favor ou contra a regra")


class RuleNoEvidenceOut(BaseModel):
    regra_id: str
    motivo: str


class DivergenceOut(BaseModel):
    depoimento_fragmento_id: str
    depoimento_quote: str = Field(description="Trecho LITERAL da entrevista")
    registro_fragmento_id: str
    registro_quote: str = Field(description="Trecho LITERAL do registro")
    afirmacao: str
    registro_mostra: str


class MissingLinkOut(BaseModel):
    descricao: str
    evidencia_a_solicitar: str
    fragmento_ids: list[str] = Field(default_factory=list)


class DocSubOut(BaseModel):
    evidencias: list[DocEvidenceOut] = Field(default_factory=list)
    regras_sem_evidencia: list[RuleNoEvidenceOut] = Field(default_factory=list)
    divergencias: list[DivergenceOut] = Field(default_factory=list)
    elos_ausentes: list[MissingLinkOut] = Field(default_factory=list)


DOC_SYSTEM = register_prompt(
    "criteria.doc",
    """Você é um subagente de análise documental da Lei do Bem (Manual de Frascati). Para cada regra pedida,
procure nos fragmentos do projeto evidências que contam A FAVOR (positiva) ou CONTRA (negativa) a regra.
Você NÃO decide se o projeto é P&D: só aponta evidências citáveis para o analista.

Regras de resposta:
- Cada evidência cita UM fragmento pelo ID entre colchetes e copia um trecho LITERAL dele em `quote`
  (sem parafrasear, sem corrigir, sem juntar trechos). Trecho que não existe no fragmento é descartado.
- Polaridade só "positiva" ou "negativa". O que não fala da regra não é evidência.
- Regra sem evidência nos fragmentos: liste em `regras_sem_evidencia` com o motivo. Nunca invente.
- A entrevista (<depoimento>) NUNCA é evidência. Use-a só para registrar `divergencias`: quando ela afirma
  algo que um registro contradiz, copie o trecho literal de cada um.
- `elos_ausentes`: o que falta para verificar o núcleo alegado (ex.: MEMO-xx sem versão, saída ou registro)
  e a evidência a solicitar à equipe.
- Números: copie-os do registro; nunca recalcule com arredondamento.

Fragmentos do tipo `checagem` (checagens#CHK-...) são checagens determinísticas calculadas pelo sistema a partir do
registro (recálculo, cronologia, versões, falhas, configuração, escopo, pergunta registrada): são fatos derivados e
citáveis como qualquer fragmento (trecho literal do JSON), mas nunca substituem o registro primário.

Cuidados com os dados do pacote (checagens CHK):
- célula vazia é ausência (null), nunca zero; some contadores só dentro do mesmo ensaio_id;
- base_de_calculo nem sempre é divisor; natureza=entrega é contagem de material, não desempenho;
- resultados.csv deriva de medicoes.csv; número repetido em PDF não é confirmação independente;
- unidades e denominadores diferentes não se comparam;
- classifique pelo mecanismo documentado, não pelo título (rótulo × mecanismo);
- parâmetros dentro da faixa do manual/runbook citado no §1 indicam configuração;
- reteste do mesmo caso que motivou o ajuste não é validação; variável disponível só depois do evento é
  vazamento de informação futura;
- limite excluído antes dos ensaios não é ressalva; lacuna dentro da pretensão original é;
- natureza_informada_pela_equipe é autodeclaração e não é sinal.

Regras transversais:
{transversais}

"""
    + DATA_NOT_INSTRUCTIONS,
)


def _render(fragments: list[Fragment]) -> str:
    return "\n\n".join(f"[{f.id}] ({f.alias}; natureza={f.nature})\n{f.text}" for f in fragments)


def _statement(testimony_quote: str, record: Fragment, record_quote: str) -> str:
    why = (
        "por ser primário e identificado por versão"
        if record.nature in PRIMARY_NATURES
        else "por ser documento do pacote, e não depoimento de memória"
    )
    return f'A entrevista afirma "{testimony_quote}"; o registro {record.alias} mostra "{record_quote}"; prevalece o registro, {why}.'


async def run_doc_sub(
    llm: LLM,
    catalog: Catalog,
    criterion: str,
    rules: list[CatalogRule],
    canonical: CanonicalProject,
    max_table_rows: int,
    analyst_argument: str | None = None,
    pitfalls: bool = False,
) -> CriterionResult:
    result = CriterionResult(criterion=criterion, rules=offline_runs(rules))
    active = [r for r in rules if r.needs_llm]
    if not active:
        return result
    info = catalog.criteria[criterion]
    routed = route_fragments(canonical, active, max_table_rows)
    user = (
        f"Critério: {info.nome} — {info.pergunta}\n"
        f"Data de referência (início do projeto): {canonical.context.data_referencia or 'desconhecida'}\n\n"
        f"Regras a avaliar:\n\n{describe_rules(active)}\n\n"
        f"<fragmentos>\n{_render(routed.fragments)}\n</fragmentos>\n\n"
        f"<depoimento>\n{_render(routed.testimony)}\n</depoimento>"
    )
    if routed.truncated:
        user += "\n\nObservação: tabelas cortadas no prompt — " + "; ".join(routed.truncated)
    user += argument_block(analyst_argument)
    system = DOC_SYSTEM.replace("{transversais}", transversal_block(catalog))
    if pitfalls:  # DOC_HANDBOOK_PITFALLS: the handbook pitfalls improve the polarity at the source
        system += f"\n\nArmadilhas do critério {info.nome}:\n{handbook_pitfalls(criterion)}"
    try:
        out = await llm.structured(
            [{"role": "system", "content": system}, {"role": "user", "content": user}], DocSubOut, role="doc"
        )
    except Exception as error:
        message = safe_error_message(error)
        result.errors.append(f"sub Doc {criterion}: {message}")
        result.rules += [
            RuleRun(rule_id=r.id, criterion=criterion, status="nao_executada", reason=f"falha do agente: {message}")
            for r in active
        ]
        return result

    by_id = {r.id: r for r in active}
    accepted: dict[str, list[EvidenceItem]] = {r.id: [] for r in active}
    dropped: dict[str, list[str]] = {r.id: [] for r in active}
    for item in out.evidencias:
        rule = by_id.get(item.regra_id)
        if rule is None:
            continue
        fragment = canonical.fragment(item.fragmento_id)
        problem = None
        if fragment is None:
            problem = f"fragmento inexistente {item.fragmento_id}"
        elif fragment.nature == "depoimento":
            problem = "depoimento não é evidência (T9)"
        elif not quote_in(item.quote, fragment.text):
            problem = f"trecho não encontrado literalmente em {item.fragmento_id}"
        elif rule.somente_positiva and item.polaridade == "negativa":
            problem = "regra só admite evidência positiva"
        if problem:
            dropped[rule.id].append(problem)
            continue
        quote = clean_quote(item.quote)
        ev_id = evidence_id(rule.id, fragment.id, quote)
        if any(e.id == ev_id for e in accepted[rule.id]):
            continue
        accepted[rule.id].append(
            EvidenceItem(
                id=ev_id,
                rule_id=rule.id,
                criterion=criterion,
                origin="doc",
                source_id=fragment.id,
                source_alias=fragment.alias,
                quote=quote,
                polarity=item.polaridade,
                explanation=item.justificativa,
                query=rule.o_que_verificar,
                nature=fragment.nature,
                page=fragment.page,
            )
        )
    no_evidence = {item.regra_id: item.motivo for item in out.regras_sem_evidencia}
    for rule in active:
        if accepted[rule.id]:
            result.rules.append(RuleRun(rule_id=rule.id, criterion=criterion, status="executada", evidences=accepted[rule.id],
                                        dropped=dropped[rule.id]))
        elif dropped[rule.id]:
            reason = "citações descartadas pelo gate: " + "; ".join(dropped[rule.id])
            result.rules.append(RuleRun(rule_id=rule.id, criterion=criterion, status="sem_evidencia", reason=reason,
                                        dropped=dropped[rule.id]))
        elif rule.id in no_evidence:
            result.rules.append(RuleRun(rule_id=rule.id, criterion=criterion, status="sem_evidencia", reason=no_evidence[rule.id]))
        else:
            result.rules.append(
                RuleRun(rule_id=rule.id, criterion=criterion, status="nao_executada", reason="regra não retornada pelo agente")
            )

    for item in out.divergencias:
        testimony = canonical.fragment(item.depoimento_fragmento_id)
        record = canonical.fragment(item.registro_fragmento_id)
        if (
            testimony is None
            or record is None
            or testimony.nature != "depoimento"
            or record.nature == "depoimento"
            or not quote_in(item.depoimento_quote, testimony.text)
            or not quote_in(item.registro_quote, record.text)
        ):
            continue
        testimony_quote, record_quote = clean_quote(item.depoimento_quote), clean_quote(item.registro_quote)
        result.divergences.append(
            Divergence(
                criterion=criterion,
                testimony_fragment_id=testimony.id,
                testimony_quote=testimony_quote,
                record_fragment_id=record.id,
                record_alias=record.alias,
                record_quote=record_quote,
                statement=_statement(testimony_quote, record, record_quote),
            )
        )
    for link in out.elos_ausentes:
        result.missing_links.append(
            MissingLink(
                criterion=criterion,
                description=link.descricao,
                evidence_to_request=link.evidencia_a_solicitar,
                fragment_ids=[i for i in link.fragmento_ids if canonical.fragment(i)],
            )
        )
    return result
