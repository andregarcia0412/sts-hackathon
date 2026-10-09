import { ruleNodeId } from "@/domain/tree";
import type { Analysis, Criterion, RuleDecision } from "@/domain/types";

/*
 * Analyst reviews are append-only: the current state of a node is its latest
 * entry. Helpers here read that state for one analysis (method).
 */

type Entry = { analysisId: string; nodeId: string; createdAt: string };

/** Latest entry per node of the given analysis */
export const latestByNode = <T extends Entry>(entries: T[], analysisId: string): Map<string, T> => {
  const latest = new Map<string, T>();
  for (const entry of entries) {
    if (entry.analysisId !== analysisId) continue;
    const current = latest.get(entry.nodeId);
    if (!current || entry.createdAt >= current.createdAt) latest.set(entry.nodeId, entry);
  }
  return latest;
};

/** A criterion is decided when every rule in it has the analyst's rating */
export const isCriterionDecided = (
  criterion: Criterion,
  decisions: ReadonlyMap<string, RuleDecision>,
) =>
  criterion.rules.length > 0 &&
  criterion.rules.every((rule) => decisions.has(ruleNodeId(criterion, rule)));

export const decidedCriteriaCount = (analysis: Analysis, decisions: RuleDecision[]) => {
  const latest = latestByNode(decisions, analysis.id);
  return analysis.criteria.filter((c) => isCriterionDecided(c, latest)).length;
};
