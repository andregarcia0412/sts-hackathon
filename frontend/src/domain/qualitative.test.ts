import { describe, expect, it } from "vitest";
import { criterionStatus, ruleStatus } from "@/domain/qualitative";
import type { Criterion, Evidence, Rule } from "@/domain/types";

const evidence = (id: string, polarity: Evidence["polarity"]): Evidence => ({
  id,
  title: id,
  polarity,
  explanation: "",
  references: [],
});

const rule = (score: number, evidences: Evidence[], points?: number[]): Rule => ({
  id: "r",
  code: "R-1",
  name: "Regra",
  score,
  explanation: "",
  normativeSource: { label: "Norma" },
  evidences,
  scoreExplanation: points && {
    method: "",
    baseline: 50,
    factors: points.map((p, i) => ({ kind: "evidence", refId: evidences[i].id, label: "", points: p })),
  },
});

describe("ruleStatus", () => {
  it("has no evidence when the rule has none", () => {
    expect(ruleStatus(rule(80, []))).toBe("no_evidence");
  });

  it("follows the score band", () => {
    expect(ruleStatus(rule(84, [evidence("a", "positive")]))).toBe("sustained");
    expect(ruleStatus(rule(60, [evidence("a", "positive")]))).toBe("partial");
    expect(ruleStatus(rule(20, [evidence("a", "negative")]))).toBe("not_sustained");
  });

  it("is contradictory when both sides weigh about the same", () => {
    const mixed = [evidence("a", "positive"), evidence("b", "negative")];
    expect(ruleStatus(rule(58, mixed, [16, -8]))).toBe("contradictory");
    expect(ruleStatus(rule(66, mixed, [24, -8]))).toBe("partial");
  });

  it("never calls a strong rule contradictory", () => {
    const mixed = [evidence("a", "positive"), evidence("b", "negative")];
    expect(ruleStatus(rule(75, mixed, [33, -8]))).toBe("sustained");
  });

  it("weighs evidences equally without an explanation", () => {
    const mixed = [evidence("a", "positive"), evidence("b", "negative")];
    expect(ruleStatus(rule(50, mixed))).toBe("contradictory");
  });
});

describe("criterionStatus", () => {
  it("follows the score band", () => {
    const criterion = (score: number) => ({ score }) as Criterion;
    expect(criterionStatus(criterion(78))).toBe("demonstrated");
    expect(criterionStatus(criterion(55))).toBe("limited");
    expect(criterionStatus(criterion(34))).toBe("not_demonstrated");
  });
});
