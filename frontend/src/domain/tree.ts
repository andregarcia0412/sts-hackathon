import type { Analysis, Criterion, Evidence, Rule } from "@/domain/types";

/*
 * Analysis tree helpers: Critério → Regra → Evidência.
 * Node ids are paths ("crit-x.rule-y.ev-z") so they stay unique even when the
 * back-end reuses rule/evidence ids across criteria, and so a URL like
 * ?no=crit-uncertainty.rule-proj-13.ev-1 is readable.
 */

export const NODE_ID_SEPARATOR = ".";

export type AnalysisNodeKind = "criterion" | "rule" | "evidence";

interface BaseNode {
  id: string;
  /** "1", "1.2", "1.2.3": same numbering in the tree, graph and decision document */
  number: string;
  parentId?: string;
  childIds: string[];
}

export interface CriterionNode extends BaseNode {
  kind: "criterion";
  criterion: Criterion;
}

export interface RuleNode extends BaseNode {
  kind: "rule";
  criterion: Criterion;
  rule: Rule;
}

export interface EvidenceNode extends BaseNode {
  kind: "evidence";
  criterion: Criterion;
  rule: Rule;
  evidence: Evidence;
}

export type AnalysisNode = CriterionNode | RuleNode | EvidenceNode;

/** Every node by id, in depth-first (reading) order */
export type AnalysisIndex = Map<string, AnalysisNode>;

export const criterionNodeId = (criterion: Criterion) => criterion.id;

export const ruleNodeId = (criterion: Criterion, rule: Rule) =>
  [criterion.id, rule.id].join(NODE_ID_SEPARATOR);

export const evidenceNodeId = (
  criterion: Criterion,
  rule: Rule,
  evidence: Evidence,
) => [criterion.id, rule.id, evidence.id].join(NODE_ID_SEPARATOR);

export const indexAnalysis = (analysis: Analysis): AnalysisIndex => {
  const index: AnalysisIndex = new Map();

  analysis.criteria.forEach((criterion, ci) => {
    const criterionId = criterionNodeId(criterion);
    const criterionNumber = `${ci + 1}`;
    const criterionEntry: CriterionNode = {
      kind: "criterion",
      id: criterionId,
      number: criterionNumber,
      childIds: [],
      criterion,
    };
    index.set(criterionId, criterionEntry);

    criterion.rules.forEach((rule, ri) => {
      const ruleId = ruleNodeId(criterion, rule);
      const ruleNumber = `${criterionNumber}.${ri + 1}`;
      const ruleEntry: RuleNode = {
        kind: "rule",
        id: ruleId,
        number: ruleNumber,
        parentId: criterionId,
        childIds: [],
        criterion,
        rule,
      };
      criterionEntry.childIds.push(ruleId);
      index.set(ruleId, ruleEntry);

      rule.evidences.forEach((evidence, ei) => {
        const evidenceId = evidenceNodeId(criterion, rule, evidence);
        ruleEntry.childIds.push(evidenceId);
        index.set(evidenceId, {
          kind: "evidence",
          id: evidenceId,
          number: `${ruleNumber}.${ei + 1}`,
          parentId: ruleId,
          childIds: [],
          criterion,
          rule,
          evidence,
        });
      });
    });
  });

  return index;
};

export const numberTree = (analysis: Analysis): Map<string, string> =>
  new Map(
    [...indexAnalysis(analysis).values()].map((node) => [node.id, node.number]),
  );

/** Root criterion → … → node. Empty when the id is unknown. */
export const getNodePath = (
  index: AnalysisIndex,
  nodeId: string,
): AnalysisNode[] => {
  const path: AnalysisNode[] = [];
  let current = index.get(nodeId);
  while (current) {
    path.unshift(current);
    current = current.parentId ? index.get(current.parentId) : undefined;
  }
  return path;
};

/** Ids of every node that has children (criteria and rules with evidences) */
export const getExpandableIds = (index: AnalysisIndex): string[] =>
  [...index.values()]
    .filter((node) => node.childIds.length > 0)
    .map((node) => node.id);

/** Root ids (criteria), in order */
export const getRootIds = (index: AnalysisIndex): string[] =>
  [...index.values()]
    .filter((node) => node.parentId === undefined)
    .map((node) => node.id);

/** Ancestor ids of a node, root first (the node itself is not included) */
export const getAncestorIds = (index: AnalysisIndex, nodeId: string) =>
  getNodePath(index, nodeId)
    .slice(0, -1)
    .map((node) => node.id);

/** Nodes shown when only `expanded` nodes have their children visible, in tree order */
export const getVisibleNodes = (
  index: AnalysisIndex,
  expanded: ReadonlySet<string>,
): AnalysisNode[] =>
  [...index.values()].filter((node) =>
    getAncestorIds(index, node.id).every((id) => expanded.has(id)),
  );

/** Short label for a node, used by the tree, breadcrumb and graph */
export const getNodeTitle = (node: AnalysisNode) => {
  if (node.kind === "criterion") return node.criterion.name;
  if (node.kind === "rule") return `${node.rule.code} ${node.rule.name}`;
  return node.evidence.title;
};
