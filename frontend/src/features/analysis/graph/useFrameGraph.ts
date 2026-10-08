import { getViewportForBounds, useReactFlow, useStoreApi } from "@xyflow/react";
import type { AnalysisFlowNode } from "@/features/analysis/graph/graphTypes";
import { nodeSize } from "@/features/analysis/graph/nodeSize";

const ANIMATION_MS = 450;
const MIN_FRAME_ZOOM = 0.15;
/** Never zoom in past 100% when framing: big cards look broken */
const MAX_FRAME_ZOOM = 1;

/**
 * Frame a set of positioned nodes. Bounds come from the given positions and
 * the computed card sizes, not from React Flow's measured DOM nodes, so we can
 * frame the *final* layout while the expand/collapse animation is running.
 */
export const useFrameGraph = () => {
  const { setViewport } = useReactFlow<AnalysisFlowNode>();
  const store = useStoreApi<AnalysisFlowNode>();

  return (nodes: AnalysisFlowNode[], padding = 0.12) => {
    if (nodes.length === 0) return;
    const boxes = nodes.map((n) => ({ ...n.position, ...nodeSize(n.data.node) }));
    const x = Math.min(...boxes.map((b) => b.x));
    const y = Math.min(...boxes.map((b) => b.y));
    const right = Math.max(...boxes.map((b) => b.x + b.width));
    const bottom = Math.max(...boxes.map((b) => b.y + b.height));

    const { width, height } = store.getState();
    // Not measured yet (first render): React Flow's own fitView frames it
    if (!width || !height) return;
    const viewport = getViewportForBounds(
      { x, y, width: right - x, height: bottom - y },
      width,
      height,
      MIN_FRAME_ZOOM,
      MAX_FRAME_ZOOM,
      padding,
    );
    void setViewport(viewport, { duration: ANIMATION_MS });
  };
};
