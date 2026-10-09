import { ChevronDown, Flag } from "lucide-react";
import type { ReactNode } from "react";
import { ReviewTag } from "@/components/ui/ReviewTag";
import { ScoreBreakdown } from "@/components/ui/ScoreBreakdown";
import { CONTESTATION_REASON_LABELS } from "@/domain/labels";
import type { CriterionNode, RuleNode } from "@/domain/tree";
import type { AnalysisChange, Contestation } from "@/domain/types";
import { useAssistant } from "@/features/assistant/assistantState";
import type { AnalysisExplorer } from "@/features/analysis/useAnalysisExplorer";
import { formatDateTime } from "@/lib/format";
import { useRequestReanalysis } from "@/services/queries";

/*
 * Pieces shared by the criterion, rule and evidence blocks of the detail
 * panel: score composition, contestation (debate) and its follow-up.
 */

/** "Força da evidência 58/100" + collapsible step-by-step composition */
export const ScoreDisclosure = ({
  node,
  explorer,
}: {
  node: CriterionNode | RuleNode;
  explorer: AnalysisExplorer;
}) => {
  const target = node.kind === "criterion" ? node.criterion : node.rule;
  const factors = (target.scoreExplanation?.factors ?? []).map((factor) => {
    const child = factor.refId ? explorer.index.get(`${node.id}.${factor.refId}`) : undefined;
    return {
      ...factor,
      number: child?.number,
      onSelect: child ? () => explorer.select(child.id) : undefined,
    };
  });

  return (
    <details className="group rounded-md bg-surface/70 px-2.5 py-2 text-xs leading-4">
      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-1.5 gap-y-1 text-fg-muted [&::-webkit-details-marker]:hidden">
        <ChevronDown className="size-3.5 -rotate-90 transition-transform group-open:rotate-0" aria-hidden />
        <span className="whitespace-nowrap">
          Força da evidência{" "}
          <strong className="font-semibold text-fg tabular-nums">{target.score}/100</strong> · sugestão
          do sistema
        </span>
        {target.scoreExplanation && (
          <span className="ml-auto font-semibold whitespace-nowrap text-accent">
            Como a nota foi formada
          </span>
        )}
      </summary>
      {target.scoreExplanation && (
        <div className="mt-2 text-sm">
          <ScoreBreakdown
            explanation={target.scoreExplanation}
            factors={factors}
            score={target.score}
            subject={node.kind === "criterion" ? "do critério" : "da regra"}
          />
        </div>
      )}
    </details>
  );
};

/** Opens the debate with the model in the assistant (contestation) */
export const QuestionButton = ({ nodeId, label = "Questionar" }: { nodeId: string; label?: string }) => {
  const { startDebate, debateNodeId } = useAssistant();
  return (
    <button
      type="button"
      className="btn-link inline-flex items-center gap-1 text-fg-secondary"
      onClick={() => startDebate(nodeId)}
      disabled={debateNodeId === nodeId}
      title="Discorda de algo? Debata com o modelo e registre a contestação"
    >
      <Flag className="size-3.5 text-state-attention" aria-hidden />
      {label}
    </button>
  );
};

const changeValue = (value: AnalysisChange["before"]) =>
  value === "positive" ? "positiva" : value === "negative" ? "negativa" : String(value);

/** "Revisado após contestação: 80 → 96" for nodes changed by accepted contestations */
export const RevisionNote = ({ changes }: { changes: AnalysisChange[] }) => {
  if (changes.length === 0) return null;
  const first = changes[0];
  const last = changes.at(-1)!;
  return (
    <p className="flex flex-wrap items-center gap-1.5 rounded-md bg-surface/70 px-2.5 py-1.5 text-xs">
      <ReviewTag marker="revised" size="xs" />
      {first.field === "polarity" ? "Polaridade" : "Nota"} revisada após contestação acatada:{" "}
      <strong className="tabular-nums">
        {changeValue(first.before)} → {changeValue(last.after)}
      </strong>
    </p>
  );
};

/** Contestations of a node, with status and reanalysis */
export const ContestationList = ({ items }: { items: Contestation[] }) => {
  const reanalysis = useRequestReanalysis();
  if (items.length === 0) return null;

  return (
    <section className="flex flex-col gap-2">
      <h4 className="caps-label text-fg-muted">Contestações ({items.length})</h4>
      <ul className="flex flex-col gap-2">
        {items.map((c) => {
          const pending = reanalysis.isPending && reanalysis.variables === c.id;
          return (
            <li
              key={c.id}
              className={`flex flex-col gap-1.5 rounded-md border p-2.5 text-xs leading-4 ${
                c.status === "open"
                  ? "border-state-attention/40 bg-state-attention-soft"
                  : "border-border bg-surface"
              }`}
            >
              <div className="flex flex-wrap items-center gap-1.5 font-medium">
                <ReviewTag marker={c.status === "open" ? "open" : "resolved"} size="xs" />
                {CONTESTATION_REASON_LABELS[c.reason]}
                {c.suggestedScore !== undefined && ` · nota sugerida ${c.suggestedScore}`}
                {c.suggestedPolarity &&
                  ` · sugere ${c.suggestedPolarity === "positive" ? "positiva" : "negativa"}`}
              </div>
              <p className="text-sm leading-5 whitespace-pre-line">{c.argument}</p>
              <p className="text-fg-muted">
                {c.author} · {formatDateTime(c.createdAt)}
              </p>
              {c.status === "open" ? (
                <button
                  type="button"
                  className="btn-secondary w-full px-3 py-2 text-xs"
                  disabled={reanalysis.isPending}
                  onClick={() => reanalysis.mutate(c.id)}
                >
                  {pending ? "Reanalisando…" : "Solicitar reanálise ao modelo"}
                </button>
              ) : (
                c.resolution && (
                  <div className="flex flex-col gap-1 border-t border-border pt-1.5">
                    <p className="font-medium">
                      Reanálise · {c.resolution.verdict === "accepted" ? "acatada" : "leitura mantida"}
                      <span className="font-normal text-fg-muted">
                        {" "}
                        · {formatDateTime(c.resolution.resolvedAt)}
                      </span>
                    </p>
                    <p>{c.resolution.explanation}</p>
                  </div>
                )
              )}
            </li>
          );
        })}
      </ul>
      {reanalysis.isError && (
        <p role="alert" className="text-xs text-danger">
          Não foi possível reanalisar. Tente novamente.
        </p>
      )}
    </section>
  );
};

/** Small titled block inside a card */
export const Field = ({ title, children }: { title: string; children: ReactNode }) => (
  <div className="flex flex-col gap-1">
    <p className="caps-label text-fg-muted">{title}</p>
    {children}
  </div>
);
