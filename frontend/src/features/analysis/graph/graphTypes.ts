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
