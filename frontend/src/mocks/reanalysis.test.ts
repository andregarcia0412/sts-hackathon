import { describe, expect, it } from "vitest";
import { indexAnalysis } from "@/domain/tree";
import type { Contestation } from "@/domain/types";
import { soilSensorAnalysis } from "@/mocks/analysis-soil-sensor";
import {
  applyAdjustments,
  citesVerifiableSource,
  reanalyze,
} from "@/mocks/reanalysis";
import { withScoreExplanations } from "@/mocks/scoreExplanations";

const contestation = (overrides: Partial<Contestation>): Contestation => ({
  id: "ct-1",
  status: "open",
  projectId: "p1",
  analysisId: soilSensorAnalysis.id,
  nodeId: "crit-uncertainty.rule-proj-13.ev-3",
  nodeLabel: "3.1.3 Resultados negativos incompletos",
  reason: "polarity",
  argument: "Os resultados estão na tabela 3, p. 10 do relatório.",
  author: "Ana",
  createdAt: "2026-10-08T10:00:00.000Z",
  ...overrides,
});

const NOW = "2026-10-08T11:00:00.000Z";

describe("citesVerifiableSource", () => {
  it("looks for pages, files, tables, annexes", () => {
    expect(citesVerifiableSource("ver p. 10")).toBe(true);
    expect(citesVerifiableSource("na página 4")).toBe(true);
    expect(citesVerifiableSource("Relatorio_Tecnico.pdf")).toBe(true);
    expect(citesVerifiableSource("tabela 3")).toBe(true);
    expect(citesVerifiableSource("acho que está errado")).toBe(false);
  });
});

describe("reanalyze", () => {
  it("accepts a polarity contestation with a source and recomputes rule and criterion", () => {
    // Same numbers as the debate simulation: PROJ-13 80 → 96, Incerteza 72 → 82
    const resolution = reanalyze(soilSensorAnalysis, contestation({}), NOW);

    expect(resolution.verdict).toBe("accepted");
    expect(resolution.changes).toEqual([
      expect.objectContaining({ nodeId: "crit-uncertainty.rule-proj-13.ev-3", field: "polarity", before: "negative", after: "positive" }),
      expect.objectContaining({ nodeId: "crit-uncertainty.rule-proj-13", field: "score", before: 80, after: 96 }),
      expect.objectContaining({ nodeId: "crit-uncertainty", field: "score", before: 72, after: 82 }),
    ]);
  });

  it("maintains the reading when the argument cites nothing verifiable", () => {
    const resolution = reanalyze(soilSensorAnalysis, contestation({ argument: "discordo" }), NOW);

    expect(resolution).toMatchObject({ verdict: "maintained", changes: [] });
  });

  it("uses the suggested score for a rule, or moves it 10 points", () => {
    const rule = "crit-novelty.rule-proj-12";
    const suggested = reanalyze(soilSensorAnalysis, contestation({ nodeId: rule, reason: "score_too_high", suggestedScore: 60 }), NOW);
    const step = reanalyze(soilSensorAnalysis, contestation({ nodeId: rule, reason: "score_too_high" }), NOW);

    expect(suggested.changes[0]).toMatchObject({ before: 84, after: 60 });
    expect(step.changes[0]).toMatchObject({ before: 84, after: 74 });
  });

  it("accepts non-quantitative points without changing scores", () => {
    const resolution = reanalyze(soilSensorAnalysis, contestation({ reason: "wrong_excerpt" }), NOW);

    expect(resolution).toMatchObject({ verdict: "accepted", changes: [] });
  });
});

describe("applyAdjustments", () => {
  it("applies accepted changes and keeps explanations consistent", () => {
    const accepted = contestation({ status: "resolved" });
    accepted.resolution = reanalyze(soilSensorAnalysis, accepted, NOW);

    const adjusted = withScoreExplanations(applyAdjustments(soilSensorAnalysis, [accepted]));
    const index = indexAnalysis(adjusted);
    const evidence = index.get("crit-uncertainty.rule-proj-13.ev-3");
    const rule = index.get("crit-uncertainty.rule-proj-13");

    expect(evidence?.kind === "evidence" && evidence.evidence.polarity).toBe("positive");
    expect(rule?.kind === "rule" && rule.rule.score).toBe(96);
    expect(adjusted.adjustments).toHaveLength(3);
    // The original analysis is untouched
    expect(soilSensorAnalysis.criteria[2].score).toBe(72);
  });

  it("ignores maintained and open contestations", () => {
    const maintained = contestation({ status: "resolved", argument: "discordo" });
    maintained.resolution = reanalyze(soilSensorAnalysis, maintained, NOW);

    expect(applyAdjustments(soilSensorAnalysis, [maintained, contestation({})])).toBe(soilSensorAnalysis);
  });
});
