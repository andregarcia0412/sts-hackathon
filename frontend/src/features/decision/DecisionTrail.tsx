import { Flag, History } from "lucide-react";
import { CONTESTATION_REASON_LABELS, DECISION_OUTCOME_LABELS } from "@/domain/labels";
import type { AnalysisIndex } from "@/domain/tree";
import type { Analysis, Contestation, Decision } from "@/domain/types";
import { formatDateTime } from "@/lib/format";

interface DecisionTrailProps {
  decisions: Decision[];
  contestations: Contestation[];
  analysis: Analysis;
  index: AnalysisIndex;
}

type TrailEvent =
  | { kind: "decision"; at: string; decision: Decision }
  | { kind: "contestation"; at: string; contestation: Contestation };

/**
 * Who decided or contested what, when, and based on what (rule DOC-13): the
 * core of a defensible trail. Newest first; nothing is ever overwritten.
 */
export const DecisionTrail = ({
  decisions,
  contestations,
  analysis,
  index,
}: DecisionTrailProps) => {
  const events: TrailEvent[] = [
    ...decisions.map((decision) => ({ kind: "decision" as const, at: decision.decidedAt, decision })),
    ...contestations.map((contestation) => ({
      kind: "contestation" as const,
      at: contestation.createdAt,
      contestation,
    })),
  ].sort((a, b) => b.at.localeCompare(a.at));
  const currentDecision = events.find((e) => e.kind === "decision");

  if (events.length === 0) {
    return (
      <p className="font-sans text-sm text-fg-muted">
        Nenhuma decisão ou contestação registrada ainda.
      </p>
    );
  }

  return (
    <ol className="space-y-4">
      {events.map((event) => (
        <li
          key={`${event.kind}-${event.at}`}
          className="relative space-y-2 border-l-2 border-border-strong pb-1 pl-5 break-inside-avoid"
        >
          {event.kind === "decision" ? (
            <DecisionEntry
              decision={event.decision}
              analysis={analysis}
              index={index}
              current={event === currentDecision}
            />
          ) : (
            <ContestationEntry contestation={event.contestation} index={index} />
          )}
        </li>
      ))}
    </ol>
  );
};

const markerClass = "absolute top-0.5 -left-[9px] size-4 bg-canvas print:bg-white";

const DecisionEntry = ({
  decision,
  analysis,
  index,
  current,
}: {
  decision: Decision;
  analysis: Analysis;
  index: AnalysisIndex;
  current: boolean;
}) => (
  <>
    <History className={`${markerClass} text-fg-muted`} aria-hidden />
    <p className="font-sans text-sm">
      <span className="text-xs text-fg-muted uppercase">Decisão · </span>
      <strong>{DECISION_OUTCOME_LABELS[decision.outcome]}</strong>
      {current && (
        <span className="ml-2 rounded-full bg-accent-soft px-2 py-0.5 text-xs text-accent">
          decisão vigente
        </span>
      )}
    </p>
    <p className="font-sans text-xs text-fg-muted">
      {decision.analystName} · {formatDateTime(decision.decidedAt)} · com base na análise{" "}
      <span className="font-mono">{decision.analysisId}</span>
      {decision.analysisId === analysis.id &&
        ` (gerada em ${formatDateTime(analysis.generatedAt)})`}
    </p>
    <p className="whitespace-pre-line">{decision.justification}</p>
    {decision.ruleOverrides && decision.ruleOverrides.length > 0 && (
      <div className="font-sans text-sm">
        <p className="text-xs font-semibold text-fg-muted uppercase">Ressalvas do analista</p>
        <ul className="mt-1 list-disc space-y-0.5 pl-5">
          {decision.ruleOverrides.map((override) => {
            const node = index.get(override.ruleId);
            const label =
              node?.kind === "rule" ? `${node.number} ${node.rule.code}` : override.ruleId;
            return (
              <li key={override.ruleId + override.note}>
                <strong>{label}:</strong> {override.note}
              </li>
            );
          })}
        </ul>
      </div>
    )}
  </>
);

const ContestationEntry = ({
  contestation,
  index,
}: {
  contestation: Contestation;
  index: AnalysisIndex;
}) => {
  // Current number if the node still exists; the recorded snapshot otherwise
  const node = index.get(contestation.nodeId);
  return (
    <>
      <Flag className={`${markerClass} text-score-moderate`} aria-hidden />
      <p className="font-sans text-sm">
        <span className="text-xs text-fg-muted uppercase">Contestação · </span>
        <strong>{node ? `${node.number} ` : ""}{contestation.nodeLabel.replace(/^[\d.]+ /, "")}</strong>
        {" · "}
        {CONTESTATION_REASON_LABELS[contestation.reason]}
      </p>
      <p className="font-sans text-xs text-fg-muted">
        {contestation.author} · {formatDateTime(contestation.createdAt)}
        {contestation.suggestedScore !== undefined && ` · nota sugerida: ${contestation.suggestedScore}`}
        {contestation.suggestedPolarity &&
          ` · polaridade sugerida: ${contestation.suggestedPolarity === "positive" ? "positiva" : "negativa"}`}
      </p>
      <p className="whitespace-pre-line">{contestation.argument}</p>
    </>
  );
};
