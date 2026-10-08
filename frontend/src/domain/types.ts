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

/**
 * How a score was reached, step by step, so the UI can show it visually.
 * Provisional: the real calculation is still being defined by the team.
 */
export interface ScoreFactor {
  /** "evidence" / "rule": points from that child; "adjustment": anything else */
  kind: "evidence" | "rule" | "adjustment";
  /** Local id of the evidence or rule inside its parent (when kind ≠ adjustment) */
  refId?: string;
  label: string;
  /** Contribution in score points (may be negative) */
  points: number;
  /** For rules inside a criterion: the rule's own score and its weight (0–1) */
  value?: number;
  weight?: number;
}

export interface ScoreExplanation {
  /** One-sentence description of the method, shown above the chart */
  method: string;
  /** Starting point before the factors (e.g. 50 = neutral; 0 for weighted averages) */
  baseline: number;
  factors: ScoreFactor[];
}

export interface Rule {
  id: string;
  code: string; // ex.: "PROJ-09", "EXC-11"
  name: string;
  score: number; // 0–100, força da evidência
  explanation: string;
  normativeSource: Reference;
  evidences: Evidence[];
  scoreExplanation?: ScoreExplanation;
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
  scoreExplanation?: ScoreExplanation;
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

/*
 * Contestation: the analyst disagrees with something the model produced
 * (a criterion, rule or evidence). Recorded, never edited: it becomes part of
 * the decision trail.
 */
export type ContestationReason =
  | "polarity"
  | "score_too_high"
  | "score_too_low"
  | "wrong_excerpt"
  | "missing_evidence"
  | "other";

export interface Contestation {
  id: string;
  projectId: string;
  analysisId: string;
  /** Path id of the node in the analysis tree */
  nodeId: string;
  /** Snapshot like "3.1 PROJ-13 Barreira tecnológica", readable even if the analysis changes */
  nodeLabel: string;
  reason: ContestationReason;
  argument: string;
  suggestedScore?: number;
  suggestedPolarity?: EvidencePolarity;
  author: string;
  createdAt: string;
}

export type NewContestationInput = Omit<Contestation, "id" | "createdAt">;
