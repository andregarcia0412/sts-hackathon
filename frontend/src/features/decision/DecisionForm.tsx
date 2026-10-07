import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";
import { DECISION_OUTCOME_LABELS } from "@/domain/labels";
import { indexAnalysis } from "@/domain/tree";
import type { Analysis, DecisionOutcome, RuleOverride } from "@/domain/types";
import { useSaveDecision } from "@/services/queries";

const OUTCOMES: DecisionOutcome[] = ["eligible", "not_eligible", "needs_review"];

interface DecisionFormProps {
  analysis: Analysis;
  /** A decision already exists: this form records a new one in the trail */
  hasPrevious: boolean;
}

export const DecisionForm = ({ analysis, hasPrevious }: DecisionFormProps) => {
  const saveDecision = useSaveDecision();
  const rules = [...indexAnalysis(analysis).values()].filter((n) => n.kind === "rule");

  const [outcome, setOutcome] = useState<DecisionOutcome | null>(null);
  const [justification, setJustification] = useState("");
  const [analystName, setAnalystName] = useState("");
  const [overrides, setOverrides] = useState<RuleOverride[]>([]);
  const [submitted, setSubmitted] = useState(false);

  const errors = {
    outcome: outcome === null,
    justification: justification.trim() === "",
    analystName: analystName.trim() === "",
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
        projectId: analysis.projectId,
        analysisId: analysis.id,
        outcome,
        justification: justification.trim(),
        analystName: analystName.trim(),
        ruleOverrides: overrides
          .filter((o) => o.ruleId && o.note.trim())
          .map((o) => ({ ...o, note: o.note.trim() })),
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
                value={override.ruleId}
                onChange={(e) => updateOverride(i, { ruleId: e.target.value })}
              >
                <option value="">Escolha a regra…</option>
                {rules.map((node) =>
                  node.kind === "rule" ? (
                    <option key={node.id} value={node.id}>
                      {node.number} {node.rule.code} · {node.rule.name}
                    </option>
                  ) : null,
                )}
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

      <div className="flex flex-wrap items-end gap-4">
        <div className="min-w-56 flex-1">
          <label htmlFor="analyst-name" className="label">
            Nome do analista <span className="text-danger">*</span>
          </label>
          <input
            id="analyst-name"
            className="input"
            autoComplete="name"
            value={analystName}
            onChange={(e) => setAnalystName(e.target.value)}
            aria-invalid={showError("analystName")}
          />
          {showError("analystName") && (
            <p className="mt-1 text-xs text-danger">Informe seu nome.</p>
          )}
        </div>
        <p className="pb-2 text-xs text-fg-muted">
          Data e hora são registradas automaticamente ao salvar.
        </p>
      </div>

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
