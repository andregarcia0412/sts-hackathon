import { Plus } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/layout/PageHeader";
import { Pagination } from "@/components/ui/Pagination";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import type { ProjectSummary } from "@/domain/types";
import { useCurrentUser } from "@/features/auth/authState";
import { NewProjectDialog } from "@/features/projects/NewProjectDialog";
import { ListToolbar } from "@/features/projects/ListToolbar";
import { ProjectSearch } from "@/features/projects/ProjectSearch";
import { ProjectTable } from "@/features/projects/ProjectTable";
import { ResendFileDialog } from "@/features/projects/ResendFileDialog";
import { StatusTabs } from "@/features/projects/StatusTabs";
import { PAGE_SIZE, useProjectFilters } from "@/features/projects/useProjectFilters";
import { NEW_PROJECT_PARAM } from "@/routes/paths";
import { useProjects } from "@/services/queries";

export const ProjectsPage = () => {
  const user = useCurrentUser();
  const [resending, setResending] = useState<ProjectSummary | null>(null);
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
      <Plus className="size-6" aria-hidden />
      Novo projeto
    </button>
  );

  const data = projects.data;
  const ownsNothing = data && Object.values(data.statusCounts).every((n) => n === 0);

  return (
    <div className="flex flex-1 flex-col">
      <PageHeader
        title="Meus Projetos"
        description={<p>Análise preliminar de enquadramento na Lei do Bem · {user.name} · dados fictícios de demonstração</p>}
        aside={newProjectButton}
      >
        {data && !ownsNothing && (
          <div className="flex flex-wrap items-center justify-between gap-4">
            <StatusTabs
              counts={data.statusCounts}
              selected={filters.statuses ?? []}
              onSelect={(statuses) => update({ statuses })}
            />
            <ProjectSearch value={filters.search ?? ""} onSearch={(search) => update({ search })} />
          </div>
        )}
      </PageHeader>

      <div className="mx-auto flex w-full max-w-[1440px] flex-1 flex-col p-4">
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
          // Dim while a new page/filter loads; the previous page stays visible
          <div
            className={`transition-opacity ${projects.isPlaceholderData ? "opacity-60" : ""}`}
            aria-busy={projects.isFetching}
          >
            {data.items.length === 0 ? (
              <div className="rounded-3xl bg-white/80 shadow-[0_4px_16px_rgb(0_0_0/0.1)]">
                <ListToolbar filters={filters} update={update} clear={clear} activeCount={activeCount} />
                <EmptyState
                  title="Nenhum projeto com esses filtros"
                  description="Ajuste ou limpe os filtros para ver mais projetos."
                  action={
                    <button type="button" className="btn-secondary" onClick={clear}>
                      Limpar filtros
                    </button>
                  }
                />
              </div>
            ) : (
              <ProjectTable
                projects={data.items}
                onResend={setResending}
                toolbar={
                  <ListToolbar filters={filters} update={update} clear={clear} activeCount={activeCount} />
                }
                footer={
                  <Pagination
                    className="px-6 py-4"
                    page={data.page}
                    pageSize={data.pageSize}
                    total={data.total}
                    note="a leitura do sistema é sugestão até a decisão do analista"
                    onChange={(page) => update({ page })}
                  />
                }
              />
            )}
          </div>
        )}
      </div>
      <NewProjectDialog open={dialogOpen} onClose={closeDialog} />
      <ResendFileDialog project={resending} onClose={() => setResending(null)} />
    </div>
  );
};
