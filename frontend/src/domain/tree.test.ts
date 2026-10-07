import { describe, expect, it } from "vitest";
import {
  getNodePath,
  indexAnalysis,
  numberTree,
} from "@/domain/tree";
import type { Analysis, Evidence, Rule } from "@/domain/types";

const evidence = (id: string): Evidence => ({
  id,
  title: id,
  polarity: "positive",
  explanation: "",
  references: [],
});

const rule = (id: string, evidences: Evidence[]): Rule => ({
  id,
  code: id.toUpperCase(),
  name: id,
  score: 50,
  explanation: "",
  normativeSource: { label: "ref" },
  evidences,
});

const analysis: Analysis = {
  id: "a1",
  projectId: "p1",
  framework: "frascati",
  generatedAt: "2026-01-01T00:00:00.000Z",
  criteria: [
    {
      id: "crit-a",
      key: "novelty",
      name: "A",
      score: 80,
      summary: "",
      rules: [rule("r1", [evidence("ev-1"), evidence("ev-2")]), rule("r2", [])],
    },
    {
      id: "crit-b",
      key: "creativity",
      name: "B",
      score: 30,
      summary: "",
      // same rule/evidence ids as in crit-a: node ids must stay unique
      rules: [rule("r1", [evidence("ev-1")])],
    },
  ],
};

describe("indexAnalysis", () => {
  it("indexes every node with a path-based unique id, in tree order", () => {
    const index = indexAnalysis(analysis);

    expect([...index.keys()]).toEqual([
      "crit-a",
      "crit-a.r1",
      "crit-a.r1.ev-1",
      "crit-a.r1.ev-2",
      "crit-a.r2",
      "crit-b",
      "crit-b.r1",
      "crit-b.r1.ev-1",
    ]);
  });

  it("links parents and children", () => {
    const index = indexAnalysis(analysis);

    expect(index.get("crit-a")?.childIds).toEqual(["crit-a.r1", "crit-a.r2"]);
    expect(index.get("crit-a.r1.ev-2")?.parentId).toBe("crit-a.r1");
    expect(index.get("crit-a")?.parentId).toBeUndefined();
  });
});

describe("numberTree", () => {
  it("numbers nodes as 1 / 1.1 / 1.1.1", () => {
    const numbers = numberTree(analysis);

    expect(numbers.get("crit-a")).toBe("1");
    expect(numbers.get("crit-a.r1")).toBe("1.1");
    expect(numbers.get("crit-a.r1.ev-2")).toBe("1.1.2");
    expect(numbers.get("crit-a.r2")).toBe("1.2");
    expect(numbers.get("crit-b.r1.ev-1")).toBe("2.1.1");
  });
});

describe("getNodePath", () => {
  it("returns the path from the root criterion to the node", () => {
    const index = indexAnalysis(analysis);

    expect(getNodePath(index, "crit-b.r1.ev-1").map((n) => n.id)).toEqual([
      "crit-b",
      "crit-b.r1",
      "crit-b.r1.ev-1",
    ]);
  });

  it("returns an empty path for unknown ids", () => {
    expect(getNodePath(indexAnalysis(analysis), "nope")).toEqual([]);
  });
});
