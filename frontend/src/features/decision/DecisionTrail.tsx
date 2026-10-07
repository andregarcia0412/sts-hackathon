import { History } from "lucide-react";
import { DECISION_OUTCOME_LABELS } from "@/domain/labels";
import type { AnalysisIndex } from "@/domain/tree";
import type { Analysis, Decision } from "@/domain/types";
import { formatDateTime } from "@/lib/format";

interface DecisionTrailProps {
  decisions: Decision[];
  analysis: Analysis;
  index: AnalysisIndex;
}

/**
 * Who decided, when, and based on what (rule DOC-13): the core of a
 * defensible trail. Newest first; nothing is ever overwritten.
 */
export const DecisionTrail = ({ decisions, analysis, index }: DecisionTrailProps) => {
  if (decisions.length === 0) {
    return (
      <p className="font-sans text-sm text-fg-muted">
        Nenhuma decisão registrada ainda.
      </p>
    );
  }

  return (
    <ol className="space-y-4">
      {[...decisions].reverse().map((decision, i) => (
        <li
          key={decision.decidedAt}
          className="relative space-y-2 border-l-2 border-border-strong pb-1 pl-5 break-inside-avoid"
        >
          <History
            className="absolute top-0.5 -left-[9px] size-4 bg-canvas text-fg-muted print:bg-white"
            aria-hidden
          />
          <p className="font-sans text-sm">
            <strong>{DECISION_OUTCOME_LABELS[decision.outcome]}</strong>
            {i === 0 && (
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
              <p className="text-xs font-semibold text-fg-muted uppercase">
                Ressalvas do analista
              </p>
              <ul className="mt-1 list-disc space-y-0.5 pl-5">
                {decision.ruleOverrides.map((override) => {
                  const node = index.get(override.ruleId);
                  const label =
                    node?.kind === "rule"
                      ? `${node.number} ${node.rule.code}`
                      : override.ruleId;
                  return (
                    <li key={override.ruleId + override.note}>
                      <strong>{label}:</strong> {override.note}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </li>
      ))}
    </ol>
  );
};
