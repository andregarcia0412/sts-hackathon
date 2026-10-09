"""Benchmark metrics: pure functions over run snapshots and the expected cases (no I/O)."""

import math
import re
import statistics
from collections import defaultdict
from collections.abc import Iterable

from backend.benchmark.models import (
    AccuracyMetrics,
    BenchmarkMetrics,
    CoherenceMetrics,
    ClassScores,
    DeterminismMetrics,
    Distribution,
    DivergenceSnapshot,
    EvidenceMetrics,
    ReliabilityMetrics,
    RunSnapshot,
    TimingMetrics,
    UsageMetrics,
)
from backend.benchmark.reference import ExpectedCase, PlantedDivergence
from backend.catalog.models import CRITERIA_ORDER, Catalog
from backend.graph.classify import CLASS_LABELS
from backend.graph.states import column_of
from backend.llm.usage import RoleUsage

CLASSES = tuple(CLASS_LABELS)
NO_CLASS = "(sem classe)"
FAVOURABLE = {"eligible", "eligible_with_caveats"}
UNFAVOURABLE = {"not_eligible", "insufficient_evidence"}
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def _rate(part: float, whole: float) -> float | None:
    return round(part / whole, 4) if whole else None


def distribution(values: Iterable[float | None]) -> Distribution:
    data = sorted(v for v in values if v is not None)
    if not data:
        return Distribution()
    p95 = data[max(0, math.ceil(0.95 * len(data)) - 1)]  # nearest rank
    return Distribution(mean=round(statistics.fmean(data), 3), median=round(statistics.median(data), 3),
                        p95=round(p95, 3), max=round(data[-1], 3), n=len(data))


def _label(cls: str | None) -> str:
    return CLASS_LABELS.get(cls or "", NO_CLASS)


# ---------------------------------------------------------------- planted divergences


def _numbers(text: str) -> set[str]:
    return {_normal_number(n) for n in NUMBER.findall(text)}


def _normal_number(token: str) -> str:
    token = token.replace(",", ".")
    return token.rstrip("0").rstrip(".") if "." in token else token


def _token_in(token: str, text: str) -> bool:
    """A number matches as a number (412 ≠ 4120; 1,20 = 1.2); words match as a case-insensitive substring."""
    parts = [p for p in token.split("/") if p]
    if parts and all(NUMBER.fullmatch(p) for p in parts):
        return all(_normal_number(p) in _numbers(text) for p in parts)
    return token.casefold() in text.casefold()


def divergence_found(planted: PlantedDivergence, divergences: list[DivergenceSnapshot]) -> bool:
    for d in divergences:
        testimony, record = f"{d.testimony_quote} {d.statement}", f"{d.record_quote} {d.statement}"
        if (not planted.testimony or _token_in(planted.testimony, testimony)) and \
                (not planted.record or _token_in(planted.record, record)):
            return True
    return False


# ---------------------------------------------------------------- accuracy


def accuracy(runs: list[RunSnapshot], expected: dict[str, ExpectedCase], reference: str,
             catalog: Catalog) -> AccuracyMetrics:
    pairs = [(run, expected[run.code]) for run in runs
             if run.code in expected and expected[run.code].source == reference]
    metrics = AccuracyMetrics(reference=reference, n=len(pairs))
    if not pairs:
        return metrics
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    expected_counts: dict[str, int] = defaultdict(int)
    predicted_counts: dict[str, int] = defaultdict(int)
    state_hits: dict[str, list[bool]] = defaultdict(list)
    column_hits: dict[str, list[bool]] = defaultdict(list)
    for run, case in pairs:
        want, got = case.expected_class, run.suggested_class
        confusion[_label(want)][_label(got)] += 1
        expected_counts[want or NO_CLASS] += 1
        predicted_counts[got or NO_CLASS] += 1
        if want == got and want is not None:
            metrics.class_hits += 1
        else:
            suffix = f"#{run.repeat}" if run.repeat > 1 else ""
            metrics.misses.append(f"{run.code}{suffix}: {_label(want)} → {_label(got)}")
        metrics.false_eligible += got in FAVOURABLE and want in UNFAVOURABLE
        metrics.false_not_eligible += got in UNFAVOURABLE and want in FAVOURABLE
        for criterion, state in case.states.items():
            if state is None:
                continue
            state_hits[criterion].append(run.states.get(criterion) == state)
            column_hits[criterion].append(run.columns.get(criterion) == column_of(criterion, state, catalog))
        for planted in case.planted_divergences:
            metrics.planted_divergences += 1
            metrics.planted_divergences_found += divergence_found(planted, run.divergences)

    n = len(pairs)
    metrics.class_accuracy = _rate(metrics.class_hits, n)
    metrics.confusion = {k: dict(v) for k, v in confusion.items()}
    f1s = []
    for cls in CLASSES:
        tp = sum(1 for run, case in pairs if run.suggested_class == cls and case.expected_class == cls)
        predicted, support = predicted_counts.get(cls, 0), expected_counts.get(cls, 0)
        if not predicted and not support:
            continue
        precision, recall = _rate(tp, predicted), _rate(tp, support)
        f1 = round(2 * precision * recall / (precision + recall), 4) if precision and recall else 0.0
        metrics.per_class[CLASS_LABELS[cls]] = ClassScores(precision=precision, recall=recall, f1=f1, support=support)
        f1s.append(f1)
    metrics.macro_f1 = round(statistics.fmean(f1s), 4) if f1s else None
    chance = sum(expected_counts.get(c, 0) * predicted_counts.get(c, 0) for c in (*CLASSES, NO_CLASS)) / (n * n)
    observed = metrics.class_hits / n
    metrics.cohen_kappa = round((observed - chance) / (1 - chance), 4) if chance < 1 else None
    metrics.state_accuracy = {c: _rate(sum(h), len(h)) for c, h in state_hits.items()}
    metrics.column_accuracy = {c: _rate(sum(h), len(h)) for c, h in column_hits.items()}
    metrics.planted_divergence_recall = _rate(metrics.planted_divergences_found, metrics.planted_divergences)
    return metrics


# ---------------------------------------------------------------- operation


def timing(runs: list[RunSnapshot]) -> TimingMetrics:
    stages: dict[str, list[float]] = defaultdict(list)
    for run in runs:
        for name, seconds in run.stage_seconds.items():
            stages[name].append(seconds)
    started = [r.started_at for r in runs if r.started_at]
    finished = [r.finished_at for r in runs if r.finished_at]
    wall = round((max(finished) - min(started)).total_seconds(), 3) if started and finished else None
    done = sum(1 for r in runs if r.finished_at)
    return TimingMetrics(
        total_s=distribution(r.total_s for r in runs),
        stages_s={name: distribution(values) for name, values in stages.items()},
        wall_clock_s=wall,
        projects_per_hour=round(done * 3600 / wall, 2) if wall else None,
    )


def reliability(runs: list[RunSnapshot]) -> ReliabilityMetrics:
    stage_failures: dict[str, int] = defaultdict(int)
    for run in runs:
        for name, status in run.stages.items():
            if status in ("falhou", "nao_executada"):
                stage_failures[name] += 1
    failed = sum(1 for r in runs if r.status != "concluida")
    return ReliabilityMetrics(
        runs=len(runs),
        failed=failed,
        failure_rate=_rate(failed, len(runs)),
        stage_failures=dict(stage_failures),
        rules_not_executed_rate=_rate(sum(r.rules_not_executed for r in runs), sum(r.rules_total for r in runs)),
        inconsistent_rate=_rate(sum(1 for r in runs if r.inconsistent), len(runs)),
        incomplete_rate=_rate(sum(1 for r in runs if r.incomplete), len(runs)),
        no_class_rate=_rate(sum(1 for r in runs if r.suggested_class is None), len(runs)),
    )


def evidence(runs: list[RunSnapshot]) -> EvidenceMetrics:
    positive = sum(r.evidences_positive for r in runs)
    accepted = positive + sum(r.evidences_negative for r in runs)
    dropped = sum(r.gate_dropped for r in runs)
    return EvidenceMetrics(
        evidences_per_run=distribution(r.evidences_positive + r.evidences_negative for r in runs),
        web_searches_reused=sum(r.web_searches_reused for r in runs),
        web_queries_ungrounded=sum(r.web_queries_ungrounded for r in runs),
        files_by_agent_share=_rate(sum(r.files_by_agent for r in runs), sum(r.files_total for r in runs)),
        positive_share=_rate(positive, accepted),
        rule_coverage=_rate(sum(r.rules_with_evidence for r in runs), sum(r.rules_total for r in runs)),
        gate_drop_rate=_rate(dropped, dropped + accepted),
        web_search_error_rate=_rate(sum(r.web_search_errors for r in runs), sum(r.web_searches for r in runs)),
        web_search_error_rate_by_base={
            base: _rate(sum(r.web_search_errors_by_base.get(base, 0) for r in runs),
                        sum(r.web_searches_by_base.get(base, 0) for r in runs))
            for base in sorted({b for r in runs for b in r.web_searches_by_base})},
        web_not_prior_art_share=_rate(sum(r.web_not_prior_art for r in runs), sum(r.web_sources for r in runs)),
        sanitized_terms_removed=sum(r.sanitized_terms_removed for r in runs),
        divergences_per_run=distribution(len(r.divergences) for r in runs),
        missing_links_per_run=distribution(r.missing_links for r in runs),
    )


def usage(runs: list[RunSnapshot]) -> UsageMetrics:
    metrics = UsageMetrics()
    for run in runs:
        if run.usage is None:
            continue
        for role, role_usage in run.usage.roles.items():
            metrics.roles.setdefault(role, RoleUsage()).add(role_usage)
        metrics.total.add(run.usage.total())
        metrics.web_search_calls += run.usage.web_search_calls
        metrics.web_fetch_calls += run.usage.web_fetch_calls
        metrics.web_retries += run.usage.web_retries
    measured = [r.usage.total() for r in runs if r.usage is not None]
    metrics.tokens_per_run = distribution(u.prompt_tokens + u.completion_tokens for u in measured)
    metrics.calls_per_run = distribution(u.calls for u in measured)
    return metrics


def determinism(runs: list[RunSnapshot]) -> DeterminismMetrics | None:
    groups: dict[tuple[str, str], list[RunSnapshot]] = defaultdict(list)
    for run in runs:
        groups[(run.set, run.code)].append(run)
    repeated = {key: group for key, group in groups.items() if len(group) > 1}
    if not repeated:
        return None
    metrics = DeterminismMetrics(projects=len(repeated))
    class_same, jaccards = [], []
    state_same: dict[str, list[bool]] = defaultdict(list)
    score_std: dict[str, list[float]] = defaultdict(list)
    for (_, code), group in sorted(repeated.items()):
        same_class = len({r.suggested_class for r in group}) == 1
        class_same.append(same_class)
        if not same_class:
            metrics.unstable.append(f"{code}: " + " / ".join(_label(r.suggested_class) for r in group))
        for criterion in CRITERIA_ORDER:
            state_same[criterion].append(len({r.states.get(criterion) for r in group}) == 1)
            scores = [r.criterion_scores.get(criterion) for r in group]
            if all(s is not None for s in scores):
                score_std[criterion].append(statistics.pstdev(scores))
        sets = [set(r.evidence_ids) for r in group]
        union = set().union(*sets)
        jaccards.append(len(set.intersection(*sets)) / len(union) if union else 1.0)
    metrics.class_agreement = _rate(sum(class_same), len(class_same))
    metrics.state_agreement = {c: _rate(sum(v), len(v)) for c, v in state_same.items()}
    metrics.score_std = {c: round(statistics.fmean(v), 3) if v else None for c, v in score_std.items()}
    metrics.evidence_jaccard = round(statistics.fmean(jaccards), 4)
    return metrics


def coherence(runs: list[RunSnapshot], expected: dict[str, ExpectedCase], catalog: Catalog) -> CoherenceMetrics:
    metrics = CoherenceMetrics()
    for run in runs:
        case = expected.get(run.code)
        for criterion, record in run.coherence.items():
            metrics.contradictions[criterion] = metrics.contradictions.get(criterion, 0) + 1
            metrics.by_source[record.original_source] = metrics.by_source.get(record.original_source, 0) + 1
            metrics.rejudged += record.rejudged
            metrics.resolved += record.status == "resolvida"
            metrics.incoherent += record.status == "incoerente"
            final = run.states.get(criterion)
            if final is None or final == record.original_state:
                continue
            if column_of(criterion, final, catalog) == column_of(criterion, record.original_state, catalog):
                continue
            metrics.changed_column += 1
            if case is not None and case.source == "oficial" and case.states.get(criterion):
                hit = case.states[criterion] == final
                metrics.changed_column_hits += hit
                metrics.changed_column_misses += not hit
    return metrics


def class_distribution(runs: list[RunSnapshot], expected: dict[str, ExpectedCase]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for run in runs:
        result["sugerida"][_label(run.suggested_class)] += 1
        if (case := expected.get(run.code)) is not None:
            result[case.source][_label(case.expected_class)] += 1
    return {k: dict(v) for k, v in result.items()}


def compute(runs: list[RunSnapshot], expected: dict[str, ExpectedCase], catalog: Catalog) -> BenchmarkMetrics:
    references = sorted({case.source for case in expected.values()})
    return BenchmarkMetrics(
        accuracy={ref: accuracy(runs, expected, ref, catalog) for ref in references},
        timing=timing(runs),
        reliability=reliability(runs),
        evidence=evidence(runs),
        usage=usage(runs),
        determinism=determinism(runs),
        coherence=coherence(runs, expected, catalog),
        class_distribution=class_distribution(runs, expected),
        by_set={s: timing([r for r in runs if r.set == s]) for s in sorted({r.set for r in runs})},
    )


# ---------------------------------------------------------------- comparison between two benchmarks


def headline(metrics: BenchmarkMetrics) -> dict[str, float | None]:
    """The few numbers worth tracking from one run to the next (model, prompt or catalog change)."""
    official, preliminary = metrics.accuracy.get("oficial"), metrics.accuracy.get("preliminar")
    return {
        "oficial.classAccuracy": official.class_accuracy if official else None,
        "oficial.macroF1": official.macro_f1 if official else None,
        "oficial.cohenKappa": official.cohen_kappa if official else None,
        "oficial.falseEligible": official.false_eligible if official else None,
        "preliminar.classAccuracy": preliminary.class_accuracy if preliminary else None,
        "preliminar.plantedDivergenceRecall": preliminary.planted_divergence_recall if preliminary else None,
        "timing.totalS.median": metrics.timing.total_s.median,
        "timing.totalS.p95": metrics.timing.total_s.p95,
        "usage.tokensPerRun.mean": metrics.usage.tokens_per_run.mean,
        "reliability.failureRate": metrics.reliability.failure_rate,
        "evidence.gateDropRate": metrics.evidence.gate_drop_rate,
        "evidence.ruleCoverage": metrics.evidence.rule_coverage,
        "determinism.classAgreement": metrics.determinism.class_agreement if metrics.determinism else None,
    }


def compare_metrics(base: BenchmarkMetrics, target: BenchmarkMetrics) -> dict[str, dict[str, float | None]]:
    old, new = headline(base), headline(target)
    return {key: {"base": old[key], "target": new[key],
                  "delta": round(new[key] - old[key], 4) if old[key] is not None and new[key] is not None else None}
            for key in old}
