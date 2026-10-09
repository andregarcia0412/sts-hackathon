import { describe, expect, it } from "vitest";
import { ruleStatus } from "@/domain/qualitative";
import { evidenceTally, pendenciesIn, pendenciesOf, weakestCriterion } from "@/domain/report";
import type { Contestation, Rule } from "@/domain/types";
import { soilSensorAnalysis } from "@/mocks/analysis-soil-sensor";

const rules = soilSensorAnalysis.criteria.flatMap((c) => c.rules);

describe("pendenciesOf", () => {
  const pendencies = pendenciesOf(soilSensorAnalysis, { webSearch: false });

  it("points every partial, contradictory and evidence-less rule", () => {
    const expected = rules.filter((r) => ["partial", "contradictory", "no_evidence"].includes(ruleStatus(r)));
    expect(pendencies).toHaveLength(expected.length);
    expect(pendencies.every((p) => p.ref.startsWith("Regra "))).toBe(true);
  });

  it("lists divergences first", () => {
    const kinds = pendencies.map((p) => p.kind);
    const order = ["divergence", "limit", "no_evidence", "pending"];
    expect(kinds).toEqual([...kinds].sort((a, b) => order.indexOf(a) - order.indexOf(b)));
  });

  it("adds the pending web search to the novelty criterion", () => {
    const withSearch = pendenciesOf(soilSensorAnalysis, { webSearch: true });
    expect(withSearch.at(-1)).toMatchObject({ kind: "pending", nodeId: "crit-novelty", ref: "Critério 1" });
  });

  it("adds open contestations of this analysis only", () => {
    const open = {
      id: "c1",
      status: "open",
      projectId: "p1",
      analysisId: soilSensorAnalysis.id,
      nodeId: "crit-uncertainty",
      nodeLabel: "3 Incerteza",
      reason: "score_too_high",
      argument: "",
      author: "Ana",
      createdAt: "2026-01-01T00:00:00Z",
    } as Contestation;
    const other = { ...open, id: "c2", analysisId: "outra" };
    const result = pendenciesOf(soilSensorAnalysis, { webSearch: false }, [open, other]);
    expect(result.filter((p) => p.kind === "pending")).toHaveLength(1);
    expect(pendenciesIn(result, "crit-uncertainty").some((p) => p.kind === "pending")).toBe(true);
  });
});

describe("weakestCriterion", () => {
  it("is the lowest score when it is not met", () => {
    const lowest = [...soilSensorAnalysis.criteria].sort((a, b) => a.score - b.score)[0];
    expect(weakestCriterion(soilSensorAnalysis.criteria)?.id).toBe(lowest.id);
  });

  it("is absent when every criterion is met", () => {
    const strong = soilSensorAnalysis.criteria.map((c) => ({ ...c, score: 90 }));
    expect(weakestCriterion(strong)).toBeUndefined();
  });
});

describe("evidenceTally", () => {
  const ev = (polarity: "positive" | "negative") => ({ id: polarity, title: "", polarity, explanation: "", references: [] });
  const rule = (evidences: Rule["evidences"]) => ({ evidences }) as Rule;

  it("reads like the design", () => {
    expect(evidenceTally(rule([]))).toBe("nenhuma localizada");
    expect(evidenceTally(rule([ev("positive")]))).toBe("1 evidência a favor");
    expect(evidenceTally(rule([ev("positive"), ev("positive"), ev("negative")]))).toBe("2 a favor · 1 contra");
    expect(evidenceTally(rule([ev("negative")]))).toBe("1 evidência contra");
  });
});
