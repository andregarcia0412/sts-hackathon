from datetime import datetime
from typing import Any, Literal

from beanie import Document
from pydantic import Field

from backend.api_schema import CamelModel
from backend.benchmark.reference import ExpectedCase
from backend.graph.coherence import Coherence
from backend.graph.states import CriterionState
from backend.llm.calls import CallsSummary
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
    search: dict[str, int] = Field(default_factory=dict)  # web search budget and concurrency of the run
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
    web_searches_by_base: dict[str, int] = Field(default_factory=dict)
    web_search_errors_by_base: dict[str, int] = Field(default_factory=dict)
    web_searches_reused: int = 0  # served by a near-identical query of the same front (spec 10)
    web_queries_ungrounded: int = 0  # dropped: no term of the project's domain
    web_sources: int = 0
    web_not_prior_art: int = 0
    sanitized_terms_removed: int = 0
    divergences: list[DivergenceSnapshot] = Field(default_factory=list)
    missing_links: int = 0
    usage: LLMUsage | None = None
    rejudged: bool = False  # only the conclusion stage ran again, over the saved evidence
    coherence: dict[str, Coherence] = Field(default_factory=dict)  # criterion → coherence gate record
    judgements: dict[str, CriterionState] = Field(default_factory=dict)  # re-judge only: the full new states
    neutralized: int = 0  # evidences neutralized by the consistency between criteria (spec 02)
    files_total: int = 0
    calls: CallsSummary | None = None  # per model / per stage
    rules_na: int = 0
    rules_partial: int = 0
    dropped_invented: int = 0  # citations not found verbatim, or of an inexistent fragment/source
    dropped_testimony: int = 0  # testimony refused as evidence (T9)
    dropped_later: int = 0  # web sources after the reference date refused as prior art (T3)
    evidences_without_source: int = 0
    incoherent: int = 0  # criteria left in conflict with their score (coherence gate)
    flagged_speculative: int = 0  # justifications marked speculative (spec 09)
    files_by_agent: int = 0  # files the extraction agent had to map (the rest: deterministic, spec 05)


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
    files_by_agent_share: float | None = None  # extraction: files mapped by the agent / total
    positive_share: float | None = None
    rule_coverage: float | None = None  # executed with evidence / rules run
    gate_drop_rate: float | None = None  # dropped / (dropped + accepted)
    web_search_error_rate: float | None = None
    web_search_error_rate_by_base: dict[str, float | None] = Field(default_factory=dict)  # openalex, patentes, web
    web_searches_reused: int = 0
    web_queries_ungrounded: int = 0
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
    web_retries: int = 0


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


class ModelMetrics(CamelModel):
    calls: int = 0
    failures: int = 0
    retries: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_s: Distribution = Field(default_factory=Distribution)
    roles: dict[str, int] = Field(default_factory=dict)
    stages: dict[str, int] = Field(default_factory=dict)
    cost: float | None = None  # with MODEL_PRICES only; never invented


class CostMetrics(CamelModel):
    priced_models: list[str] = Field(default_factory=list)
    unpriced_models: list[str] = Field(default_factory=list)
    total: float | None = None
    per_run: Distribution = Field(default_factory=Distribution)
    unit: str = "USD por milhão de tokens (MODEL_PRICES)"


class ManualComparison(CamelModel):
    manual_minutes: float
    source: str
    median_minutes: float | None = None
    p95_minutes: float | None = None
    reduction: float | None = None  # 1 - median / manual


class CoverageMetrics(CamelModel):
    active_rules: int = 0  # in the catalog
    executed_per_run: Distribution = Field(default_factory=Distribution)
    na_per_run: Distribution = Field(default_factory=Distribution)
    partial_per_run: Distribution = Field(default_factory=Distribution)
    with_state: float | None = None  # criteria with a suggested state / criteria


class DefensibilityMetrics(CamelModel):
    evidences: int = 0
    with_source: float | None = None  # must be 1.0
    invented_citations_refused: int = 0
    testimony_refused: int = 0
    later_sources_separated: int = 0
    divergences_recorded: int = 0
    queries_sanitized_terms_removed: int = 0
    queries_ungrounded_dropped: int = 0
    evidences_neutralized: int = 0
    speculative_flagged: int = 0
    criteria_incoherent: int = 0


class CompletenessMetrics(CamelModel):
    with_caveats: int = 0
    with_caveats_complete: float | None = None
    insufficient: int = 0
    insufficient_with_missing_link: float | None = None


class SafetyMetrics(CamelModel):
    false_eligible: int = 0
    false_not_eligible: int = 0
    no_class_rate: float | None = None


class BenchmarkMetrics(CamelModel):
    accuracy: dict[str, AccuracyMetrics] = Field(default_factory=dict)  # "oficial" / "preliminar"
    timing: TimingMetrics = Field(default_factory=TimingMetrics)
    reliability: ReliabilityMetrics = Field(default_factory=ReliabilityMetrics)
    evidence: EvidenceMetrics = Field(default_factory=EvidenceMetrics)
    usage: UsageMetrics = Field(default_factory=UsageMetrics)
    determinism: DeterminismMetrics | None = None
    coherence: CoherenceMetrics = Field(default_factory=CoherenceMetrics)
    by_model: dict[str, ModelMetrics] = Field(default_factory=dict)
    by_stage: dict[str, ModelMetrics] = Field(default_factory=dict)
    cost: CostMetrics = Field(default_factory=CostMetrics)
    time_vs_manual: ManualComparison | None = None
    coverage: CoverageMetrics = Field(default_factory=CoverageMetrics)
    defensibility: DefensibilityMetrics = Field(default_factory=DefensibilityMetrics)
    completeness: CompletenessMetrics = Field(default_factory=CompletenessMetrics)
    safety: SafetyMetrics = Field(default_factory=SafetyMetrics)
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
