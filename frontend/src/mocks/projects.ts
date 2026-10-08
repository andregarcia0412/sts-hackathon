import type { Analysis, Decision, Project } from "@/domain/types";
import {
  reconciliationAnalysis,
  reconciliationDecisions,
  reconciliationDocuments,
} from "@/mocks/analysis-reconciliation";
import {
  soilSensorAnalysis,
  soilSensorDocuments,
} from "@/mocks/analysis-soil-sensor";
import { soilSensorMctiAnalysis } from "@/mocks/analysis-soil-sensor-mcti";

/* EXEMPLOS FICTÍCIOS: nenhum projeto, empresa ou pessoa aqui é real. */

export const mockProjects: Project[] = [
  {
    id: "p1",
    name: "Sensor de umidade de solo para o semiárido (EXEMPLO FICTÍCIO)",
    company: "AgroSertão Tecnologia Ltda. (fictícia)",
    createdAt: "2026-09-28T13:12:00.000Z",
    status: "ready",
    documents: soilSensorDocuments,
  },
  {
    id: "p2",
    name: "Plataforma de conciliação financeira (EXEMPLO FICTÍCIO)",
    company: "Conta Fácil Sistemas (fictícia)",
    createdAt: "2026-09-15T10:02:00.000Z",
    status: "decided",
    documents: reconciliationDocuments,
  },
  {
    id: "p3",
    name: "Bioinsumo a partir de resíduos de caju (EXEMPLO FICTÍCIO)",
    company: "Caju Bio (fictícia)",
    createdAt: "2026-10-07T09:40:00.000Z",
    status: "processing",
    documents: [],
    freeText:
      "Queremos desenvolver um fertilizante biológico a partir da casca e do bagaço do caju. Ainda não sabemos qual cepa de microrganismo consegue degradar o tanino da casca em escala. EXEMPLO FICTÍCIO.",
  },
  {
    id: "p4",
    name: "Dessalinizador solar compacto (EXEMPLO FICTÍCIO)",
    createdAt: "2026-10-02T16:20:00.000Z",
    status: "error",
    documents: [
      {
        id: "doc-1",
        fileName: "Projeto_digitalizado_EXEMPLO.pdf",
        mimeType: "application/pdf",
        sizeBytes: 15_728_640,
        uploadedAt: "2026-10-02T16:20:00.000Z",
      },
    ],
  },
];

export const mockAnalyses: Analysis[] = [
  soilSensorAnalysis,
  soilSensorMctiAnalysis,
  reconciliationAnalysis,
];

export const mockDecisions: Decision[] = [...reconciliationDecisions];

/** Templates used when a mock-created project finishes "processing" (one per method) */
export const analysisTemplates: Analysis[] = [soilSensorAnalysis, soilSensorMctiAnalysis];
