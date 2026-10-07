import {
  Background,
  Controls,
  MiniMap,
  Panel,
  ReactFlow,
} from "@xyflow/react";
import type { AriaLabelConfig } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useEffectEvent, useRef } from "react";
import { scoreBand } from "@/domain/score";
import {
  buildEdges,
  buildGraph,
  layoutGraph,
} from "@/features/analysis/graph/buildGraph";
import { GraphLegend } from "@/features/analysis/graph/GraphLegend";
import type { AnalysisFlowNode } from "@/features/analysis/graph/graphTypes";
import { nodeTypes } from "@/features/analysis/graph/nodeTypes";
import { useAnimatedNodes } from "@/features/analysis/graph/useAnimatedNodes";
import { useFrameGraph } from "@/features/analysis/graph/useFrameGraph";
import type { AnalysisExplorer } from "@/features/analysis/useAnalysisExplorer";

const ARIA_LABELS: Partial<AriaLabelConfig> = {
  "controls.ariaLabel": "Controles do grafo",
  "controls.zoomIn.ariaLabel": "Aproximar",
  "controls.zoomOut.ariaLabel": "Afastar",
  "controls.fitView.ariaLabel": "Enquadrar o grafo inteiro",
  "minimap.ariaLabel": "Minimapa do grafo",
};

/* MiniMap paints with an inline style, so use the theme's CSS variables */
const MINIMAP_COLORS = {
  strong: "var(--color-score-strong)",
  moderate: "var(--color-score-moderate)",
  weak: "var(--color-score-weak)",
  positive: "var(--color-evidence-positive)",
  negative: "var(--color-evidence-negative)",
};

const minimapNodeColor = (node: AnalysisFlowNode) => {
  const { node: entry } = node.data;
  if (entry.kind === "evidence") return MINIMAP_COLORS[entry.evidence.polarity];
  const score = entry.kind === "criterion" ? entry.criterion.score : entry.rule.score;
  return MINIMAP_COLORS[scoreBand(score)];
};

/**
 * Critério → Regras → Evidências, left to right.
 * The selection comes from the URL (via the explorer); clicking a node selects
 * it, clicking it again collapses/expands its children.
 */
export const AnalysisGraph = ({ explorer }: { explorer: AnalysisExplorer }) => {
  const { index, expanded, selectedId, frameRequest, activate } = explorer;
  const frameGraph = useFrameGraph();

  const { nodes: visibleNodes, edges: visibleEdges } = buildGraph(index, expanded);
  const target = layoutGraph(visibleNodes, visibleEdges);

  const { nodes: animatedNodes } = useAnimatedNodes(target);

  /**
   * Frame the final layout (not the animating one): a node and its visible
   * children, or the whole graph. The camera moves together with the nodes.
   */
  const frame = useEffectEvent((nodeId: string | null) => {
    if (!nodeId) {
      frameGraph(target);
      return;
    }
    const branchIds = new Set([nodeId, ...(index.get(nodeId)?.childIds ?? [])]);
    frameGraph(target.filter((n) => branchIds.has(n.id)), 0.25);
  });

  // End of intro, "Ver todos os critérios", "Expandir tudo"
  const onFrameRequest = useEffectEvent(() => {
    if (!frameRequest) return;
    frame(frameRequest.scope === "selection" ? selectedId : null);
  });
  useEffect(() => onFrameRequest(), [frameRequest]);

  // Selection coming from outside the graph (tree, breadcrumb, back button)
  const graphClickRef = useRef<string | null>(null);
  const onSelectionChange = useEffectEvent(() => {
    if (!selectedId) return;
    if (graphClickRef.current === selectedId) {
      graphClickRef.current = null;
      return;
    }
    frame(selectedId);
  });
  useEffect(() => onSelectionChange(), [selectedId]);

  // A graph click that expands a node brings its new children into view;
  // a plain selection keeps the camera still
  const expandedByClickRef = useRef<string | null>(null);
  const onLayoutChange = useEffectEvent(() => {
    const nodeId = expandedByClickRef.current;
    if (!nodeId || !expanded.has(nodeId)) return;
    expandedByClickRef.current = null;
    frame(nodeId);
  });
  useEffect(() => onLayoutChange(), [target]);

  const handleNodeClick = (nodeId: string) => {
    const node = index.get(nodeId);
    if (node && node.childIds.length > 0 && !expanded.has(nodeId)) {
      expandedByClickRef.current = nodeId;
    }
    graphClickRef.current = nodeId;
    activate(nodeId);
  };

  const nodes = animatedNodes.map((n) =>
    n.id === selectedId ? { ...n, selected: true } : n,
  );
  const edges = buildEdges(animatedNodes);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodeClick={(_, node) => handleNodeClick(node.id)}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
      fitView
      fitViewOptions={{ padding: 0.12, maxZoom: 1 }}
      minZoom={0.15}
      maxZoom={1.75}
      ariaLabelConfig={ARIA_LABELS}
      className="bg-canvas"
    >
      <Background gap={24} />
      <Controls showInteractive={false} position="bottom-left" />
      <MiniMap<AnalysisFlowNode>
        pannable
        zoomable
        position="bottom-right"
        nodeColor={minimapNodeColor}
      />
      <Panel position="top-right">
        <GraphLegend />
      </Panel>
    </ReactFlow>
  );
};
