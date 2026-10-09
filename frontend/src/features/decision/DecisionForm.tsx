import { Link } from "react-router-dom";
import { useState } from "react";
import type { FormEvent } from "react";
import { FRAMEWORKS } from "@/domain/frameworks";
import { DECISION_OUTCOMES, DECISION_OUTCOME_LABELS } from "@/domain/labels";
import { latestByNode } from "@/domain/reviews";
import type { Analysis, DecisionOutcome, RuleDecision } from "@/domain/types";
import { useCurrentUser } from "@/features/auth/authState";
import { paths } from "@/routes/paths";
import { useSaveDecision } from "@/services/queries";

/** What each classification means (text from the design) */
const OUTCOME_HINTS: Record<DecisionOutcome, string> = {
  eligible: "As evidências caracterizam P&D no escopo definido.",
  with_reservations: "Há prova de P&D, mas uma limitação concreta restringe parte da conclusão.",
  not_eligible: "O mecanismo documentado é rotina, configuração ou aplicação conhecida.",
  insufficient_evidence: "Falta informação essencial para concluir entre P&D e rotina.",
};

interface DecisionFormProps {
  /** Every analysis of the project: the decision covers all of them */
  analyses: Analysis[];
  /** Method on screen: its rule ratings and criteria version are shown */
  focused: Analysis;
  /** Analyst's rule ratings (all analyses), to show what is still pending */
  ruleDecisions: RuleDecision[];
}

/** Final decision on the project: classification + justification, recorded in the trail */
export const DecisionForm = ({ analyses, focused, ruleDecisions }: DecisionFormProps) => {
  const saveDecision = useSaveDecision();
  const user = useCurrentUser();
  const primary = analyses[0];
  const [outcome, setOutcome] = useState<DecisionOutcome | null>(null);
  const [justification, setJustification] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const errors = { outcome: outcome === null, justification: justification.trim() === "" };
  const showError = (field: keyof typeof errors) => submitted && errors[field];

  const rated = latestByNode(ruleDecisions, focused.id).size;
  const total = focused.criteria.reduce((sum, c) => sum + c.rules.length, 0);
  const criteriaVersion = FRAMEWORKS[focused.framework].version.split(" · ").at(-1)?.replace("critérios ", "");

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

  const drafting = outcome !== null || justification.trim() !== "";

  return (
    <>
    <form
      onSubmit={handleSubmit}
      noValidate
      aria-labelledby="decisao-titulo"
      className="flex flex-col gap-5 rounded-3xl border border-border bg-surface p-6 print:hidden"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 id="decisao-titulo" className="text-xl leading-7 font-semibold">
          Decisão do analista
        </h2>
        <p className="text-sm leading-5 text-fg-muted">Registrar uma decisão nova não apaga as anteriores.</p>
      </div>

      <p className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 rounded-2xl bg-surface-sunken px-4 py-3 text-sm leading-5">
        <span>
          Notas do analista por regra ({FRAMEWORKS[focused.framework].label}):{" "}
          <strong className="font-semibold tabular-nums">
            {rated} de {total}
          </strong>
          .{" "}
          {rated < total && "Regras sem nota entram no documento só com a leitura sugerida pelo sistema."}
        </span>
        {rated < total && (
          <Link to={paths.analysis(focused.projectId, undefined, focused.framework)} className="btn-link">
            Dar notas na árvore
          </Link>
        )}
      </p>

      <fieldset className="flex flex-col gap-3">
        <legend className="mb-3 text-base leading-6 font-semibold">
          Classificação <span className="text-action">*</span>
        </legend>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {DECISION_OUTCOMES.map((value) => (
            <label
              key={value}
              className="flex cursor-pointer flex-col gap-1.5 rounded-3xl border border-border-strong bg-surface p-4 transition-colors has-checked:border-action has-checked:bg-accent-soft/40 has-focus-visible:outline-2 has-focus-visible:outline-action hover:border-fg-faint"
            >
              <span className="flex items-center gap-2 text-base leading-6 font-semibold">
                <input
                  type="radio"
                  name="outcome"
                  value={value}
                  checked={outcome === value}
                  onChange={() => setOutcome(value)}
                  className="size-4 shrink-0 accent-action"
                />
                {DECISION_OUTCOME_LABELS[value]}
              </span>
              <span className="text-xs leading-[18px] text-fg-secondary">{OUTCOME_HINTS[value]}</span>
            </label>
          ))}
        </div>
        <p className="text-xs leading-4 text-fg-muted">
          Com ressalvas pede o recorte sustentado, a limitação e a evidência necessária. Evidência
          insuficiente pede o elo ausente e o que solicitar.
        </p>
        {showError("outcome") && <p className="text-xs text-danger">Escolha uma classificação.</p>}
      </fieldset>

      <div className="flex flex-col gap-2">
        <label htmlFor="justification" className="text-base leading-6 font-semibold">
          Justificativa <span className="text-action">*</span>
        </label>
        <textarea
          id="justification"
          className="input min-h-24 resize-y rounded-3xl px-4"
          placeholder="Qual evidência sustenta a conclusão, quais pesam contra e qual prevalece nas divergências."
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          aria-invalid={showError("justification")}
        />
        {showError("justification") && <p className="text-xs text-danger">A justificativa é obrigatória.</p>}
      </div>

      {saveDecision.isError && (
        <p role="alert" className="text-sm text-danger">
          Não foi possível registrar a decisão. Tente novamente.
        </p>
      )}

      <div className="flex flex-wrap items-center justify-end gap-3">
        <p className="min-w-0 flex-1 text-sm leading-5 text-fg-muted">
          Será registrada em nome de {user.name}, com data, hora e a versão dos critérios
          {criteriaVersion && ` (${criteriaVersion})`}.
        </p>
        <button type="submit" className="btn-primary" disabled={saveDecision.isPending}>
          {saveDecision.isPending ? "Registrando…" : "Registrar decisão"}
        </button>
      </div>
    </form>

    {/* PDF: what the analyst marked here goes on paper too, flagged as not recorded yet */}
    {drafting && (
      <div className="hidden flex-col gap-2 rounded-2xl border border-dashed border-border-strong p-4 text-sm leading-5 print:flex">
        <p className="caps-label text-fg-muted">Decisão em elaboração · ainda não registrada</p>
        <p>
          <span className="text-fg-muted">Classificação: </span>
          <strong className="font-semibold">{outcome ? DECISION_OUTCOME_LABELS[outcome] : "não escolhida"}</strong>
        </p>
        {justification.trim() && <p className="whitespace-pre-line">{justification.trim()}</p>}
        <p className="text-xs text-fg-muted">
          Analista: {user.name} · critérios {criteriaVersion}. Só a trilha abaixo tem valor de registro.
        </p>
      </div>
    )}
    </>
  );
};
