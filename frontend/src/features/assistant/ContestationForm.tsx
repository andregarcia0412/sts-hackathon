import { useState } from "react";
import type { FormEvent } from "react";
import {
  CONTESTATION_REASONS_BY_KIND,
  CONTESTATION_REASON_LABELS,
} from "@/domain/labels";
import { getNodeTitle } from "@/domain/tree";
import type { AnalysisNode } from "@/domain/tree";
import type {
  Analysis,
  Contestation,
  ContestationReason,
  EvidencePolarity,
} from "@/domain/types";
import { useCurrentUser } from "@/features/auth/authState";
import { useCreateContestation } from "@/services/queries";

interface ContestationFormProps {
  analysis: Analysis;
  node: AnalysisNode;
  initialReason: ContestationReason;
  /** What the analyst wrote during the debate, used as a starting argument */
  initialArgument: string;
  onRecorded: (contestation: Contestation) => void;
  onCancel: () => void;
}

/** Records a contestation of a criterion, rule or evidence (goes to the trail) */
export const ContestationForm = ({
  analysis,
  node,
  initialReason,
  initialArgument,
  onRecorded,
  onCancel,
}: ContestationFormProps) => {
  const createContestation = useCreateContestation();
  const user = useCurrentUser();
  const reasons = CONTESTATION_REASONS_BY_KIND[node.kind];
  const currentPolarity = node.kind === "evidence" ? node.evidence.polarity : undefined;

  const [reason, setReason] = useState<ContestationReason>(
    reasons.includes(initialReason) ? initialReason : reasons[0],
  );
  const [argument, setArgument] = useState(initialArgument);
  const [suggestedScore, setSuggestedScore] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const scoreNumber = suggestedScore === "" ? undefined : Number(suggestedScore);
  const errors = {
    argument: argument.trim() === "",
    score: scoreNumber !== undefined && (Number.isNaN(scoreNumber) || scoreNumber < 0 || scoreNumber > 100),
  };
  const label = `${node.number} ${getNodeTitle(node)}`;

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setSubmitted(true);
    if (Object.values(errors).some(Boolean)) return;
    const suggestedPolarity: EvidencePolarity | undefined =
      reason === "polarity" && currentPolarity
        ? currentPolarity === "positive" ? "negative" : "positive"
        : undefined;
    createContestation.mutate(
      {
        projectId: analysis.projectId,
        analysisId: analysis.id,
        nodeId: node.id,
        nodeLabel: label,
        reason,
        argument: argument.trim(),
        suggestedScore: node.kind !== "evidence" ? scoreNumber : undefined,
        suggestedPolarity,
        author: user.name,
      },
      { onSuccess: onRecorded },
    );
  };

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      aria-label={`Registrar contestação de ${label}`}
      className="space-y-3 rounded-2xl border border-state-attention/30 bg-state-attention-soft p-4 text-sm leading-5"
    >
      <p className="font-semibold">Registrar contestação de {label}</p>

      <div>
        <label htmlFor="ct-reason" className="field-label">Motivo</label>
        <select
          id="ct-reason"
          className="select py-2 text-sm"
          value={reason}
          onChange={(e) => setReason(e.target.value as ContestationReason)}
        >
          {reasons.map((r) => (
            <option key={r} value={r}>{CONTESTATION_REASON_LABELS[r]}</option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="ct-argument" className="field-label">
          Argumento <span className="text-action">*</span>
        </label>
        <textarea
          id="ct-argument"
          className="input min-h-20 resize-y py-2 text-sm"
          placeholder="Por que discorda? Cite arquivo e página, se puder."
          value={argument}
          onChange={(e) => setArgument(e.target.value)}
          aria-invalid={submitted && errors.argument}
        />
        {submitted && errors.argument && (
          <p className="mt-0.5 text-xs text-danger">Explique o motivo da contestação.</p>
        )}
      </div>

      {node.kind !== "evidence" ? (
        <div>
          <label htmlFor="ct-score" className="field-label">
            Nota que você considera justa <span className="font-normal text-fg-muted">(opcional, 0–100)</span>
          </label>
          <input
            id="ct-score"
            type="number"
            min={0}
            max={100}
            inputMode="numeric"
            className="input w-24 py-2 text-sm"
            value={suggestedScore}
            onChange={(e) => setSuggestedScore(e.target.value)}
            aria-invalid={submitted && errors.score}
          />
          {submitted && errors.score && (
            <p className="mt-0.5 text-xs text-danger">Use um número de 0 a 100.</p>
          )}
        </div>
      ) : (
        reason === "polarity" && (
          <p className="text-xs text-fg-muted">
            Polaridade sugerida:{" "}
            <strong>{currentPolarity === "positive" ? "negativa" : "positiva"}</strong>
          </p>
        )
      )}

      <p className="text-xs text-fg-muted">
        Registrada em nome de <strong className="text-fg">{user.name}</strong>.
      </p>

      {createContestation.isError && (
        <p role="alert" className="text-xs text-danger">Não foi possível registrar. Tente novamente.</p>
      )}

      <div className="flex justify-end gap-2">
        <button type="button" className="btn-secondary px-4 py-2 text-sm" onClick={onCancel}>Cancelar</button>
        <button type="submit" className="btn-primary px-4 py-2 text-sm" disabled={createContestation.isPending}>
          {createContestation.isPending ? "Registrando…" : "Registrar"}
        </button>
      </div>
    </form>
  );
};
