import { describe, expect, it } from "vitest";
import { getExpandableIds, getRootIds, indexAnalysis } from "@/domain/tree";
import {
  buildGraph,
  layoutGraph,
} from "@/features/analysis/graph/buildGraph";
import { soilSensorAnalysis } from "@/mocks/analysis-soil-sensor";

const index = indexAnalysis(soilSensorAnalysis);

describe("buildGraph", () => {
  it("shows only the 5 criteria, without edges, when nothing is expanded", () => {
    const { nodes, edges } = buildGraph(index, new Set());

    expect(nodes.map((n) => n.id)).toEqual([
      "crit-novelty",
      "crit-creativity",
      "crit-uncertainty",
      "crit-systematic",
      "crit-transferability",
    ]);
    expect(nodes.every((n) => n.type === "criterion")).toBe(true);
    expect(edges).toEqual([]);
  });

  it("adds children and parent → child edges below expanded nodes", () => {
    const { nodes, edges } = buildGraph(
      index,
      new Set(["crit-uncertainty", "crit-uncertainty.rule-proj-13"]),
    );

    expect(nodes).toHaveLength(5 + 2 + 3);
    expect(edges).toContainEqual(
      expect.objectContaining({
        source: "crit-uncertainty",
        target: "crit-uncertainty.rule-proj-14",
      }),
    );
    expect(edges).toContainEqual(
      expect.objectContaining({
        source: "crit-uncertainty.rule-proj-13",
        target: "crit-uncertainty.rule-proj-13.ev-1",
      }),
    );
    expect(edges).toHaveLength(2 + 3);
  });

  it("marks which nodes are expanded", () => {
    const { nodes } = buildGraph(index, new Set(["crit-novelty"]));

    expect(nodes.find((n) => n.id === "crit-novelty")?.data.expanded).toBe(true);
    expect(nodes.find((n) => n.id === "crit-creativity")?.data.expanded).toBe(
      false,
    );
  });
});

describe("layoutGraph", () => {
  it("places children to the right of their parent (left-to-right)", () => {
    const { nodes, edges } = buildGraph(
      index,
      new Set(["crit-uncertainty", "crit-uncertainty.rule-proj-13"]),
    );
    const positioned = new Map(
      layoutGraph(nodes, edges).map((n) => [n.id, n.position]),
    );

    const criterion = positioned.get("crit-uncertainty")!;
    const rule = positioned.get("crit-uncertainty.rule-proj-13")!;
    const evidence = positioned.get("crit-uncertainty.rule-proj-13.ev-1")!;
    expect(rule.x).toBeGreaterThan(criterion.x);
    expect(evidence.x).toBeGreaterThan(rule.x);
  });

  it("stacks root criteria vertically without overlapping", () => {
    const { nodes, edges } = buildGraph(index, new Set());
    const ys = layoutGraph(nodes, edges)
      .map((n) => n.position.y)
      .sort((a, b) => a - b);

    for (let i = 1; i < ys.length; i++) {
      expect(ys[i] - ys[i - 1]).toBeGreaterThanOrEqual(92);
    }
  });

  it.each([
    ["everything", getExpandableIds(index)],
    ["one criterion", ["crit-uncertainty"]],
    ["a criterion and a rule", ["crit-uncertainty", "crit-transferability", "crit-uncertainty.rule-proj-13"]],
  ])("keeps siblings in numbering order, top to bottom (%s expanded)", (_, expandedIds) => {
    const { nodes, edges } = buildGraph(index, new Set(expandedIds));
    const positioned = layoutGraph(nodes, edges);
    const y = new Map(positioned.map((n) => [n.id, n.position.y]));

    for (const node of index.values()) {
      const siblingsY = node.childIds.filter((id) => y.has(id)).map((id) => y.get(id)!);
      expect(siblingsY).toEqual([...siblingsY].sort((a, b) => a - b));
    }
    const criteriaY = getRootIds(index).map((id) => y.get(id)!);
    expect(criteriaY).toEqual([...criteriaY].sort((a, b) => a - b));
  });
});
