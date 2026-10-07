import { Plus } from "lucide-react";
import { useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { NewProjectDialog } from "@/features/projects/NewProjectDialog";
import { ProjectTable } from "@/features/projects/ProjectTable";
import { useProjects } from "@/services/queries";

export const ProjectsPage = () => {
  const projects = useProjects();
  const [dialogOpen, setDialogOpen] = useState(false);

  const newProjectButton = (
    <button
      type="button"
      className="btn-primary"
      onClick={() => setDialogOpen(true)}
    >
      <Plus className="size-4" aria-hidden />
      Novo projeto
    </button>
  );

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Projetos</h1>
          <p className="text-sm text-fg-muted">
            Projetos enviados para análise preliminar de enquadramento na Lei
            do Bem.
          </p>
        </div>
        {newProjectButton}
      </div>

      {projects.isPending ? (
        <LoadingState label="Carregando projetos…" />
      ) : projects.isError ? (
        <ErrorState
          title="Não foi possível carregar os projetos"
          error={projects.error}
          onRetry={() => projects.refetch()}
        />
      ) : projects.data.length === 0 ? (
        <EmptyState
          title="Nenhum projeto ainda"
          description="Envie os documentos ou uma descrição de um projeto para gerar a primeira análise."
          action={newProjectButton}
        />
      ) : (
        <ProjectTable projects={projects.data} />
      )}

      <NewProjectDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
    </div>
  );
};
