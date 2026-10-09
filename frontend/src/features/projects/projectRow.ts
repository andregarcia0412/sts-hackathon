import { criterionStatusInfo } from "@/domain/qualitative";
import type { Tone } from "@/domain/qualitative";
import type { ProjectSummary } from "@/domain/types";

/*
 * What each column of the project list shows for a project, as plain data
 * (the table only draws it). Mirrors the "Tela de projetos" design.
 */

export type SituationMarker = "ring" | "dot" | "dot-muted" | "dash";

export interface Situation {
  label: string;
  marker: SituationMarker;
  /** 0–1, only while processing */
  progress?: number;
  danger?: boolean;
}

export const situationOf = (project: ProjectSummary): Situation => {
  switch (project.status) {
    case "processing":
      return { label: "Processando", marker: "ring", progress: project.processingProgress };
    case "error":
      return { label: "Erro na leitura", marker: "dash", danger: true };
    case "decided":
      return { label: "Decidido", marker: "dot-muted" };
    default: {
      const decided = project.decidedCriteria;
      return {
        label: decided ? `Em análise · ${decided.decided} de ${decided.total}` : "Em análise",
        marker: "dot",
      };
    }
  }
};

export type WeakestCriterion =
  | { kind: "message"; text: string }
  | {
      kind: "criterion";
      name: string;
      reading: string;
      tone: Tone;
      /** Position of the weakest criterion among all of them (for the bar strip) */
      index: number;
      count: number;
    };

export const weakestCriterionOf = (project: ProjectSummary): WeakestCriterion => {
  if (project.status === "processing") {
    return { kind: "message", text: "Lendo documentos e extraindo evidências" };
  }
  if (project.status === "error") {
    return {
      kind: "message",
      text: project.readError
        ? `“${project.readError.fileName}” não pôde ser lido. A análise espera o reenvio.`
        : "Um arquivo não pôde ser lido. A análise espera o reenvio.",
    };
  }
  const scores = project.scoreSummary;
  if (!scores?.length) return { kind: "message", text: "—" };
  const index = scores.reduce((min, s, i) => (s.score < scores[min].score ? i : min), 0);
  const weakest = scores[index];
  const info = criterionStatusInfo({ key: weakest.criterionKey, score: weakest.score });
  return {
    kind: "criterion",
    name: weakest.name,
    reading: info.short,
    tone: info.tone,
    index,
    count: scores.length,
  };
};
