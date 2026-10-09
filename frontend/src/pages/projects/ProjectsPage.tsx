import { Plus } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { dataSourceLabel } from "@/services/api";
import { useCurrentUser } from "@/features/auth/authState";
import { NewProjectDialog } from "@/features/projects/NewProjectDialog";
import { PageHeader } from "@/components/layout/PageHeader";
import { Pagination } from "@/components/ui/Pagination";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { ProjectFilterBar } from "@/features/projects/ProjectFilterBar";
import { ProjectOverview } from "@/features/projects/ProjectOverview";
import { ProjectTable } from "@/features/projects/ProjectTable";
import { PAGE_SIZE, useProjectFilters } from "@/features/projects/useProjectFilters";
import { NEW_PROJECT_PARAM } from "@/routes/paths";
import { useProjects } from "@/services/queries";

export const ProjectsPage = () => {
  const user = useCurrentUser();
  const { filters, update, clear, activeCount } = useProjectFilters();
  const projects = useProjects({ ...filters, ownerId: user.id, pageSize: PAGE_SIZE });
  // "Upload de arquivos" in the header links here with ?novo=1
  const [searchParams, setSearchParams] = useSearchParams();
  const [openedHere, setDialogOpen] = useState(false);
  const dialogOpen = openedHere || searchParams.has(NEW_PROJECT_PARAM);
  const closeDialog = () => {
    setDialogOpen(false);
    if (searchParams.has(NEW_PROJECT_PARAM)) {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.delete(NEW_PROJECT_PARAM);
          return next;
        },
        { replace: true },
      );
    }
  };

  const newProjectButton = (
    <button type="button" className="btn-primary" onClick={() => setDialogOpen(true)}>
      <Plus className="size-5" aria-hidden />
      Novo projeto
    </button>
  );

  const data = projects.data;
  const ownsNothing = data && Object.values(data.statusCounts).every((n) => n === 0);

  return (
    <div className="flex flex-1 flex-col">
      <PageHeader
        eyebrow={<span className="btn-chip cursor-default hover:bg-surface">Analista: {user.name}</span>}
        title="Meus projetos"
        description={
          <p>
            Projetos para análise preliminar de enquadramento na Lei do Bem ·{" "}
            {dataSourceLabel().toLowerCase()}.
          </p>
        }
        aside={newProjectButton}
      />
      <div className="mx-auto flex w-full max-w-[1440px] flex-1 flex-col gap-4 p-4 sm:px-10 sm:py-6">
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
              className={`flex flex-col gap-4 transition-opacity ${projects.isPlaceholderData ? "opacity-60" : ""}`}
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
      </div>
      <NewProjectDialog open={dialogOpen} onClose={closeDialog} />
    </div>
  );
};
