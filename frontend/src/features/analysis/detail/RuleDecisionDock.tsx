import { useState } from "react";
import { PillSelect } from "@/components/ui/PillSelect";
import { Tag } from "@/components/ui/Tag";
import {
  RULE_RATING,
  RULE_RATINGS,
  ruleStatus,
  suggestedRating,
} from "@/domain/qualitative";
import type { RuleNode } from "@/domain/tree";
import type { RuleDecision, RuleRating } from "@/domain/types";
import { useCurrentUser } from "@/features/auth/authState";
import { formatDateTime } from "@/lib/format";
import { useCreateRuleDecision } from "@/services/queries";

interface RuleDecisionDockProps {
  node: RuleNode;
  projectId: string;
  analysisId: string;
  /** Latest rating of this rule, if any */
  current?: RuleDecision;
}

/**
 * "Decisão do analista" for the open rule: the analyst's rating + required
 * justification. Append-only: confirming again adds a new entry to the trail.
 * Remount it per rule (key) so the form starts from that rule's state.
 */
export const RuleDecisionDock = ({ node, projectId, analysisId, current }: RuleDecisionDockProps) => {
  const user = useCurrentUser();
  const create = useCreateRuleDecision();
  const suggested = suggestedRating(ruleStatus(node.rule));
  // Until the analyst picks one, follow the latest rating or the current suggestion
  // (a reanalysis may change the suggestion while this rule is open)
  const [chosen, setRating] = useState<RuleRating | null>(null);
  const rating: RuleRating | "" = chosen ?? current?.rating ?? suggested ?? "";
  const [justification, setJustification] = useState("");
  const [showErrors, setShowErrors] = useState(false);
  const fieldId = `nota-${node.id}`;
  const missingJustification = !justification.trim();

  const submit = () => {
    if (!rating || missingJustification) {
      setShowErrors(true);
      return;
    }
    create.mutate(
      {
        projectId,
        analysisId,
        nodeId: node.id,
        nodeLabel: `${node.number} ${node.rule.code} ${node.rule.name}`,
        rating,
        suggested,
        justification: justification.trim(),
        author: user.name,
      },
      {
        onSuccess: () => {
          setJustification("");
          setRating(null);
          setShowErrors(false);
        },
      },
    );
  };

  return (
    <form
      aria-label="Decisão do analista"
      className="flex shrink-0 flex-col gap-2 rounded-b-2xl border-t border-border bg-surface px-4 pb-3 shadow-dock"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <div className="flex items-center justify-between gap-3 border-b border-border-strong pt-3 pb-2">
        <h2 className="text-xl leading-6 font-semibold">Decisão do analista</h2>
        <span className="btn-chip" title={node.rule.name}>
          Regra {node.number}
        </span>
      </div>

      <div className="flex flex-col gap-1">
        <span id={fieldId} aria-hidden className="label mb-0">
          Nota da regra
        </span>
        <PillSelect
          label="Nota da regra"
          placeholder="Escolha a nota"
          allowEmpty={false}
          openUp
          value={rating || undefined}
          onChange={(value) => value && setRating(value)}
          renderOption={(option) => (
            <Tag tone={RULE_RATING[option.value].tone} label={RULE_RATING[option.value].label} />
          )}
          options={RULE_RATINGS.map((r) => ({
            value: r,
            label: RULE_RATING[r].label,
            hint: r === suggested ? "sugestão do sistema" : undefined,
          }))}
        />
        {showErrors && !rating && (
          <p role="alert" className="text-xs text-danger">
            Escolha a nota da regra.
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor={`${fieldId}-justificativa`} className="label mb-0">
          Justificativa <span className="text-action">*</span>
        </label>
        <textarea
          id={`${fieldId}-justificativa`}
          rows={1}
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          placeholder="Indique qual evidência prevalece e por quê."
          aria-invalid={showErrors && missingJustification}
          className="input field-sizing-content max-h-32 min-h-12 resize-none rounded-3xl px-4"
        />
        {showErrors && missingJustification && (
          <p role="alert" className="text-xs text-danger">
            A justificativa é obrigatória: ela entra na trilha de decisão.
          </p>
        )}
      </div>

      <div className="mt-1 flex items-center gap-4">
        <p
          className="flex min-h-11 min-w-0 flex-1 flex-col items-center justify-center rounded-full border border-border-strong bg-surface px-4 py-1.5 text-center text-sm leading-4 font-semibold"
          aria-live="polite"
        >
          {current ? (
            <>
              <span>Registrada: {RULE_RATING[current.rating].label}</span>
              <span className="text-[11px] font-normal text-fg-muted">
                {current.author} · {formatDateTime(current.createdAt)}
              </span>
            </>
          ) : (
            "Sem decisão registrada"
          )}
        </p>
        <button type="submit" className="btn-primary min-h-11 flex-1" disabled={create.isPending}>
          {create.isPending ? "Registrando…" : current ? "Registrar nova nota" : "Confirmar nota da regra"}
        </button>
      </div>
      {create.isError && (
        <p role="alert" className="-mt-2 text-xs text-danger">
          Não foi possível registrar a nota. Tente novamente.
        </p>
      )}
    </form>
  );
};
