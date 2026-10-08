import type { Edge, Node } from "@xyflow/react";
import type { AnalysisNode } from "@/domain/tree";

export type GraphNodeData = {
  node: AnalysisNode;
  /** Children currently visible in the graph */
  expanded: boolean;
  /** An analyst recorded a contestation for this node */
  contested: boolean;
};

export type AnalysisFlowNode = Node<GraphNodeData, AnalysisNode["kind"]>;

export type AnalysisFlowEdge = Edge;

/** Fixed node sizes: used by the dagre layout and by the node components */
export const NODE_SIZES: Record<
  AnalysisNode["kind"],
  { width: number; height: number }
> = {
  criterion: { width: 248, height: 92 },
  rule: { width: 248, height: 84 },
  evidence: { width: 232, height: 52 },
};
