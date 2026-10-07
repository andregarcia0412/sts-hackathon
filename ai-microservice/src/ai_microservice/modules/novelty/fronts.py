import asyncio
import re
import unicodedata
from datetime import UTC, date, datetime

from ai_microservice.errors import safe_error_message
from ai_microservice.llm import LLMClient
from ai_microservice.modules.novelty.prompts import COMPARE_SYSTEM, FRONT_GUIDANCE, QUERY_SYSTEM
from ai_microservice.modules.novelty.schemas import (
    Descarte,
    DocComparison,
    Front,
    FrontResult,
    ProjectProfile,
    QueryPlan,
    SearchLogEntry,
    SourceDoc,
)
from ai_microservice.search.base import SearchHit, SearchProvider

OUTPUT_EXCERPT_CHARS = 600
MIN_SENSITIVE_TERM_LEN = 3


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def find_sensitive_term(query: str, terms: list[str]) -> str | None:
    """Regra T6: devolve o primeiro termo sensível presente na query (sem diferenciar caixa e acentos)."""
    normalized = _normalize(query)
    for term in terms:
        needle = _normalize(term).strip()
        if len(needle) >= MIN_SENSITIVE_TERM_LEN and re.search(rf"\b{re.escape(needle)}\b", normalized):
            return term
    return None


def redact(query: str, term: str) -> str:
    return re.sub(re.escape(term), "***", query, flags=re.IGNORECASE)


class FrontAgent:
    """Busca o estado da arte de uma frente (literatura, patentes ou mercado) até a data de referência."""

    def __init__(
        self,
        frente: Front,
        provider: SearchProvider,
        llm: LLMClient,
        queries: int,
        results_per_query: int,
        max_docs: int,
    ) -> None:
        self.frente = frente
        self.provider = provider
        self.llm = llm
        self.n_queries = queries
        self.results_per_query = results_per_query
        self.max_docs = max_docs

    async def run(self, profile: ProjectProfile) -> FrontResult:
        log: list[SearchLogEntry] = []
        queries = await self._plan_queries(profile, log)
        searches = await asyncio.gather(*(self._search(query, profile.data_referencia) for query in queries))
        log += [entry for entry, _ in searches]

        selected = self._select(searches)
        enriched = await asyncio.gather(*(self._enrich(hit) for hit, _ in selected))
        docs = []
        for (hit, entry), doc_hit in zip(selected, enriched, strict=True):
            doc = self._to_source_doc(doc_hit, profile.data_referencia)
            if doc.anterior_a_referencia is False:
                entry.descartados.append(
                    Descarte(
                        alvo=doc.id,
                        motivo=f"publicado em {doc.data_publicacao}, depois da data de referência "
                        f"{profile.data_referencia}: não é estado da arte (usado só em NOV-W6)",
                    )
                )
            else:
                entry.selecionados.append(doc.id)
            docs.append(doc)

        comparable = [doc for doc in docs if doc.anterior_a_referencia is not False]
        comparisons = await asyncio.gather(*(self._compare(doc, profile) for doc in comparable))
        for doc, comparison in zip(comparable, comparisons, strict=True):
            doc.comparacao = comparison
        for doc in docs:
            doc.trecho = doc.trecho[:OUTPUT_EXCERPT_CHARS]
        return FrontResult(frente=self.frente, fontes=docs, log=log)

    async def _plan_queries(self, profile: ProjectProfile, log: list[SearchLogEntry]) -> list[str]:
        system = QUERY_SYSTEM.format(
            guidance=FRONT_GUIDANCE[self.frente],
            n=self.n_queries,
            sensiveis=", ".join(profile.termos_sensiveis) or "(nenhum)",
        )
        context = (
            f"Elemento novo declarado: {profile.elemento_novo_declarado.texto}\n"
            f"Problema técnico: {profile.problema_tecnico.texto}\n"
            f"Domínio/setor: {profile.dominio_setor.texto}\n"
            f"Referência anterior declarada: {profile.referencia_anterior_declarada.texto}\n"
            f"Palavras-chave: {', '.join(profile.palavras_chave_en + profile.palavras_chave_pt)}"
        )
        plan = await self.llm.structured(
            [{"role": "system", "content": system}, {"role": "user", "content": context}], QueryPlan, role="search"
        )
        accepted: list[str] = []
        for query in dict.fromkeys(q.strip() for q in plan.queries if q.strip()):
            if term := find_sensitive_term(query, profile.termos_sensiveis):
                log.append(
                    SearchLogEntry(
                        frente=self.frente,
                        base=self.provider.name,
                        query=redact(query, term),
                        executado_em=datetime.now(UTC),
                        erro="query descartada antes da busca: contém termo sensível do projeto (regra T6)",
                    )
                )
                continue
            accepted.append(query)
        return accepted[: self.n_queries]

    async def _search(self, query: str, before: date) -> tuple[SearchLogEntry, list[SearchHit]]:
        entry = SearchLogEntry(
            frente=self.frente,
            base=self.provider.name,
            query=query,
            filtros={"publicado_ate": before.isoformat(), "max_resultados": str(self.results_per_query)},
            executado_em=datetime.now(UTC),
        )
        try:
            hits = await self.provider.search(query, before=before, limit=self.results_per_query)
        except Exception as error:  # uma busca que falha não derruba a frente; fica registrada no log
            entry.erro = safe_error_message(error)
            return entry, []
        entry.n_resultados = len(hits)
        return entry, hits

    def _select(
        self, searches: list[tuple[SearchLogEntry, list[SearchHit]]]
    ) -> list[tuple[SearchHit, SearchLogEntry]]:
        """Intercala os resultados das queries (1º de cada, 2º de cada…), sem repetir, até `max_docs`."""
        selected: list[tuple[SearchHit, SearchLogEntry]] = []
        seen: set[str] = set()
        depth = max((len(hits) for _, hits in searches), default=0)
        for rank in range(depth):
            for entry, hits in searches:
                if rank >= len(hits):
                    continue
                hit = hits[rank]
                if hit.id in seen:
                    entry.descartados.append(Descarte(alvo=hit.id, motivo="duplicado de outra query"))
                elif len(selected) >= self.max_docs:
                    entry.descartados.append(
                        Descarte(alvo=hit.id, motivo=f"fora do limite de {self.max_docs} documentos por frente")
                    )
                else:
                    selected.append((hit, entry))
                seen.add(hit.id)
        return selected

    async def _enrich(self, hit: SearchHit) -> SearchHit:
        try:
            return await self.provider.enrich(hit)
        except Exception:  # sem a página completa, segue com o snippet da busca e data desconhecida
            return hit

    def _to_source_doc(self, hit: SearchHit, reference: date) -> SourceDoc:
        anterior = None if hit.published_date is None else hit.published_date <= reference
        return SourceDoc(
            id=hit.id,
            frente=self.frente,
            base=hit.provider,
            titulo=hit.title,
            url=hit.url,
            data_publicacao=hit.published_date,
            data_verificada=hit.published_date is not None,
            anterior_a_referencia=anterior,
            tipo_data=hit.extra.get("tipo_data") or ("publicacao" if hit.date_source == "metadata" else None),
            trecho=hit.snippet,
        )

    async def _compare(self, doc: SourceDoc, profile: ProjectProfile) -> DocComparison | None:
        project = (
            f"Elemento novo declarado: {profile.elemento_novo_declarado.texto}\n"
            f"Problema técnico: {profile.problema_tecnico.texto}"
        )
        document = f"Título: {doc.titulo}\nData: {doc.data_publicacao or 'desconhecida'}\n\n{doc.trecho}"
        try:
            return await self.llm.structured(
                [
                    {"role": "system", "content": COMPARE_SYSTEM},
                    {"role": "user", "content": f"<projeto>\n{project}\n</projeto>\n\n<documento>\n{document}\n</documento>"},
                ],
                DocComparison,
                role="search",
            )
        except Exception:  # documento sem comparação continua listado, mas não sustenta veredito
            return None
