import { useEffect, useState } from "react";
import { useSelectedNode } from "@/features/analysis/useSelectedNode";
import {
  getAncestorIds,
  getExpandableIds,
  getNodePath,
  getRootIds,
  indexAnalysis,
  isInSubtree,
} from "@/domain/tree";
import type { Analysis } from "@/domain/types";

interface FrameRequest {
  /** "selection" falls back to the whole graph when nothing is selected */
  scope: "all" | "selection";
}

/** How long the fully expanded overview stays on screen before collapsing */
export const INTRO_HOLD_MS = 1800;

/**
 * criterion: the graph shows one criterion with all its rules and evidences
 * (default, as in the design); overview: the 5 criteria, expandable.
 */
export type GraphView = "criterion" | "overview";

/**
 * Selection + expansion state shared by the tree, the graph, the breadcrumb
 * and the detail panel.
 *
 * The graph starts on the criterion of the selection (the first one when
 * nothing is selected). "Mapa geral" shows every criterion: there, the intro
 * expands everything (overview of the whole analysis) and then collapses to
 * the 5 criteria. Any user interaction ends the intro early.
 *
 * The selected node's ancestors are always expanded, so a deep link or the
 * browser's back button always reveals the selection.
 */
export const useAnalysisExplorer = (analysis: Analysis) => {
  const index = indexAnalysis(analysis);
  const { selectedId: rawSelectedId, select } = useSelectedNode();
  const selectedId =
    rawSelectedId && index.has(rawSelectedId) ? rawSelectedId : null;

  const [view, setViewState] = useState<GraphView>("criterion");
  const [introActive, setIntroActive] = useState(false);
  const [introPlayed, setIntroPlayed] = useState(false);
  const focusCriterionId =
    (selectedId ? getNodePath(index, selectedId)[0]?.id : undefined) ?? getRootIds(index)[0];
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(new Set());
  /**
   * Asks the graph to re-frame. Explicit scope instead of reading the selection
   * later: router updates arrive in a transition, after this state.
   */
  const [frameRequest, setFrameRequest] = useState<FrameRequest | null>(null);
  const requestFrame = (scope: FrameRequest["scope"]) => setFrameRequest({ scope });

  useEffect(() => {
    if (!introActive) return;
    const timer = setTimeout(() => {
      setIntroActive(false);
      // Collapsed to the criteria: show all of them
      requestFrame("all");
    }, INTRO_HOLD_MS);
    return () => clearTimeout(timer);
  }, [introActive]);

  const effectiveExpanded: ReadonlySet<string> =
    view === "criterion"
      ? new Set(getExpandableIds(index).filter((id) => isInSubtree(id, focusCriterionId)))
      : introActive
        ? new Set(getExpandableIds(index))
        : new Set([
            ...expanded,
            ...(selectedId ? getAncestorIds(index, selectedId) : []),
          ]);

  const setView = (next: GraphView) => {
    if (next === view) return;
    setViewState(next);
    // The expand-then-collapse intro plays the first time the overview opens
    if (next === "overview" && !introPlayed) {
      setIntroPlayed(true);
      setIntroActive(true);
    } else {
      setIntroActive(false);
      requestFrame(next === "criterion" ? "all" : "selection");
    }
  };

  const setExpandedAfterIntro = (
    update: (current: ReadonlySet<string>) => ReadonlySet<string>,
  ) => {
    setIntroActive(false);
    setExpanded(update);
  };

  const toggle = (nodeId: string) => {
    const isOpen = effectiveExpanded.has(nodeId);
    setExpandedAfterIntro((current) => {
      const next = new Set(current);
      if (isOpen) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
    // Collapsing a branch that hides the selection moves it up (as in Explorer)
    if (isOpen && selectedId && getAncestorIds(index, selectedId).includes(nodeId)) {
      select(nodeId);
    }
  };

  /** Click on a node: select it and show its children; click again to collapse */
  const activate = (nodeId: string) => {
    if (nodeId === selectedId) {
      toggle(nodeId);
      return;
    }
    select(nodeId);
    setExpandedAfterIntro((current) => new Set([...current, nodeId]));
  };

  const collapseAll = () => {
    setExpandedAfterIntro(() => new Set());
    select(null);
    requestFrame("all");
  };

  const expandAll = () => {
    setExpandedAfterIntro(() => new Set(getExpandableIds(index)));
    requestFrame("all");
  };

  return {
    index,
    view,
    setView,
    /** Criterion shown by the graph in "criterion" view */
    focusCriterionId,
    selectedId,
    selectedNode: selectedId ? index.get(selectedId) : undefined,
    expanded: effectiveExpanded,
    introActive,
    frameRequest,
    select,
    activate,
    toggle,
    collapseAll,
    expandAll,
  };
};

export type AnalysisExplorer = ReturnType<typeof useAnalysisExplorer>;
