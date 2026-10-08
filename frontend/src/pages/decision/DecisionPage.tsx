import { ArrowLeft, Printer } from "lucide-react";
import { useRef } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useReactToPrint } from "react-to-print";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { FRAMEWORKS } from "@/domain/frameworks";
import type { Analysis, Contestation, Decision, Project } from "@/domain/types";
import { useRegisterAssistantContext } from "@/features/assistant/assistantState";
import {
  ReportDetails,
  ReportHeader,
  ReportSection,
  ReportSummary,
} from "@/features/decision/AnalysisReport";
import { DecisionForm } from "@/features/decision/DecisionForm";
import { DecisionTrail } from "@/features/decision/DecisionTrail";
import { FRAMEWORK_PARAM, paths } from "@/routes/paths";
import { NotFoundError } from "@/services/api";
import {
  useAnalyses,
  useContestations,
  useDecisions,
  useProject,
} from "@/services/queries";

export const DecisionPage = () => {
  const { projectId = "" } = useParams();
  const project = useProject(projectId);
  const analyses = useAnalyses(projectId);
  const decisions = useDecisions(projectId);
  const contestations = useContestations(projectId);

  const backToProjects = (
    <Link to={paths.projects()} className="btn-secondary">
      Voltar para os projetos
    </Link>
  );

  if (project.isPending || analyses.isPending || decisions.isPending || contestations.isPending) {
    return <LoadingState label="Carregando documento de decisão…" />;
  }

  if (project.isError || analyses.isError || decisions.isError || contestations.isError) {
    const error = project.error ?? analyses.error ?? decisions.error ?? contestations.error;
    return (
      <ErrorState
        action={backToProjects}
        title={
          error instanceof NotFoundError
            ? "Projeto não encontrado"
            : "Não foi possível carregar o documento de decisão"
        }
      />
    );
  }

  if (analyses.data === null) {
    return (
      <ErrorState
        action={backToProjects}
        title="A análise deste projeto ainda não está pronta"
        error={new Error("O documento de decisão fica disponível quando a análise terminar.")}
      />
    );
  }

  return (
    <DecisionDocument
      project={project.data}
      analyses={analyses.data}
      decisions={decisions.data}
      contestations={contestations.data}
    />
  );
};

interface DecisionDocumentProps {
  project: Project;
  /** One analysis per method; the first is the primary one */
  analyses: Analysis[];
  decisions: Decision[];
  contestations: Contestation[];
}

const DecisionDocument = ({
  project,
  analyses,
  decisions,
  contestations,
}: DecisionDocumentProps) => {
  const documentRef = useRef<HTMLElement>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const print = useReactToPrint({
    contentRef: documentRef,
    documentTitle: `Decisao_${project.name}_${analyses[0].id}`.replace(/[^\w-]+/g, "_"),
  });

  // The assistant answers about the method in ?metodo= (default: the first)
  const focused =
    analyses.find((a) => a.framework === searchParams.get(FRAMEWORK_PARAM)) ?? analyses[0];
  useRegisterAssistantContext({ screen: "decision", analysis: focused, selectedNodeId: null });

  const goToMethod = (analysis: Analysis) => {
    setSearchParams({ [FRAMEWORK_PARAM]: analysis.framework }, { replace: true });
    document
      .getElementById(`detalhamento-${analysis.framework}`)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const contestedIdsOf = (analysis: Analysis) =>
    new Set(contestations.filter((c) => c.analysisId === analysis.id).map((c) => c.nodeId));

  return (
    <div className="flex-1 bg-surface-muted print:bg-white">
      <div className="sticky top-0 z-10 border-b border-border bg-surface/95 backdrop-blur print:hidden">
        <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-6 py-2">
          <Link to={paths.analysis(project.id, undefined, focused.framework)} className="btn-ghost">
            <ArrowLeft className="size-4" aria-hidden />
            Voltar para a análise
          </Link>
          {analyses.length > 1 && (
            <nav aria-label="Detalhamento por método" className="flex items-center gap-1 text-sm">
              <span className="text-xs text-fg-muted">Ir para:</span>
              {analyses.map((analysis) => (
                <button
                  key={analysis.id}
                  type="button"
                  className={`btn-ghost px-2 py-1 ${analysis.id === focused.id ? "text-fg" : ""}`}
                  aria-current={analysis.id === focused.id ? "true" : undefined}
                  onClick={() => goToMethod(analysis)}
                >
                  {FRAMEWORKS[analysis.framework].label}
                </button>
              ))}
            </nav>
          )}
          <button type="button" className="btn-primary" onClick={() => print()}>
            <Printer className="size-4" aria-hidden />
            Exportar PDF
          </button>
        </div>
      </div>

      <article
        ref={documentRef}
        className="mx-auto my-8 max-w-4xl space-y-10 bg-surface px-8 py-10 font-serif leading-relaxed shadow-sm sm:px-14 print:my-0 print:max-w-none print:px-0 print:py-0 print:shadow-none"
      >
        <ReportHeader project={project} analyses={analyses} />
        <ReportSection title="Resumo">
          {analyses.map((analysis) => (
            <ReportSummary key={analysis.id} analysis={analysis} />
          ))}
        </ReportSection>
        {analyses.map((analysis) => (
          <ReportDetails
            key={analysis.id}
            project={project}
            analysis={analysis}
            contestedIds={contestedIdsOf(analysis)}
          />
        ))}
        {/* The form is not printed: the trail below carries the current decision */}
        <ReportSection title="Decisão do analista" className="print:hidden">
          <DecisionForm analyses={analyses} hasPrevious={decisions.length > 0} />
        </ReportSection>
        <ReportSection title="Trilha de decisão">
          <DecisionTrail
            decisions={decisions}
            contestations={contestations}
            analyses={analyses}
          />
        </ReportSection>
      </article>
    </div>
  );
};
