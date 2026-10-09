import { BaseEdge } from "@xyflow/react";
import type { EdgeProps } from "@xyflow/react";
import { bracketPath } from "@/features/analysis/graph/bracketPath";

/** Card-to-card connector drawn like the Figma (see bracketPath) */
export const BracketEdge = ({ id, sourceX, sourceY, targetX, targetY, style, markerEnd }: EdgeProps) => (
  <BaseEdge id={id} path={bracketPath(sourceX, sourceY, targetX, targetY)} style={style} markerEnd={markerEnd} />
);
