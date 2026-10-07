import { LoaderCircle } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { AnalysisWorkspace } from "@/features/analysis/AnalysisWorkspace";
import { paths } from "@/routes/paths";
import { NotFoundError } from "@/services/api";
import { useAnalysis, useProject } from "@/services/queries";

export const AnalysisPage = () => {
  const { projectId = "" } = useParams();
  const project = useProject(projectId);
  const analysis = useAnalysis(projectId);

  if (project.isPending || analysis.isPending) {
    return <LoadingState label="Carregando análise…" />;
  }

  if (project.isError || analysis.isError) {
    const error = project.error ?? analysis.error;
    return (
      <ErrorState
        title={
          error instanceof NotFoundError
            ? "Projeto não encontrado"
            : "Não foi possível carregar a análise"
        }
        onRetry={
          error instanceof NotFoundError
            ? undefined
            : () => {
                project.refetch();
                analysis.refetch();
              }
        }
      />
    );
  }

  if (project.data.status === "error") {
    return (
      <ErrorState
        title="Não foi possível processar este projeto"
        error={new Error(
          "O material enviado não pôde ser analisado. Verifique os arquivos e envie o projeto novamente.",
        )}
      />
    );
  }

  if (analysis.data === null) {
    return (
      <div
        role="status"
        className="flex flex-1 flex-col items-center justify-center gap-2 p-10 text-center"
      >
        <LoaderCircle className="size-8 animate-spin text-accent" aria-hidden />
        <p className="font-medium">Análise ainda em processamento</p>
        <p className="max-w-md text-sm text-fg-muted">
          Estamos lendo o material de “{project.data.name}”. Esta página é
          atualizada sozinha quando a análise ficar pronta.
        </p>
        <Link to={paths.projects()} className="btn-secondary mt-2">
          Voltar para os projetos
        </Link>
      </div>
    );
  }

  return <AnalysisWorkspace project={project.data} analysis={analysis.data} />;
};
