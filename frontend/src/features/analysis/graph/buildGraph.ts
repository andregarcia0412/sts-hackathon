import { Graph, layout } from "@dagrejs/dagre";
import type { ReviewMarker } from "@/domain/contestations";
import { getVisibleNodes, isInSubtree } from "@/domain/tree";
import type { AnalysisIndex } from "@/domain/tree";
import { NODE_SIZES } from "@/features/analysis/graph/graphTypes";
import type {
  AnalysisFlowEdge,
  AnalysisFlowNode,
} from "@/features/analysis/graph/graphTypes";

const RANK_SEPARATION = 40;
const NODE_SEPARATION = 8;

/**
 * Visible part of the analysis as React Flow nodes (positions not set yet).
 * Critério → Regras → Evidências, only below expanded nodes.
 * With `rootId`, only that criterion's branch.
 */
export const buildGraph = (
  index: AnalysisIndex,
  expanded: ReadonlySet<string>,
  reviewMarkers: ReadonlyMap<string, ReviewMarker> = new Map(),
  rootId?: string,
): { nodes: AnalysisFlowNode[]; edges: AnalysisFlowEdge[] } => {
  const visible = getVisibleNodes(index, expanded).filter(
    (node) => !rootId || isInSubtree(node.id, rootId),
  );
  const nodes: AnalysisFlowNode[] = visible.map(
    (node) => ({
      id: node.id,
      type: node.kind,
      position: { x: 0, y: 0 },
      ...NODE_SIZES[node.kind],
      data: {
        node,
        expanded: expanded.has(node.id),
        review: reviewMarkers.get(node.id),
      },
    }),
  );
  return { nodes, edges: buildEdges(nodes) };
};

/** Parent → child edges between the given nodes */
export const buildEdges = (nodes: AnalysisFlowNode[]): AnalysisFlowEdge[] => {
  const ids = new Set(nodes.map((n) => n.id));
  return nodes.flatMap((n) => {
    const parentId = n.data.node.parentId;
    if (!parentId || !ids.has(parentId)) return [];
    return [{ id: `${parentId}->${n.id}`, source: parentId, target: n.id }];
  });
};

/** Left-to-right layered layout (dagre). Positions are top-left corners. */
export const layoutGraph = (
  nodes: AnalysisFlowNode[],
  edges: AnalysisFlowEdge[],
): AnalysisFlowNode[] => {
  const graph = new Graph();
  graph.setGraph({
    rankdir: "LR",
    ranksep: RANK_SEPARATION,
    nodesep: NODE_SEPARATION,
  });
  graph.setDefaultEdgeLabel(() => ({}));

  for (const node of nodes) {
    // dagre writes x/y into the label object: never pass the shared constant
    graph.setNode(node.id, { ...NODE_SIZES[node.data.node.kind] });
  }
  for (const edge of edges) {
    graph.setEdge(edge.source, edge.target);
  }

  // Keep insertion (= numbering) order instead of dagre's crossing
  // minimisation: a tree has no crossings anyway, and 1.1 must stay above 1.2
  layout(graph, { disableOptimalOrderHeuristic: true });

  return nodes.map((node) => {
    const { x, y } = graph.node(node.id);
    const { width, height } = NODE_SIZES[node.data.node.kind];
    return { ...node, position: { x: x - width / 2, y: y - height / 2 } };
  });
};
