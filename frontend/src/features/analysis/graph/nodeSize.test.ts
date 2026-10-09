import { describe, expect, it } from "vitest";
import { indexAnalysis } from "@/domain/tree";
import { countLines, nodeSize } from "@/features/analysis/graph/nodeSize";
import { soilSensorAnalysis } from "@/mocks/analysis-soil-sensor";

const FONT = "600 16px Heebo";

describe("countLines", () => {
  it("keeps a short text on one line", () => {
    expect(countLines("Novidade", FONT, 200)).toBe(1);
  });

  it("wraps at word boundaries as the text grows", () => {
    const short = countLines("Elemento tecnologicamente", FONT, 200);
    const long = countLines("Elemento tecnologicamente novo em relação ao estado da arte do setor", FONT, 200);
    expect(long).toBeGreaterThan(short);
  });

  it("breaks a word wider than the card", () => {
    expect(countLines("a".repeat(80), FONT, 100)).toBeGreaterThan(1);
  });
});

describe("nodeSize", () => {
  const index = indexAnalysis(soilSensorAnalysis);
  const criterion = index.get("crit-novelty")!;

  it("keeps the design height for short titles", () => {
    expect(nodeSize(criterion)).toEqual({ width: 204, height: 176 });
  });

  it("grows the card for a long title instead of cutting it", () => {
    const long = { ...criterion, criterion: { ...criterion.criterion, name: "Elemento tecnologicamente novo ".repeat(4) } };
    expect(nodeSize(long as typeof criterion).height).toBeGreaterThan(176);
  });

  it("returns a fresh object (dagre writes x/y into it)", () => {
    expect(nodeSize(criterion)).not.toBe(nodeSize(criterion));
  });
});
