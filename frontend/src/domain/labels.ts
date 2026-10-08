import type {
  ContestationReason,
  DecisionOutcome,
  EvidencePolarity,
  ProjectStatus,
  SuggestedCategory,
} from "@/domain/types";

export const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
  processing: "Processando",
  ready: "Pronto para análise",
  decided: "Decidido",
  error: "Erro",
};

export const POLARITY_LABELS: Record<EvidencePolarity, string> = {
  positive: "Positiva",
  negative: "Negativa",
};

export const SUGGESTED_CATEGORY_LABELS: Record<SuggestedCategory, string> = {
  PB: "Pesquisa básica (PB)",
  PA: "Pesquisa aplicada (PA)",
  DE: "Desenvolvimento experimental (DE)",
};

export const DECISION_OUTCOME_LABELS: Record<DecisionOutcome, string> = {
  eligible: "Enquadrável",
  not_eligible: "Não enquadrável",
  needs_review: "Precisa de revisão",
};

export const CONTESTATION_REASON_LABELS: Record<ContestationReason, string> = {
  polarity: "Polaridade errada (a favor × contra)",
  score_too_high: "Nota alta demais",
  score_too_low: "Nota baixa demais",
  wrong_excerpt: "O trecho não sustenta a conclusão",
  missing_evidence: "Faltou considerar algo",
  other: "Outro motivo",
};

/** Reasons that make sense for each kind of node, in the order they are offered */
export const CONTESTATION_REASONS_BY_KIND: Record<
  "criterion" | "rule" | "evidence",
  ContestationReason[]
> = {
  criterion: ["score_too_high", "score_too_low", "missing_evidence", "other"],
  rule: ["score_too_high", "score_too_low", "missing_evidence", "other"],
  evidence: ["polarity", "wrong_excerpt", "other"],
};
