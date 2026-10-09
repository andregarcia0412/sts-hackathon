"""Web sub-agent: all -W rules of a criterion, over sanitized searches in four fronts."""

import asyncio
from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.catalog.models import Catalog, CatalogRule
from backend.criteria.citation import clean_quote, quote_in
from backend.criteria.common import DATA_NOT_INSTRUCTIONS, argument_block, describe_rules, offline_runs
from backend.criteria.doc_sub import RuleNoEvidenceOut
from backend.criteria.schemas import (
    FRONTS,
    ClosestDoc,
    CriterionResult,
    EvidenceItem,
    Front,
    RuleRun,
    SearchLogEntry,
    WebSource,
    evidence_id,
)
from backend.errors import safe_error_message
from backend.extraction.schema import CanonicalProject
from backend.llm import LLM
from backend.llm.prompts import register_prompt
from backend.search.base import SearchHit, SearchProvider
from backend.search.grounding import domain_terms, grounded
from backend.search.sanitize import sanitize_query
from backend.search.session import SearchSession

PROMPT_SNIPPET_CHARS = 1500
LATER_SOURCES_RULES = {"NOV-W6"}  # NOV-W6 is about simultaneous work: it reads later publications too
PROCEDURAL = {"NOV-W1", "NOV-W2", "NOV-W8"}


class PlannedQuery(BaseModel):
    frente: Front
    query: str = Field(description="Até 10 palavras, termos técnicos genéricos")
    regras: list[str] = Field(default_factory=list)


class QueryPlanOut(BaseModel):
    queries: list[PlannedQuery] = Field(default_factory=list)


class WebEvidenceOut(BaseModel):
    regra_id: str
    fonte_id: str
    quote: str = Field(description="Trecho LITERAL copiado do texto da fonte")
    polaridade: Literal["positiva", "negativa"]
    justificativa: str


class ClosestDocOut(BaseModel):
    fonte_id: str
    cobertura: Literal["total", "parcial", "nenhuma"]
    o_que_o_projeto_tem_a_mais: str


class WebJudgeOut(BaseModel):
    evidencias: list[WebEvidenceOut] = Field(default_factory=list)
    regras_sem_evidencia: list[RuleNoEvidenceOut] = Field(default_factory=list)
    documento_mais_proximo: ClosestDocOut | None = None


PLAN_SYSTEM = register_prompt(
    "criteria.web.plan",
    """Você planeja buscas na internet para verificar regras de um critério da Lei do Bem.
Frentes: literatura (OpenAlex; inglês acadêmico), patentes (Google Patents; inglês de reivindicação),
mercado (produtos, serviços, bibliotecas; inglês e português), documentacao (documentação oficial de
fornecedores e frameworks, RFC, OWASP/NIST, GitHub, Stack Overflow).
Gere até {n} queries por frente, curtas e diferentes, marcadas com as regras que servem.
O que cada família de regra procura:
{familias}
PROIBIDO usar nomes internos, códigos, nomes de equipe, números de resultado ou qualquer dado que
identifique o projeto. Termos proibidos: {sensiveis}.
"""
    + DATA_NOT_INSTRUCTIONS,
)

JUDGE_SYSTEM = register_prompt(
    "criteria.web.judge",
    """Você avalia regras de um critério da Lei do Bem a partir de fontes recuperadas na internet.
Você não decide se o projeto é P&D: só aponta evidências citáveis para o analista.
- Cite SOMENTE `fonte_id` da lista recebida e copie um trecho LITERAL do texto da fonte em `quote`.
- Polaridade só "positiva" ou "negativa"; achado que não fala da regra (ex.: "circuit breaker" elétrico numa
  busca de software) não é evidência.
- Fontes marcadas "não é estado da arte" (posteriores à data de referência) não servem como estado da arte;
  só a regra NOV-W6 pode usá-las.
- Ausência de achado não prova novidade: sem evidência, liste a regra em `regras_sem_evidencia`.
- `documento_mais_proximo`: só para o critério Novidade — a fonte anterior mais próxima do elemento novo e
  a cobertura (total = um único documento descreve o elemento inteiro).
"""
    + DATA_NOT_INSTRUCTIONS,
)


def _date_label(source_date: date | None, reference: date | None) -> tuple[bool | None, str]:
    if source_date is None or reference is None:
        return None, "data indeterminada"
    if source_date <= reference:
        return True, "estado da arte"
    return False, "não é estado da arte"


def _select(searches: list[tuple[SearchLogEntry, list[SearchHit]]], limit: int) -> list[tuple[SearchHit, SearchLogEntry]]:
    """Interleaves the results of the queries of one front (1st of each, 2nd of each…), without repeats."""
    selected: list[tuple[SearchHit, SearchLogEntry]] = []
    seen: set[str] = set()
    depth = max((len(hits) for _, hits in searches), default=0)
    for rank in range(depth):
        for entry, hits in searches:
            if rank >= len(hits):
                continue
            hit = hits[rank]
            if hit.id in seen:
                entry.discarded.append(f"{hit.id}: duplicado de outra query")
            elif len(selected) >= limit:
                entry.discarded.append(f"{hit.id}: fora do limite de {limit} documentos por frente")
            else:
                selected.append((hit, entry))
                entry.selected.append(hit.id)
            seen.add(hit.id)
    return selected


class WebSub:
    def __init__(self, llm: LLM, catalog: Catalog, criterion: str, rules: list[CatalogRule], canonical: CanonicalProject,
                 providers: dict[str, SearchProvider], queries_per_front: int, results_per_query: int,
                 fetch_per_front: int, closest_doc: ClosestDoc | None, analyst_argument: str | None = None,
                 session: SearchSession | None = None) -> None:
        self.llm, self.catalog, self.criterion, self.rules = llm, catalog, criterion, rules
        self.canonical, self.providers, self.closest_doc = canonical, providers, closest_doc
        self.queries_per_front, self.results_per_query, self.fetch_per_front = queries_per_front, results_per_query, fetch_per_front
        self.reference = canonical.context.data_referencia
        self.analyst_argument = analyst_argument
        self.session = session or SearchSession()
        self.terms = domain_terms(canonical)

    def _context(self) -> str:
        ctx = self.canonical.context
        return (
            f"Elemento novo declarado: {ctx.elemento_novo.text or '-'}\n"
            f"Barreira técnica: {ctx.barreira.text or '-'}\n"
            f"Referência anterior declarada: {ctx.referencia_anterior.text or '-'}\n"
            f"Produtos citados: {', '.join(ctx.produtos_citados) or '-'}\n"
            f"Palavras-chave: {', '.join(ctx.palavras_chave_en + ctx.palavras_chave_pt) or '-'}"
        )

    async def _plan(self) -> list[PlannedQuery]:
        families = sorted({family for rule in self.rules for family in rule.roteamento if family in self.catalog.familias_web})
        system = (
            PLAN_SYSTEM.replace("{n}", str(self.queries_per_front))
            .replace("{familias}", "\n".join(f"- {f}: {self.catalog.familias_web[f]}" for f in families) or "-")
            .replace("{sensiveis}", ", ".join(self.canonical.context.termos_sensiveis) or "(nenhum)")
        )
        rules = "\n".join(f"- {r.id}: {r.o_que_verificar}" for r in self.rules)
        user = f"Regras:\n{rules}\n\n<fragmentos>\n{self._context()}\n</fragmentos>"
        plan = await self.llm.structured(
            [{"role": "system", "content": system}, {"role": "user", "content": user}], QueryPlanOut, role="search"
        )
        per_front: dict[str, int] = {}
        kept = []
        for query in plan.queries:
            if per_front.get(query.frente, 0) < self.queries_per_front:
                per_front[query.frente] = per_front.get(query.frente, 0) + 1
                kept.append(query)
        return kept

    async def _search(self, planned: PlannedQuery) -> tuple[SearchLogEntry, list[SearchHit]]:
        sanitized = sanitize_query(planned.query, self.canonical.context.termos_sensiveis)
        provider = self.providers.get(planned.frente)
        before = self.reference or date.today()
        entry = SearchLogEntry(
            criterion=self.criterion,
            front=planned.frente,
            base=provider.name if provider else "indisponível",
            original_query=planned.query,
            sanitized_query=sanitized.sanitized,
            removed_terms=sanitized.removed,
            rules=planned.regras,
            filters={"publicado_ate": before.isoformat(), "max_resultados": str(self.results_per_query)},
            executed_at=datetime.now(UTC),
        )
        if not sanitized.sanitized:
            entry.error = "query vazia depois da sanitização (T6): não enviada"
            return entry, []
        if provider is None:
            entry.error = "frente sem provedor configurado"
            return entry, []
        if not grounded(sanitized.sanitized, self.terms):
            entry.error = "query sem termo do domínio: não enviada"
            return entry, []
        try:
            hits, entry.reused_from = await self.session.search(
                planned.frente, sanitized.sanitized,
                lambda: provider.search(sanitized.sanitized, before=before, limit=self.results_per_query))
        except Exception as error:
            entry.error = safe_error_message(error)
            return entry, []
        entry.n_results = len(hits)
        return entry, hits

    async def _enrich(self, front: str, hit: SearchHit) -> SearchHit:
        try:
            return await self.session.page(hit.url, lambda: self.providers[front].enrich(hit))
        except Exception:  # without the full page the search snippet is kept, date unknown
            return hit

    async def _collect(self, planned: list[PlannedQuery]) -> tuple[list[SearchLogEntry], list[WebSource]]:
        searches = await asyncio.gather(*(self._search(p) for p in planned))
        log = [entry for entry, _ in searches]
        sources: list[WebSource] = []
        seen: set[str] = set()
        for front in FRONTS:
            front_searches = [(e, h) for (e, h) in searches if e.front == front]
            selected = [(hit, entry) for hit, entry in _select(front_searches, self.fetch_per_front) if hit.id not in seen]
            enriched = await asyncio.gather(*(self._enrich(front, hit) for hit, _ in selected))
            for (hit, entry), full in zip(selected, enriched, strict=True):
                seen.add(hit.id)
                prior_art, label = _date_label(full.published_date, self.reference)
                if prior_art is False:
                    entry.discarded.append(f"{hit.id}: publicado em {full.published_date}, {label} (só NOV-W6)")
                sources.append(
                    WebSource(id=hit.id, front=front, base=full.provider, title=full.title, url=full.url,
                              published_date=full.published_date, prior_art=prior_art, date_label=label,
                              snippet=full.snippet, captured_at=datetime.now(UTC))
                )
        return log, sources

    def _procedural(self, rule: CatalogRule, log: list[SearchLogEntry], sources: list[WebSource]) -> RuleRun:
        ok = [e for e in log if e.error is None]
        run = RuleRun(rule_id=rule.id, criterion=self.criterion, status="executada")
        if rule.id == "NOV-W1":
            ctx = self.canonical.context
            if ctx.data_referencia is None:
                return run.model_copy(update={"status": "sem_evidencia", "reason": "data de referência não encontrada"})
            later = sum(s.prior_art is False for s in sources)
            undated = sum(s.prior_art is None for s in sources)
            origin = ctx.data_referencia_fragmento or ctx.data_referencia_origem
            run.note = (f"Data de referência {ctx.data_referencia.isoformat()} (origem: {origin}). "
                        f"{later} fonte(s) posterior(es) fora do estado da arte; {undated} sem data verificável.")
            return run
        if not ok:
            return run.model_copy(update={"status": "nao_executada", "reason": "busca web indisponível: nenhuma busca concluída"})
        if rule.id == "NOV-W2":
            parts, empty = [], []
            for front in FRONTS:
                done = [e for e in ok if e.front == front]
                count = sum(s.front == front for s in sources)
                (parts if done and count else empty).append(f"{front} ({len(done)} buscas, {count} fontes)")
            run.note = "Frentes com fontes: " + ("; ".join(parts) or "nenhuma") + ". Sem fontes: " + ("; ".join(empty) or "nenhuma") + "."
            return run
        failed = len(log) - len(ok)
        run.note = (f"{len(log)} busca(s) registradas com base, query original × sanitizada, filtros, data/hora, nº de "
                    f"resultados e fontes selecionadas/descartadas ({failed} com erro ou não enviadas).")
        return run

    async def _judge(self, judged: list[CatalogRule], sources: list[WebSource]) -> WebJudgeOut:
        listing = "\n\n".join(
            f"[{s.id}] frente={s.front} base={s.base} data={s.published_date or '?'} ({s.date_label})\n"
            f"título: {s.title}\nurl: {s.url}\ntexto: {s.snippet[:PROMPT_SNIPPET_CHARS]}"
            for s in sources
        )
        ctx = self.canonical.context
        closest = ""
        if self.closest_doc:
            closest = (f"\nEstado da arte mais próximo (definido pela Novidade, NOV-W3): {self.closest_doc.title} "
                       f"({self.closest_doc.url}); cobertura {self.closest_doc.cobertura}; o que o projeto tem a mais: "
                       f"{self.closest_doc.o_que_o_projeto_tem_a_mais}\n")
        info = self.catalog.criteria[self.criterion]
        user = (
            f"Critério: {info.nome}\nData de referência: {ctx.data_referencia or 'desconhecida'}\n{closest}\n"
            f"Regras:\n\n{describe_rules(judged)}\n\n<fragmentos>\n{self._context()}\n</fragmentos>\n\n"
            f"<fontes>\n{listing}\n</fontes>"
        ) + argument_block(self.analyst_argument)
        return await self.llm.structured(
            [{"role": "system", "content": JUDGE_SYSTEM}, {"role": "user", "content": user}], WebJudgeOut, role="judge"
        )

    def _gate(self, out: WebJudgeOut, judged: list[CatalogRule], sources: list[WebSource], log: list[SearchLogEntry]) -> list[RuleRun]:
        by_source = {s.id: s for s in sources}
        query_of = {hit: e.sanitized_query for e in log for hit in e.selected}
        accepted: dict[str, list[EvidenceItem]] = {r.id: [] for r in judged}
        dropped: dict[str, list[str]] = {r.id: [] for r in judged}
        for item in out.evidencias:
            if item.regra_id not in accepted:
                continue
            source = by_source.get(item.fonte_id)
            if source is None:
                dropped[item.regra_id].append(f"fonte inexistente {item.fonte_id}")
            elif source.prior_art is False and item.regra_id not in LATER_SOURCES_RULES:
                dropped[item.regra_id].append(f"{source.id} não é estado da arte")
            elif not quote_in(item.quote, source.snippet):
                dropped[item.regra_id].append(f"trecho não encontrado literalmente em {source.id}")
            else:
                quote = clean_quote(item.quote)
                ev_id = evidence_id(item.regra_id, source.id, quote)
                if all(e.id != ev_id for e in accepted[item.regra_id]):
                    accepted[item.regra_id].append(
                        EvidenceItem(id=ev_id, rule_id=item.regra_id, criterion=self.criterion, origin="web",
                                     source_id=source.id, source_alias=source.url, quote=quote, polarity=item.polaridade,
                                     explanation=item.justificativa, query=query_of.get(source.id, ""), nature="web",
                                     url=source.url, published_date=source.published_date, captured_at=source.captured_at)
                    )
        no_evidence = {i.regra_id: i.motivo for i in out.regras_sem_evidencia}
        runs = []
        for rule in judged:
            if accepted[rule.id]:
                runs.append(RuleRun(rule_id=rule.id, criterion=self.criterion, status="executada", evidences=accepted[rule.id],
                                    dropped=dropped[rule.id]))
            elif dropped[rule.id]:
                runs.append(RuleRun(rule_id=rule.id, criterion=self.criterion, status="sem_evidencia",
                                    reason="citações descartadas pelo gate: " + "; ".join(dropped[rule.id]),
                                    dropped=dropped[rule.id]))
            else:
                reason = no_evidence.get(rule.id, f"nada encontrado após {len(log)} busca(s) em {len(sources)} fonte(s)")
                runs.append(RuleRun(rule_id=rule.id, criterion=self.criterion, status="sem_evidencia", reason=reason))
        return runs

    def _closest(self, out: WebJudgeOut, sources: list[WebSource]) -> ClosestDoc | None:
        found = out.documento_mais_proximo
        source = next((s for s in sources if found and s.id == found.fonte_id), None)
        if source is None or source.prior_art is False:
            return None
        return ClosestDoc(source_id=source.id, title=source.title, url=source.url, cobertura=found.cobertura,
                          o_que_o_projeto_tem_a_mais=found.o_que_o_projeto_tem_a_mais)

    async def run(self) -> CriterionResult:
        result = CriterionResult(criterion=self.criterion, rules=offline_runs(self.rules))
        active = [r for r in self.rules if r.executavel and r.status == "aplicavel"]
        judged = [r for r in active if r.id not in PROCEDURAL]
        try:
            planned = await self._plan()
        except Exception as error:
            planned = []
            result.errors.append(f"sub Web {self.criterion}: planejamento falhou: {safe_error_message(error)}")
        log, sources = await self._collect(planned)
        result.search_log, result.web_sources = log, sources
        result.rules += [self._procedural(r, log, sources) for r in active if r.id in PROCEDURAL]
        if not any(e.error is None for e in log):
            reason = "busca web indisponível: nenhuma busca concluída (regra não executada, nunca zero)"
            result.rules += [RuleRun(rule_id=r.id, criterion=self.criterion, status="nao_executada", reason=reason) for r in judged]
            return result
        try:
            out = await self._judge(judged, sources)
        except Exception as error:
            message = safe_error_message(error)
            result.errors.append(f"sub Web {self.criterion}: juiz falhou: {message}")
            result.rules += [RuleRun(rule_id=r.id, criterion=self.criterion, status="nao_executada",
                                     reason=f"falha do agente: {message}") for r in judged]
            return result
        result.rules += self._gate(out, judged, sources, log)
        if self.criterion == "NOV":
            result.closest_doc = self._closest(out, sources)
        return result


async def run_web_sub(llm: LLM, catalog: Catalog, criterion: str, rules: list[CatalogRule], canonical: CanonicalProject,
                      providers: dict[str, SearchProvider], queries_per_front: int, results_per_query: int,
                      fetch_per_front: int, closest_doc: ClosestDoc | None = None,
                      analyst_argument: str | None = None, session: SearchSession | None = None) -> CriterionResult:
    return await WebSub(llm, catalog, criterion, rules, canonical, providers, queries_per_front, results_per_query,
                        fetch_per_front, closest_doc, analyst_argument, session).run()
