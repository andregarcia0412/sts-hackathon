from datetime import datetime
from typing import Literal

from pydantic import Field

from backend.api_schema import CamelModel
from backend.benchmark.metrics import divergence_found, headline
from backend.benchmark.models import Benchmark, BenchmarkConfig, BenchmarkMetrics, PackageSet, RunSnapshot
from backend.benchmark.reference import ExpectedCase
from backend.graph.classify import CLASS_LABELS


class BenchmarkRequest(CamelModel):
    """Paths are relative to PACKAGE_DIR (or absolute inside it); omitted ones use the package layout."""

    name: str | None = None
    sets: list[PackageSet] = Field(default_factory=lambda: ["historico", "analise"], min_length=1)
    historico_dir: str | None = None
    analise_dir: str | None = None
    answer_key: str | None = None
    preliminary_key: str | None = None
    repeats: int = Field(default=1, ge=1, le=5)
    projects: list[str] = Field(default_factory=list, description="e.g. ['PRJ01', 'PRJ21']; empty = all")


class BenchmarkSummary(CamelModel):
    id: str
    name: str
    status: str
    created_at: datetime
    finished_at: datetime | None = None
    total: int
    progress: dict[str, int]
    headline: dict[str, float | None] = {}
    errors: list[str] = []

    @classmethod
    def of(cls, benchmark: Benchmark, progress: dict[str, int]) -> "BenchmarkSummary":
        return cls(id=str(benchmark.id), name=benchmark.name, status=benchmark.status,
                   created_at=benchmark.created_at, finished_at=benchmark.finished_at, total=len(benchmark.runs),
                   progress=progress, headline=headline(benchmark.metrics) if benchmark.metrics else {},
                   errors=benchmark.errors)


class BenchmarkRead(BenchmarkSummary):
    config: BenchmarkConfig
    batch_ids: list[str] = []
    metrics: BenchmarkMetrics | None = None

    @classmethod
    def of(cls, benchmark: Benchmark, progress: dict[str, int]) -> "BenchmarkRead":
        return cls(**BenchmarkSummary.of(benchmark, progress).model_dump(), config=benchmark.config,
                   batch_ids=benchmark.batch_ids, metrics=benchmark.metrics)


class BenchmarkProjectRow(CamelModel):
    set: str
    code: str
    repeat: int
    analysis_id: str
    status: str
    reference: Literal["oficial", "preliminar"] | None = None
    expected_class: str | None = None
    suggested_class: str | None = None
    class_hit: bool | None = None
    inconsistent: bool | None = None
    expected_states: dict[str, str | None] = {}
    states: dict[str, str | None] = {}
    state_hits: int | None = None
    criterion_scores: dict[str, int | None] = {}
    total_s: float | None = None
    llm_calls: int = 0
    tokens: int = 0
    evidences: int = 0
    gate_dropped: int = 0
    divergences: int = 0
    planted_divergences: int = 0
    planted_divergences_found: int = 0
    error: str | None = None

    @classmethod
    def of(cls, snap: RunSnapshot, case: ExpectedCase | None) -> "BenchmarkProjectRow":
        total = snap.usage.total() if snap.usage else None
        row = cls(
            set=snap.set, code=snap.code, repeat=snap.repeat, analysis_id=snap.analysis_id, status=snap.status,
            suggested_class=snap.suggested_class, inconsistent=snap.inconsistent, states=snap.states,
            criterion_scores=snap.criterion_scores, total_s=snap.total_s,
            llm_calls=total.calls if total else 0,
            tokens=(total.prompt_tokens + total.completion_tokens) if total else 0,
            evidences=snap.evidences_positive + snap.evidences_negative, gate_dropped=snap.gate_dropped,
            divergences=len(snap.divergences), error=snap.error,
        )
        if case is not None:
            row.reference, row.expected_class, row.expected_states = case.source, case.expected_class, case.states
            row.class_hit = case.expected_class is not None and case.expected_class == snap.suggested_class
            if case.states:
                row.state_hits = sum(snap.states.get(c) == s for c, s in case.states.items())
            row.planted_divergences = len(case.planted_divergences)
            row.planted_divergences_found = sum(divergence_found(p, snap.divergences) for p in case.planted_divergences)
        return row

    def csv_row(self) -> dict[str, str]:
        label = lambda cls: CLASS_LABELS.get(cls or "", "")  # noqa: E731
        return {
            "conjunto": self.set, "projeto_id": self.code, "repeticao": str(self.repeat), "status": self.status,
            "referencia": self.reference or "", "classe_esperada": label(self.expected_class),
            "classe_sugerida": label(self.suggested_class),
            "acerto_classe": "" if self.class_hit is None else str(int(self.class_hit)),
            "acertos_estado": "" if self.state_hits is None else str(self.state_hits),
            "inconsistente": "" if self.inconsistent is None else str(int(self.inconsistent)),
            "tempo_s": "" if self.total_s is None else str(self.total_s),
            "chamadas_llm": str(self.llm_calls), "tokens": str(self.tokens), "evidencias": str(self.evidences),
            "citacoes_descartadas": str(self.gate_dropped), "divergencias": str(self.divergences),
            "divergencias_plantadas_achadas": f"{self.planted_divergences_found}/{self.planted_divergences}"
            if self.planted_divergences else "",
            "analise_id": self.analysis_id, "erro": self.error or "",
        }


class BenchmarkComparison(CamelModel):
    base: BenchmarkSummary
    target: BenchmarkSummary
    deltas: dict[str, dict[str, float | None]]
    models_changed: dict[str, dict[str, str | None]] = {}
    prompts_changed: list[str] = []
    catalog_changed: bool = False
