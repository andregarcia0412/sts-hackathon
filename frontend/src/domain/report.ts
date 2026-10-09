import { CONTESTATION_REASON_LABELS } from "@/domain/labels";
import { criterionStatus, ruleStatus } from "@/domain/qualitative";
import { indexAnalysis } from "@/domain/tree";
import type { AnalysisNode } from "@/domain/tree";
import type { Analysis, Contestation, Criterion, Project, Rule } from "@/domain/types";

/*
 * Readings of the decision document: what the analyst should look at before
 * deciding. Derived from the analysis; the system points, never resolves.
 */

export type PendencyKind = "divergence" | "limit" | "no_evidence" | "pending";

export interface Pendency {
  kind: PendencyKind;
  /** Node the pendency is about (opens it in the document) */
  nodeId: string;
  /** "Regra 1.4", "Critério 1"… */
  ref: string;
  text: string;
}

export const PENDENCY_LABELS: Record<PendencyKind, string> = {
  divergence: "Divergência",
  limit: "Limite declarado",
  no_evidence: "Sem evidência",
  pending: "Pendente",
};

/** Criteria where the web search for similar work applies (novelty) */
const WEB_SEARCH_CRITERIA = new Set(["novelty", "novel_element"]);

const KIND_ORDER: PendencyKind[] = ["divergence", "limit", "no_evidence", "pending"];

const refOf = (node: AnalysisNode) =>
  `${node.kind === "criterion" ? "Critério" : node.kind === "rule" ? "Regra" : "Evidência"} ${node.number}`;

export const pendenciesOf = (
  analysis: Analysis,
  project: Pick<Project, "webSearch">,
  contestations: Contestation[] = [],
): Pendency[] => {
  const index = indexAnalysis(analysis);
  const items: Pendency[] = [];

  for (const node of index.values()) {
    if (node.kind !== "rule") continue;
    const { rule } = node;
    const status = ruleStatus(rule);
    if (status === "contradictory") {
      items.push({
        kind: "divergence",
        nodeId: node.id,
        ref: refOf(node),
        text: `${rule.explanation} O sistema não resolve a divergência.`,
      });
    } else if (status === "partial") {
      items.push({ kind: "limit", nodeId: node.id, ref: refOf(node), text: rule.explanation });
    } else if (status === "no_evidence") {
      items.push({
        kind: "no_evidence",
        nodeId: node.id,
        ref: refOf(node),
        text: `${rule.name}: nenhum trecho localizado no material. Ausência de evidência não equivale a "não atende".`,
      });
    }
  }

  for (const contestation of contestations) {
    const node = index.get(contestation.nodeId);
    if (contestation.status !== "open" || contestation.analysisId !== analysis.id || !node) continue;
    items.push({
      kind: "pending",
      nodeId: node.id,
      ref: refOf(node),
      text: `Contestação aberta (${CONTESTATION_REASON_LABELS[contestation.reason].toLowerCase()}) aguardando reanálise.`,
    });
  }

  const novelty = [...index.values()].find(
    (node) => node.kind === "criterion" && WEB_SEARCH_CRITERIA.has(node.criterion.key),
  );
  if (project.webSearch && novelty) {
    items.push({
      kind: "pending",
      nodeId: novelty.id,
      ref: refOf(novelty),
      text: "Busca externa (Google Scholar, arXiv) não executada. O plano de busca aguarda aprovação do analista.",
    });
  }

  return items.sort((a, b) => KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind));
};

/** Pendencies inside a criterion (its "N alertas" in the summary) */
export const pendenciesIn = (pendencies: Pendency[], criterionId: string) =>
  pendencies.filter((p) => p.nodeId === criterionId || p.nodeId.startsWith(`${criterionId}.`));

/** Lowest-scoring criterion, when it is not fully met: "mais fraca" in the summary */
export const weakestCriterion = (criteria: Criterion[]): Criterion | undefined => {
  const weakest = criteria.reduce<Criterion | undefined>(
    (low, c) => (!low || c.score < low.score ? c : low),
    undefined,
  );
  return weakest && criterionStatus(weakest) !== "met" ? weakest : undefined;
};

/** "1 evidência a favor", "2 a favor · 1 contra", "nenhuma localizada" */
export const evidenceTally = (rule: Rule): string => {
  const positive = rule.evidences.filter((e) => e.polarity === "positive").length;
  const negative = rule.evidences.length - positive;
  if (positive + negative === 0) return "nenhuma localizada";
  if (negative === 0) return `${positive} ${positive === 1 ? "evidência" : "evidências"} a favor`;
  if (positive === 0) return `${negative} ${negative === 1 ? "evidência" : "evidências"} contra`;
  return `${positive} a favor · ${negative} contra`;
};
