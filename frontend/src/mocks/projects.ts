import { recognizeDocumentKind } from "@/domain/documents";
import type { Analysis, Decision, Project, ProjectDocument } from "@/domain/types";
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

const withKinds = (documents: ProjectDocument[]) =>
  documents.map((doc) => ({ ...doc, kind: recognizeDocumentKind(doc.fileName) }));

export const mockProjects: Project[] = [
  {
    id: "p1",
    ownerId: "u1",
    name: "Sensor de umidade de solo para o semiárido (EXEMPLO FICTÍCIO)",
    company: "AgroSertão Tecnologia Ltda. (fictícia)",
    createdAt: "2026-09-28T13:12:00.000Z",
    cutoffDate: "2026-09-19T00:00:00.000Z",
    status: "ready",
    documents: withKinds(soilSensorDocuments),
  },
  {
    id: "p2",
    ownerId: "u1",
    name: "Plataforma de conciliação financeira (EXEMPLO FICTÍCIO)",
    company: "Conta Fácil Sistemas (fictícia)",
    createdAt: "2026-09-15T10:02:00.000Z",
    cutoffDate: "2026-08-31T00:00:00.000Z",
    status: "decided",
    documents: withKinds(reconciliationDocuments),
  },
  {
    id: "p3",
    ownerId: "u1",
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
    ownerId: "u1",
    name: "Dessalinizador solar compacto (EXEMPLO FICTÍCIO)",
    createdAt: "2026-10-02T16:20:00.000Z",
    status: "error",
    readError: { fileName: "Projeto_digitalizado_EXEMPLO.pdf" },
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
