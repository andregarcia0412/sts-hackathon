import { describe, expect, it } from "vitest";
import { reviewMarkers } from "@/domain/contestations";
import type { Analysis, Contestation } from "@/domain/types";

const analysis = {
  id: "a1",
  adjustments: [
    { contestationId: "c1", nodeId: "n-rule", nodeLabel: "", field: "score", before: 80, after: 96 },
  ],
} as unknown as Analysis;

const contestation = (id: string, nodeId: string, status: Contestation["status"]) =>
  ({ id, nodeId, status, analysisId: "a1" }) as Contestation;

describe("reviewMarkers", () => {
  it("marks open, revised and resolved nodes, open winning", () => {
    const markers = reviewMarkers(analysis, [
      contestation("c1", "n-evidence", "resolved"),
      contestation("c2", "n-other", "resolved"),
      contestation("c3", "n-rule", "open"),
      { ...contestation("c4", "n-x", "open"), analysisId: "another" },
    ]);

    expect(Object.fromEntries(markers)).toEqual({
      "n-evidence": "resolved",
      "n-other": "resolved",
      "n-rule": "open",
    });
  });

  it("marks nodes changed by an accepted contestation as revised", () => {
    expect(reviewMarkers(analysis, []).get("n-rule")).toBe("revised");
  });
});
