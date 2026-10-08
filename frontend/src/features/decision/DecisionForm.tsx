import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";
import { DECISION_OUTCOME_LABELS } from "@/domain/labels";
import { FRAMEWORKS } from "@/domain/frameworks";
import { indexAnalysis } from "@/domain/tree";
import type { RuleNode } from "@/domain/tree";
import type { Analysis, DecisionOutcome, RuleOverride } from "@/domain/types";
import { useCurrentUser } from "@/features/auth/authState";
import { useSaveDecision } from "@/services/queries";

const OUTCOMES: DecisionOutcome[] = ["eligible", "not_eligible", "needs_review"];

/** Override value in the select: rules of different methods may share ids */
const overrideKey = (analysisId: string, ruleId: string) => `${analysisId}::${ruleId}`;

interface DecisionFormProps {
  /** Every analysis of the project; the first is the primary one */
  analyses: Analysis[];
  /** A decision already exists: this form records a new one in the trail */
  hasPrevious: boolean;
}

export const DecisionForm = ({ analyses, hasPrevious }: DecisionFormProps) => {
  const saveDecision = useSaveDecision();
  const primary = analyses[0];
  const rulesByAnalysis = analyses.map((analysis) => ({
    analysis,
    rules: [...indexAnalysis(analysis).values()].filter((n): n is RuleNode => n.kind === "rule"),
  }));

  const [outcome, setOutcome] = useState<DecisionOutcome | null>(null);
  const [justification, setJustification] = useState("");
  const user = useCurrentUser();
  const [overrides, setOverrides] = useState<RuleOverride[]>([]);
  const [submitted, setSubmitted] = useState(false);

  const errors = {
    outcome: outcome === null,
    justification: justification.trim() === "",
  };
  const hasErrors = Object.values(errors).some(Boolean);

  const updateOverride = (i: number, patch: Partial<RuleOverride>) =>
    setOverrides((current) =>
      current.map((o, j) => (j === i ? { ...o, ...patch } : o)),
    );

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setSubmitted(true);
    if (hasErrors || outcome === null) return;
    saveDecision.mutate(
      {
        projectId: primary.projectId,
        analysisId: primary.id,
        analysisIds: analyses.map((a) => a.id),
        outcome,
        justification: justification.trim(),
        analystName: user.name,
        ruleOverrides: overrides
          .filter((o) => o.ruleId && o.note.trim())
          .map((o) => ({
            ruleId: o.ruleId,
            analysisId: o.analysisId ?? primary.id,
            note: o.note.trim(),
          })),
      },
      {
        onSuccess: () => {
          setOutcome(null);
          setJustification("");
          setOverrides([]);
          setSubmitted(false);
        },
      },
    );
  };

  const showError = (field: keyof typeof errors) => submitted && errors[field];

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className="space-y-5 rounded-lg border border-border bg-surface p-5 font-sans print:hidden"
    >
      <p className="text-sm text-fg-muted">
        {hasPrevious
          ? "Registrar uma nova decisão não apaga as anteriores: ela entra na trilha abaixo."
          : "A decisão é do analista. O sistema só organiza as evidências."}
      </p>

      <fieldset>
        <legend className="label">
          Resultado <span className="text-danger">*</span>
        </legend>
        <div className="flex flex-wrap gap-2">
          {OUTCOMES.map((value) => (
            <label
              key={value}
              className="flex cursor-pointer items-center gap-2 rounded-md border border-border-strong px-3 py-2 text-sm has-checked:border-accent has-checked:bg-accent-soft has-checked:font-medium"
            >
              <input
                type="radio"
                name="outcome"
                value={value}
                checked={outcome === value}
                onChange={() => setOutcome(value)}
                className="accent-accent"
              />
              {DECISION_OUTCOME_LABELS[value]}
            </label>
          ))}
        </div>
        {showError("outcome") && (
          <p className="mt-1 text-xs text-danger">Escolha um resultado.</p>
        )}
      </fieldset>

      <div>
        <label htmlFor="justification" className="label">
          Justificativa <span className="text-danger">*</span>
        </label>
        <textarea
          id="justification"
          className="input min-h-32 resize-y"
          placeholder="Explique a decisão com base nos critérios, regras e evidências acima (cite a numeração, ex.: 3.1.1)."
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          aria-invalid={showError("justification")}
        />
        {showError("justification") && (
          <p className="mt-1 text-xs text-danger">A justificativa é obrigatória.</p>
        )}
      </div>

      <div>
        <p className="label">Ressalvas por regra (opcional)</p>
        <p className="mb-2 text-xs text-fg-muted">
          Use quando discordar da nota de uma regra.
        </p>
        <ul className="space-y-2">
          {overrides.map((override, i) => (
            <li key={i} className="flex flex-wrap items-start gap-2">
              <select
                aria-label={`Regra da ressalva ${i + 1}`}
                className="input w-auto max-w-64"
                value={override.ruleId ? overrideKey(override.analysisId ?? primary.id, override.ruleId) : ""}
                onChange={(e) => {
                  const [analysisId, ruleId] = e.target.value.split("::");
                  updateOverride(i, { analysisId, ruleId: ruleId ?? "" });
                }}
              >
                <option value="">Escolha a regra…</option>
                {rulesByAnalysis.map(({ analysis, rules }) => (
                  <optgroup key={analysis.id} label={FRAMEWORKS[analysis.framework].label}>
                    {rules.map((node) => (
                      <option key={node.id} value={overrideKey(analysis.id, node.id)}>
                        {node.number} {node.rule.code} · {node.rule.name}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
              <input
                aria-label={`Ressalva ${i + 1}`}
                className="input min-w-48 flex-1"
                placeholder="Por que discorda da nota"
                value={override.note}
                onChange={(e) => updateOverride(i, { note: e.target.value })}
              />
              <button
                type="button"
                className="btn-ghost p-2"
                aria-label={`Remover ressalva ${i + 1}`}
                onClick={() => setOverrides((current) => current.filter((_, j) => j !== i))}
              >
                <Trash2 className="size-4" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
        <button
          type="button"
          className="btn-ghost mt-1"
          onClick={() => setOverrides((current) => [...current, { ruleId: "", note: "" }])}
        >
          <Plus className="size-4" aria-hidden />
          Adicionar ressalva
        </button>
      </div>

      <p className="text-xs text-fg-muted">
        Será registrada em nome de <strong className="text-fg">{user.name}</strong>, com data e
        hora automáticas.
      </p>

      {saveDecision.isError && (
        <p role="alert" className="text-sm text-danger">
          Não foi possível registrar a decisão. Tente novamente.
        </p>
      )}

      <div className="flex justify-end">
        <button type="submit" className="btn-primary" disabled={saveDecision.isPending}>
          {saveDecision.isPending ? "Registrando…" : "Registrar decisão"}
        </button>
      </div>
    </form>
  );
};
