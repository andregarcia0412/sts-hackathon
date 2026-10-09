import { Fragment } from "react";
import type { ReactNode } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { projectCode } from "@/domain/projects";
import type { Project } from "@/domain/types";

interface ProjectHeaderProps {
  project: Project;
  /** "Empresa: X", "3 documentos"... shown separated by "·" */
  meta: string[];
  /** Under the status tag, e.g. "0 de 5 critérios decididos pelo analista" */
  progress?: string;
  /** Main action of the screen */
  action?: ReactNode;
  /** The decision document shows no status tag (as in the design) */
  showStatus?: boolean;
}

/** "Projeto em análise" band: identification on the left, status and action on the right */
export const ProjectHeader = ({ project, meta, progress, action, showStatus = true }: ProjectHeaderProps) => (
  <PageHeader
    eyebrow={<span className="btn-chip cursor-default hover:bg-surface">Projeto {projectCode(project.id)}</span>}
    title={project.name}
    description={
      <p className="flex flex-wrap gap-y-1">
        {meta.map((item, i) => (
          <Fragment key={item}>
            {i > 0 && (
              <span aria-hidden className="mx-2">
                ·
              </span>
            )}
            <span>{item}</span>
          </Fragment>
        ))}
      </p>
    }
    aside={
      <>
        {(showStatus || progress) && (
          <div className="flex flex-col items-end gap-1">
            {showStatus && <StatusBadge status={project.status} size="md" />}
            {progress && <p className="text-xs leading-4 text-fg-muted">{progress}</p>}
          </div>
        )}
        {action}
      </>
    }
  />
);
