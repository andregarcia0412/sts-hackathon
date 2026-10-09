import { getNodePath, indexAnalysis } from "@/domain/tree";
import type { Analysis } from "@/domain/types";

/*
 * Which criterion and rule are open in the document. The source of truth is
 * the node in the URL (?no=), like the analysis screen: absent opens the first
 * criterion (as in the design), empty closes everything.
 */

export interface OpenState {
  criterionId?: string;
  ruleId?: string;
}

export const openStateOf = (analysis: Analysis, nodeId: string | null): OpenState => {
  if (nodeId === null) return { criterionId: analysis.criteria[0]?.id };
  if (nodeId === "") return {};
  const [criterion, rule] = getNodePath(indexAnalysis(analysis), nodeId);
  return { criterionId: criterion?.id, ruleId: rule?.kind === "rule" ? rule.id : undefined };
};

/** Node to put in the URL when the analyst clicks a criterion or rule header */
export const toggledNode = (open: OpenState, nodeId: string, parentId?: string): string => {
  if (parentId === undefined) return open.criterionId === nodeId ? "" : nodeId;
  return open.ruleId === nodeId ? parentId : nodeId;
};
