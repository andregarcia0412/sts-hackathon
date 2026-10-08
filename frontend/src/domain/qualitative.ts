import { scoreBand } from "@/domain/score";
import type { ScoreBand } from "@/domain/score";
import type { Criterion, CriterionKey, EvidencePolarity, Rule, RuleRating } from "@/domain/types";

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

export type CriterionStatus = "met" | "limited" | "not_met";

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

/** Criterion reading of each score band */
export const BAND_CRITERION_STATUS: Record<ScoreBand, CriterionStatus> = {
  strong: "met",
  moderate: "limited",
  weak: "not_met",
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

const CRITERION_TONES: Record<CriterionStatus, Tone> = {
  met: "positive",
  limited: "attention",
  not_met: "negative",
};

/*
 * Each criterion is read with its own word, as in the design: Novidade is
 * "Demonstrada no recorte", Incerteza is "Investigada", Sistematização is
 * "Documentada"... Keyed by CriterionKey (Frascati and Formulário MCTI).
 */
const CRITERION_WORDS: Record<CriterionKey, Record<CriterionStatus, string>> = {
  // Frascati
  novelty: { met: "Demonstrada no recorte", limited: "Demonstrada com limite", not_met: "Não demonstrada" },
  creativity: { met: "Demonstrada no recorte", limited: "Demonstrada com limite", not_met: "Não demonstrada" },
  uncertainty: { met: "Investigada", limited: "Investigada com limite", not_met: "Não investigada" },
  systematic: { met: "Documentada", limited: "Documentada com limite", not_met: "Não documentada" },
  transferability: { met: "Documentada", limited: "Documentada com limite", not_met: "Não documentada" },
  // Formulário MCTI: same vocabulary as the design's Frascati criteria
  novel_element: { met: "Demonstrada no recorte", limited: "Demonstrada com limite", not_met: "Não demonstrada" },
  technological_barrier: { met: "Investigada", limited: "Investigada com limite", not_met: "Não investigada" },
  methodology: { met: "Documentada", limited: "Documentada com limite", not_met: "Não documentada" },
  description_scope: { met: "Documentada", limited: "Documentada com limite", not_met: "Não documentada" },
  schedule: { met: "Documentada", limited: "Documentada com limite", not_met: "Não documentada" },
};

/** Only for a criterion key this front-end does not know yet (new method from the back-end) */
const UNKNOWN_CRITERION_WORDS: Record<CriterionStatus, string> = {
  met: "Atendido",
  limited: "Atendido com limite",
  not_met: "Não atendido",
};

/** Label and tone of a criterion's reading; `short` is "Com limite" in compact places */
export const criterionStatusInfo = (criterion: Pick<Criterion, "key" | "score">): StatusInfo => {
  const status = criterionStatus(criterion);
  const label = (CRITERION_WORDS[criterion.key] ?? UNKNOWN_CRITERION_WORDS)[status];
  return { label, short: status === "limited" ? "Com limite" : label, tone: CRITERION_TONES[status] };
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
