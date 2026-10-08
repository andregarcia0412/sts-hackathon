import { getNodeTitle, indexAnalysis } from "@/domain/tree";
import type { AnalysisIndex, CriterionNode, RuleNode } from "@/domain/tree";
import type {
  Analysis,
  AnalysisChange,
  Contestation,
  ContestationResolution,
  EvidencePolarity,
} from "@/domain/types";
import { explainCriterionScore, explainRuleScore } from "@/mocks/scoreExplanations";

/*
 * MOCK reanalysis of a contestation. The "model" accepts the analyst's point
 * when the argument cites something verifiable in the material (page, file,
 * table, annex...), which is what makes a change defensible. Accepted
 * polarity/score contestations change the analysis; the changes are applied
 * on top of the analysis when it is read (see applyAdjustments).
 */

const SCORE_STEP = 10;

const clamp = (value: number) => Math.round(Math.max(0, Math.min(100, value)));

/** Does the argument point to something that can be checked in the material? */
export const citesVerifiableSource = (argument: string) =>
  /(p\.\s*\d|p[aá]g|p[aá]gina|\.(pdf|docx?|txt)\b|tabela|anexo|se[cç][aã]o|§|figura|ata\b)/i.test(argument);

const label = (node: { number: string } & Parameters<typeof getNodeTitle>[0]) =>
  `${node.number} ${getNodeTitle(node)}`;

/** Rule score change and its effect on the criterion (weighted like the explanation) */
const ruleAndCriterionChanges = (
  index: AnalysisIndex,
  rule: RuleNode,
  newRuleScore: number,
): AnalysisChange[] => {
  const criterion = index.get(rule.parentId!) as CriterionNode;
  const weight = explainCriterionScore(criterion.criterion).factors.find(
    (f) => f.refId === rule.rule.id,
  )?.weight ?? 0;
  const newCriterionScore = clamp(criterion.criterion.score + weight * (newRuleScore - rule.rule.score));
  return [
    { nodeId: rule.id, nodeLabel: label(rule), field: "score", before: rule.rule.score, after: newRuleScore },
    ...(newCriterionScore !== criterion.criterion.score
      ? [{
          nodeId: criterion.id,
          nodeLabel: label(criterion),
          field: "score" as const,
          before: criterion.criterion.score,
          after: newCriterionScore,
        }]
      : []),
  ];
};

/**
 * What would change in the analysis if the contestation were accepted.
 * Empty for reasons that don't translate into a number (wrong excerpt,
 * missing evidence, other): those wait for a new reading of the material.
 */
export const contestationChanges = (
  analysis: Analysis,
  contestation: Pick<Contestation, "nodeId" | "reason" | "suggestedScore">,
): AnalysisChange[] => {
  const index = indexAnalysis(analysis);
  const node = index.get(contestation.nodeId);
  if (!node) return [];

  if (contestation.reason === "polarity" && node.kind === "evidence") {
    const rule = index.get(node.parentId!) as RuleNode;
    const points =
      explainRuleScore(rule.rule).factors.find((f) => f.refId === node.evidence.id)?.points ?? 0;
    const flipped: EvidencePolarity = node.evidence.polarity === "positive" ? "negative" : "positive";
    return [
      { nodeId: node.id, nodeLabel: label(node), field: "polarity", before: node.evidence.polarity, after: flipped },
      ...ruleAndCriterionChanges(index, rule, clamp(rule.rule.score - 2 * points)),
    ];
  }

  const direction =
    contestation.reason === "score_too_high" ? -1 : contestation.reason === "score_too_low" ? 1 : 0;
  if (direction === 0 || node.kind === "evidence") return [];

  if (node.kind === "rule") {
    const target = contestation.suggestedScore ?? clamp(node.rule.score + direction * SCORE_STEP);
    return ruleAndCriterionChanges(index, node, target);
  }
  const target = contestation.suggestedScore ?? clamp(node.criterion.score + direction * SCORE_STEP);
  return [{ nodeId: node.id, nodeLabel: label(node), field: "score", before: node.criterion.score, after: target }];
};

const describe = (change: AnalysisChange) =>
  change.field === "polarity"
    ? `${change.nodeLabel} passa a ser evidência ${change.after === "positive" ? "positiva" : "negativa"}`
    : `${change.nodeLabel}: ${change.before} → ${change.after}`;

export const reanalyze = (
  analysis: Analysis,
  contestation: Contestation,
  resolvedAt: string,
): ContestationResolution => {
  if (!citesVerifiableSource(contestation.argument)) {
    return {
      verdict: "maintained",
      explanation:
        "Reanalisei e mantive a leitura: o argumento não aponta um trecho verificável do material (arquivo, página, tabela ou anexo). Registre uma nova contestação citando a fonte para uma nova reanálise.",
      changes: [],
      resolvedAt,
    };
  }
  const changes = contestationChanges(analysis, contestation);
  return {
    verdict: "accepted",
    explanation: changes.length
      ? `Reanalisei com a fonte indicada e acatei a contestação. ${changes.map(describe).join("; ")}.`
      : "Reanalisei com a fonte indicada e acatei o ponto. Ele não muda a nota agora: fica registrado para a próxima leitura do material.",
    changes,
    resolvedAt,
  };
};

/** The analysis as it stands after every accepted contestation, oldest first */
export const applyAdjustments = (analysis: Analysis, contestations: Contestation[]): Analysis => {
  const accepted = contestations
    .filter((c) => c.analysisId === analysis.id && c.resolution?.verdict === "accepted")
    .sort((a, b) => a.resolution!.resolvedAt.localeCompare(b.resolution!.resolvedAt));
  if (accepted.length === 0) return analysis;

  const adjusted: Analysis = structuredClone(analysis);
  const index = indexAnalysis(adjusted);
  adjusted.adjustments = [];
  for (const contestation of accepted) {
    for (const change of contestation.resolution!.changes) {
      const node = index.get(change.nodeId);
      if (!node) continue;
      if (change.field === "polarity" && node.kind === "evidence") {
        node.evidence.polarity = change.after as EvidencePolarity;
      } else if (change.field === "score" && node.kind === "rule") {
        node.rule.score = change.after as number;
      } else if (change.field === "score" && node.kind === "criterion") {
        node.criterion.score = change.after as number;
      }
      adjusted.adjustments.push({ ...change, contestationId: contestation.id });
    }
  }
  return adjusted;
};
