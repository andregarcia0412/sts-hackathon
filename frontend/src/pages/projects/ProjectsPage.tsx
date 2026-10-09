import { Plus } from "lucide-react";
import { useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/layout/PageHeader";
import { Pagination } from "@/components/ui/Pagination";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import type { ProjectSummary } from "@/domain/types";
import { useCurrentUser } from "@/features/auth/authState";
import { ProjectSearch } from "@/features/projects/ProjectSearch";
import { dataSourceLabel } from "@/services/api";
import { ProjectTable } from "@/features/projects/ProjectTable";
import { ResendFileDialog } from "@/features/projects/ResendFileDialog";
import { ProjectFilterBar } from "@/features/projects/ProjectFilterBar";
import { StatCards } from "@/features/projects/StatCards";
import { PAGE_SIZE, useProjectFilters } from "@/features/projects/useProjectFilters";
import { NEW_PROJECT_PARAM, paths } from "@/routes/paths";
import { useProjects } from "@/services/queries";

export const ProjectsPage = () => {
  const user = useCurrentUser();
  const [resending, setResending] = useState<ProjectSummary | null>(null);
  const { filters, update, clear, activeCount } = useProjectFilters();
  const projects = useProjects({ ...filters, ownerId: user.id, pageSize: PAGE_SIZE });
  // Old links (?novo=1) open the upload screen
  const [searchParams] = useSearchParams();

  const newProjectButton = (
    <Link to={paths.newProject()} className="btn-primary">
      <Plus className="size-6" aria-hidden />
      Novo projeto
    </Link>
  );

  if (searchParams.has(NEW_PROJECT_PARAM)) return <Navigate to={paths.newProject()} replace />;

  const data = projects.data;
  const ownsNothing = data && Object.values(data.statusCounts).every((n) => n === 0);

  return (
    // Large screens: header and filters stay fixed, only the list scrolls (design)
    <div className="flex flex-1 flex-col lg:min-h-0 lg:overflow-hidden">
      <PageHeader
        title="Meus Projetos"
        description={
          <p>
            Análise preliminar de enquadramento na Lei do Bem · {dataSourceLabel().toLowerCase()}
          </p>
        }
        aside={newProjectButton}
      >
        {data && !ownsNothing && (
          <>
            <StatCards
              counts={data.statusCounts}
              selected={filters.statuses ?? []}
              onSelect={(statuses) => update({ statuses })}
            />
            <div className="flex flex-wrap items-center justify-between gap-4">
              <ProjectFilterBar filters={filters} update={update} clear={clear} activeCount={activeCount} />
              <ProjectSearch value={filters.search ?? ""} onSearch={(search) => update({ search })} />
            </div>
          </>
        )}
      </PageHeader>

      <div className="flex w-full flex-1 flex-col p-4 lg:min-h-0">
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
            className={`flex flex-col transition-opacity lg:min-h-0 lg:flex-1 ${projects.isPlaceholderData ? "opacity-60" : ""}`}
            aria-busy={projects.isFetching}
          >
            {data.items.length === 0 ? (
              <div className="rounded-3xl bg-white/80 shadow-[0_4px_16px_rgb(0_0_0/0.1)]">
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
      <ResendFileDialog project={resending} onClose={() => setResending(null)} />
    </div>
  );
};
