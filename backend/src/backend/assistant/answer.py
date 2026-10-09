"""Module 6: chatbot. Explains the analysis from the graph and the norms; it never decides."""

import re
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from backend.api_schema import CamelModel
from backend.assistant.norms import BM25Index, NormChunk
from backend.catalog.models import Catalog
from backend.criteria.citation import clean_quote, quote_in
from backend.criteria.common import DATA_NOT_INSTRUCTIONS
from backend.frontend_api import schemas as fe
from backend.llm import LLM
from backend.llm.prompts import register_prompt
from backend.report.redact import numbers_gate

RULE_ID_RE = re.compile(r"\b(?:NOV|CRI|INC|SIS|REP)-[WD]\d{1,2}\b|\bT\d{1,2}\b", re.IGNORECASE)
NORM_WORDS_RE = re.compile(
    r"\b(lei|decreto|portaria|frascati|manual|guia|faq|norma|normativ\w*|artigo|art\.|§|mcti|anpei|regulament\w*)",
    re.IGNORECASE,
)
DECISION_RE = re.compile(
    r"\b(mud[ae]r?|alter[ae]r?|aprov[ae]r?|decid[ae]r?|classifiqu?e|marque|reprov[ae]r?)\b.*"
    r"\b(eleg\w*|ressalv\w*|insuficiente|classe|decis\w*|aprovad\w*|reprovad\w*)",
    re.IGNORECASE,
)
GRAPH_ITEMS = 14
MAX_EVIDENCE_ITEMS = 60
NORM_ITEMS = 5
NO_BASIS = "Não encontrei base para responder a essa pergunta nas evidências da análise nem nas normas indexadas."


class TextBlock(CamelModel):
    type: Literal["text"] = "text"
    text: str


class ListBlock(CamelModel):
    type: Literal["list"] = "list"
    items: list[str]


class QuoteBlock(CamelModel):
    type: Literal["quote"] = "quote"
    text: str
    caption: str


class AnswerSource(CamelModel):
    node_id: str
    label: str


class AssistantAction(CamelModel):
    type: Literal["record-contestation", "request-reanalysis"]
    node_id: str
    reason: str | None = None
    contestation_id: str | None = None


class AssistantAnswer(CamelModel):
    blocks: list[TextBlock | ListBlock | QuoteBlock]
    sources: list[AnswerSource] = []
    suggestions: list[str] = []
    actions: list[AssistantAction] = []
    route: list[str] = []  # extension: which bases were searched


class Citation(BaseModel):
    fonte_id: str
    trecho: str = Field(description="Trecho LITERAL copiado do texto da fonte")


class AnswerOut(BaseModel):
    paragrafos: list[str] = Field(default_factory=list)
    itens: list[str] = Field(default_factory=list)
    citacoes: list[Citation] = Field(default_factory=list)
    fontes: list[str] = Field(default_factory=list, description="IDs das fontes usadas")
    sugestoes: list[str] = Field(default_factory=list)
    sem_base: bool = False


CHAT_SYSTEM = register_prompt(
    "assistant.answer",
    """Você é o assistente de um analista de P&D da Lei do Bem. Responde perguntas sobre a análise de um projeto
e sobre as normas, SOMENTE com as fontes recebidas (cada uma com um ID entre colchetes).
- Explique, não decida: nunca mude estado, classe ou parecer; a decisão é do analista.
- Cite em `fontes` os IDs usados; em `citacoes`, copie trechos LITERAIS das fontes.
- Números: copie das fontes, nunca recalcule.
- Ao explicar uma classe ou um estado, mencione também as evidências contrárias e as divergências.
- Nunca compare com outros projetos nem classifique por semelhança.
- Se as fontes não respondem, marque sem_base=true. Não responda de memória.
- Linguagem simples, para quem não conhece a norma a fundo; em português.
"""
    + DATA_NOT_INSTRUCTIONS,
)


@dataclass
class RoutePlan:
    graph: bool
    norms: bool
    rule_ids: list[str] = field(default_factory=list)
    decision_request: bool = False


def route(question: str, has_analysis: bool) -> RoutePlan:
    rule_ids = list(dict.fromkeys(m.upper() for m in RULE_ID_RE.findall(question)))
    norms = bool(NORM_WORDS_RE.search(question)) or not has_analysis
    return RoutePlan(graph=has_analysis, norms=norms, rule_ids=rule_ids, decision_request=bool(DECISION_RE.search(question)))


@dataclass
class Item:
    ref: str  # id shown to the model
    node_id: str  # where the front-end link points (tree node, regra:ID or norma:ID)
    label: str
    text: str


def graph_items(tree: fe.Analysis) -> list[Item]:
    items = [Item("classe", "analysis", "Classe sugerida",
                  f"Classe sugerida: {tree.suggested_class or 'sem classe automática'} ({tree.class_reason or '-'}). "
                  f"Inconsistente: {'sim' if tree.inconsistent else 'não'}.")]
    for criterion in tree.criteria:
        items.append(Item(criterion.id, criterion.id, criterion.name,
                          f"Estado: {criterion.state or 'não avaliado'}. Nota indicativa: {criterion.score}. {criterion.summary}"))
        for rule in criterion.rules:
            rule_node = f"{criterion.id}.{rule.id}"
            items.append(Item(rule_node, rule_node, f"{rule.code} {rule.name}",
                              f"Regra {rule.code} ({rule.status}): {rule.explanation} Nota: {rule.score}; "
                              f"positivas {rule.counts.positive}, negativas {rule.counts.negative}."))
            for evidence in rule.evidences:
                node = f"{rule_node}.{evidence.id}"
                quote = evidence.project_excerpt.excerpt if evidence.project_excerpt else (evidence.references[0].citation if evidence.references else "")
                items.append(Item(node, node, f"{rule.code} · {evidence.source.alias}",
                                  f"Evidência {evidence.polarity} da regra {rule.code}: \"{quote}\" — {evidence.explanation}"))
    for index, divergence in enumerate(tree.divergences, start=1):
        criterion_id = next((c.id for c in tree.criteria if c.key == divergence.criterion_key), "analysis")
        items.append(Item(f"divergencia-{index}", criterion_id, "Divergência entrevista × registro", divergence.statement))
    return items


def _subtree(items: list[Item], node_id: str | None) -> list[Item]:
    if not node_id:
        return []
    return [i for i in items if i.ref == node_id or i.ref.startswith(node_id + ".")]


class Assistant:
    def __init__(self, llm: LLM, catalog: Catalog, norms: BM25Index) -> None:
        self.llm, self.catalog, self.norms = llm, catalog, norms

    def _retrieve(self, question: str, plan: RoutePlan, tree: fe.Analysis | None, selected: str | None) -> list[Item]:
        items: list[Item] = []
        if plan.graph and tree is not None:
            every = graph_items(tree)
            ranked = BM25Index(every).search(question, k=GRAPH_ITEMS)
            anchors = [i for i in every if i.ref == "classe" or "." not in i.ref and i.ref.startswith("crit-")]
            divergences = [i for i in every if i.ref.startswith("divergencia-")]
            evidences = [i for i in every if i.ref.count(".") == 2]
            if len(evidences) > MAX_EVIDENCE_ITEMS:  # evidence is what answers "why": keep the most relevant ones
                evidences = BM25Index(evidences).search(question, k=MAX_EVIDENCE_ITEMS)
            chosen = _subtree(every, selected) + anchors + divergences + ranked + evidences
            items += list({i.ref: i for i in chosen}.values())
        for rule_id in plan.rule_ids:
            rule = self.catalog.get(rule_id)
            if rule:
                items.append(Item(f"regra:{rule.id}", f"regra:{rule.id}", f"{rule.id} — {rule.titulo}",
                                  f"{rule.titulo}. O que verificar: {rule.o_que_verificar} Em linguagem simples: "
                                  f"{rule.explicacao_simples} Fontes: {'; '.join(rule.fontes_normativas)}. "
                                  f"Status no pacote: {rule.status}{' — ' + rule.motivo_status if rule.motivo_status else ''}."))
        if plan.norms:
            chunks: list[NormChunk] = self.norms.search(question, k=NORM_ITEMS)
            items += [Item(f"norma:{c.id}", f"norma:{c.id}", c.caption, c.text) for c in chunks]
        return items

    async def ask(self, question: str, analysis, tree: fe.Analysis | None, selected_node_id: str | None = None,
                  debate_node_id: str | None = None) -> AssistantAnswer:
        plan = route(question, has_analysis=tree is not None)
        if plan.decision_request:
            return AssistantAnswer(
                blocks=[TextBlock(text="Eu explico a análise, mas não mudo estado, classe nem parecer: a decisão é do "
                                       "analista. Registre a decisão na tela de decisão, com a justificativa, ou conteste "
                                       "o nó que considera errado para pedir uma reanálise.")],
                suggestions=["Quais evidências contrárias existem?", "Onde a entrevista diverge do registro?"],
                route=["guarda de decisão"],
            )
        items = self._retrieve(question, plan, tree, debate_node_id or selected_node_id)
        if not items:
            return AssistantAnswer(blocks=[TextBlock(text=NO_BASIS)], route=self._route_names(plan))
        listing = "\n\n".join(f"[{i.ref}] {i.label}\n{i.text}" for i in items)
        focus = f"\nNó em foco: {debate_node_id or selected_node_id}" if (debate_node_id or selected_node_id) else ""
        out = await self.llm.structured(
            [{"role": "system", "content": CHAT_SYSTEM},
             {"role": "user", "content": f"Pergunta: {question}{focus}\n\n<fontes>\n{listing}\n</fontes>"}],
            AnswerOut,
            role="chat",
        )
        return self._gate(out, items, plan, debate_node_id)

    def _route_names(self, plan: RoutePlan) -> list[str]:
        return [name for name, on in (("grafo", plan.graph), ("normas", plan.norms), ("catálogo", bool(plan.rule_ids))) if on]

    def _gate(self, out: AnswerOut, items: list[Item], plan: RoutePlan, debate_node_id: str | None) -> AssistantAnswer:
        by_ref = {i.ref: i for i in items}
        used = [by_ref[ref] for ref in dict.fromkeys(out.fontes) if ref in by_ref]
        quotes = [(by_ref[c.fonte_id], clean_quote(c.trecho)) for c in out.citacoes
                  if c.fonte_id in by_ref and quote_in(c.trecho, by_ref[c.fonte_id].text)]
        for item, _ in quotes:
            if item not in used:
                used.append(item)
        if out.sem_base or not used:
            return AssistantAnswer(blocks=[TextBlock(text=NO_BASIS)], route=self._route_names(plan))
        allowed = "\n".join(i.text for i in items)
        blocks: list[TextBlock | ListBlock | QuoteBlock] = []
        for paragraph in out.paragrafos:
            if text := numbers_gate(paragraph, allowed):
                blocks.append(TextBlock(text=text))
        list_items = [t for t in (numbers_gate(i, allowed) for i in out.itens) if t]
        if list_items:
            blocks.append(ListBlock(items=list_items))
        blocks += [QuoteBlock(text=quote, caption=item.label) for item, quote in quotes]
        if not blocks:
            return AssistantAnswer(blocks=[TextBlock(text=NO_BASIS)], route=self._route_names(plan))
        actions = [AssistantAction(type="record-contestation", node_id=debate_node_id, reason="other")] if debate_node_id else []
        return AssistantAnswer(
            blocks=blocks,
            sources=list({i.node_id: AnswerSource(node_id=i.node_id, label=i.label) for i in used}.values()),
            suggestions=out.sugestoes[:4],
            actions=actions,
            route=self._route_names(plan),
        )

    def debate_opening(self, node_id: str, tree: fe.Analysis) -> AssistantAnswer:
        """The basis of the system's reading of one node, straight from the graph (no generation)."""
        items = _subtree(graph_items(tree), node_id)
        if not items:
            return AssistantAnswer(blocks=[TextBlock(text="Nó não encontrado nesta análise.")])
        head, *children = items
        blocks: list[TextBlock | ListBlock | QuoteBlock] = [TextBlock(text=f"Leitura do sistema para {head.label}: {head.text}")]
        for child in children:
            match = re.search(r'"(.+?)"', child.text)
            if match:
                blocks.append(QuoteBlock(text=match.group(1), caption=child.label))
        blocks.append(TextBlock(text="Se discorda, diga o trecho ou arquivo que mostra o contrário; registre a "
                                     "contestação e peça a reanálise. A decisão final é sua."))
        return AssistantAnswer(
            blocks=blocks,
            sources=[AnswerSource(node_id=i.node_id, label=i.label) for i in items[:6]],
            suggestions=["Qual trecho sustenta essa leitura?", "Existe evidência contrária?"],
            actions=[AssistantAction(type="record-contestation", node_id=node_id, reason="other")],
            route=["grafo"],
        )
