import type {
  DecisionOutcome,
  EvidencePolarity,
  Framework,
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

export const FRAMEWORK_LABELS: Record<Framework, string> = {
  frascati: "Frascati",
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
