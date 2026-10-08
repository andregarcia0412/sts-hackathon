import { ChevronDown, ChevronRight, TriangleAlert } from "lucide-react";
import { useEffect, useRef } from "react";
import { KeyboardArrowDownIcon, KeyboardArrowRightIcon } from "@/components/icons/MaterialIcons";
import { ReferenceLink } from "@/components/ui/ReferenceLink";
import { Tag } from "@/components/ui/Tag";
import { latestByNode } from "@/domain/reviews";
import {
  CRITERION_STATUS,
  RULE_STATUS,
  criterionStatus,
  ruleStatus,
} from "@/domain/qualitative";
import { getNodePath } from "@/domain/tree";
import type { CriterionNode, RuleNode } from "@/domain/tree";
import type {
  Analysis,
  AnalysisChange,
  Contestation,
  EvidenceReview,
  RuleDecision,
} from "@/domain/types";
import {
  ContestationList,
  Field,
  QuestionButton,
  RevisionNote,
  ScoreDisclosure,
} from "@/features/analysis/detail/DetailParts";
import { EvidenceCard } from "@/features/analysis/detail/EvidenceCard";
import { RuleDecisionDock } from "@/features/analysis/detail/RuleDecisionDock";
import type { AnalysisExplorer } from "@/features/analysis/useAnalysisExplorer";

interface DetailPanelProps {
  explorer: AnalysisExplorer;
  projectId: string;
  /** Analysis on screen (with adjustments from accepted contestations) */
  analysis: Analysis;
  /** Contestations of this analysis */
  contestations: Contestation[];
  ruleDecisions: RuleDecision[];
  evidenceReviews: EvidenceReview[];
  className?: string;
}

/**
 * "Detalhamento de informações": the criteria as an accordion. The selection
 * (URL) decides what is open: its criterion, its rule and its evidence. Every
 * score leads to the rule text, the project excerpt and the norm.
 */
export const DetailPanel = ({
  explorer,
  projectId,
  analysis,
  contestations,
  ruleDecisions,
  evidenceReviews,
  className = "",
}: DetailPanelProps) => {
  const { index, selectedId, focusCriterionId } = explorer;
  const path = selectedId ? getNodePath(index, selectedId) : [];
  const openRule = path.find((n): n is RuleNode => n.kind === "rule");
  const decisions = latestByNode(ruleDecisions, analysis.id);
  const reviews = latestByNode(evidenceReviews, analysis.id);
  const changesOf = (nodeId: string) =>
    (analysis.adjustments ?? []).filter((a) => a.nodeId === nodeId);
  const contestationsOf = (nodeId: string) => contestations.filter((c) => c.nodeId === nodeId);

  // Keep the selection in view (graph clicks, deep links)
  const scrollRef = useRef<HTMLDivElement>(null);
  // (scrolls only the panel: scrollIntoView would also move the page on small screens)
  useEffect(() => {
    const container = scrollRef.current;
    if (!selectedId || !container) return;
    const target = container.querySelector<HTMLElement>(`[data-node="${CSS.escape(selectedId)}"]`);
    if (!target) return;
    // Opening an item swaps the clicked button for the open card: keep keyboard focus on it
    if (document.activeElement === document.body) {
      (target.matches("button") ? target : target.querySelector("button"))?.focus({
        preventScroll: true,
      });
    }
    const box = container.getBoundingClientRect();
    const item = target.getBoundingClientRect();
    const margin = 8;
    if (item.top < box.top || item.height > box.height) {
      container.scrollBy({ top: item.top - box.top - margin, behavior: "smooth" });
    } else if (item.bottom > box.bottom) {
      container.scrollBy({ top: item.bottom - box.bottom + margin, behavior: "smooth" });
    }
  }, [selectedId]);

  const criteria = [...index.values()].filter((n): n is CriterionNode => n.kind === "criterion");

  return (
    <section
      aria-label="Detalhamento de informações"
      className={`flex flex-col rounded-2xl border-r border-border bg-white/80 lg:min-h-0 lg:overflow-hidden ${className}`}
    >
      <h2 className="shrink-0 px-4 pt-4 pb-3 text-xl leading-6 font-semibold">
        Detalhamento de informações
      </h2>
      {/* Desktop: this list scrolls and the decision stays docked; phone: everything flows with the page */}
      <div ref={scrollRef} className="flex flex-col gap-1 px-4 pb-4 lg:min-h-0 lg:flex-1 lg:overflow-y-auto">
        {criteria.map((node) =>
          node.id === focusCriterionId ? (
            <OpenCriterion
              key={node.id}
              node={node}
              explorer={explorer}
              showInfo={!openRule}
              openRuleId={openRule?.id}
              projectId={projectId}
              analysisId={analysis.id}
              decisions={decisions}
              reviews={reviews}
              changesOf={changesOf}
              contestationsOf={contestationsOf}
            />
          ) : (
            <ClosedCriterion key={node.id} node={node} onOpen={() => explorer.select(node.id)} />
          ),
        )}
      </div>
      {openRule && (
        <RuleDecisionDock
          key={openRule.id}
          node={openRule}
          projectId={projectId}
          analysisId={analysis.id}
          current={decisions.get(openRule.id)}
        />
      )}
    </section>
  );
};

const ClosedCriterion = ({ node, onOpen }: { node: CriterionNode; onOpen: () => void }) => {
  const status = CRITERION_STATUS[criterionStatus(node.criterion)];
  return (
    <button
      type="button"
      data-node={node.id}
      onClick={onOpen}
      aria-expanded={false}
      className="flex w-full items-center gap-2 rounded-md px-2 py-2.5 text-left transition-colors hover:bg-surface-sunken/60"
    >
      <ChevronRight className="size-3.5 shrink-0 text-fg-secondary" strokeWidth={2.5} aria-hidden />
      <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-surface-sunken text-xs leading-4 font-semibold text-fg-secondary">
        {node.number}
      </span>
      <span className="min-w-0 flex-1 text-sm leading-5 font-semibold">{node.criterion.name}</span>
      <Tag tone={status.tone} label={status.label} size="sm" />
    </button>
  );
};

interface OpenCriterionProps {
  node: CriterionNode;
  explorer: AnalysisExplorer;
  /** The criterion itself is selected (no rule open): show its summary */
  showInfo: boolean;
  openRuleId?: string;
  projectId: string;
  analysisId: string;
  decisions: ReadonlyMap<string, RuleDecision>;
  reviews: ReadonlyMap<string, EvidenceReview>;
  changesOf: (nodeId: string) => AnalysisChange[];
  contestationsOf: (nodeId: string) => Contestation[];
}

const OpenCriterion = ({
  node,
  explorer,
  showInfo,
  openRuleId,
  decisions,
  changesOf,
  contestationsOf,
  ...rest
}: OpenCriterionProps) => {
  const status = CRITERION_STATUS[criterionStatus(node.criterion)];
  const rules = node.childIds
    .map((id) => explorer.index.get(id))
    .filter((n): n is RuleNode => n?.kind === "rule");

  return (
    <div className="flex flex-col gap-1">
      <button
        type="button"
        data-node={node.id}
        aria-expanded
        onClick={() => explorer.select(node.id)}
        className="flex w-full items-center gap-2 rounded-2xl border-2 border-action p-2 text-left"
      >
        <KeyboardArrowDownIcon className="size-6 shrink-0 text-action" />
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-action text-base leading-4 font-bold text-white">
          {node.number}
        </span>
        <span className="min-w-0 flex-1 text-base leading-5 font-semibold">{node.criterion.name}</span>
        <Tag tone={status.tone} label={status.label} />
      </button>

      <div className="flex flex-col gap-2 border-l border-border pb-2">
        {showInfo && (
          <div className="mx-2 mt-1 flex flex-col gap-2 text-sm leading-5">
            <RevisionNote changes={changesOf(node.id)} />
            <p>{node.criterion.summary}</p>
            <ScoreDisclosure node={node} explorer={explorer} />
            <div className="flex items-center justify-between gap-2 text-xs leading-4 text-fg-muted">
              <span>
                {rules.filter((r) => decisions.has(r.id)).length} de {rules.length} regras com nota
                do analista
              </span>
              <QuestionButton nodeId={node.id} label="Questionar critério" />
            </div>
            <ContestationList items={contestationsOf(node.id)} />
          </div>
        )}
        {rules.map((rule) =>
          rule.id === openRuleId ? (
            <OpenRule
              key={rule.id}
              node={rule}
              explorer={explorer}
              decision={decisions.get(rule.id)}
              changesOf={changesOf}
              contestationsOf={contestationsOf}
              {...rest}
            />
          ) : (
            <ClosedRule
              key={rule.id}
              node={rule}
              decided={decisions.has(rule.id)}
              onOpen={() => explorer.select(rule.id)}
            />
          ),
        )}
      </div>
    </div>
  );
};

const ClosedRule = ({
  node,
  decided,
  onOpen,
}: {
  node: RuleNode;
  decided: boolean;
  onOpen: () => void;
}) => {
  const status = RULE_STATUS[ruleStatus(node.rule)];
  return (
    <button
      type="button"
      data-node={node.id}
      onClick={onOpen}
      aria-expanded={false}
      className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-fg-muted transition-colors hover:bg-surface-sunken/60 hover:text-fg"
    >
      <KeyboardArrowRightIcon className="size-6 shrink-0" />
      <span className="text-base leading-4 font-semibold tabular-nums">{node.number}</span>
      <span className="min-w-0 flex-1 truncate text-base leading-5" title={node.rule.name}>
        {node.rule.name}
      </span>
      {decided && <span className="sr-only">(com nota do analista)</span>}
      <Tag tone={status.tone} label={status.short} />
    </button>
  );
};

const OpenRule = ({
  node,
  explorer,
  decision,
  projectId,
  analysisId,
  reviews,
  changesOf,
  contestationsOf,
}: {
  node: RuleNode;
  explorer: AnalysisExplorer;
  decision?: RuleDecision;
  projectId: string;
  analysisId: string;
  reviews: ReadonlyMap<string, EvidenceReview>;
  changesOf: (nodeId: string) => AnalysisChange[];
  contestationsOf: (nodeId: string) => Contestation[];
}) => {
  const ruleState = ruleStatus(node.rule);
  const status = RULE_STATUS[ruleState];
  const parentId = node.parentId;

  return (
    <div
      data-node={node.id}
      className="flex flex-col gap-3 rounded-lg border border-accent bg-accent-soft p-3"
    >
      <button
        type="button"
        aria-expanded
        onClick={() => parentId && explorer.select(parentId)}
        className="flex w-full items-center gap-2 text-left"
        title="Recolher a regra"
      >
        <ChevronDown className="size-3.5 shrink-0 text-accent" strokeWidth={2.5} aria-hidden />
        <span className="text-xs leading-4 font-semibold text-accent tabular-nums">{node.number}</span>
        <span className="min-w-0 flex-1 text-sm leading-5 font-semibold">{node.rule.name}</span>
        <Tag tone={status.tone} label={status.label} size="sm" />
      </button>

      <RevisionNote changes={changesOf(node.id)} />

      <Field title={`Regra ${node.rule.code}`}>
        <p className="text-sm leading-5">{node.rule.explanation}</p>
      </Field>

      <ScoreDisclosure node={node} explorer={explorer} />

      <Field title="Referência normativa">
        <ReferenceLink reference={node.rule.normativeSource} />
      </Field>

      {ruleState === "contradictory" && (
        <p className="flex items-start gap-2 rounded-md bg-state-attention-soft px-2.5 py-2 text-xs leading-4 font-medium text-state-attention">
          <TriangleAlert className="mt-px size-3.5 shrink-0" strokeWidth={2.5} aria-hidden />
          As evidências apontam em sentidos opostos, com peso parecido. O sistema não resolve a
          divergência: indique na sua nota qual evidência prevalece.
        </p>
      )}

      {node.childIds.length > 0 ? (
        <div className="flex flex-col gap-2">
          {node.childIds.map((id) => {
            const evidence = explorer.index.get(id);
            if (evidence?.kind !== "evidence") return null;
            return (
              <div key={id} data-node={id}>
                <EvidenceCard
                  node={evidence}
                  projectId={projectId}
                  analysisId={analysisId}
                  selected={explorer.selectedId === id}
                  onSelect={() => explorer.select(explorer.selectedId === id ? node.id : id)}
                  review={reviews.get(id)}
                  contestations={contestationsOf(id)}
                  changes={changesOf(id)}
                />
              </div>
            );
          })}
        </div>
      ) : (
        <p className="rounded-md bg-surface px-2.5 py-2 text-xs leading-4 text-fg-muted">
          Nenhuma evidência foi encontrada no material para esta regra.
        </p>
      )}

      <ContestationList items={contestationsOf(node.id)} />
      <div className="flex items-center justify-between gap-2 text-xs leading-4 text-fg-muted">
        <span>{decision ? "Nota do analista registrada" : "Nota sugerida · aguarda o analista"}</span>
        <QuestionButton nodeId={node.id} label="Questionar regra" />
      </div>
    </div>
  );
};
