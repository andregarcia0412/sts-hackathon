import { scoreBand } from "@/domain/score";
import type { ScoreBand } from "@/domain/score";
import type { Criterion, EvidencePolarity, Rule, RuleRating } from "@/domain/types";

/*
 * Qualitative reading of the scores, as shown by the high-fidelity design
 * ("Sustentado", "Parcialmente", "Contraditório"...). The 0–100 score is still
 * the source: these labels are derived from it and from the evidences, and the
 * number stays visible in the detail panel. Names are provisional (the team
 * will review them): change them here and the whole UI follows.
 */

/** Visual tone of an "Etiqueta": always icon + text, color is never the only signal */
export type Tone = "positive" | "attention" | "negative" | "neutral";

export type RuleStatus =
  | "sustained"
  | "partial"
  | "contradictory"
  | "not_sustained"
  | "no_evidence";

export type CriterionStatus = "demonstrated" | "limited" | "not_demonstrated";

/**
 * Positive and negative evidences of comparable weight: the system does not
 * pick a side, the analyst does (the smaller side ≥ this share of the larger).
 */
const CONTRADICTION_RATIO = 0.5;

const evidenceWeights = (rule: Rule) => {
  const factors = rule.scoreExplanation?.factors.filter((f) => f.kind === "evidence");
  if (factors?.length) {
    return {
      positive: factors.filter((f) => f.points > 0).reduce((sum, f) => sum + f.points, 0),
      negative: -factors.filter((f) => f.points < 0).reduce((sum, f) => sum + f.points, 0),
    };
  }
  // No explanation: every evidence weighs the same
  return {
    positive: rule.evidences.filter((e) => e.polarity === "positive").length,
    negative: rule.evidences.filter((e) => e.polarity === "negative").length,
  };
};

export const ruleStatus = (rule: Rule): RuleStatus => {
  if (rule.evidences.length === 0) return "no_evidence";
  const band = scoreBand(rule.score);
  if (band === "strong") return "sustained";
  const { positive, negative } = evidenceWeights(rule);
  if (
    positive > 0 &&
    negative > 0 &&
    Math.min(positive, negative) / Math.max(positive, negative) >= CONTRADICTION_RATIO
  ) {
    return "contradictory";
  }
  return band === "moderate" ? "partial" : "not_sustained";
};

/** Criterion reading of each score band (also used by the project list filter) */
export const BAND_CRITERION_STATUS: Record<ScoreBand, CriterionStatus> = {
  strong: "demonstrated",
  moderate: "limited",
  weak: "not_demonstrated",
};

export const criterionStatus = (criterion: Pick<Criterion, "score">): CriterionStatus =>
  BAND_CRITERION_STATUS[scoreBand(criterion.score)];

interface StatusInfo {
  label: string;
  /** Compact label for the graph cards */
  short: string;
  tone: Tone;
}

export const RULE_STATUS: Record<RuleStatus, StatusInfo> = {
  sustained: { label: "Sustentado", short: "Sustentado", tone: "positive" },
  partial: { label: "Parcialmente sustentado", short: "Parcialmente", tone: "attention" },
  contradictory: { label: "Contraditório", short: "Contraditório", tone: "attention" },
  not_sustained: { label: "Não sustentado", short: "Não sustentado", tone: "negative" },
  no_evidence: { label: "Sem evidência", short: "Sem evidência", tone: "neutral" },
};

export const CRITERION_STATUS: Record<CriterionStatus, StatusInfo> = {
  demonstrated: { label: "Demonstrado", short: "Demonstrado", tone: "positive" },
  limited: { label: "Demonstrado com limite", short: "Com limite", tone: "attention" },
  not_demonstrated: { label: "Não demonstrado", short: "Não demonstrado", tone: "negative" },
};

export const POLARITY_STATUS: Record<EvidencePolarity, StatusInfo> = {
  positive: { label: "Positiva", short: "Positiva", tone: "positive" },
  negative: { label: "Negativa", short: "Negativa", tone: "negative" },
};

/* Analyst's reading of a rule ("Nota da regra"), in the order it is offered */
export const RULE_RATINGS: RuleRating[] = [
  "sustained",
  "partial",
  "contradictory",
  "not_sustained",
  "needs_expert",
];

export const RULE_RATING: Record<RuleRating, StatusInfo> = {
  sustained: RULE_STATUS.sustained,
  partial: RULE_STATUS.partial,
  contradictory: RULE_STATUS.contradictory,
  not_sustained: RULE_STATUS.not_sustained,
  needs_expert: { label: "Necessita especialista", short: "Especialista", tone: "attention" },
};

/** The system's suggestion as a starting point for the analyst (none when there is no evidence) */
export const suggestedRating = (status: RuleStatus): RuleRating | undefined =>
  status === "no_evidence" ? undefined : status;
