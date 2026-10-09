import type { AnalysisNode } from "@/domain/tree";

/**
 * Card sizes of the evidence tree. Width is fixed per kind; height grows with
 * the number of lines of the title, so a long name is never cut. The same size
 * feeds the dagre layout, the framing and the card itself.
 */

interface CardMetrics {
  width: number;
  /** Room for the title: width minus horizontal padding and border */
  textWidth: number;
  /** Canvas font of the title (same as the card's Tailwind classes) */
  font: string;
  lineHeight: number;
  /** Height of everything but the title */
  chrome: number;
  /** Design height; short titles keep it */
  minHeight: number;
}

const METRICS: Record<AnalysisNode["kind"], CardMetrics> = {
  // p-3.5 (pr-5: room for the "+N" badge), text-xl/7 semibold
  criterion: { width: 204, textWidth: 170, font: "600 20px Heebo", lineHeight: 28, chrome: 112, minHeight: 176 },
  // p-3 (pr-5: room for the "+N" badge), text-base/5 semibold
  rule: { width: 240, textWidth: 208, font: "600 16px Heebo", lineHeight: 20, chrome: 76, minHeight: 106 },
  // px-4 + border-2, text-base/5 semibold
  evidence: { width: 376, textWidth: 340, font: "600 16px Heebo", lineHeight: 20, chrome: 44, minHeight: 64 },
};

/** Measured widths are padded a little: the web font may still be loading */
const SAFETY = 1.06;
/** Without a canvas (tests), an average Heebo glyph is ~0.56em */
const FALLBACK_EM = 0.56;

let context: CanvasRenderingContext2D | null | undefined;

const measure = (text: string, font: string) => {
  if (context === undefined) {
    context = typeof document === "undefined" ? null : document.createElement("canvas").getContext("2d");
  }
  if (!context) return text.length * FALLBACK_EM * Number.parseFloat(font.split(" ")[1]);
  context.font = `${font}, sans-serif`;
  return context.measureText(text).width;
};

/** Lines a text takes when wrapped at word boundaries (long words break, as `break-words`) */
export const countLines = (text: string, font: string, maxWidth: number): number => {
  const space = measure(" ", font) * SAFETY;
  let lines = 1;
  let current = 0;
  for (const word of text.trim().split(/\s+/)) {
    const width = measure(word, font) * SAFETY;
    if (current > 0 && current + space + width <= maxWidth) {
      current += space + width;
      continue;
    }
    if (current > 0) lines += 1;
    // A word wider than the card wraps inside itself
    lines += Math.max(0, Math.ceil(width / maxWidth) - 1);
    current = width % maxWidth || Math.min(width, maxWidth);
  }
  return lines;
};

const titleOf = (node: AnalysisNode) =>
  node.kind === "criterion" ? node.criterion.name : node.kind === "rule" ? node.rule.name : node.evidence.title;

const cache = new Map<string, { width: number; height: number }>();

export const nodeSize = (node: AnalysisNode): { width: number; height: number } => {
  const title = titleOf(node);
  const key = `${node.kind}:${title}`;
  const cached = cache.get(key);
  if (cached) return { ...cached };
  const m = METRICS[node.kind];
  const lines = countLines(title, m.font, m.textWidth);
  const size = { width: m.width, height: Math.max(m.minHeight, m.chrome + lines * m.lineHeight) };
  cache.set(key, size);
  return { ...size };
};
