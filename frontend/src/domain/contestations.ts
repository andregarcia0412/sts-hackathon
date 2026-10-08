import type { Analysis, Contestation } from "@/domain/types";

/**
 * How a node shows up after contestations:
 * - open: someone contested it and the reanalysis was not requested yet
 * - revised: an accepted contestation changed it (score or polarity)
 * - resolved: contested and resolved without changing it
 */
export type ReviewMarker = "open" | "revised" | "resolved";

export const REVIEW_MARKER_LABELS: Record<ReviewMarker, string> = {
  open: "contestado",
  revised: "revisado",
  resolved: "contestação resolvida",
};

export const reviewMarkers = (
  analysis: Analysis,
  contestations: Contestation[],
): Map<string, ReviewMarker> => {
  const markers = new Map<string, ReviewMarker>();
  const own = contestations.filter((c) => c.analysisId === analysis.id);
  for (const c of own) {
    if (c.status === "resolved") markers.set(c.nodeId, "resolved");
  }
  for (const change of analysis.adjustments ?? []) {
    markers.set(change.nodeId, "revised");
  }
  // An open contestation is what needs attention: it wins
  for (const c of own) {
    if (c.status === "open") markers.set(c.nodeId, "open");
  }
  return markers;
};
