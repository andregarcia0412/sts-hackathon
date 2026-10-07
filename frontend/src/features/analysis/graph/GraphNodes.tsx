import { Handle, NodeToolbar, Position } from "@xyflow/react";
import type { NodeProps } from "@xyflow/react";
import { ChevronRight } from "lucide-react";
import { useState } from "react";
import type { ReactNode } from "react";
import { ScoreBadge } from "@/components/ui/ScoreBadge";
import { POLARITY_ICONS, POLARITY_STYLES } from "@/components/ui/polarityStyles";
import { SCORE_BAND_STYLES } from "@/components/ui/scoreStyles";
import { POLARITY_LABELS } from "@/domain/labels";
import { scoreBand } from "@/domain/score";
import { NODE_SIZES } from "@/features/analysis/graph/graphTypes";
import type { AnalysisFlowNode } from "@/features/analysis/graph/graphTypes";

/*
 * Custom nodes are plain React + Tailwind, so the designer's visual can be
 * applied here without touching the graph logic.
 */

const hiddenHandle = "!size-1 !min-w-0 !border-0 !bg-transparent";

const Handles = ({ target = true, source = true }) => (
  <>
    {target && (
      <Handle type="target" position={Position.Left} isConnectable={false} className={hiddenHandle} />
    )}
    {source && (
      <Handle type="source" position={Position.Right} isConnectable={false} className={hiddenHandle} />
    )}
  </>
);

const ExpandHint = ({ expanded, count, noun }: { expanded: boolean; count: number; noun: string }) => (
  <span className="inline-flex items-center gap-0.5 text-xs text-fg-muted">
    <ChevronRight
      className={`size-3.5 transition-transform ${expanded ? "rotate-90" : ""}`}
      aria-hidden
    />
    {count} {noun}
  </span>
);

const Card = ({
  selected,
  band,
  size,
  children,
}: {
  selected: boolean;
  band: ReturnType<typeof scoreBand>;
  size: { width: number; height: number };
  children: ReactNode;
}) => (
  <div
    style={size}
    className={`flex flex-col justify-between overflow-hidden rounded-lg border border-l-4 bg-surface px-3 py-2 shadow-sm transition-shadow ${
      SCORE_BAND_STYLES[band].border
    } ${selected ? "ring-2 ring-accent ring-offset-1" : "hover:shadow-md"}`}
  >
    {children}
  </div>
);

export const CriterionGraphNode = ({ data, selected }: NodeProps<AnalysisFlowNode>) => {
  if (data.node.kind !== "criterion") return null;
  const { criterion, number, childIds } = data.node;

  return (
    <>
      <Handles target={false} source={childIds.length > 0} />
      <Card selected={selected} band={scoreBand(criterion.score)} size={NODE_SIZES.criterion}>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-xs text-fg-muted">Critério {number}</p>
            <p className="truncate text-base font-semibold">{criterion.name}</p>
          </div>
          <ScoreBadge score={criterion.score} />
        </div>
        <ExpandHint
          expanded={data.expanded}
          count={childIds.length}
          noun={childIds.length === 1 ? "regra" : "regras"}
        />
      </Card>
    </>
  );
};

export const RuleGraphNode = ({ data, selected }: NodeProps<AnalysisFlowNode>) => {
  if (data.node.kind !== "rule") return null;
  const { rule, number, childIds } = data.node;

  return (
    <>
      <Handles source={childIds.length > 0} />
      <Card selected={selected} band={scoreBand(rule.score)} size={NODE_SIZES.rule}>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-xs text-fg-muted">
              {number} · <span className="font-medium text-fg">{rule.code}</span>
            </p>
            <p className="line-clamp-2 text-sm leading-tight font-medium" title={rule.name}>
              {rule.name}
            </p>
          </div>
          <ScoreBadge score={rule.score} size="sm" />
        </div>
        <ExpandHint
          expanded={data.expanded}
          count={childIds.length}
          noun={childIds.length === 1 ? "evidência" : "evidências"}
        />
      </Card>
    </>
  );
};

export const EvidenceGraphNode = ({ data, selected }: NodeProps<AnalysisFlowNode>) => {
  const [hovered, setHovered] = useState(false);
  if (data.node.kind !== "evidence") return null;
  const { evidence, number } = data.node;
  const styles = POLARITY_STYLES[evidence.polarity];
  const Icon = POLARITY_ICONS[evidence.polarity];
  const polarityLabel = `Evidência ${POLARITY_LABELS[evidence.polarity].toLowerCase()}`;
  const mainReference = evidence.references[0];

  return (
    <>
      <Handles source={false} />
      <NodeToolbar isVisible={hovered} position={Position.Top}>
        <div
          role="tooltip"
          className="max-w-72 rounded-md bg-fg px-3 py-2 text-xs text-surface shadow-lg"
        >
          <p className="font-semibold">{polarityLabel}</p>
          {mainReference && <p className="mt-0.5 opacity-80">{mainReference.label}</p>}
          {evidence.projectExcerpt?.fileName && (
            <p className="mt-0.5 opacity-80">
              {evidence.projectExcerpt.fileName}
              {evidence.projectExcerpt.page !== undefined &&
                `, p. ${evidence.projectExcerpt.page}`}
            </p>
          )}
        </div>
      </NodeToolbar>
      <div
        style={NODE_SIZES.evidence}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        className={`flex items-center gap-2 rounded-full border bg-surface py-1 pr-3 pl-1 shadow-sm ${
          styles.border
        } ${selected ? "ring-2 ring-accent ring-offset-1" : ""}`}
      >
        <span
          className={`flex size-9 shrink-0 items-center justify-center rounded-full ${styles.soft} ${styles.text}`}
        >
          <Icon className="size-5" aria-label={polarityLabel} />
        </span>
        <span className="min-w-0">
          <span className="block text-[11px] leading-none text-fg-muted">{number}</span>
          <span className="line-clamp-2 text-xs leading-tight font-medium" title={evidence.title}>
            {evidence.title}
          </span>
        </span>
      </div>
    </>
  );
};
