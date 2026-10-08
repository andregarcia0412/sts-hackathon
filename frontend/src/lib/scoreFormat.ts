import type { ScoreExplanation } from "@/domain/types";

const pointsFormat = new Intl.NumberFormat("pt-BR", {
  maximumFractionDigits: 1,
  signDisplay: "always",
});
const scoreFormat = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
const percentFormat = new Intl.NumberFormat("pt-BR", { style: "percent" });

/** "+19", "−8", "+0,8" (typographic minus) */
export const formatPoints = (points: number) =>
  pointsFormat.format(points).replace("-", "−");

export const formatScore = (value: number) => scoreFormat.format(value);

export const formatPercent = (ratio: number) => percentFormat.format(ratio);

/**
 * One-line text version of a score explanation, e.g. for print:
 * rule "50 +19 +19 −8 = 80"; criterion "80×60% + 58×40% (ajuste +0,8) = 72"
 */
export const breakdownFormula = (explanation: ScoreExplanation, score: number) => {
  const adjustments = explanation.factors.filter((f) => f.kind === "adjustment");
  const adjustmentText = adjustments.length
    ? ` (ajuste ${formatPoints(adjustments.reduce((sum, f) => sum + f.points, 0))})`
    : "";
  const main = explanation.factors.filter((f) => f.kind !== "adjustment");

  if (explanation.baseline > 0) {
    const steps = main.map((f) => formatPoints(f.points)).join(" ");
    return `${formatScore(explanation.baseline)} ${steps}${adjustmentText} = ${formatScore(score)}`;
  }
  const terms = main
    .map((f) =>
      f.value !== undefined && f.weight !== undefined
        ? `${f.value}×${formatPercent(f.weight)}`
        : formatPoints(f.points),
    )
    .join(" + ");
  return `${terms}${adjustmentText} = ${formatScore(score)}`;
};
