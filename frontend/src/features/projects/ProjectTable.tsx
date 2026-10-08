import { ChevronRight, Flag, PenLine } from "lucide-react";
import { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import { ArticleIcon, KeyboardArrowRightIcon } from "@/components/icons/MaterialIcons";
import { OutcomeBadge } from "@/components/ui/OutcomeBadge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { FRAMEWORKS } from "@/domain/frameworks";
import type { ProjectSummary } from "@/domain/types";
import { ScoreProfile } from "@/features/projects/ScoreProfile";
import { formatDate, formatDateTime, pluralize } from "@/lib/format";
import { paths } from "@/routes/paths";

/** Where a project opens: analysis when ready, decision when decided */
const projectLink = (project: ProjectSummary) => {
  if (project.status === "ready") {
    return { to: paths.analysis(project.id), label: "Abrir análise" };
  }
  if (project.status === "decided") {
    return { to: paths.decision(project.id), label: "Ver decisão" };
  }
  return null;
};

const COLUMNS = 6;

export const ProjectTable = ({ projects }: { projects: ProjectSummary[] }) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="card relative overflow-x-auto">
      <table className="w-full text-left text-sm leading-5">
        <thead className="caps-label border-b border-border text-fg-muted">
          <tr>
            <th scope="col" className="px-4 py-3 font-semibold">Projeto</th>
            <th scope="col" className="px-4 py-3 font-semibold">Enviado em</th>
            <th scope="col" className="px-4 py-3 font-semibold">Status</th>
            <th scope="col" className="px-4 py-3 font-semibold">Critério mais fraco</th>
            <th scope="col" className="px-4 py-3 font-semibold">Decisão</th>
            <th scope="col" className="px-4 py-3">
              <span className="sr-only">Ações</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {projects.map((project) => {
            const link = projectLink(project);
            const expanded = expandedId === project.id;
            const detailsId = `detalhes-${project.id}`;
            return (
              <Fragment key={project.id}>
                <tr className="align-top transition-colors hover:bg-surface">
                  <td className="max-w-96 px-4 py-4">
                    <div className="flex items-start gap-1.5">
                      <button
                        type="button"
                        className="-ml-1.5 rounded-full p-0.5 text-fg-secondary hover:bg-surface-sunken"
                        aria-expanded={expanded}
                        aria-controls={detailsId}
                        aria-label={`${expanded ? "Ocultar" : "Ver"} detalhes de ${project.name}`}
                        onClick={() => setExpandedId(expanded ? null : project.id)}
                      >
                        <ChevronRight
                          className={`size-5 transition-transform ${expanded ? "rotate-90" : ""}`}
                          aria-hidden
                        />
                      </button>
                      <div className="min-w-0">
                        {link ? (
                          <Link to={link.to} className="text-base leading-5 font-semibold hover:text-accent hover:underline">
                            {project.name}
                          </Link>
                        ) : (
                          <span className="text-base leading-5 font-semibold">{project.name}</span>
                        )}
                        <p className="mt-1 text-xs leading-4 text-fg-muted">
                          {project.company ?? "Empresa não informada"}
                          {!!project.contestationCount && (
                            <span className="ml-2 inline-flex items-center gap-1 text-fg-secondary">
                              <Flag className="size-3 text-state-attention" aria-hidden />
                              {pluralize(project.contestationCount, "contestação", "contestações")}
                              {!!project.openContestationCount &&
                                ` (${project.openContestationCount} ${project.openContestationCount === 1 ? "aberta" : "abertas"})`}
                            </span>
                          )}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-fg-muted">
                    {formatDate(project.createdAt)}
                  </td>
                  <td className="px-4 py-4">
                    <StatusBadge status={project.status} />
                  </td>
                  <td className="px-4 py-4">
                    {project.scoreSummary ? (
                      <ScoreProfile scores={project.scoreSummary} />
                    ) : (
                      <span className="text-xs text-fg-muted">—</span>
                    )}
                  </td>
                  <td className="px-4 py-4">
                    {project.lastDecision ? (
                      <>
                        <OutcomeBadge outcome={project.lastDecision.outcome} />
                        <p className="mt-1 text-xs text-fg-muted">{formatDate(project.lastDecision.decidedAt)}</p>
                      </>
                    ) : (
                      <span className="text-xs text-fg-muted">Sem decisão</span>
                    )}
                  </td>
                  <td className="px-4 py-4 text-right">
                    {link && (
                      <Link to={link.to} className="btn-chip pr-2">
                        {link.label}
                        <KeyboardArrowRightIcon className="size-5" />
                      </Link>
                    )}
                  </td>
                </tr>
                {expanded && (
                  <tr id={detailsId} className="bg-surface-muted">
                    <td colSpan={COLUMNS} className="px-4 py-4">
                      <ProjectDetails project={project} />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

/** Useful information at a glance, without opening the project */
const ProjectDetails = ({ project }: { project: ProjectSummary }) => (
  <dl className="grid gap-x-8 gap-y-4 pl-6 text-sm leading-5 sm:grid-cols-2 lg:grid-cols-4">
    <div>
      <dt className="caps-label text-fg-muted">Material</dt>
      <dd>
        <ul className="mt-1 space-y-0.5">
          {project.documents.map((doc) => (
            <li key={doc.id} className="flex items-center gap-1.5">
              <ArticleIcon className="size-4 shrink-0 text-fg-secondary" />
              <span className="truncate">{doc.fileName}</span>
            </li>
          ))}
          {project.freeText && (
            <li className="flex items-center gap-1.5">
              <PenLine className="size-3.5 shrink-0 text-fg-muted" aria-hidden />
              Descrição em texto livre
            </li>
          )}
          {project.documents.length === 0 && !project.freeText && <li className="text-fg-muted">—</li>}
        </ul>
      </dd>
    </div>
    <div>
      <dt className="caps-label text-fg-muted">Métodos analisados</dt>
      <dd className="mt-1">
        {project.frameworks?.length
          ? project.frameworks.map((f) => FRAMEWORKS[f].label).join(" · ")
          : "Análise ainda não disponível"}
      </dd>
    </div>
    <div>
      <dt className="caps-label text-fg-muted">Notas por critério</dt>
      <dd className="mt-1">
        {project.scoreSummary ? (
          <ul className="space-y-0.5">
            {project.scoreSummary.map((s) => (
              <li key={s.criterionKey} className="flex justify-between gap-3">
                <span>{s.name}</span>
                <span className="font-medium tabular-nums">{s.score}</span>
              </li>
            ))}
          </ul>
        ) : (
          "—"
        )}
      </dd>
    </div>
    <div>
      <dt className="caps-label text-fg-muted">Última decisão</dt>
      <dd className="mt-1">
        {project.lastDecision ? (
          <>
            <OutcomeBadge outcome={project.lastDecision.outcome} />
            <p className="text-xs text-fg-muted">
              {project.lastDecision.analystName} · {formatDateTime(project.lastDecision.decidedAt)}
            </p>
          </>
        ) : (
          "Nenhuma"
        )}
        {project.freeText && (
          <p className="mt-2 line-clamp-3 text-xs text-fg-muted">“{project.freeText}”</p>
        )}
      </dd>
    </div>
  </dl>
);
