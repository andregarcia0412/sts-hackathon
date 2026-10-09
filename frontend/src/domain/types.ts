/*
 * Domain types. Provisional contract: the real one comes from the back-end,
 * so keep every API shape here to make the swap happen in one place.
 */

export type ProjectStatus = "processing" | "ready" | "decided" | "error";

export interface User {
  id: string;
  name: string;
  email: string;
}

export interface ProjectDocument {
  id: string;
  fileName: string;
  mimeType: string;
  sizeBytes: number;
  uploadedAt: string; // ISO
  /** Recognized type ("Dossiê", "Registro técnico", "Depoimento"…), see domain/documents.ts */
  kind?: string;
}

export interface Project {
  id: string;
  /** Analyst who owns the project (each analyst sees their own list) */
  ownerId: string;
  name: string;
  company?: string;
  createdAt: string;
  status: ProjectStatus;
  documents: ProjectDocument[];
  freeText?: string; // descrição escrita pelo empresário
  /** Cut-off date of the period the material covers ("Corte"), when known */
  cutoffDate?: string;
  /** status "error": the file that could not be read (the analysis waits for a new one) */
  readError?: { fileName: string };
  /** Analyst allowed the search for similar work on the web (Novidade, Criatividade) */
  webSearch?: boolean;
}

export interface CriterionScoreSummary {
  criterionKey: CriterionKey;
  name: string;
  score: number;
}

/** Project as shown in the list, with a score overview when an analysis exists */
export interface ProjectSummary extends Project {
  /** Scores of the primary method's analysis (first in FRAMEWORK_ORDER) */
  scoreSummary?: CriterionScoreSummary[];
  /** Methods with an analysis available for this project */
  frameworks?: Framework[];
  /** Current (latest) decision, if any */
  lastDecision?: Pick<Decision, "outcome" | "decidedAt" | "analystName">;
  contestationCount?: number;
  openContestationCount?: number;
  /** Primary method: criteria with every rule rated by the analyst */
  decidedCriteria?: { decided: number; total: number };
  /** status "processing": share of the work done (0–1), when known */
  processingProgress?: number;
}

export type ProjectSort = "recent" | "oldest" | "name" | "weakest";

/** Filters of the project list. Mirrors what a paginated back-end endpoint takes. */
export interface ProjectQuery {
  ownerId: string;
  search?: string;
  statuses?: ProjectStatus[];
  /** Band of the project's weakest criterion (primary method) */
  weakestBand?: "strong" | "moderate" | "weak";
  /** Outcome of the current decision; "none" = no decision yet */
  outcome?: DecisionOutcome | "none";
  /** Submission date range, inclusive, "YYYY-MM-DD" */
  from?: string;
  to?: string;
  sort: ProjectSort;
  page: number;
  pageSize: number;
}

export interface ProjectPage {
  items: ProjectSummary[];
  /** Matches for the filters (all pages) */
  total: number;
  page: number;
  pageSize: number;
  /** Owner's projects per status, ignoring the other filters (for the overview) */
  statusCounts: Record<ProjectStatus, number>;
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

/**
 * Stable key of a criterion inside its method, e.g. Frascati's "novelty",
 * "uncertainty"... Free string because each method has its own criteria.
 */
export type CriterionKey = string;

export interface Criterion {
  id: string;
  key: CriterionKey;
  name: string; // "Novidade", "Criatividade", ...
  score: number; // 0–100
  summary: string;
  rules: Rule[];
  scoreExplanation?: ScoreExplanation;
}

/** Method that generated an analysis tree; metadata in domain/frameworks.ts */
export type Framework = "frascati" | "mcti_form";

export type SuggestedCategory = "PB" | "PA" | "DE";

export interface Analysis {
  id: string;
  projectId: string;
  framework: Framework;
  suggestedCategory?: SuggestedCategory;
  generatedAt: string;
  criteria: Criterion[];
  /** Changes applied after accepted contestations (oldest first) */
  adjustments?: (AnalysisChange & { contestationId: string })[];
  /**
   * Example added by the front for a method the back-end does not produce yet
   * (mocks/illustrativeMcti.ts): shown as such, never sent to the back-end
   */
  illustrative?: boolean;
}

export type DecisionOutcome =
  | "eligible"
  | "with_reservations"
  | "not_eligible"
  /** The material lacks something essential to tell R&D from routine */
  | "insufficient_evidence";

export interface RuleOverride {
  /** Node id of the rule in its analysis tree */
  ruleId: string;
  note: string;
  /** Analysis the rule belongs to (defaults to the decision's analysisId) */
  analysisId?: string;
}

export interface Decision {
  projectId: string;
  /** Primary analysis (first method) */
  analysisId: string;
  /** Every analysis (one per method) the analyst had in front of them */
  analysisIds?: string[];
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
  webSearch: boolean;
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

export type ContestationStatus = "open" | "resolved";

/** One value changed in the analysis by an accepted contestation */
export interface AnalysisChange {
  nodeId: string;
  /** Snapshot like "3.1 PROJ-13 Barreira tecnológica" */
  nodeLabel: string;
  field: "score" | "polarity";
  before: number | EvidencePolarity;
  after: number | EvidencePolarity;
}

/** Outcome of the model's reanalysis of a contestation */
export interface ContestationResolution {
  /** accepted: the analysis changes (or the point is taken); maintained: the model keeps its reading */
  verdict: "accepted" | "maintained";
  explanation: string;
  /** What changed in the analysis (empty when nothing quantitative changes) */
  changes: AnalysisChange[];
  resolvedAt: string;
}

export interface Contestation {
  id: string;
  status: ContestationStatus;
  resolution?: ContestationResolution;
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

export type NewContestationInput = Omit<
  Contestation,
  "id" | "createdAt" | "status" | "resolution"
>;

/*
 * Analyst review inside the analysis screen (append-only, part of the trail):
 * evidences are confirmed or discarded, rules get the analyst's rating.
 * The latest entry per node is the current one.
 */
export type RuleRating =
  | "sustained"
  | "partial"
  | "contradictory"
  | "not_sustained"
  | "needs_expert";

export interface RuleDecision {
  id: string;
  projectId: string;
  analysisId: string;
  /** Path id of the rule in the analysis tree */
  nodeId: string;
  /** Snapshot like "1.4 PROJ-14 Barreira tecnológica" */
  nodeLabel: string;
  rating: RuleRating;
  /** System's reading at the time, for the trail */
  suggested?: RuleRating;
  justification: string;
  author: string;
  createdAt: string;
}

export type EvidenceVerdict = "confirmed" | "discarded";

export interface EvidenceReview {
  id: string;
  projectId: string;
  analysisId: string;
  nodeId: string;
  nodeLabel: string;
  verdict: EvidenceVerdict;
  note?: string;
  author: string;
  createdAt: string;
}

export type NewRuleDecisionInput = Omit<RuleDecision, "id" | "createdAt">;
export type NewEvidenceReviewInput = Omit<EvidenceReview, "id" | "createdAt">;
