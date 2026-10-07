import { ArrowLeft, Printer } from "lucide-react";
import { useRef } from "react";
import { Link, useParams } from "react-router-dom";
import { useReactToPrint } from "react-to-print";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { indexAnalysis } from "@/domain/tree";
import type { Analysis, Decision, Project } from "@/domain/types";
import {
  ReportDetails,
  ReportHeader,
  ReportSection,
  ReportSummary,
} from "@/features/decision/AnalysisReport";
import { DecisionForm } from "@/features/decision/DecisionForm";
import { DecisionTrail } from "@/features/decision/DecisionTrail";
import { paths } from "@/routes/paths";
import { NotFoundError } from "@/services/api";
import { useAnalysis, useDecisions, useProject } from "@/services/queries";

export const DecisionPage = () => {
  const { projectId = "" } = useParams();
  const project = useProject(projectId);
  const analysis = useAnalysis(projectId);
  const decisions = useDecisions(projectId);

  if (project.isPending || analysis.isPending || decisions.isPending) {
    return <LoadingState label="Carregando documento de decisão…" />;
  }

  if (project.isError || analysis.isError || decisions.isError) {
    const error = project.error ?? analysis.error ?? decisions.error;
    return (
      <ErrorState
        action={
          <Link to={paths.projects()} className="btn-secondary">
            Voltar para os projetos
          </Link>
        }
        title={
          error instanceof NotFoundError
            ? "Projeto não encontrado"
            : "Não foi possível carregar o documento de decisão"
        }
      />
    );
  }

  if (analysis.data === null) {
    return (
      <ErrorState
        action={
          <Link to={paths.projects()} className="btn-secondary">
            Voltar para os projetos
          </Link>
        }
        title="A análise deste projeto ainda não está pronta"
        error={new Error("O documento de decisão fica disponível quando a análise terminar.")}
      />
    );
  }

  return (
    <DecisionDocument
      project={project.data}
      analysis={analysis.data}
      decisions={decisions.data}
    />
  );
};

interface DecisionDocumentProps {
  project: Project;
  analysis: Analysis;
  decisions: Decision[];
}

const DecisionDocument = ({ project, analysis, decisions }: DecisionDocumentProps) => {
  const documentRef = useRef<HTMLElement>(null);
  const print = useReactToPrint({
    contentRef: documentRef,
    documentTitle: `Decisao_${project.name}_${analysis.id}`.replace(/[^\w-]+/g, "_"),
  });
  const index = indexAnalysis(analysis);

  return (
    <div className="flex-1 bg-surface-muted print:bg-white">
      <div className="sticky top-0 z-10 border-b border-border bg-surface/95 backdrop-blur print:hidden">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-4 px-6 py-2">
          <Link to={paths.analysis(project.id)} className="btn-ghost">
            <ArrowLeft className="size-4" aria-hidden />
            Voltar para a análise
          </Link>
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
        <ReportHeader project={project} analysis={analysis} />
        <ReportSummary analysis={analysis} />
        <ReportDetails project={project} analysis={analysis} />
        {/* The form is not printed: the trail below carries the current decision */}
        <ReportSection title="Decisão do analista" className="print:hidden">
          <DecisionForm analysis={analysis} hasPrevious={decisions.length > 0} />
        </ReportSection>
        <ReportSection title="Trilha de decisão">
          <DecisionTrail decisions={decisions} analysis={analysis} index={index} />
        </ReportSection>
      </article>
    </div>
  );
};
