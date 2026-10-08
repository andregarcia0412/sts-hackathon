import type {
  Analysis,
  Criterion,
  Rule,
  ScoreExplanation,
  ScoreFactor,
} from "@/domain/types";

/*
 * MOCK score explanations. The team has not defined the real calculation yet,
 * so these are illustrative and always add up exactly to the given score:
 *
 * - Rule: starts at 50 (neutral); positive evidences add points, negative
 *   evidences subtract them.
 * - Criterion: weighted average of its rules (weight = share of evidences),
 *   plus an adjustment when the model's score differs from the average.
 */

const RULE_BASELINE = 50;
const NEGATIVE_POINTS = 8;
const MIN_POSITIVE_POINTS = 3;

/** Split an integer total into `count` integer parts, remainder to the first ones */
const split = (total: number, count: number): number[] => {
  const base = Math.trunc(total / count);
  let remainder = total - base * count;
  return Array.from({ length: count }, () => {
    const step = Math.sign(remainder);
    remainder -= step;
    return base + step;
  });
};

export const explainRuleScore = (rule: Rule): ScoreExplanation => {
  const delta = rule.score - RULE_BASELINE;
  const positives = rule.evidences.filter((e) => e.polarity === "positive");
  const negatives = rule.evidences.filter((e) => e.polarity === "negative");

  let positiveTotal = 0;
  let negativeTotal = 0;
  if (positives.length && negatives.length) {
    positiveTotal = Math.max(delta + NEGATIVE_POINTS * negatives.length, MIN_POSITIVE_POINTS * positives.length);
    negativeTotal = Math.min(0, delta - positiveTotal);
  } else if (positives.length) {
    positiveTotal = Math.max(0, delta);
  } else if (negatives.length) {
    negativeTotal = Math.min(0, delta);
  }
  const adjustment = delta - positiveTotal - negativeTotal;

  const pointsById = new Map<string, number>();
  split(positiveTotal, positives.length || 1).forEach((p, i) => positives[i] && pointsById.set(positives[i].id, p));
  split(negativeTotal, negatives.length || 1).forEach((p, i) => negatives[i] && pointsById.set(negatives[i].id, p));

  const factors: ScoreFactor[] = rule.evidences.map((evidence) => ({
    kind: "evidence",
    refId: evidence.id,
    label: evidence.title,
    points: pointsById.get(evidence.id) ?? 0,
  }));
  if (adjustment !== 0) {
    factors.push({
      kind: "adjustment",
      label:
        adjustment < 0
          ? "Lacunas de informação no material"
          : "Contexto geral do projeto",
      points: adjustment,
    });
  }

  return {
    method:
      "Parte de 50 (neutro). Cada evidência positiva soma e cada negativa subtrai pontos, conforme o peso dela para a regra.",
    baseline: RULE_BASELINE,
    factors,
  };
};

export const explainCriterionScore = (criterion: Criterion): ScoreExplanation => {
  const totalEvidences = criterion.rules.reduce((sum, r) => sum + Math.max(1, r.evidences.length), 0);
  const factors: ScoreFactor[] = criterion.rules.map((rule) => {
    const weight = Math.max(1, rule.evidences.length) / totalEvidences;
    return {
      kind: "rule",
      refId: rule.id,
      label: `${rule.code} ${rule.name}`,
      value: rule.score,
      weight,
      points: Math.round(rule.score * weight * 10) / 10,
    };
  });

  const average = factors.reduce((sum, f) => sum + f.points, 0);
  const adjustment = Math.round((criterion.score - average) * 10) / 10;
  if (adjustment !== 0) {
    factors.push({
      kind: "adjustment",
      label:
        adjustment < 0
          ? "Ajuste do modelo: pontos fracos que pesam no critério todo"
          : "Ajuste do modelo: coerência entre as regras",
      points: adjustment,
    });
  }

  return {
    method:
      "Média ponderada das regras: cada regra pesa conforme a quantidade de evidências que reúne.",
    baseline: 0,
    factors,
  };
};

/** Attaches mock explanations to every criterion and rule that lacks one */
export const withScoreExplanations = (analysis: Analysis): Analysis => ({
  ...analysis,
  criteria: analysis.criteria.map((criterion) => ({
    ...criterion,
    scoreExplanation: criterion.scoreExplanation ?? explainCriterionScore(criterion),
    rules: criterion.rules.map((rule) => ({
      ...rule,
      scoreExplanation: rule.scoreExplanation ?? explainRuleScore(rule),
    })),
  })),
});
