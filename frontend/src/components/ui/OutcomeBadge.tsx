import { Tag } from "@/components/ui/Tag";
import { DECISION_OUTCOME_LABELS, DECISION_OUTCOME_TONES } from "@/domain/labels";
import type { DecisionOutcome } from "@/domain/types";

/** The analyst's decision (never an automatic verdict): icon + label */
export const OutcomeBadge = ({ outcome, size = "sm" }: { outcome: DecisionOutcome; size?: "sm" | "md" }) => (
  <Tag tone={DECISION_OUTCOME_TONES[outcome]} label={DECISION_OUTCOME_LABELS[outcome]} size={size} />
);
