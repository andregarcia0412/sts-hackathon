import { Printer } from "lucide-react";
import { useRef } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useReactToPrint } from "react-to-print";
import { ProjectHeader } from "@/components/layout/ProjectHeader";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { reviewMarkers } from "@/domain/contestations";
import { FRAMEWORKS } from "@/domain/frameworks";
import { DECISION_OUTCOME_LABELS } from "@/domain/labels";
import { decidedCriteriaCount, latestByNode } from "@/domain/reviews";
import type {
  Analysis,
  Contestation,
  Decision,
  EvidenceReview,
  Project,
  RuleDecision,
} from "@/domain/types";
import { useRegisterAssistantContext } from "@/features/assistant/assistantState";
import {
  ReportDetails,
  ReportHeader,
  ReportSection,
  ReportSummary,
} from "@/features/decision/AnalysisReport";
import { DecisionForm } from "@/features/decision/DecisionForm";
import { DecisionTrail } from "@/features/decision/DecisionTrail";
import { formatDate, pluralize } from "@/lib/format";
import { FRAMEWORK_PARAM, paths } from "@/routes/paths";
import { NotFoundError } from "@/services/api";
import {
  useAnalyses,
  useContestations,
  useDecisions,
  useEvidenceReviews,
  useProject,
  useRuleDecisions,
} from "@/services/queries";

export const DecisionPage = () => {
  const { projectId = "" } = useParams();
  const project = useProject(projectId);
  const analyses = useAnalyses(projectId);
  const decisions = useDecisions(projectId);
  const contestations = useContestations(projectId);
  const ruleDecisions = useRuleDecisions(projectId);
  const evidenceReviews = useEvidenceReviews(projectId);

  const backToProjects = (
    <Link to={paths.projects()} className="btn-secondary">
      Voltar para os projetos
    </Link>
  );

  if (
    project.isPending ||
    analyses.isPending ||
    decisions.isPending ||
    contestations.isPending ||
    ruleDecisions.isPending ||
    evidenceReviews.isPending
  ) {
    return <LoadingState label="Carregando documento de decisão…" />;
  }

  if (
    project.isError ||
    analyses.isError ||
    decisions.isError ||
    contestations.isError ||
    ruleDecisions.isError ||
    evidenceReviews.isError
  ) {
    const error =
      project.error ??
      analyses.error ??
      decisions.error ??
      contestations.error ??
      ruleDecisions.error ??
      evidenceReviews.error;
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
      ruleDecisions={ruleDecisions.data}
      evidenceReviews={evidenceReviews.data}
    />
  );
};

interface DecisionDocumentProps {
  project: Project;
  /** One analysis per method; the first is the primary one */
  analyses: Analysis[];
  decisions: Decision[];
  contestations: Contestation[];
  ruleDecisions: RuleDecision[];
  evidenceReviews: EvidenceReview[];
}

const DecisionDocument = ({
  project,
  analyses,
  decisions,
  contestations,
  ruleDecisions,
  evidenceReviews,
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

  const reviewsOf = (analysis: Analysis) => ({
    decisions: latestByNode(ruleDecisions, analysis.id),
    evidence: latestByNode(evidenceReviews, analysis.id),
  });

  const scrollTo = (id: string) =>
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  const goToMethod = (analysis: Analysis) => {
    setSearchParams({ [FRAMEWORK_PARAM]: analysis.framework }, { replace: true });
    scrollTo(`detalhamento-${analysis.framework}`);
  };

  const current = decisions.at(-1);
  const sections = [
    { id: "resumo", label: "Resumo" },
    ...analyses.map((a) => ({
      id: `detalhamento-${a.framework}`,
      label: `Detalhamento · ${FRAMEWORKS[a.framework].label}`,
      analysis: a,
    })),
    { id: "decisao", label: "Decisão do analista" },
    { id: "trilha", label: "Trilha de decisão" },
  ];

  return (
    <div className="flex flex-1 flex-col print:block">
      <ProjectHeader
        project={project}
        meta={[
          `Empresa: ${project.company ?? "não informada"}`,
          `Enviado em ${formatDate(project.createdAt)}`,
          pluralize(project.documents.length, "documento", "documentos"),
          pluralize(analyses.length, "método analisado", "métodos analisados"),
          current
            ? `Decisão vigente: ${DECISION_OUTCOME_LABELS[current.outcome]} (${formatDate(current.decidedAt)})`
            : "Sem decisão registrada",
        ]}
        progress={`${decidedCriteriaCount(focused, ruleDecisions)} de ${focused.criteria.length} critérios decididos pelo analista · ${FRAMEWORKS[focused.framework].label}`}
        action={
          <>
            <Link to={paths.analysis(project.id, undefined, focused.framework)} className="btn-secondary">
              Voltar para o grafo
            </Link>
            <button type="button" className="btn-primary" onClick={() => print()}>
              <Printer className="size-5" aria-hidden />
              Exportar PDF
            </button>
          </>
        }
      />

      <div className="mx-auto flex w-full max-w-[1440px] flex-1 items-start gap-6 p-4 sm:px-10 sm:py-6 print:block print:p-0">
        <nav
          aria-label="Seções do documento"
          className="card sticky top-6 hidden w-64 shrink-0 flex-col gap-1 p-3 lg:flex print:hidden"
        >
          <p className="caps-label px-2 pb-1 text-fg-muted">Neste documento</p>
          {sections.map((section) => {
            const active = "analysis" in section && section.analysis?.id === focused.id;
            return (
              <button
                key={section.id}
                type="button"
                aria-current={active ? "true" : undefined}
                onClick={() =>
                  "analysis" in section && section.analysis
                    ? goToMethod(section.analysis)
                    : scrollTo(section.id)
                }
                className={`rounded-lg px-2 py-1.5 text-left text-sm leading-5 transition-colors hover:bg-surface-sunken ${
                  active ? "bg-accent-soft font-semibold text-accent" : "text-fg-secondary"
                }`}
              >
                {section.label}
              </button>
            );
          })}
        </nav>

        <article
          ref={documentRef}
          className="flex min-w-0 flex-1 flex-col gap-12 rounded-2xl bg-surface px-6 py-8 shadow-card sm:px-14 sm:py-12 print:rounded-none print:px-0 print:py-0 print:shadow-none"
        >
          <ReportHeader project={project} analyses={analyses} />
          <ReportSection title="Resumo" id="resumo">
            {analyses.map((analysis) => (
              <ReportSummary key={analysis.id} analysis={analysis} reviews={reviewsOf(analysis)} />
            ))}
          </ReportSection>
          {analyses.map((analysis) => (
            <ReportDetails
              key={analysis.id}
              project={project}
              analysis={analysis}
              markers={reviewMarkers(analysis, contestations)}
              reviews={reviewsOf(analysis)}
            />
          ))}
          {/* The form is not printed: the trail below carries the current decision */}
          <ReportSection title="Decisão do analista" id="decisao" className="print:hidden">
            <DecisionForm
              analyses={analyses}
              ruleDecisions={ruleDecisions}
              hasPrevious={decisions.length > 0}
            />
          </ReportSection>
          <ReportSection title="Trilha de decisão" id="trilha">
            <DecisionTrail
              decisions={decisions}
              contestations={contestations}
              ruleDecisions={ruleDecisions}
              evidenceReviews={evidenceReviews}
              analyses={analyses}
            />
          </ReportSection>
        </article>
      </div>
    </div>
  );
};
