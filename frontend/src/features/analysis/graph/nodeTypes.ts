import type { NodeTypes } from "@xyflow/react";
import {
  CriterionGraphNode,
  EvidenceGraphNode,
  RuleGraphNode,
} from "@/features/analysis/graph/GraphNodes";

/** Module-level so React Flow never sees a new object between renders */
export const nodeTypes = {
  criterion: CriterionGraphNode,
  rule: RuleGraphNode,
  evidence: EvidenceGraphNode,
} satisfies NodeTypes;
