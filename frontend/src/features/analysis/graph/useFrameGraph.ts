import { getViewportForBounds, useReactFlow, useStoreApi } from "@xyflow/react";
import type { AnalysisFlowNode } from "@/features/analysis/graph/graphTypes";
import { nodeSize } from "@/features/analysis/graph/nodeSize";

/** Same padding type React Flow takes (a number or per side, e.g. "64px") */
type Padding = Parameters<typeof getViewportForBounds>[5];

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

  /**
   * `minZoom` above the default keeps the cards readable: the camera then
   * shows the middle of the bounds and the rest is reached by panning.
   */
  return (nodes: AnalysisFlowNode[], padding: Padding = 0.12, durationMs = ANIMATION_MS, minZoom = MIN_FRAME_ZOOM) => {
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
      minZoom,
      MAX_FRAME_ZOOM,
      padding,
    );
    void setViewport(viewport, { duration: durationMs });
  };
};
