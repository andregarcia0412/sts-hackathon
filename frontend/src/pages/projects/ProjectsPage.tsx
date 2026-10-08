import { Plus } from "lucide-react";
import { useState } from "react";
import { Pagination } from "@/components/ui/Pagination";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useCurrentUser } from "@/features/auth/authState";
import { NewProjectDialog } from "@/features/projects/NewProjectDialog";
import { ProjectFilterBar } from "@/features/projects/ProjectFilterBar";
import { ProjectOverview } from "@/features/projects/ProjectOverview";
import { ProjectTable } from "@/features/projects/ProjectTable";
import { PAGE_SIZE, useProjectFilters } from "@/features/projects/useProjectFilters";
import { useProjects } from "@/services/queries";

export const ProjectsPage = () => {
  const user = useCurrentUser();
  const { filters, update, clear, activeCount } = useProjectFilters();
  const projects = useProjects({ ...filters, ownerId: user.id, pageSize: PAGE_SIZE });
  const [dialogOpen, setDialogOpen] = useState(false);

  const newProjectButton = (
    <button type="button" className="btn-primary" onClick={() => setDialogOpen(true)}>
      <Plus className="size-4" aria-hidden />
      Novo projeto
    </button>
  );

  const data = projects.data;
  const ownsNothing = data && Object.values(data.statusCounts).every((n) => n === 0);

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-5 p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Meus projetos</h1>
          <p className="text-sm text-fg-muted">
            Projetos de {user.name} para análise preliminar de enquadramento na Lei do Bem.
            {" "}
            <span className="text-xs">(Dados de demonstração, fictícios.)</span>
          </p>
        </div>
        {newProjectButton}
      </div>

      {projects.isError && !data ? (
        <ErrorState
          title="Não foi possível carregar os projetos"
          error={projects.error}
          onRetry={() => projects.refetch()}
        />
      ) : !data ? (
        <LoadingState label="Carregando projetos…" />
      ) : ownsNothing ? (
        <EmptyState
          title="Nenhum projeto ainda"
          description="Envie os documentos ou uma descrição de um projeto para gerar a primeira análise."
          action={newProjectButton}
        />
      ) : (
        <>
          <ProjectOverview
            counts={data.statusCounts}
            selected={filters.statuses ?? []}
            onSelect={(statuses) => update({ statuses })}
          />
          <ProjectFilterBar filters={filters} update={update} clear={clear} activeCount={activeCount} />
          {/* Dim while a new page/filter loads; the previous page stays visible */}
          <div
            className={`space-y-3 transition-opacity ${projects.isPlaceholderData ? "opacity-60" : ""}`}
            aria-busy={projects.isFetching}
          >
            {data.items.length === 0 ? (
              <EmptyState
                title="Nenhum projeto com esses filtros"
                description="Ajuste ou limpe os filtros para ver mais projetos."
                action={
                  <button type="button" className="btn-secondary" onClick={clear}>
                    Limpar filtros
                  </button>
                }
              />
            ) : (
              <>
                <ProjectTable projects={data.items} />
                <Pagination
                  page={data.page}
                  pageSize={data.pageSize}
                  total={data.total}
                  onChange={(page) => update({ page })}
                />
              </>
            )}
          </div>
        </>
      )}

      <NewProjectDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
    </div>
  );
};
