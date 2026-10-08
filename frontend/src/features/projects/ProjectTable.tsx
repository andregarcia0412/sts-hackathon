import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { TONE_STYLES } from "@/components/ui/toneStyles";
import { DECISION_OUTCOME_LABELS, DECISION_OUTCOME_TONES } from "@/domain/labels";
import { projectCode } from "@/domain/projects";
import type { Tone } from "@/domain/qualitative";
import type { ProjectSummary } from "@/domain/types";
import { situationOf, weakestCriterionOf } from "@/features/projects/projectRow";
import type { Situation, WeakestCriterion } from "@/features/projects/projectRow";
import { formatDate, pluralize } from "@/lib/format";
import { paths } from "@/routes/paths";

/* Static class names so Tailwind can see them */
const STRIP_FILL: Record<Tone, string> = {
  positive: "bg-state-positive",
  attention: "bg-state-attention-bar",
  negative: "bg-state-negative",
  neutral: "bg-fg-faint",
};

const MARKER_FILL: Record<Tone, string> = {
  positive: "bg-state-positive",
  attention: "bg-state-attention-mark",
  negative: "bg-state-negative",
  neutral: "bg-fg-faint",
};

interface ProjectTableProps {
  projects: ProjectSummary[];
  /** "Reenviar arquivo" on projects whose file could not be read */
  onResend: (project: ProjectSummary) => void;
  /** Filters and sort, shown above the columns */
  toolbar?: ReactNode;
  /** Pagination, shown under the rows */
  footer?: ReactNode;
}

export const ProjectTable = ({ projects, onResend, toolbar, footer }: ProjectTableProps) => (
  <div className="overflow-hidden rounded-3xl bg-white/80 shadow-[0_4px_16px_rgb(0_0_0/0.1)]">
    {toolbar}
    <div className="overflow-x-auto">
      <table className="w-full min-w-[1100px] table-fixed text-left">
        <colgroup>
          <col className="w-[28%]" />
          <col className="w-[9%]" />
          <col className="w-[13%]" />
          <col className="w-[22%]" />
          <col className="w-[12%]" />
          <col className="w-[16%]" />
        </colgroup>
        <thead className="border-b border-track text-xs font-semibold text-fg-muted">
          <tr>
            <th scope="col" className="py-3.5 pr-4 pl-6">Projeto</th>
            <th scope="col" className="px-4 py-3.5" title="Data de corte do período analisado">
              Corte
            </th>
            <th scope="col" className="px-4 py-3.5">Situação</th>
            <th scope="col" className="px-4 py-3.5">Critério mais fraco</th>
            <th scope="col" className="px-4 py-3.5">Decisão</th>
            <th scope="col" className="py-3.5 pr-6 pl-4">
              <span className="sr-only">Ações</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-divider text-[13px] leading-5">
          {projects.map((project) => (
            <Row key={project.id} project={project} onResend={onResend} />
          ))}
        </tbody>
      </table>
    </div>
    {footer}
  </div>
);

const Row = ({ project, onResend }: { project: ProjectSummary; onResend: (p: ProjectSummary) => void }) => {
  const files = project.documents.length;
  const meta = [
    project.company,
    files ? pluralize(files, "arquivo", "arquivos") : project.freeText ? "descrição em texto" : undefined,
    `enviado em ${formatDate(project.createdAt)}`,
    project.openContestationCount
      ? pluralize(project.openContestationCount, "contestação aberta", "contestações abertas")
      : undefined,
  ].filter(Boolean);

  return (
    <tr className="transition-colors hover:bg-surface/70">
      <td className="py-4 pr-4 pl-6 align-top">
        <p className="text-[15px] leading-[22px] font-semibold text-fg">{project.name}</p>
        <div className="mt-2 flex min-w-0 items-center gap-2">
          <span className="shrink-0 rounded-full border border-border-strong bg-surface p-2 text-xs leading-3 font-semibold">
            Projeto {projectCode(project.id)}
          </span>
          <span className="min-w-0 text-xs leading-4 text-fg-muted">{meta.join(" · ")}</span>
        </div>
      </td>
      <td className="px-4 py-4 align-middle text-fg-secondary">
        {project.cutoffDate ? formatDate(project.cutoffDate) : <span className="text-fg-muted">—</span>}
      </td>
      <td className="px-4 py-4 align-middle">
        <SituationCell situation={situationOf(project)} />
      </td>
      <td className="px-4 py-4 align-middle">
        <WeakestCell weakest={weakestCriterionOf(project)} />
      </td>
      <td className="px-4 py-4 align-middle">
        {project.lastDecision ? (
          <span
            className={`inline-block rounded-full px-3 py-1 font-semibold whitespace-nowrap ${
              TONE_STYLES[DECISION_OUTCOME_TONES[project.lastDecision.outcome]].soft
            } ${DECISION_TEXT[DECISION_OUTCOME_TONES[project.lastDecision.outcome]]}`}
            title={`${project.lastDecision.analystName} · ${formatDate(project.lastDecision.decidedAt)}`}
          >
            {DECISION_OUTCOME_LABELS[project.lastDecision.outcome]}
          </span>
        ) : (
          <span className="text-fg-muted">{project.status === "ready" ? "Sem decisão" : "—"}</span>
        )}
      </td>
      <td className="py-4 pr-6 pl-4 text-right align-middle">
        <RowAction project={project} onResend={onResend} />
      </td>
    </tr>
  );
};

const DECISION_TEXT: Record<Tone, string> = {
  positive: "text-state-positive-strong",
  attention: "text-state-attention-strong",
  negative: "text-accent",
  neutral: "text-state-neutral",
};

const RowAction = ({ project, onResend }: { project: ProjectSummary; onResend: (p: ProjectSummary) => void }) => {
  if (project.status === "ready") {
    return (
      <Link to={paths.analysis(project.id)} className="btn-primary" aria-label={`Abrir análise de ${project.name}`}>
        Abrir análise
      </Link>
    );
  }
  if (project.status === "decided") {
    return (
      <Link to={paths.decision(project.id)} className="btn-secondary" aria-label={`Ver decisão de ${project.name}`}>
        Ver decisão
      </Link>
    );
  }
  if (project.status === "error") {
    return (
      <button type="button" className="btn-secondary" onClick={() => onResend(project)}>
        Reenviar arquivo
      </button>
    );
  }
  return null;
};

const SituationCell = ({ situation }: { situation: Situation }) => (
  <div className="flex flex-col gap-1.5">
    <p className={`flex items-center gap-1.5 ${situation.danger ? "font-medium text-state-negative" : "text-fg-secondary"}`}>
      {situation.marker === "ring" && <span aria-hidden className="size-3.5 shrink-0 rounded-full border-2 border-border-strong" />}
      {situation.marker === "dot" && <span aria-hidden className="size-1.5 shrink-0 rounded-full bg-brand-deep" />}
      {situation.marker === "dot-muted" && <span aria-hidden className="size-1.5 shrink-0 rounded-full bg-fg-secondary" />}
      {situation.marker === "dash" && <span aria-hidden className="h-0.5 w-2 shrink-0 rounded bg-state-negative" />}
      {situation.label}
    </p>
    {situation.progress !== undefined && (
      <span
        role="progressbar"
        aria-label="Progresso do processamento"
        aria-valuenow={Math.round(situation.progress * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
        className="block h-1 w-[110px] overflow-hidden rounded-sm bg-track"
      >
        <span className="block h-full rounded-sm bg-brand-deep" style={{ width: `${situation.progress * 100}%` }} />
      </span>
    )}
  </div>
);

const WeakestCell = ({ weakest }: { weakest: WeakestCriterion }) => {
  if (weakest.kind === "message") {
    return <p className="text-fg-muted">{weakest.text}</p>;
  }
  return (
    <div className="flex flex-col gap-1.5">
      {/* One segment per criterion; only the weakest is colored */}
      <span aria-hidden className="flex gap-[3px]">
        {Array.from({ length: weakest.count }, (_, i) => (
          <span
            key={i}
            className={`h-1.5 w-[18px] rounded-[3px] ${i === weakest.index ? STRIP_FILL[weakest.tone] : "bg-strip"}`}
          />
        ))}
      </span>
      <p className="flex flex-wrap items-center gap-x-1.5">
        {weakest.tone === "negative" ? (
          <span aria-hidden className="h-0.5 w-2 rounded bg-state-negative" />
        ) : (
          <span aria-hidden className={`size-1.5 rotate-45 ${MARKER_FILL[weakest.tone]}`} />
        )}
        <span className="text-fg">{weakest.name} ·</span>
        <span className={`font-semibold ${TONE_STYLES[weakest.tone].strongText}`}>{weakest.reading}</span>
      </p>
    </div>
  );
};
