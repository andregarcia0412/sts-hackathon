import type { EdgeTypes, NodeTypes } from "@xyflow/react";
import { BracketEdge } from "@/features/analysis/graph/BracketEdge";
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

export const edgeTypes = { bracket: BracketEdge } satisfies EdgeTypes;
