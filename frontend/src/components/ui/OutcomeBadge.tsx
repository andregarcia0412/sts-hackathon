import { CircleCheckBig, CircleHelp, CircleX } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { DECISION_OUTCOME_LABELS } from "@/domain/labels";
import type { DecisionOutcome } from "@/domain/types";

const STYLES: Record<DecisionOutcome, { Icon: LucideIcon; className: string }> = {
  eligible: { Icon: CircleCheckBig, className: "text-score-strong" },
  not_eligible: { Icon: CircleX, className: "text-danger" },
  needs_review: { Icon: CircleHelp, className: "text-score-moderate" },
};

/** The analyst's decision (never an automatic verdict): icon + label */
export const OutcomeBadge = ({ outcome }: { outcome: DecisionOutcome }) => {
  const { Icon, className } = STYLES[outcome];
  return (
    <span className="inline-flex items-center gap-1 text-sm font-medium whitespace-nowrap">
      <Icon className={`size-4 shrink-0 ${className}`} aria-hidden />
      {DECISION_OUTCOME_LABELS[outcome]}
    </span>
  );
};
