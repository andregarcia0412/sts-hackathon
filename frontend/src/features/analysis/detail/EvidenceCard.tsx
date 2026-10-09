import { BookOpen, ExternalLink } from "lucide-react";
import { useState } from "react";
import { SOURCE_ICONS } from "@/components/ui/sourceIcons";
import { Tag } from "@/components/ui/Tag";
import { evidenceSource } from "@/domain/evidence";
import { POLARITY_STATUS } from "@/domain/qualitative";
import type { EvidenceNode } from "@/domain/tree";
import type { AnalysisChange, Contestation, EvidenceReview } from "@/domain/types";
import { useCurrentUser } from "@/features/auth/authState";
import {
  ContestationList,
  QuestionButton,
  RevisionNote,
} from "@/features/analysis/detail/DetailParts";
import { formatDateTime } from "@/lib/format";
import { formatPoints } from "@/lib/scoreFormat";
import { useCreateEvidenceReview } from "@/services/queries";

interface EvidenceCardProps {
  node: EvidenceNode;
  projectId: string;
  analysisId: string;
  selected: boolean;
  onSelect: () => void;
  /** Latest confirm/discard of the analyst, if any */
  review?: EvidenceReview;
  contestations: Contestation[];
  changes: AnalysisChange[];
}

/**
 * Evidence inside the open rule: excerpt, source and the analyst's triage
 * (confirm / discard, append-only). Selected: also why it counts, references
 * and how much it moved the rule's score.
 */
export const EvidenceCard = ({
  node,
  projectId,
  analysisId,
  selected,
  onSelect,
  review,
  contestations,
  changes,
}: EvidenceCardProps) => {
  const { evidence } = node;
  const status = POLARITY_STATUS[evidence.polarity];
  const source = evidenceSource(evidence);
  const SourceIcon = SOURCE_ICONS[source.kind];
  const impact = node.rule.scoreExplanation?.factors.find(
    (f) => f.kind === "evidence" && f.refId === evidence.id,
  );
  const discarded = review?.verdict === "discarded";

  return (
    <article
      id={`evidencia-${node.id}`}
      aria-label={`Evidência ${node.number}`}
      className={`flex items-start gap-2 p-2.5 ${selected ? "rounded-2xl bg-accent-soft" : ""}`}
    >
      <Tag tone={status.tone} label={`Evidência ${status.label.toLowerCase()}`} size="plain" iconOnly />
      <div className="flex min-w-0 flex-1 flex-col gap-2 py-1">
        <button
          type="button"
          onClick={onSelect}
          aria-expanded={selected}
          className="flex w-full items-start gap-2 text-left"
        >
          <span
            className={`flex-1 text-sm leading-5 font-medium ${discarded ? "text-fg-muted line-through" : "text-fg"}`}
          >
            {evidence.title}
          </span>
          <span className="text-xs leading-5 text-fg-muted tabular-nums">{node.number}</span>
        </button>

        {evidence.projectExcerpt && (
          <blockquote className="text-xs leading-4 text-fg-soft">“{evidence.projectExcerpt.excerpt}”</blockquote>
        )}
        <p className="flex items-start gap-1 text-xs leading-4 text-fg-muted">
          <SourceIcon className="size-4 shrink-0 text-fg-secondary" aria-hidden />
          {source.label}
        </p>

        {selected && (
          <div className="flex flex-col gap-2 border-t border-border pt-2 text-xs leading-4">
            <RevisionNote changes={changes} />
            <p className="text-sm leading-5">{evidence.explanation}</p>
            {impact && (
              <p className="text-fg-muted">
                Impacto na nota da regra:{" "}
                <strong className="font-semibold text-fg tabular-nums">
                  {formatPoints(impact.points)} {Math.abs(impact.points) === 1 ? "ponto" : "pontos"}
                </strong>
              </p>
            )}
            {evidence.references.length > 0 && (
              <ul className="flex flex-col gap-1">
                {evidence.references.map((reference) => (
                  <li key={reference.label} className="flex items-start gap-1">
                    <BookOpen className="mt-px size-3.5 shrink-0 text-fg-muted" aria-hidden />
                    {reference.url ? (
                      <a
                        href={reference.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 font-medium text-accent hover:underline"
                      >
                        {reference.label}
                        <ExternalLink className="size-3 shrink-0" aria-hidden />
                        <span className="sr-only">(abre em nova aba)</span>
                      </a>
                    ) : (
                      <span className="font-medium">{reference.label}</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
            <ContestationList items={contestations} />
          </div>
        )}

        <EvidenceTriage
          node={node}
          projectId={projectId}
          analysisId={analysisId}
          review={review}
        />
      </div>
    </article>
  );
};

/** "Sugerida · não confirmada  Confirmar  Descartar"; discarding asks why */
const EvidenceTriage = ({
  node,
  projectId,
  analysisId,
  review,
}: {
  node: EvidenceNode;
  projectId: string;
  analysisId: string;
  review?: EvidenceReview;
}) => {
  const user = useCurrentUser();
  const create = useCreateEvidenceReview();
  const [discarding, setDiscarding] = useState(false);
  const [note, setNote] = useState("");

  const save = (verdict: EvidenceReview["verdict"], reason?: string) =>
    create.mutate(
      {
        projectId,
        analysisId,
        nodeId: node.id,
        nodeLabel: `${node.number} ${node.evidence.title}`,
        verdict,
        note: reason,
        author: user.name,
      },
      {
        onSuccess: () => {
          setDiscarding(false);
          setNote("");
        },
      },
    );

  if (discarding) {
    return (
      <form
        className="flex flex-col gap-1.5 border-t border-border pt-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (note.trim()) save("discarded", note.trim());
        }}
      >
        <label htmlFor={`descarte-${node.id}`} className="text-xs leading-4 font-semibold text-fg-soft">
          Por que descartar esta evidência? <span className="text-action">*</span>
        </label>
        <input
          id={`descarte-${node.id}`}
          className="input rounded-lg px-2.5 py-1.5 text-sm"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Ex.: o trecho fala de outro projeto"
          autoFocus
        />
        <p className="text-xs leading-4 text-fg-muted">
          Descartar registra a sua leitura na trilha; a nota sugerida pelo sistema não muda.
        </p>
        <div className="flex justify-end gap-3">
          <button type="button" className="btn-link text-fg-secondary" onClick={() => setDiscarding(false)}>
            Cancelar
          </button>
          <button type="submit" className="btn-link" disabled={!note.trim() || create.isPending}>
            {create.isPending ? "Registrando…" : "Descartar evidência"}
          </button>
        </div>
      </form>
    );
  }

  return (
    <div className="flex flex-col gap-2 text-xs leading-4">
      <p className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-fg-muted">
        <span>
          {review ? (
            <>
              <span
                className={
                  review.verdict === "confirmed"
                    ? "font-medium text-state-positive"
                    : "font-medium text-fg-secondary"
                }
              >
                {review.verdict === "confirmed" ? "Confirmada" : "Descartada"}
              </span>{" "}
              · {review.author}, {formatDateTime(review.createdAt)}
              {review.note && <span className="block">“{review.note}”</span>}
            </>
          ) : (
            "Sugerida · não confirmada"
          )}
        </span>
        <QuestionButton nodeId={node.id} />
      </p>
      <div className="flex gap-4">
        {review?.verdict !== "confirmed" && (
          <button
            type="button"
            className="flex-1 rounded-full bg-action px-6 py-1 text-xs leading-5 font-semibold text-white transition-[filter] hover:brightness-95 disabled:opacity-50"
            disabled={create.isPending}
            onClick={() => save("confirmed")}
          >
            Confirmar
          </button>
        )}
        {review?.verdict !== "discarded" && (
          <button
            type="button"
            className="flex-1 rounded-full border border-border-strong bg-surface px-6 py-1 text-xs leading-5 font-semibold text-fg transition-colors hover:bg-surface-muted"
            onClick={() => setDiscarding(true)}
          >
            Descartar
          </button>
        )}
      </div>
      {create.isError && (
        <p role="alert" className="w-full text-danger">
          Não foi possível registrar. Tente novamente.
        </p>
      )}
    </div>
  );
};
