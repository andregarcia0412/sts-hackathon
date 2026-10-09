import { describe, expect, it } from "vitest";
import type { Analysis } from "@/domain/types";
import { soilSensorAnalysis } from "@/mocks/analysis-soil-sensor";
import { soilSensorMctiAnalysis } from "@/mocks/analysis-soil-sensor-mcti";
import { illustrativeMcti, isIllustrativeAnalysisId, withIllustrativeMcti } from "@/mocks/illustrativeMcti";

/** Frascati as the back-end sends it: its own keys, null score without evidence */
const backendFrascati: Analysis = {
  ...soilSensorAnalysis,
  id: "6ac8cb2508861ec8bad60b3e",
  projectId: "6ac8cb2508861ec8bad60b04",
  criteria: soilSensorAnalysis.criteria.map((c) =>
    c.key === "systematic" ? { ...c, key: "systematicity", score: 40 } : c.key === "novelty" ? { ...c, score: 14 } : c,
  ),
};

describe("withIllustrativeMcti", () => {
  it("adds the example MCTI tree, flagged, to a Frascati-only answer", () => {
    const [frascati, mcti] = withIllustrativeMcti([backendFrascati]);
    expect(frascati).toBe(backendFrascati);
    expect(mcti).toMatchObject({ framework: "mcti_form", projectId: backendFrascati.projectId, illustrative: true });
    expect(isIllustrativeAnalysisId(mcti.id)).toBe(true);
    expect(isIllustrativeAnalysisId(frascati.id)).toBe(false);
  });

  it("keeps a real MCTI analysis when the back-end sends one", () => {
    const analyses = [backendFrascati, soilSensorMctiAnalysis];
    expect(withIllustrativeMcti(analyses)).toBe(analyses);
  });

  it("adds nothing without a Frascati analysis", () => {
    expect(withIllustrativeMcti([])).toEqual([]);
  });
});

describe("illustrativeMcti", () => {
  it("follows the project's Frascati scores, back-end keys included", () => {
    const mcti = illustrativeMcti(backendFrascati);
    const score = (key: string) => mcti.criteria.find((c) => c.key === key)?.score;
    expect(score("novel_element")).toBe(14);
    expect(score("methodology")).toBe(40);
    for (const rule of mcti.criteria.flatMap((c) => c.rules)) {
      expect(rule.score).toBeGreaterThanOrEqual(0);
      expect(rule.score).toBeLessThanOrEqual(100);
    }
  });

  it("keeps the example's score when the back-end has none", () => {
    const empty = { ...backendFrascati, criteria: [] };
    expect(illustrativeMcti(empty).criteria.map((c) => c.score)).toEqual(
      soilSensorMctiAnalysis.criteria.map((c) => c.score),
    );
  });
});
