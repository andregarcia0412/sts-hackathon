import { Link } from "react-router-dom";
import { useState } from "react";
import type { FormEvent } from "react";
import { TONE_ICONS, TONE_STYLES } from "@/components/ui/toneStyles";
import { FRAMEWORKS } from "@/domain/frameworks";
import { DECISION_OUTCOME_LABELS, DECISION_OUTCOME_TONES } from "@/domain/labels";
import { latestByNode } from "@/domain/reviews";
import type { Analysis, DecisionOutcome, RuleDecision } from "@/domain/types";
import { useCurrentUser } from "@/features/auth/authState";
import { paths } from "@/routes/paths";
import { useSaveDecision } from "@/services/queries";

const OUTCOMES: DecisionOutcome[] = ["eligible", "with_reservations", "not_eligible"];

const OUTCOME_HINTS: Record<DecisionOutcome, string> = {
  eligible: "O projeto atende aos critérios",
  with_reservations: "Atende, com pontos a acompanhar",
  not_eligible: "O projeto não atende aos critérios",
};

interface DecisionFormProps {
  /** Every analysis of the project; the first is the primary one */
  analyses: Analysis[];
  /** Analyst's rule ratings (all analyses), to show what is still pending */
  ruleDecisions: RuleDecision[];
  /** A decision already exists: this form records a new one in the trail */
  hasPrevious: boolean;
}

/** Final decision on the project: outcome + justification, recorded in the trail */
export const DecisionForm = ({ analyses, ruleDecisions, hasPrevious }: DecisionFormProps) => {
  const saveDecision = useSaveDecision();
  const user = useCurrentUser();
  const primary = analyses[0];
  const [outcome, setOutcome] = useState<DecisionOutcome | null>(null);
  const [justification, setJustification] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const errors = { outcome: outcome === null, justification: justification.trim() === "" };
  const showError = (field: keyof typeof errors) => submitted && errors[field];

  const progress = analyses.map((analysis) => {
    const rated = latestByNode(ruleDecisions, analysis.id);
    const total = analysis.criteria.reduce((sum, c) => sum + c.rules.length, 0);
    return { analysis, rated: rated.size, total };
  });

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setSubmitted(true);
    if (errors.outcome || errors.justification || outcome === null) return;
    saveDecision.mutate(
      {
        projectId: primary.projectId,
        analysisId: primary.id,
        analysisIds: analyses.map((a) => a.id),
        outcome,
        justification: justification.trim(),
        analystName: user.name,
      },
      {
        onSuccess: () => {
          setOutcome(null);
          setJustification("");
          setSubmitted(false);
        },
      },
    );
  };

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className="flex flex-col gap-5 rounded-2xl border border-border bg-surface-muted p-5 print:hidden"
    >
      <p className="text-sm leading-5 text-fg-muted">
        {hasPrevious
          ? "Registrar uma nova decisão não apaga as anteriores: ela entra na trilha abaixo."
          : "A decisão é do analista. O sistema só organiza as evidências."}
      </p>

      <div className="flex flex-col gap-2 rounded-xl bg-surface p-3 text-sm leading-5">
        <p className="caps-label text-fg-muted">Notas do analista por regra</p>
        <ul className="flex flex-col gap-1">
          {progress.map(({ analysis, rated, total }) => (
            <li key={analysis.id} className="flex flex-wrap items-center justify-between gap-2">
              <span>
                {FRAMEWORKS[analysis.framework].label}:{" "}
                <strong className="font-semibold tabular-nums">
                  {rated} de {total}
                </strong>{" "}
                regras com nota
              </span>
              {rated < total && (
                <Link to={paths.analysis(analysis.projectId, undefined, analysis.framework)} className="btn-link">
                  Dar notas no grafo
                </Link>
              )}
            </li>
          ))}
        </ul>
        {progress.some((p) => p.rated < p.total) && (
          <p className="text-xs leading-4 text-fg-muted">
            Regras sem nota aparecem no documento só com a leitura sugerida pelo sistema.
          </p>
        )}
      </div>

      <fieldset className="flex flex-col gap-2">
        <legend className="label">
          Resultado <span className="text-action">*</span>
        </legend>
        <div className="grid gap-2 sm:grid-cols-3">
          {OUTCOMES.map((value) => {
            const tone = DECISION_OUTCOME_TONES[value];
            const Icon = TONE_ICONS[tone];
            return (
              <label
                key={value}
                className="flex cursor-pointer items-start gap-2 rounded-2xl border-2 border-border bg-surface p-3 transition-colors has-checked:border-action has-focus-visible:outline-2 has-focus-visible:outline-action hover:border-border-strong"
              >
                <input
                  type="radio"
                  name="outcome"
                  value={value}
                  checked={outcome === value}
                  onChange={() => setOutcome(value)}
                  className="sr-only"
                />
                <span
                  className={`flex size-8 shrink-0 items-center justify-center rounded-full ${TONE_STYLES[tone].soft} ${TONE_STYLES[tone].icon}`}
                >
                  <Icon className="size-6" aria-hidden />
                </span>
                <span className="flex flex-col">
                  <span className="text-base leading-5 font-semibold">{DECISION_OUTCOME_LABELS[value]}</span>
                  <span className="text-xs leading-4 text-fg-muted">{OUTCOME_HINTS[value]}</span>
                </span>
              </label>
            );
          })}
        </div>
        {showError("outcome") && <p className="text-xs text-danger">Escolha um resultado.</p>}
      </fieldset>

      <div className="flex flex-col gap-2">
        <label htmlFor="justification" className="label mb-0">
          Justificativa <span className="text-action">*</span>
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
          <p className="text-xs text-danger">A justificativa é obrigatória.</p>
        )}
      </div>

      {saveDecision.isError && (
        <p role="alert" className="text-sm text-danger">
          Não foi possível registrar a decisão. Tente novamente.
        </p>
      )}

      <div className="flex flex-wrap items-center justify-end gap-3">
        <p className="min-w-0 flex-1 text-xs leading-4 text-fg-muted">
          Será registrada em nome de <strong className="font-semibold text-fg">{user.name}</strong>,
          com data e hora automáticas.
        </p>
        <button type="submit" className="btn-primary" disabled={saveDecision.isPending}>
          {saveDecision.isPending ? "Registrando…" : "Registrar decisão"}
        </button>
      </div>
    </form>
  );
};
