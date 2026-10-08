import { Fragment } from "react";
import type { ReactNode } from "react";
import { Tag } from "@/components/ui/Tag";
import type { Tone } from "@/domain/qualitative";
import type { Project, ProjectStatus } from "@/domain/types";

const STATUS: Record<ProjectStatus, { label: string; tone: Tone }> = {
  processing: { label: "Processando", tone: "neutral" },
  ready: { label: "Em análise", tone: "neutral" },
  decided: { label: "Decidido", tone: "positive" },
  error: { label: "Erro no processamento", tone: "negative" },
};

interface ProjectHeaderProps {
  project: Project;
  /** "Empresa: X", "3 documentos"... shown separated by "·" */
  meta: string[];
  /** Under the status tag, e.g. "0 de 5 critérios decididos pelo analista" */
  progress?: string;
  /** Main action of the screen */
  action?: ReactNode;
}

/** "Projeto em análise" band: identification on the left, status and action on the right */
export const ProjectHeader = ({ project, meta, progress, action }: ProjectHeaderProps) => {
  const status = STATUS[project.status];

  return (
    <div className="flex shrink-0 flex-wrap items-end gap-x-6 gap-y-4 border-b border-border bg-white/50 px-4 pt-4 pb-6 sm:px-10 print:hidden">
      <div className="flex min-w-0 flex-1 basis-96 flex-col items-start gap-4">
        <span className="btn-chip cursor-default hover:bg-surface">Projeto {project.id.toUpperCase()}</span>
        <h1 className="text-2xl leading-7 font-semibold text-fg">{project.name}</h1>
        <p className="flex flex-wrap gap-y-1 text-xs leading-4 text-fg-muted">
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
      </div>
      <div className="flex flex-wrap items-end gap-4">
        <div className="flex flex-col items-end gap-1">
          <Tag tone={status.tone} label={status.label} />
          {progress && <p className="text-xs leading-4 text-fg-muted">{progress}</p>}
        </div>
        {action}
      </div>
    </div>
  );
};
