/*
 * Domain types. Provisional contract: the real one comes from the back-end,
 * so keep every API shape here to make the swap happen in one place.
 */

export type ProjectStatus = "processing" | "ready" | "decided" | "error";

export interface ProjectDocument {
  id: string;
  fileName: string;
  mimeType: string;
  sizeBytes: number;
  uploadedAt: string; // ISO
}

export interface Project {
  id: string;
  name: string;
  company?: string;
  createdAt: string;
  status: ProjectStatus;
  documents: ProjectDocument[];
  freeText?: string; // descrição escrita pelo empresário
}

export interface CriterionScoreSummary {
  criterionKey: CriterionKey;
  name: string;
  score: number;
}

/** Project as shown in the list, with a score overview when an analysis exists */
export interface ProjectSummary extends Project {
  scoreSummary?: CriterionScoreSummary[];
}

/** Referência normativa ou web que sustenta uma regra ou evidência */
export interface Reference {
  label: string; // ex.: "Manual de Frascati §2.18"
  citation?: string; // trecho literal da norma, quando houver
  url?: string;
}

/** Trecho do material do projeto que serviu de evidência */
export interface ProjectExcerpt {
  documentId?: string; // ausente se veio do texto livre
  fileName?: string;
  page?: number;
  excerpt: string; // citação literal
}

export type EvidencePolarity = "positive" | "negative";

export interface Evidence {
  id: string;
  title: string;
  polarity: EvidencePolarity;
  explanation: string; // por que conta a favor ou contra
  projectExcerpt?: ProjectExcerpt;
  references: Reference[];
}

export interface Rule {
  id: string;
  code: string; // ex.: "PROJ-09", "EXC-11"
  name: string;
  score: number; // 0–100, força da evidência
  explanation: string;
  normativeSource: Reference;
  evidences: Evidence[];
}

export type CriterionKey =
  | "novelty"
  | "creativity"
  | "uncertainty"
  | "systematic"
  | "transferability";

export interface Criterion {
  id: string;
  key: CriterionKey;
  name: string; // "Novidade", "Criatividade", ...
  score: number; // 0–100
  summary: string;
  rules: Rule[];
}

export type Framework = "frascati";

export type SuggestedCategory = "PB" | "PA" | "DE";

export interface Analysis {
  id: string;
  projectId: string;
  framework: Framework;
  suggestedCategory?: SuggestedCategory;
  generatedAt: string;
  criteria: Criterion[];
}

export type DecisionOutcome = "eligible" | "not_eligible" | "needs_review";

export interface RuleOverride {
  ruleId: string;
  note: string;
}

export interface Decision {
  projectId: string;
  analysisId: string;
  outcome: DecisionOutcome;
  justification: string;
  analystName: string;
  decidedAt: string;
  ruleOverrides?: RuleOverride[];
}

export interface NewProjectInput {
  name: string;
  company?: string;
  freeText?: string;
  files: File[];
}

export type NewDecisionInput = Omit<Decision, "decidedAt">;
