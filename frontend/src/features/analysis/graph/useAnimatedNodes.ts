import { useEffect, useRef, useState } from "react";
import type { XYPosition } from "@xyflow/react";
import type { AnalysisFlowNode } from "@/features/analysis/graph/graphTypes";

const DURATION_MS = 450;

const easeInOutCubic = (t: number) =>
  t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;

const lerp = (a: XYPosition, b: XYPosition, t: number): XYPosition => ({
  x: a.x + (b.x - a.x) * t,
  y: a.y + (b.y - a.y) * t,
});

/** Position of the closest ancestor present in `nodes` */
const ancestorPosition = (
  node: AnalysisFlowNode,
  nodes: Map<string, AnalysisFlowNode>,
): XYPosition | undefined => {
  let parentId = node.data.node.parentId;
  while (parentId) {
    const parent = nodes.get(parentId);
    if (parent) return parent.position;
    // Walk up through the index entry of the missing parent
    parentId = parentId.split(".").slice(0, -1).join(".") || undefined;
  }
  return undefined;
};

const sameLayout = (a: AnalysisFlowNode[], b: AnalysisFlowNode[]) =>
  a.length === b.length &&
  a.every(
    (n, i) =>
      n.id === b[i].id &&
      n.position.x === b[i].position.x &&
      n.position.y === b[i].position.y,
  );

/**
 * Animates layout changes so expanding/collapsing reads as motion:
 * new nodes grow out of their parent, removed nodes shrink back into it.
 * Edges are derived from the rendered nodes, so they follow along.
 * Respects prefers-reduced-motion.
 */
export const useAnimatedNodes = (target: AnalysisFlowNode[]) => {
  const [rendered, setRendered] = useState(target);
  const renderedRef = useRef(target);

  useEffect(() => {
    const from = renderedRef.current;
    const commit = (nodes: AnalysisFlowNode[]) => {
      renderedRef.current = nodes;
      setRendered(nodes);
    };

    if (sameLayout(from, target)) {
      // Same structure (e.g. only data changed): no motion needed
      commit(target);
      return;
    }

    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (reduceMotion) {
      commit(target);
      return;
    }

    const fromById = new Map(from.map((n) => [n.id, n]));
    const targetById = new Map(target.map((n) => [n.id, n]));

    const tracks = [
      ...target.map((node) => {
        const previous = fromById.get(node.id);
        return {
          node,
          start: previous?.position ?? ancestorPosition(node, fromById) ?? node.position,
          end: node.position,
          fade: previous ? null : ("in" as const),
        };
      }),
      ...from
        .filter((node) => !targetById.has(node.id))
        .map((node) => ({
          node,
          start: node.position,
          end: ancestorPosition(node, targetById) ?? node.position,
          fade: "out" as const,
        })),
    ];

    const startedAt = performance.now();
    let frame = 0;

    const step = (now: number) => {
      const progress = Math.min(1, (now - startedAt) / DURATION_MS);
      if (progress >= 1) {
        commit(target);
        return;
      }
      const t = easeInOutCubic(progress);
      commit(
        tracks.map(({ node, start, end, fade }) => ({
          ...node,
          position: lerp(start, end, t),
          style: fade
            ? { ...node.style, opacity: fade === "in" ? t : 1 - t }
            : node.style,
        })),
      );
      frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);

    return () => cancelAnimationFrame(frame);
  }, [target]);

  return { nodes: rendered };
};
