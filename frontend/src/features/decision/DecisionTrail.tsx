import type { ReactNode } from "react";
import { Tag } from "@/components/ui/Tag";
import { FRAMEWORKS } from "@/domain/frameworks";
import {
  CONTESTATION_REASON_LABELS,
  DECISION_OUTCOME_LABELS,
  DECISION_OUTCOME_TONES,
} from "@/domain/labels";
import { RULE_RATING } from "@/domain/qualitative";
import { indexAnalysis } from "@/domain/tree";
import type { AnalysisIndex } from "@/domain/tree";
import type {
  Analysis,
  Contestation,
  Decision,
  EvidenceReview,
  RuleDecision,
} from "@/domain/types";
import { formatDateTime } from "@/lib/format";

interface DecisionTrailProps {
  decisions: Decision[];
  contestations: Contestation[];
  ruleDecisions: RuleDecision[];
  evidenceReviews: EvidenceReview[];
  /** Every analysis of the project (one per method) */
  analyses: Analysis[];
  /** Files the analyses read ("14 arquivos lidos") */
  filesRead: number;
}

/** Analysis + its index, to resolve node numbers in any method */
type AnalysisLookup = Map<string, { analysis: Analysis; index: AnalysisIndex }>;

type TrailEvent =
  | { kind: "decision"; at: string; decision: Decision }
  | { kind: "contestation"; at: string; contestation: Contestation }
  | { kind: "reanalysis"; at: string; contestation: Contestation }
  | { kind: "rule"; at: string; rating: RuleDecision }
  | { kind: "evidence"; at: string; review: EvidenceReview }
  | { kind: "analysis"; at: string; analysis: Analysis };

/**
 * Who decided, rated, triaged or contested what, when, and based on what: the
 * core of a defensible trail. Newest first; nothing is ever overwritten.
 */
export const DecisionTrail = ({
  decisions,
  contestations,
  ruleDecisions,
  evidenceReviews,
  analyses,
  filesRead,
}: DecisionTrailProps) => {
  const lookup: AnalysisLookup = new Map(
    analyses.map((analysis) => [analysis.id, { analysis, index: indexAnalysis(analysis) }]),
  );
  const events: TrailEvent[] = [
    ...decisions.map((decision) => ({ kind: "decision" as const, at: decision.decidedAt, decision })),
    ...contestations.map((contestation) => ({
      kind: "contestation" as const,
      at: contestation.createdAt,
      contestation,
    })),
    ...contestations
      .filter((c) => c.resolution)
      .map((contestation) => ({
        kind: "reanalysis" as const,
        at: contestation.resolution!.resolvedAt,
        contestation,
      })),
    ...ruleDecisions.map((rating) => ({ kind: "rule" as const, at: rating.createdAt, rating })),
    ...evidenceReviews.map((review) => ({ kind: "evidence" as const, at: review.createdAt, review })),
    ...analyses.map((analysis) => ({ kind: "analysis" as const, at: analysis.generatedAt, analysis })),
  ].sort((a, b) => b.at.localeCompare(a.at));
  const currentDecision = events.find((e) => e.kind === "decision");

  return (
    <ol className="flex flex-col">
      {!currentDecision && (
        <li className="relative flex gap-3 pb-5 break-inside-avoid">
          <TimelineLine />
          <Dot variant="empty" />
          <Body
            kind="Nenhuma decisão registrada"
            meta="Cada decisão entra aqui com autor, data, versão dos critérios e justificativa. Decisões anteriores nunca são editadas."
          />
        </li>
      )}
      {events.map((event, i) => (
        <li key={`${event.kind}-${event.at}-${i}`} className="relative flex gap-3 pb-5 break-inside-avoid last:pb-0">
          {i < events.length - 1 && <TimelineLine />}
          <Entry event={event} lookup={lookup} current={event === currentDecision} filesRead={filesRead} />
        </li>
      ))}
    </ol>
  );
};

/** Line between markers */
const TimelineLine = () => <span aria-hidden className="absolute top-3 bottom-0 left-[5px] w-px bg-border-strong" />;

/** "1.4 O novo é o conhecimento" with the current number, or the snapshot */
const nodeName = (lookup: AnalysisLookup, analysisId: string, nodeId: string, snapshot: string) => {
  const entry = lookup.get(analysisId);
  const node = entry?.index.get(nodeId);
  const method = entry && lookup.size > 1 ? `${FRAMEWORKS[entry.analysis.framework].label} · ` : "";
  return `${method}${node ? `${node.number} ` : ""}${snapshot.replace(/^[\d.]+ /, "")}`;
};

const DOT_STYLES = {
  system: "bg-brand-deep",
  decision: "bg-action",
  review: "bg-fg-faint",
  empty: "border border-dashed border-fg-faint bg-surface",
};

/** Timeline marker, as in the design: filled for what happened, dashed for what is missing */
const Dot = ({ variant }: { variant: keyof typeof DOT_STYLES }) => (
  <span aria-hidden className={`relative z-10 mt-1.5 size-[11px] shrink-0 rounded-full ${DOT_STYLES[variant]}`} />
);

const Body = ({
  kind,
  title,
  meta,
  children,
}: {
  kind: string;
  title?: ReactNode;
  meta: ReactNode;
  children?: ReactNode;
}) => (
  <div className="flex min-w-0 flex-1 flex-col gap-1 text-sm leading-5">
    <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
      <span className="text-base leading-6 font-semibold">{kind}</span>
      {title}
    </p>
    <p className="text-sm leading-5 text-fg-muted">{meta}</p>
    {children}
  </div>
);

const Entry = ({
  event,
  lookup,
  current,
  filesRead,
}: {
  event: TrailEvent;
  lookup: AnalysisLookup;
  current: boolean;
  filesRead: number;
}) => {
  if (event.kind === "analysis") {
    const { analysis } = event;
    return (
      <>
        <Dot variant="system" />
        <Body
          kind="Análise gerada pelo sistema"
          meta={
            <>
              {analysis.id} · {FRAMEWORKS[analysis.framework].version} ·{" "}
              {filesRead} {filesRead === 1 ? "arquivo lido" : "arquivos lidos"} · {formatDateTime(analysis.generatedAt)}
            </>
          }
        />
      </>
    );
  }

  if (event.kind === "decision") {
    const { decision } = event;
    const basedOn = decision.analysisIds ?? [decision.analysisId];
    return (
      <>
        <Dot variant="decision" />
        <Body
          kind="Decisão"
          title={
            <>
              <Tag
                tone={DECISION_OUTCOME_TONES[decision.outcome]}
                label={DECISION_OUTCOME_LABELS[decision.outcome]}
                size="sm"
              />
              {current && <span className="btn-chip px-2.5 py-0.5 text-[11px]">decisão vigente</span>}
            </>
          }
          meta={
            <>
              {decision.analystName} · {formatDateTime(decision.decidedAt)} · com base{" "}
              {basedOn.length > 1 ? "nas análises" : "na análise"}{" "}
              {basedOn.map((id, i) => {
                const entry = lookup.get(id);
                return (
                  <span key={id}>
                    {i > 0 && ", "}
                    {entry && `${FRAMEWORKS[entry.analysis.framework].label} `}
                    <span className="font-mono">{id}</span>
                    {entry && ` (gerada em ${formatDateTime(entry.analysis.generatedAt)})`}
                  </span>
                );
              })}
            </>
          }
        >
          <p className="whitespace-pre-line">{decision.justification}</p>
          {decision.ruleOverrides && decision.ruleOverrides.length > 0 && (
            <ul className="mt-1 list-disc pl-5">
              {decision.ruleOverrides.map((override) => {
                const entry = lookup.get(override.analysisId ?? decision.analysisId);
                const node = entry?.index.get(override.ruleId);
                const label = node?.kind === "rule" ? `${node.number} ${node.rule.code}` : override.ruleId;
                return (
                  <li key={override.ruleId + override.note}>
                    <strong className="font-semibold">Ressalva {label}:</strong> {override.note}
                  </li>
                );
              })}
            </ul>
          )}
        </Body>
      </>
    );
  }

  if (event.kind === "rule") {
    const { rating } = event;
    const info = RULE_RATING[rating.rating];
    return (
      <>
        <Dot variant="review" />
        <Body
          kind="Nota da regra"
          title={
            <>
              <strong className="font-semibold">
                {nodeName(lookup, rating.analysisId, rating.nodeId, rating.nodeLabel)}
              </strong>
              <Tag tone={info.tone} label={info.label} size="sm" />
            </>
          }
          meta={
            <>
              {rating.author} · {formatDateTime(rating.createdAt)}
              {rating.suggested &&
                ` · sugestão do sistema: ${RULE_RATING[rating.suggested].label.toLowerCase()}`}
            </>
          }
        >
          <p className="whitespace-pre-line">{rating.justification}</p>
        </Body>
      </>
    );
  }

  if (event.kind === "evidence") {
    const { review } = event;
    const confirmed = review.verdict === "confirmed";
    return (
      <>
        <Dot variant="review" />
        <Body
          kind={confirmed ? "Evidência confirmada" : "Evidência descartada"}
          title={
            <strong className="font-semibold">
              {nodeName(lookup, review.analysisId, review.nodeId, review.nodeLabel)}
            </strong>
          }
          meta={`${review.author} · ${formatDateTime(review.createdAt)}`}
        >
          {review.note && <p>“{review.note}”</p>}
        </Body>
      </>
    );
  }

  const { contestation } = event;
  const name = nodeName(lookup, contestation.analysisId, contestation.nodeId, contestation.nodeLabel);

  if (event.kind === "reanalysis") {
    const resolution = contestation.resolution!;
    return (
      <>
        <Dot variant="system" />
        <Body
          kind="Reanálise do modelo"
          title={
            <>
              <strong className="font-semibold">{name}</strong>
              <Tag
                tone={resolution.verdict === "accepted" ? "positive" : "neutral"}
                label={resolution.verdict === "accepted" ? "Contestação acatada" : "Leitura mantida"}
                size="sm"
              />
            </>
          }
          meta={formatDateTime(resolution.resolvedAt)}
        >
          <p>{resolution.explanation}</p>
        </Body>
      </>
    );
  }

  return (
    <>
      <Dot variant="review" />
      <Body
        kind="Contestação"
        title={
          <>
            <strong className="font-semibold">{name}</strong>
            <span className="text-fg-muted">· {CONTESTATION_REASON_LABELS[contestation.reason]}</span>
            <Tag
              tone={contestation.status === "open" ? "attention" : "neutral"}
              label={contestation.status === "open" ? "Aberta, aguardando reanálise" : "Resolvida"}
              size="sm"
            />
          </>
        }
        meta={
          <>
            {contestation.author} · {formatDateTime(contestation.createdAt)}
            {contestation.suggestedScore !== undefined && ` · nota sugerida: ${contestation.suggestedScore}`}
            {contestation.suggestedPolarity &&
              ` · polaridade sugerida: ${contestation.suggestedPolarity === "positive" ? "positiva" : "negativa"}`}
          </>
        }
      >
        <p className="whitespace-pre-line">{contestation.argument}</p>
      </Body>
    </>
  );
};
