import type {
  Analysis,
  Decision,
  DecisionOutcome,
  Project,
  ProjectStatus,
} from "@/domain/types";
import { recognizeDocumentKind } from "@/domain/documents";
import { analysisTemplates } from "@/mocks/projects";
import { mockUsers } from "@/mocks/users";

/*
 * ~400 FICTITIOUS projects so the list, filters and pagination can be tried at
 * the scale the analysts described. Deterministic (seeded): every reload
 * produces the same data. Analyses are synthesized on demand from the
 * templates (400 trees would not fit in localStorage).
 */

export const GENERATED_COUNT = 400;

/** Small seeded PRNG (mulberry32): same seed, same sequence */
export const seededRandom = (seed: number) => {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
};

const THEMES = [
  "Biossensor para qualidade da água",
  "Dessalinização por membrana de baixo custo",
  "Plataforma de crédito com aprendizado de máquina",
  "Bioinsumo a partir de resíduos agroindustriais",
  "Rastreamento de rebanho com visão computacional",
  "Embalagem biodegradável de fibra de coco",
  "Irrigação inteligente para fruticultura",
  "Detecção de fraude em pagamentos instantâneos",
  "Painel solar com limpeza autônoma",
  "Fermentação controlada de cacau",
  "Microgeração eólica para comunidades isoladas",
  "Diagnóstico de pragas por imagem de satélite",
  "Concreto com resíduo de mineração",
  "Telemedicina com triagem automatizada",
  "Secagem solar de pescado",
  "Bateria de sódio para armazenamento rural",
  "Tradução automática de documentos jurídicos",
  "Monitoramento de barragens com IoT",
  "Extração de óleo de babaçu por enzimas",
  "Previsão de safra com dados climáticos",
  "Robô de inspeção de linhas de transmissão",
  "Cimento de baixa emissão para habitação",
  "Sistema de gestão de estoque hospitalar",
  "Antifúngico natural a partir de caju",
  "Dessalinizador térmico para pequenas comunidades",
  "Otimização logística de frota refrigerada",
  "Couro vegetal a partir de resíduo de abacaxi",
  "Modelo de risco climático para agricultura familiar",
  "Tratamento de efluente têxtil por fotocatálise",
  "Aplicativo de atendimento ao cliente",
];

const QUALIFIERS = ["", "(fase 2)", "para o semiárido", "em escala piloto", "– protótipo", "industrial"];

const COMPANY_A = ["Nordeste", "Sertão", "Litoral", "Caatinga", "Atlântico", "Mandacaru", "Jangada", "Carnaúba"];
const COMPANY_B = ["Tecnologia", "Inovação", "Bio", "Engenharia", "Sistemas", "Agro", "Energia", "Labs"];

const DOCUMENT_NAMES = [
  ["Plano_de_Projeto.pdf", "application/pdf"],
  ["Relatorio_Tecnico_2025.pdf", "application/pdf"],
  ["Cronograma_e_Orcamento.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
  ["Memorial_Descritivo.pdf", "application/pdf"],
  ["Notas_de_Laboratorio.txt", "text/plain"],
] as const;

const START = Date.parse("2025-04-01T09:00:00.000Z");
const END = Date.parse("2026-10-06T18:00:00.000Z");
const DAY = 24 * 60 * 60 * 1000;

export interface GeneratedProject {
  project: Project;
  /** Criterion scores per method, in template order */
  scores: number[][];
  decision?: Decision;
}

const clamp = (value: number, min = 5, max = 95) => Math.round(Math.max(min, Math.min(max, value)));

const pick = <T,>(random: () => number, items: readonly T[]) => items[Math.floor(random() * items.length)];

/** Stable number from a project id, to seed per-project values */
export const hashId = (id: string) =>
  [...id].reduce((hash, char) => (Math.imul(hash, 31) + char.charCodeAt(0)) | 0, 7);

const pickStatus = (r: number): ProjectStatus =>
  r < 0.5 ? "decided" : r < 0.83 ? "ready" : r < 0.91 ? "processing" : "error";

const outcomeFor = (minScore: number, r: number): DecisionOutcome => {
  if (minScore >= 55) return r < 0.85 ? "eligible" : "with_reservations";
  if (minScore < 35) return r < 0.8 ? "not_eligible" : "with_reservations";
  if (r < 0.5) return "with_reservations";
  if (r < 0.7) return "eligible";
  return r < 0.85 ? "not_eligible" : "insufficient_evidence";
};

const generate = (): GeneratedProject[] => {
  const random = seededRandom(20261007);
  return Array.from({ length: GENERATED_COUNT }, (_, i) => {
    const id = `g${String(i + 1).padStart(3, "0")}`;
    const owner = mockUsers[random() < 0.35 ? 0 : random() < 0.5 ? 1 : 2];
    const status = pickStatus(random());
    // Still processing only makes sense for something sent in the last days
    const createdAt = new Date(
      status === "processing" ? END - random() * 3 * DAY : START + random() * (END - START),
    ).toISOString();
    const documents = DOCUMENT_NAMES.slice(0, 1 + Math.floor(random() * DOCUMENT_NAMES.length)).map(
      ([fileName, mimeType], d) => ({
        id: `doc-${d + 1}`,
        fileName,
        mimeType,
        sizeBytes: Math.round(80_000 + random() * 4_000_000),
        uploadedAt: createdAt,
        kind: recognizeDocumentKind(fileName),
      }),
    );
    const quality = 25 + random() * 60;
    const scores = analysisTemplates.map((template) =>
      template.criteria.map(() => clamp(quality + (random() - 0.5) * 40)),
    );

    // Fields added later come from their own seed, so the main sequence (and every
    // project generated above) stays the same
    const extra = seededRandom(hashId(id));
    const project: Project = {
      id,
      ownerId: owner.id,
      name: `${pick(random, THEMES)} ${pick(random, QUALIFIERS)}`.trim(),
      company: `${pick(random, COMPANY_A)} ${pick(random, COMPANY_B)} (fictícia)`,
      createdAt,
      status,
      documents,
      cutoffDate: new Date(Date.parse(createdAt) - (7 + extra() * 50) * DAY).toISOString(),
      readError:
        status === "error"
          ? { fileName: documents[Math.floor(extra() * documents.length)].fileName }
          : undefined,
    };

    const decision: Decision | undefined =
      status === "decided"
        ? {
            projectId: id,
            analysisId: `an-${id}-0`,
            analysisIds: analysisTemplates.map((_, t) => `an-${id}-${t}`),
            outcome: outcomeFor(Math.min(...scores[0]), random()),
            justification: "Decisão de demonstração registrada para um projeto fictício gerado automaticamente.",
            analystName: owner.name,
            decidedAt: new Date(
              Math.min(END, Date.parse(createdAt) + (2 + random() * 28) * DAY),
            ).toISOString(),
          }
        : undefined;

    return { project, scores, decision };
  });
};

let cache: GeneratedProject[] | undefined;
export const generatedProjects = () => (cache ??= generate());

/** Analyses of a generated project: the templates with this project's scores */
export const synthesizeAnalyses = ({ project, scores }: GeneratedProject): Analysis[] => {
  if (project.status === "processing" || project.status === "error") return [];
  return analysisTemplates.map((template, t) => ({
    ...structuredClone(template),
    id: `an-${project.id}-${t}`,
    projectId: project.id,
    generatedAt: new Date(Date.parse(project.createdAt) + 10 * 60 * 1000).toISOString(),
    criteria: template.criteria.map((criterion, c) => {
      const score = scores[t][c];
      const delta = score - criterion.score;
      return {
        ...structuredClone(criterion),
        score,
        rules: criterion.rules.map((rule) => ({
          ...structuredClone(rule),
          score: clamp(rule.score + delta, 0, 100),
        })),
      };
    }),
  }));
};
