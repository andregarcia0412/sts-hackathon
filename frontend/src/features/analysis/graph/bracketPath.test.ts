import { describe, expect, it } from "vitest";
import { bracketPath } from "@/features/analysis/graph/bracketPath";

describe("bracketPath", () => {
  it("is a straight line when the cards are aligned", () => {
    expect(bracketPath(0, 10, 40, 10)).toBe("M 0 10 H 40");
  });

  it("turns at the middle with 8px corners", () => {
    expect(bracketPath(0, 0, 40, 100)).toBe("M 0 0 H 12 Q 20 0 20 8 V 92 Q 20 100 28 100 H 40");
  });

  it("shrinks the corners for small height differences (no S curve)", () => {
    expect(bracketPath(0, 0, 40, 6)).toBe("M 0 0 H 17 Q 20 0 20 3 V 3 Q 20 6 23 6 H 40");
  });

  it("goes up as well as down", () => {
    expect(bracketPath(0, 100, 40, 0)).toContain("V 8");
  });
});
