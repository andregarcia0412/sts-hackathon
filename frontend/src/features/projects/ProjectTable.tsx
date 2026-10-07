import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { ScoreBadge } from "@/components/ui/ScoreBadge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { ProjectSummary } from "@/domain/types";
import { formatDate, pluralize } from "@/lib/format";
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

export const ProjectTable = ({ projects }: { projects: ProjectSummary[] }) => {
  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-surface">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-surface-muted text-xs text-fg-muted uppercase">
          <tr>
            <th scope="col" className="px-4 py-2.5 font-medium">Projeto</th>
            <th scope="col" className="px-4 py-2.5 font-medium">Enviado em</th>
            <th scope="col" className="px-4 py-2.5 font-medium">Material</th>
            <th scope="col" className="px-4 py-2.5 font-medium">Status</th>
            <th scope="col" className="px-4 py-2.5 font-medium">
              Força da evidência por critério
            </th>
            <th scope="col" className="px-4 py-2.5">
              <span className="sr-only">Ações</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {projects.map((project) => {
            const link = projectLink(project);
            return (
              <tr key={project.id} className="align-top hover:bg-surface-muted/60">
                <td className="max-w-80 px-4 py-3">
                  {link ? (
                    <Link to={link.to} className="font-medium hover:underline">
                      {project.name}
                    </Link>
                  ) : (
                    <span className="font-medium">{project.name}</span>
                  )}
                  {project.company && (
                    <p className="text-xs text-fg-muted">{project.company}</p>
                  )}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-fg-muted">
                  {formatDate(project.createdAt)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-fg-muted">
                  {pluralize(project.documents.length, "documento", "documentos")}
                  {project.freeText && (
                    <span className="block text-xs">+ texto livre</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={project.status} />
                </td>
                <td className="px-4 py-3">
                  {project.scoreSummary ? (
                    <ul className="flex flex-wrap gap-1.5">
                      {project.scoreSummary.map((item) => (
                        <li
                          key={item.criterionKey}
                          className="flex items-center gap-1 text-xs text-fg-muted"
                        >
                          <span>{item.name}</span>
                          <ScoreBadge score={item.score} size="sm" />
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-xs text-fg-muted">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  {link && (
                    <Link to={link.to} className="btn-ghost whitespace-nowrap">
                      {link.label}
                      <ArrowRight className="size-4" aria-hidden />
                    </Link>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
