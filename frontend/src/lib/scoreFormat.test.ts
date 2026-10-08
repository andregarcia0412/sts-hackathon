import { describe, expect, it } from "vitest";
import { breakdownFormula, formatPoints } from "@/lib/scoreFormat";

describe("formatPoints", () => {
  it("always shows the sign, with a typographic minus and pt-BR decimals", () => {
    expect(formatPoints(19)).toBe("+19");
    expect(formatPoints(-8)).toBe("−8");
    expect(formatPoints(0.8)).toBe("+0,8");
  });
});

describe("breakdownFormula", () => {
  it("writes a rule as baseline and signed steps", () => {
    expect(
      breakdownFormula(
        {
          method: "",
          baseline: 50,
          factors: [
            { kind: "evidence", label: "a", points: 19 },
            { kind: "evidence", label: "b", points: 19 },
            { kind: "evidence", label: "c", points: -8 },
          ],
        },
        80,
      ),
    ).toBe("50 +19 +19 −8 = 80");
  });

  it("writes a criterion as weighted rules plus the adjustment", () => {
    expect(
      breakdownFormula(
        {
          method: "",
          baseline: 0,
          factors: [
            { kind: "rule", label: "a", points: 48, value: 80, weight: 0.6 },
            { kind: "rule", label: "b", points: 23.2, value: 58, weight: 0.4 },
            { kind: "adjustment", label: "ajuste", points: 0.8 },
          ],
        },
        72,
      ),
    ).toBe("80×60% + 58×40% (ajuste +0,8) = 72");
  });
});
