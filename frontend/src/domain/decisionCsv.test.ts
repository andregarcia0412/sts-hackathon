import { describe, expect, it } from "vitest";
import { decisionCsvColumns, decisionCsvFileName, decisionCsvRow, toCsv } from "@/domain/decisionCsv";
import { pendenciesOf } from "@/domain/report";
import type { Decision } from "@/domain/types";
import { soilSensorAnalysis } from "@/mocks/analysis-soil-sensor";

const project = { id: "proj-1", name: "Sensor de umidade" };
const decision: Decision = {
  projectId: "proj-1",
  analysisId: soilSensorAnalysis.id,
  outcome: "with_reservations",
  justification: "Transferibilidade fraca; pedir registros.",
  analystName: "Ana Ribeiro",
  decidedAt: "2026-03-10T14:30:00Z",
};
const pendencies = pendenciesOf(soilSensorAnalysis, { webSearch: false });

describe("decisionCsvColumns", () => {
  it("keeps the back-end's 27 columns first, then who decided", () => {
    const columns = decisionCsvColumns(5);
    expect(columns).toHaveLength(30);
    expect(columns.slice(0, 8)).toEqual([
      "projeto_id",
      "titulo",
      "classificacao",
      "justificativa",
      "limite",
      "fontes_decisivas",
      "divergencia_depoimento",
      "criterio_1",
    ]);
    expect(columns.slice(-3)).toEqual(["metodo", "analista", "decidido_em"]);
  });
});

describe("decisionCsvRow", () => {
  it("records the analyst's decision and every criterion", () => {
    const row = decisionCsvRow(project, soilSensorAnalysis, decision, pendencies);
    expect(row.classificacao).toBe("Com ressalvas");
    expect(row.justificativa).toBe(decision.justification);
    expect(row.analista).toBe("Ana Ribeiro");
    soilSensorAnalysis.criteria.forEach((criterion, i) => {
      expect(row[`criterio_${i + 1}`]).toBe(criterion.name);
      expect(row[`estado_${i + 1}`]).not.toBe("");
    });
  });

  it("leaves the decision empty when there is none yet", () => {
    const row = decisionCsvRow(project, soilSensorAnalysis, undefined, pendencies);
    expect(row.classificacao).toBe("");
    expect(row.analista).toBe("");
  });
});

describe("toCsv", () => {
  it("writes BOM, semicolons and quotes only where needed", () => {
    const csv = toCsv(["a", "b"], [{ a: "x;y", b: 'diz "oi"\nfim' }]);
    expect(csv).toBe('\uFEFFa;b\r\n"x;y";"diz ""oi""\nfim"\r\n');
  });

  it("never lets a cell run as a formula", () => {
    expect(toCsv(["a"], [{ a: "=SOMA(A1)" }])).toBe("\uFEFFa\r\n'=SOMA(A1)\r\n");
  });
});

it("names the file after the project and the method", () => {
  expect(decisionCsvFileName({ id: "proj 1" }, { framework: "frascati" })).toBe("parecer_proj_1_frascati.csv");
});
