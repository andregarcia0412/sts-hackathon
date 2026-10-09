import { Panel, ReactFlow } from "@xyflow/react";
import type { AriaLabelConfig } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useEffectEvent, useRef } from "react";
import type { ReactNode } from "react";
import type { ReviewMarker } from "@/domain/contestations";
import { getAncestorIds } from "@/domain/tree";
import {
  buildEdges,
  buildGraph,
  layoutGraph,
} from "@/features/analysis/graph/buildGraph";
import { GraphLegend } from "@/features/analysis/graph/GraphLegend";
import { ZoomControls } from "@/features/analysis/graph/ZoomControls";
import type { AnalysisFlowEdge } from "@/features/analysis/graph/graphTypes";
import { edgeTypes, nodeTypes } from "@/features/analysis/graph/nodeTypes";
import { useAnimatedNodes } from "@/features/analysis/graph/useAnimatedNodes";
import { useFrameGraph } from "@/features/analysis/graph/useFrameGraph";
import type { AnalysisExplorer } from "@/features/analysis/useAnalysisExplorer";

const ARIA_LABELS: Partial<AriaLabelConfig> = {
  "controls.ariaLabel": "Controles da árvore",
  "controls.zoomIn.ariaLabel": "Aproximar",
  "controls.zoomOut.ariaLabel": "Afastar",
  "controls.fitView.ariaLabel": "Enquadrar a árvore inteira",
};

/* Whole tree: clear of the view/method toggles (top) and the zoom controls (left) */
const WHOLE_TREE_PADDING = { top: "64px", right: "24px", bottom: "24px", left: "56px" } as const;
/*
 * "Critério" view: a real criterion has ~18 rules. Fitting all of them would
 * shrink the cards past reading; below this zoom the column is cropped
 * (centered on the criterion card) and the analyst pans or scrolls.
 */
const CRITERION_VIEW_MIN_ZOOM = 0.5;

/* Edges paint with inline styles, so use the theme's CSS variables */
const EDGE_STYLE = { stroke: "var(--color-border-strong)", strokeWidth: 1.5 };
const EDGE_ON_PATH_STYLE = { stroke: "var(--color-accent)", strokeWidth: 2 };

/**
 * Critério → Regras → Evidências, left to right.
 * The selection comes from the URL (via the explorer); clicking a node selects
 * it, and in the overview clicking it again collapses/expands its children.
 */
export const AnalysisGraph = ({
  explorer,
  reviewMarkers,
  toolbar,
}: {
  explorer: AnalysisExplorer;
  reviewMarkers: ReadonlyMap<string, ReviewMarker>;
  /** Controls shown in the top-right corner (view, method) */
  toolbar?: ReactNode;
}) => {
  const { index, expanded, selectedId, frameRequest, activate, select, view, focusCriterionId } =
    explorer;
  const frameGraph = useFrameGraph();

  const { nodes: visibleNodes, edges: visibleEdges } = buildGraph(
    index,
    expanded,
    reviewMarkers,
    view === "criterion" ? focusCriterionId : undefined,
  );
  const target = layoutGraph(visibleNodes, visibleEdges);

  const { nodes: animatedNodes } = useAnimatedNodes(target);

  /**
   * Frame the final layout (not the animating one): a node and its visible
   * children, or the whole graph. The camera moves together with the nodes.
   */
  const frame = useEffectEvent((nodeId: string | null, durationMs?: number) => {
    if (!nodeId) {
      frameGraph(target, WHOLE_TREE_PADDING, durationMs, view === "criterion" ? CRITERION_VIEW_MIN_ZOOM : undefined);
      return;
    }
    const branchIds = new Set([nodeId, ...(index.get(nodeId)?.childIds ?? [])]);
    frameGraph(target.filter((n) => branchIds.has(n.id)), 0.25);
  });

  // End of intro, switching views
  const onFrameRequest = useEffectEvent(() => {
    if (!frameRequest) return;
    frame(frameRequest.scope === "selection" ? selectedId : null, frameRequest.durationMs);
  });
  useEffect(() => onFrameRequest(), [frameRequest]);

  // Criterion view: a new criterion on screen is framed whole
  const onFocusChange = useEffectEvent(() => {
    if (view === "criterion") frame(null);
  });
  useEffect(() => onFocusChange(), [focusCriterionId]);

  // Overview: selection coming from outside the graph (panel, back button)
  const graphClickRef = useRef<string | null>(null);
  const onSelectionChange = useEffectEvent(() => {
    if (!selectedId || view === "criterion") return;
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
    // Criterion view shows everything already: a click only selects
    if (view === "criterion") {
      select(nodeId);
      return;
    }
    const node = index.get(nodeId);
    if (node && node.childIds.length > 0 && !expanded.has(nodeId)) {
      expandedByClickRef.current = nodeId;
    }
    graphClickRef.current = nodeId;
    activate(nodeId);
  };

  const nodes = animatedNodes.map((n) =>
    n.id === selectedId
      ? { ...n, selected: true }
      : selectedId && n.data.node.parentId === selectedId
        ? { ...n, data: { ...n.data, highlighted: true } }
        : n,
  );

  // Path of the selection in wine: criterion → rule → its evidences
  const onPath = new Set(selectedId ? [...getAncestorIds(index, selectedId), selectedId] : []);
  const edges: AnalysisFlowEdge[] = buildEdges(animatedNodes).map((edge) => {
    const highlighted = onPath.has(edge.target) || edge.source === selectedId;
    return {
      ...edge,
      type: "bracket",
      style: highlighted ? EDGE_ON_PATH_STYLE : EDGE_STYLE,
      zIndex: highlighted ? 1 : 0,
    };
  });

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onNodeClick={(_, node) => handleNodeClick(node.id)}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
      fitView
      fitViewOptions={{
        padding: 0.08,
        maxZoom: 1,
        minZoom: view === "criterion" ? CRITERION_VIEW_MIN_ZOOM : undefined,
      }}
      minZoom={0.15}
      maxZoom={1.75}
      ariaLabelConfig={ARIA_LABELS}
      attributionPosition="bottom-right"
      className="!bg-transparent"
    >
      {toolbar && (
        <Panel position="top-right" className="flex flex-wrap justify-end gap-2">
          {toolbar}
        </Panel>
      )}
      <Panel position="bottom-left" className="max-md:hidden">
        <GraphLegend />
      </Panel>
      <Panel position="top-left">
        <ZoomControls onFit={() => frameGraph(target)} />
      </Panel>
    </ReactFlow>
  );
};
