import { describe, expect, it } from "vitest";
import { reconciliationAnalysis } from "@/mocks/analysis-reconciliation";
import { soilSensorAnalysis } from "@/mocks/analysis-soil-sensor";
import { soilSensorMctiAnalysis } from "@/mocks/analysis-soil-sensor-mcti";
import { withScoreExplanations } from "@/mocks/scoreExplanations";
import type { ScoreExplanation } from "@/domain/types";

const total = (e: ScoreExplanation) =>
  Math.round((e.baseline + e.factors.reduce((sum, f) => sum + f.points, 0)) * 10) / 10;

describe.each([
  ["soil sensor", soilSensorAnalysis],
  ["reconciliation", reconciliationAnalysis],
  ["soil sensor, MCTI form", soilSensorMctiAnalysis],
])("withScoreExplanations (%s)", (_, analysis) => {
  const explained = withScoreExplanations(analysis);

  it("explains every rule: baseline + evidence points = rule score", () => {
    for (const rule of explained.criteria.flatMap((c) => c.rules)) {
      expect(total(rule.scoreExplanation!)).toBe(rule.score);
    }
  });

  it("explains every criterion: weighted rules (+ adjustment) = criterion score", () => {
    for (const criterion of explained.criteria) {
      expect(total(criterion.scoreExplanation!)).toBe(criterion.score);
    }
  });

  it("gives positive evidences non-negative points and negative ones non-positive", () => {
    for (const rule of explained.criteria.flatMap((c) => c.rules)) {
      for (const factor of rule.scoreExplanation!.factors) {
        const evidence = rule.evidences.find((e) => e.id === factor.refId);
        if (evidence?.polarity === "positive") expect(factor.points).toBeGreaterThanOrEqual(0);
        if (evidence?.polarity === "negative") expect(factor.points).toBeLessThanOrEqual(0);
      }
    }
  });

  it("weights of a criterion's rules add up to 1", () => {
    for (const criterion of explained.criteria) {
      const weights = criterion.scoreExplanation!.factors
        .filter((f) => f.kind === "rule")
        .reduce((sum, f) => sum + f.weight!, 0);
      expect(weights).toBeCloseTo(1);
    }
  });
});
