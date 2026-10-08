import { ChevronRight, Flag } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { POLARITY_ICONS, POLARITY_STYLES } from "@/components/ui/polarityStyles";
import { SCORE_BAND_ICONS, SCORE_BAND_STYLES } from "@/components/ui/scoreStyles";
import { SCORE_BAND_LABELS, scoreBand } from "@/domain/score";
import { POLARITY_LABELS } from "@/domain/labels";
import { getNodeTitle, getVisibleNodes } from "@/domain/tree";
import type { AnalysisNode } from "@/domain/tree";
import type { AnalysisExplorer } from "@/features/analysis/useAnalysisExplorer";

const DEPTH: Record<AnalysisNode["kind"], number> = {
  criterion: 1,
  rule: 2,
  evidence: 3,
};

/**
 * Numbered tree (1 / 1.1 / 1.1.1), like the Windows Explorer folder tree.
 * Keyboard (WAI-ARIA tree pattern): ↑/↓ move, → expands or enters,
 * ← collapses or goes to the parent, Enter/Space selects, Home/End jump.
 */
export const AnalysisTree = ({
  explorer,
  contestedIds,
}: {
  explorer: AnalysisExplorer;
  /** Nodes with a recorded contestation (flagged) */
  contestedIds: ReadonlySet<string>;
}) => {
  const { index, expanded, selectedId, introActive, activate, toggle } = explorer;
  const visible = getVisibleNodes(index, expanded);
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const itemRefs = useRef(new Map<string, HTMLLIElement>());

  // Roving tabindex: the focused item, else the selection, else the first item
  const tabStopId =
    [focusedId, selectedId].find((id) => id && visible.some((n) => n.id === id)) ??
    visible[0]?.id;

  // Keep the selection in view (deep links, graph clicks, after the intro collapses)
  useEffect(() => {
    if (selectedId) {
      itemRefs.current.get(selectedId)?.scrollIntoView({ block: "nearest" });
    }
  }, [selectedId, introActive]);

  const focusItem = (id: string | undefined) => {
    if (!id) return;
    setFocusedId(id);
    itemRefs.current.get(id)?.focus();
  };

  const handleKeyDown = (event: KeyboardEvent, node: AnalysisNode) => {
    const position = visible.findIndex((n) => n.id === node.id);
    const hasChildren = node.childIds.length > 0;
    const isOpen = expanded.has(node.id);

    const keyActions: Record<string, () => void> = {
      ArrowDown: () => focusItem(visible[position + 1]?.id),
      ArrowUp: () => focusItem(visible[position - 1]?.id),
      Home: () => focusItem(visible[0]?.id),
      End: () => focusItem(visible.at(-1)?.id),
      ArrowRight: () => {
        if (!hasChildren) return;
        if (isOpen) focusItem(node.childIds[0]);
        else toggle(node.id);
      },
      ArrowLeft: () => {
        if (hasChildren && isOpen) toggle(node.id);
        else focusItem(node.parentId);
      },
      Enter: () => activate(node.id),
      " ": () => activate(node.id),
    };

    const action = keyActions[event.key];
    if (!action) return;
    event.preventDefault();
    event.stopPropagation();
    action();
  };

  return (
    <ul role="tree" aria-label="Critérios, regras e evidências" className="py-1">
      {visible.map((node) => {
        const hasChildren = node.childIds.length > 0;
        const isOpen = expanded.has(node.id);
        const isSelected = node.id === selectedId;
        const depth = DEPTH[node.kind];

        return (
          <li
            key={node.id}
            ref={(el) => {
              if (el) itemRefs.current.set(node.id, el);
              else itemRefs.current.delete(node.id);
            }}
            role="treeitem"
            aria-level={depth}
            aria-selected={isSelected}
            aria-expanded={hasChildren ? isOpen : undefined}
            tabIndex={node.id === tabStopId ? 0 : -1}
            onKeyDown={(e) => handleKeyDown(e, node)}
            onFocus={() => setFocusedId(node.id)}
            onClick={() => activate(node.id)}
            className={`flex cursor-pointer items-center gap-1.5 py-1 pr-2 text-sm outline-offset-[-2px] ${
              isSelected
                ? "bg-accent-soft font-medium text-accent"
                : "hover:bg-surface-muted"
            }`}
            style={{ paddingLeft: `${(depth - 1) * 1.1 + 0.4}rem` }}
          >
            {hasChildren ? (
              <button
                type="button"
                tabIndex={-1}
                aria-hidden
                className="rounded p-0.5 text-fg-muted hover:bg-border"
                onClick={(e) => {
                  e.stopPropagation();
                  toggle(node.id);
                }}
              >
                <ChevronRight
                  className={`size-4 transition-transform ${isOpen ? "rotate-90" : ""}`}
                />
              </button>
            ) : (
              <span className="w-5 shrink-0" />
            )}
            <span className="shrink-0 text-xs text-fg-muted tabular-nums">
              {node.number}
            </span>
            <span className="min-w-0 flex-1 truncate" title={getNodeTitle(node)}>
              {getNodeTitle(node)}
            </span>
            {contestedIds.has(node.id) && (
              <Flag
                className="size-3.5 shrink-0 text-score-moderate"
                aria-label="Contestado pelo analista"
              />
            )}
            <NodeIndicator node={node} />
          </li>
        );
      })}
    </ul>
  );
};

/** Score band (criteria/rules) or polarity (evidences): icon + color + accessible label */
const NodeIndicator = ({ node }: { node: AnalysisNode }) => {
  if (node.kind === "evidence") {
    const { polarity } = node.evidence;
    const Icon = POLARITY_ICONS[polarity];
    return (
      <Icon
        className={`size-4 shrink-0 ${POLARITY_STYLES[polarity].text}`}
        aria-label={`Evidência ${POLARITY_LABELS[polarity].toLowerCase()}`}
      />
    );
  }

  const score = node.kind === "criterion" ? node.criterion.score : node.rule.score;
  const band = scoreBand(score);
  const Icon = SCORE_BAND_ICONS[band];
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-0.5 text-xs font-medium tabular-nums ${SCORE_BAND_STYLES[band].text}`}
      title={`Força da evidência: ${score}/100`}
    >
      <Icon className="size-3.5" aria-hidden />
      {score}
      <span className="sr-only">({SCORE_BAND_LABELS[band]})</span>
    </span>
  );
};
