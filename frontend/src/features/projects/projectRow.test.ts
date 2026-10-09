import { describe, expect, it } from "vitest";
import { situationOf, weakestCriterionOf } from "@/features/projects/projectRow";
import type { ProjectSummary } from "@/domain/types";

const project = (patch: Partial<ProjectSummary>): ProjectSummary => ({
  id: "p1",
  ownerId: "u1",
  name: "Projeto",
  createdAt: "2026-10-01T00:00:00Z",
  status: "ready",
  documents: [],
  ...patch,
});

describe("situationOf", () => {
  it("shows the analyst's progress while in analysis", () => {
    expect(situationOf(project({ decidedCriteria: { decided: 2, total: 5 } })).label).toBe(
      "Em análise · 2 de 5",
    );
  });

  it("marks processing, error and decided", () => {
    expect(situationOf(project({ status: "processing", processingProgress: 0.4 }))).toMatchObject({
      marker: "ring",
      progress: 0.4,
    });
    expect(situationOf(project({ status: "error" }))).toMatchObject({ label: "Erro na leitura", danger: true });
    expect(situationOf(project({ status: "decided" })).label).toBe("Decidido");
  });
});

describe("weakestCriterionOf", () => {
  it("finds the weakest criterion with the design's reading", () => {
    const weakest = weakestCriterionOf(
      project({
        scoreSummary: [
          { criterionKey: "novelty", name: "Novidade", score: 80 },
          { criterionKey: "transferability", name: "Transferibilidade", score: 55 },
        ],
      }),
    );
    expect(weakest).toMatchObject({ kind: "criterion", name: "Transferibilidade", reading: "Com limite", index: 1 });
  });

  it("explains a read error with the file name", () => {
    const weakest = weakestCriterionOf(project({ status: "error", readError: { fileName: "a.pdf" } }));
    expect(weakest).toEqual({ kind: "message", text: "“a.pdf” não pôde ser lido. A análise espera o reenvio." });
  });
});
