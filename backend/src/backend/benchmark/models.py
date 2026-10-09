from datetime import datetime
from typing import Any, Literal

from beanie import Document
from pydantic import Field

from backend.api_schema import CamelModel
from backend.benchmark.reference import ExpectedCase
from backend.graph.coherence import Coherence
from backend.llm.usage import LLMUsage, RoleUsage
from backend.projects.models import now

BenchmarkStatus = Literal["rodando", "concluido"]
PackageSet = Literal["historico", "analise"]


class BenchmarkConfig(CamelModel):
    """What was run and with which models/prompts/catalog, so two benchmarks can be compared (principle 11)."""

    sets: dict[str, str] = Field(default_factory=dict)  # set → folder
    answer_key: str | None = None
    answer_key_sha256: str | None = None
    preliminary_key: str | None = None
    preliminary_key_sha256: str | None = None
    repeats: int = 1
    projects: list[str] = Field(default_factory=list)  # empty = every project found
    models: dict[str, str | None] = Field(default_factory=dict)
    catalog_version: str | None = None
    prompts: dict[str, str] = Field(default_factory=dict)
    backend_version: str | None = None
    rejudged_from: str | None = None  # re-judge benchmark: id of the benchmark whose analyses were re-judged
    judge_options: dict[str, Any] = Field(default_factory=dict)


class BenchmarkRun(CamelModel):
    set: PackageSet
    code: str
    project_id: str
    analysis_id: str
    repeat: int


class DivergenceSnapshot(CamelModel):
    criterion: str
    testimony_quote: str
    record_quote: str
    statement: str


class RunSnapshot(CamelModel):
    """What the metrics need from one finished analysis (the analysis itself keeps the full record)."""

    set: PackageSet
    code: str
    repeat: int
    analysis_id: str
    status: str
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    total_s: float | None = None
    stages: dict[str, str] = Field(default_factory=dict)  # stage → status
    stage_seconds: dict[str, float] = Field(default_factory=dict)
    suggested_class: str | None = None
    inconsistent: bool | None = None
    incomplete: bool = False
    states: dict[str, str | None] = Field(default_factory=dict)
    columns: dict[str, str | None] = Field(default_factory=dict)
    criterion_scores: dict[str, int | None] = Field(default_factory=dict)
    rules_total: int = 0
    rules_with_evidence: int = 0
    rules_not_executed: int = 0
    evidence_ids: list[str] = Field(default_factory=list)
    evidences_positive: int = 0
    evidences_negative: int = 0
    gate_dropped: int = 0
    web_searches: int = 0
    web_search_errors: int = 0
    web_sources: int = 0
    web_not_prior_art: int = 0
    sanitized_terms_removed: int = 0
    divergences: list[DivergenceSnapshot] = Field(default_factory=list)
    missing_links: int = 0
    usage: LLMUsage | None = None
    rejudged: bool = False  # only the conclusion stage ran again, over the saved evidence
    coherence: dict[str, Coherence] = Field(default_factory=dict)  # criterion → coherence gate record


class Distribution(CamelModel):
    mean: float | None = None
    median: float | None = None
    p95: float | None = None
    max: float | None = None
    n: int = 0


class ClassScores(CamelModel):
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    support: int = 0


class AccuracyMetrics(CamelModel):
    """Suggested × expected for one reference (official and preliminary are never mixed)."""

    reference: str
    n: int = 0
    class_hits: int = 0
    class_accuracy: float | None = None
    macro_f1: float | None = None
    cohen_kappa: float | None = None
    per_class: dict[str, ClassScores] = Field(default_factory=dict)
    confusion: dict[str, dict[str, int]] = Field(default_factory=dict)  # expected → suggested → n
    false_eligible: int = 0  # suggested eligible(-ish) when expected not eligible / insufficient: the costly error
    false_not_eligible: int = 0  # suggested not eligible / insufficient when expected eligible(-ish)
    state_accuracy: dict[str, float | None] = Field(default_factory=dict)  # exact vocabulary, per criterion
    column_accuracy: dict[str, float | None] = Field(default_factory=dict)  # pd / rotina / insuficiente
    planted_divergences: int = 0
    planted_divergences_found: int = 0
    planted_divergence_recall: float | None = None
    misses: list[str] = Field(default_factory=list)  # "PRJ05: Com ressalvas → Elegível"


class TimingMetrics(CamelModel):
    total_s: Distribution = Field(default_factory=Distribution)
    stages_s: dict[str, Distribution] = Field(default_factory=dict)
    wall_clock_s: float | None = None
    projects_per_hour: float | None = None


class ReliabilityMetrics(CamelModel):
    runs: int = 0
    failed: int = 0
    failure_rate: float | None = None
    stage_failures: dict[str, int] = Field(default_factory=dict)  # failed or not executed
    rules_not_executed_rate: float | None = None
    inconsistent_rate: float | None = None
    incomplete_rate: float | None = None
    no_class_rate: float | None = None


class EvidenceMetrics(CamelModel):
    evidences_per_run: Distribution = Field(default_factory=Distribution)
    positive_share: float | None = None
    rule_coverage: float | None = None  # executed with evidence / rules run
    gate_drop_rate: float | None = None  # dropped / (dropped + accepted)
    web_search_error_rate: float | None = None
    web_not_prior_art_share: float | None = None
    sanitized_terms_removed: int = 0
    divergences_per_run: Distribution = Field(default_factory=Distribution)
    missing_links_per_run: Distribution = Field(default_factory=Distribution)


class UsageMetrics(CamelModel):
    roles: dict[str, RoleUsage] = Field(default_factory=dict)
    total: RoleUsage = Field(default_factory=RoleUsage)
    tokens_per_run: Distribution = Field(default_factory=Distribution)
    calls_per_run: Distribution = Field(default_factory=Distribution)
    web_search_calls: int = 0
    web_fetch_calls: int = 0


class DeterminismMetrics(CamelModel):
    """Agreement between repeats of the same project (only with repeats ≥ 2)."""

    projects: int = 0
    class_agreement: float | None = None
    state_agreement: dict[str, float | None] = Field(default_factory=dict)
    score_std: dict[str, float | None] = Field(default_factory=dict)  # mean std-dev of the criterion score
    evidence_jaccard: float | None = None
    unstable: list[str] = Field(default_factory=list)


class CoherenceMetrics(CamelModel):
    """Score × state contradictions found by the coherence gate (spec 11)."""

    contradictions: dict[str, int] = Field(default_factory=dict)  # per criterion
    by_source: dict[str, int] = Field(default_factory=dict)  # "juiz" (state choice) / "gate" (configuration gate)
    rejudged: int = 0
    resolved: int = 0
    incoherent: int = 0
    changed_column: int = 0  # the new judgement moved the criterion to another column
    changed_column_hits: int = 0  # ... and the final state matches the official answer key
    changed_column_misses: int = 0


class BenchmarkMetrics(CamelModel):
    accuracy: dict[str, AccuracyMetrics] = Field(default_factory=dict)  # "oficial" / "preliminar"
    timing: TimingMetrics = Field(default_factory=TimingMetrics)
    reliability: ReliabilityMetrics = Field(default_factory=ReliabilityMetrics)
    evidence: EvidenceMetrics = Field(default_factory=EvidenceMetrics)
    usage: UsageMetrics = Field(default_factory=UsageMetrics)
    determinism: DeterminismMetrics | None = None
    coherence: CoherenceMetrics = Field(default_factory=CoherenceMetrics)
    class_distribution: dict[str, dict[str, int]] = Field(default_factory=dict)  # "sugerida"/reference → class → n
    by_set: dict[str, TimingMetrics] = Field(default_factory=dict)


class Benchmark(Document):
    owner_id: str
    name: str
    status: BenchmarkStatus = "rodando"
    created_at: datetime = Field(default_factory=now)
    finished_at: datetime | None = None
    config: BenchmarkConfig = Field(default_factory=BenchmarkConfig)
    batch_ids: list[str] = Field(default_factory=list)
    runs: list[BenchmarkRun] = Field(default_factory=list)
    expected: dict[str, ExpectedCase] = Field(default_factory=dict)
    snapshots: list[RunSnapshot] = Field(default_factory=list)
    metrics: BenchmarkMetrics | None = None
    errors: list[str] = Field(default_factory=list)

    class Settings:
        name = "benchmarks"
