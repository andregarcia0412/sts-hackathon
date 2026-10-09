import { describe, expect, it } from "vitest";
import { decidedCriteriaCount, latestByNode } from "@/domain/reviews";
import type { Analysis, RuleDecision } from "@/domain/types";

const decision = (nodeId: string, createdAt: string, analysisId = "an-1"): RuleDecision => ({
  id: `${nodeId}-${createdAt}`,
  projectId: "p1",
  analysisId,
  nodeId,
  nodeLabel: nodeId,
  rating: "sustained",
  justification: "ok",
  author: "Ana",
  createdAt,
});

const analysis = {
  id: "an-1",
  criteria: [
    { id: "c1", rules: [{ id: "r1" }, { id: "r2" }] },
    { id: "c2", rules: [{ id: "r1" }] },
    { id: "c3", rules: [] },
  ],
} as unknown as Analysis;

describe("latestByNode", () => {
  it("keeps the newest entry per node of the analysis", () => {
    const latest = latestByNode(
      [decision("c1.r1", "2026-10-01"), decision("c1.r1", "2026-10-02"), decision("c1.r2", "2026-10-03", "an-2")],
      "an-1",
    );
    expect([...latest.keys()]).toEqual(["c1.r1"]);
    expect(latest.get("c1.r1")?.createdAt).toBe("2026-10-02");
  });
});

describe("decidedCriteriaCount", () => {
  it("counts criteria whose every rule has a rating", () => {
    expect(decidedCriteriaCount(analysis, [decision("c1.r1", "1")])).toBe(0);
    expect(
      decidedCriteriaCount(analysis, [decision("c1.r1", "1"), decision("c1.r2", "2"), decision("c2.r1", "3")]),
    ).toBe(2);
  });
});
