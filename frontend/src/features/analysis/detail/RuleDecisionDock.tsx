import { useState } from "react";
import { KeyboardArrowDownIcon } from "@/components/icons/MaterialIcons";
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
  const [rating, setRating] = useState<RuleRating | "">(current?.rating ?? suggested ?? "");
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
          setShowErrors(false);
        },
      },
    );
  };

  return (
    <form
      aria-label="Decisão do analista"
      className="flex shrink-0 flex-col gap-4 border-t border-border bg-surface px-4 pb-4 shadow-dock"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <div className="flex items-center justify-between gap-3 border-b border-border-strong pt-4 pb-3">
        <h2 className="text-xl leading-6 font-semibold">Decisão do analista</h2>
        <span className="btn-chip" title={node.rule.name}>
          Regra {node.number}
        </span>
      </div>

      <div className="flex flex-col gap-2">
        <label htmlFor={fieldId} className="label mb-0">
          Nota da regra
        </label>
        {/* Native select for keyboard/screen readers, drawn as the design's tag */}
        <div className="relative flex h-12 items-center justify-between rounded-2xl border border-border-strong bg-surface px-2 py-1 focus-within:outline-2 focus-within:outline-action">
          {rating ? (
            <Tag tone={RULE_RATING[rating].tone} label={RULE_RATING[rating].label} />
          ) : (
            <span className="px-1 text-base leading-5 text-fg-muted">Escolha a nota</span>
          )}
          <KeyboardArrowDownIcon className="size-6 text-fg-secondary" />
          <select
            id={fieldId}
            value={rating}
            onChange={(e) => setRating(e.target.value as RuleRating)}
            className="absolute inset-0 cursor-pointer opacity-0"
          >
            <option value="" disabled>
              Escolha a nota
            </option>
            {RULE_RATINGS.map((r) => (
              <option key={r} value={r}>
                {RULE_RATING[r].label}
                {r === suggested ? " (sugestão do sistema)" : ""}
              </option>
            ))}
          </select>
        </div>
        {showErrors && !rating && (
          <p role="alert" className="text-xs text-danger">
            Escolha a nota da regra.
          </p>
        )}
      </div>

      <div className="flex flex-col gap-2">
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
          className="input field-sizing-content max-h-32 min-h-12 resize-none"
        />
        {showErrors && missingJustification && (
          <p role="alert" className="text-xs text-danger">
            A justificativa é obrigatória: ela entra na trilha de decisão.
          </p>
        )}
      </div>

      <div className="flex items-center gap-3">
        <p className="min-w-0 flex-1 text-center text-xs leading-4 text-fg-muted" aria-live="polite">
          {current ? (
            <>
              Registrada: <strong className="font-semibold text-fg">{RULE_RATING[current.rating].label}</strong>
              <br />
              {current.author} · {formatDateTime(current.createdAt)}
            </>
          ) : (
            "Sem decisão registrada"
          )}
        </p>
        <button type="submit" className="btn-primary" disabled={create.isPending}>
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
