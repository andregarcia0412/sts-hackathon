import type { Edge, Node } from "@xyflow/react";
import type { ReviewMarker } from "@/domain/contestations";
import type { AnalysisNode } from "@/domain/tree";

export type GraphNodeData = {
  node: AnalysisNode;
  /** Children currently visible in the graph */
  expanded: boolean;
  /** Contested / revised / resolved, if any */
  review?: ReviewMarker;
  /** Child of the selected node (outlined, as the design shows the rule's evidences) */
  highlighted?: boolean;
};

export type AnalysisFlowNode = Node<GraphNodeData, AnalysisNode["kind"]>;

export type AnalysisFlowEdge = Edge;

/** Fixed node sizes: used by the dagre layout and by the node components */
export const NODE_SIZES: Record<
  AnalysisNode["kind"],
  { width: number; height: number }
> = {
  criterion: { width: 204, height: 176 },
  rule: { width: 240, height: 106 },
  evidence: { width: 376, height: 60 },
};
