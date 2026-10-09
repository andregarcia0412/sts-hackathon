import { Handle, Position } from "@xyflow/react";
import type { NodeProps } from "@xyflow/react";
import { REVIEW_MARKER_STYLES } from "@/components/ui/reviewStyles";
import { SOURCE_ICONS } from "@/components/ui/sourceIcons";
import { Tag } from "@/components/ui/Tag";
import { TONE_SMALL_ICONS, TONE_STYLES } from "@/components/ui/toneStyles";
import { REVIEW_MARKER_LABELS } from "@/domain/contestations";
import type { ReviewMarker } from "@/domain/contestations";
import { evidenceSource } from "@/domain/evidence";
import {
  POLARITY_STATUS,
  RULE_STATUS,
  criterionStatusInfo,
  ruleStatus,
} from "@/domain/qualitative";
import type { AnalysisFlowNode } from "@/features/analysis/graph/graphTypes";
import { nodeSize } from "@/features/analysis/graph/nodeSize";

/*
 * Graph cards of the design system ("Critério", "Regra", "Evidência").
 * Plain React + Tailwind: the graph logic does not depend on them.
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

/** "+7" at the right edge of a collapsed card (overview): there is more behind it */
const CollapsedHint = ({ count, noun }: { count: number; noun: string }) => (
  <span
    className="absolute top-1/2 -right-3 flex h-6 min-w-6 -translate-y-1/2 items-center justify-center rounded-full border border-border-strong bg-surface px-1.5 text-xs font-semibold text-fg-secondary shadow-card"
    title={`${count} ${noun} recolhidas: clique para ver`}
  >
    +{count}
  </span>
);

/** Contested / revised / resolved: icon with an accessible label */
const ReviewIcon = ({ marker, className = "" }: { marker?: ReviewMarker; className?: string }) => {
  if (!marker) return null;
  const { Icon, icon } = REVIEW_MARKER_STYLES[marker];
  return (
    <Icon
      className={`size-3.5 shrink-0 ${className || icon}`}
      aria-label={REVIEW_MARKER_LABELS[marker]}
      role="img"
    />
  );
};

export const CriterionGraphNode = ({ data, selected }: NodeProps<AnalysisFlowNode>) => {
  if (data.node.kind !== "criterion") return null;
  const { criterion, number, childIds } = data.node;
  const status = criterionStatusInfo(criterion);

  return (
    <>
      <Handles target={false} source={childIds.length > 0} />
      <div
        style={nodeSize(data.node)}
        className={`relative flex flex-col justify-center gap-2 rounded-xl bg-brand-deep py-3.5 pr-5 pl-3.5 text-white transition-shadow ${
          selected ? "ring-2 ring-action ring-offset-2" : "hover:shadow-card-accent"
        }`}
      >
        <p className="flex items-center gap-1.5 text-xs leading-4 tracking-[0.06em] text-brand-blush uppercase">
          Critério {number}
          <ReviewIcon marker={data.review} className="text-brand-blush" />
        </p>
        <p className="text-xl leading-7 font-semibold break-words">
          {criterion.name}
        </p>
        <hr className="border-brand-blush" />
        <div className="flex flex-col gap-2 leading-4">
          <p className="text-xs text-brand-blush">Nota sugerida:</p>
          <p className="text-sm font-medium">{status.label}</p>
        </div>
        {!data.expanded && childIds.length > 0 && (
          <CollapsedHint count={childIds.length} noun={childIds.length === 1 ? "regra" : "regras"} />
        )}
      </div>
    </>
  );
};

export const RuleGraphNode = ({ data, selected }: NodeProps<AnalysisFlowNode>) => {
  if (data.node.kind !== "rule") return null;
  const { rule, number, childIds } = data.node;
  const status = RULE_STATUS[ruleStatus(rule)];

  return (
    <>
      <Handles source={childIds.length > 0} />
      <div
        style={nodeSize(data.node)}
        className={`relative flex flex-col items-start justify-center gap-1.5 rounded-2xl py-3 pr-5 pl-3 transition-shadow ${
          selected
            ? "bg-action text-white shadow-card-accent"
            : "bg-surface-muted text-fg shadow-card hover:shadow-card-accent"
        }`}
      >
        <p
          className={`flex min-w-0 items-center gap-1.5 text-xs leading-4 tracking-[0.06em] uppercase ${
            selected ? "text-brand-blush" : "text-fg-subtle"
          }`}
          title={rule.code}
        >
          <span className="truncate">Regra {number}</span>
          <ReviewIcon marker={data.review} className={selected ? "text-white" : ""} />
        </p>
        <p className="w-full text-base leading-5 font-semibold break-words">
          {rule.name}
        </p>
        <Tag tone={status.tone} label={status.short} size="plain" inverted={selected} />
        {!data.expanded && childIds.length > 0 && (
          <CollapsedHint
            count={childIds.length}
            noun={childIds.length === 1 ? "evidência" : "evidências"}
          />
        )}
      </div>
    </>
  );
};

export const EvidenceGraphNode = ({ data, selected }: NodeProps<AnalysisFlowNode>) => {
  if (data.node.kind !== "evidence") return null;
  const { evidence } = data.node;
  const status = POLARITY_STATUS[evidence.polarity];
  const StatusIcon = TONE_SMALL_ICONS[status.tone];
  const source = evidenceSource(evidence);
  const SourceIcon = SOURCE_ICONS[source.kind];

  return (
    <>
      <Handles source={false} />
      <div
        style={nodeSize(data.node)}
        className={`flex flex-col justify-center gap-2 overflow-hidden rounded-2xl border-2 px-4 py-2 shadow-card transition-colors ${
          selected
            ? "border-action bg-accent-soft"
            : data.highlighted
              ? "border-action bg-surface-muted"
              : "border-transparent bg-surface-muted hover:bg-surface"
        }`}
      >
        <p className="text-base leading-5 font-semibold break-words text-fg">
          {evidence.title}
        </p>
        <p className="flex min-w-0 items-center gap-1 text-xs leading-4">
          <StatusIcon className={`size-3 shrink-0 stroke-[2.5] ${TONE_STYLES[status.tone].text}`} aria-hidden />
          <span className={TONE_STYLES[status.tone].text}>{status.label}</span>
          <span className="text-fg-faint" aria-hidden>
            ·
          </span>
          <SourceIcon className="size-4 shrink-0 text-fg-secondary" aria-hidden />
          <span className="truncate text-fg-muted" title={source.label}>
            {source.label}
          </span>
          <ReviewIcon marker={data.review} />
        </p>
      </div>
    </>
  );
};
