import { BaseEdge, useStore } from "@xyflow/react";
import type { EdgeProps } from "@xyflow/react";
import { bracketPath } from "@/features/analysis/graph/bracketPath";

/**
 * Card-to-card connector drawn like the Figma (see bracketPath). Zoomed out,
 * the line keeps its width on screen: a real criterion has ~18 rules, the tree
 * is framed far below 100% and a scaled 1.5px line would vanish. (CSS
 * `vector-effect` does not help: React Flow zooms with a CSS transform.)
 */
export const BracketEdge = ({ id, sourceX, sourceY, targetX, targetY, style, markerEnd }: EdgeProps) => {
  const zoom = useStore((state) => state.transform[2]);
  const width = Number(style?.strokeWidth ?? 1) / Math.min(zoom, 1);
  return (
    <BaseEdge
      id={id}
      path={bracketPath(sourceX, sourceY, targetX, targetY)}
      style={{ ...style, strokeWidth: width }}
      markerEnd={markerEnd}
    />
  );
};
