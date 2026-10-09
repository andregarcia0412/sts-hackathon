import hashlib
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Polarity = Literal["positiva", "negativa"]
RuleStatus = Literal["executada", "sem_evidencia", "nao_executada", "na", "parcial"]
Front = Literal["literatura", "patentes", "mercado", "documentacao"]
FRONTS: tuple[Front, ...] = ("literatura", "patentes", "mercado", "documentacao")


def evidence_id(rule_id: str, source_id: str, quote: str) -> str:
    """Deterministic: re-running the same analysis produces the same evidence ids (idempotent graph)."""
    return "ev-" + hashlib.sha1(f"{rule_id}|{source_id}|{quote}".encode()).hexdigest()[:16]


class Adjustment(BaseModel):
    """A deterministic adjustment made after the sub-agents (never deletes, keeps the original polarity)."""

    kind: Literal["consistencia", "pergunta"]  # consistencia = out of the score; pergunta = counts as negative
    by_rule: str
    reason: str


class EvidenceItem(BaseModel):
    id: str
    rule_id: str
    criterion: str
    origin: Literal["doc", "web"]
    source_id: str  # fragment id or web source id
    source_alias: str  # file#anchor or URL
    quote: str  # verbatim, passed the citation gate
    polarity: Polarity
    explanation: str
    query: str
    nature: str  # fragment nature, or "web"
    page: int | None = None
    url: str | None = None
    published_date: date | None = None
    captured_at: datetime | None = None
    adjustment: Adjustment | None = None

    @property
    def scored_polarity(self) -> Polarity | None:
        """The polarity the score and the state gates use: None = neutralized (out of the score)."""
        if self.adjustment is None:
            return self.polarity
        return "negativa" if self.adjustment.kind == "pergunta" else None


class RuleRun(BaseModel):
    rule_id: str
    criterion: str
    status: RuleStatus
    reason: str | None = None
    note: str | None = None  # procedural rules (NOV-W1/W2/W8): what was checked
    evidences: list[EvidenceItem] = Field(default_factory=list)
    dropped: list[str] = Field(default_factory=list)  # citations refused by the gates, with the reason


class Divergence(BaseModel):
    criterion: str
    testimony_fragment_id: str
    testimony_quote: str
    record_fragment_id: str
    record_alias: str
    record_quote: str
    statement: str


class MissingLink(BaseModel):
    criterion: str
    description: str
    evidence_to_request: str
    fragment_ids: list[str] = Field(default_factory=list)


class WebSource(BaseModel):
    id: str
    front: Front
    base: str
    title: str
    url: str
    published_date: date | None = None
    prior_art: bool | None = None  # None = undated
    date_label: str
    snippet: str
    captured_at: datetime


class SearchLogEntry(BaseModel):
    criterion: str
    front: Front
    base: str
    original_query: str
    sanitized_query: str
    removed_terms: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    filters: dict[str, str] = Field(default_factory=dict)
    executed_at: datetime
    n_results: int = 0
    selected: list[str] = Field(default_factory=list)
    discarded: list[str] = Field(default_factory=list)
    error: str | None = None


class ClosestDoc(BaseModel):
    source_id: str
    title: str
    url: str
    cobertura: Literal["total", "parcial", "nenhuma"]
    o_que_o_projeto_tem_a_mais: str
    quote: str = ""


class CriterionResult(BaseModel):
    criterion: str
    rules: list[RuleRun] = Field(default_factory=list)
    divergences: list[Divergence] = Field(default_factory=list)
    missing_links: list[MissingLink] = Field(default_factory=list)
    web_sources: list[WebSource] = Field(default_factory=list)
    search_log: list[SearchLogEntry] = Field(default_factory=list)
    closest_doc: ClosestDoc | None = None
    errors: list[str] = Field(default_factory=list)

    def rule(self, rule_id: str) -> RuleRun | None:
        return next((r for r in self.rules if r.rule_id == rule_id), None)
