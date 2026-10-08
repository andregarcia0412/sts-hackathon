/*
 * Score = força da evidência (0–100), never "probabilidade de aprovação".
 * Bands are provisional: change the thresholds here and the whole UI follows.
 */

export const SCORE_MAX = 100;

export type ScoreBand = "strong" | "moderate" | "weak";

const STRONG_MIN = 70;
const MODERATE_MIN = 40;

export const scoreBand = (score: number): ScoreBand => {
  if (score >= STRONG_MIN) return "strong";
  if (score >= MODERATE_MIN) return "moderate";
  return "weak";
};

export const SCORE_BAND_LABELS: Record<ScoreBand, string> = {
  strong: "Evidência forte",
  moderate: "Evidência moderada",
  weak: "Evidência fraca",
};

export const SCORE_BAND_RANGES: Record<ScoreBand, string> = {
  strong: `${STRONG_MIN}–${SCORE_MAX}`,
  moderate: `${MODERATE_MIN}–${STRONG_MIN - 1}`,
  weak: `0–${MODERATE_MIN - 1}`,
};

export const SCORE_BANDS: ScoreBand[] = ["strong", "moderate", "weak"];
