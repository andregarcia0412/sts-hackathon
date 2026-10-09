import { useEffect, useEffectEvent, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useReactToPrint } from "react-to-print";
import { ProjectHeader } from "@/components/layout/ProjectHeader";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { reviewMarkers } from "@/domain/contestations";
import { FRAMEWORKS } from "@/domain/frameworks";
import { DECISION_OUTCOME_LABELS } from "@/domain/labels";
import { pendenciesOf } from "@/domain/report";
import { latestByNode } from "@/domain/reviews";
import type {
  Analysis,
  Contestation,
  Decision,
  EvidenceReview,
  Framework,
  Project,
  RuleDecision,
} from "@/domain/types";
import { useCurrentUser } from "@/features/auth/authState";
import { useRegisterAssistantContext } from "@/features/assistant/assistantState";
import {
  ReportDetails,
  ReportHeader,
  ReportPendencies,
  ReportSection,
  ReportSummary,
} from "@/features/decision/AnalysisReport";
import { DecisionForm } from "@/features/decision/DecisionForm";
import { DecisionTrail } from "@/features/decision/DecisionTrail";
import { openStateOf, toggledNode } from "@/features/decision/reportState";
import { formatDate, pluralize } from "@/lib/format";
import { FRAMEWORK_PARAM, SELECTED_NODE_PARAM, paths, reportAnchorId } from "@/routes/paths";
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

/** Sections of the document, in order (index + scroll spy) */
const SECTIONS = [
  { id: "resumo", label: "Resumo" },
  { id: "pendencias", label: "Pendências" },
  { id: "detalhamento", label: "Detalhamento" },
  { id: "decisao", label: "Decisão do analista" },
  { id: "trilha", label: "Trilha de decisão" },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

const DecisionDocument = ({
  project,
  analyses,
  decisions,
  contestations,
  ruleDecisions,
  evidenceReviews,
}: DecisionDocumentProps) => {
  const documentRef = useRef<HTMLElement>(null);
  const user = useCurrentUser();
  const [searchParams, setSearchParams] = useSearchParams();
  // One method at a time (?metodo=, default: the first); the decision covers all of them
  const focused =
    analyses.find((a) => a.framework === searchParams.get(FRAMEWORK_PARAM)) ?? analyses[0];
  const framework = FRAMEWORKS[focused.framework];
  const nodeParam = searchParams.get(SELECTED_NODE_PARAM);
  const open = openStateOf(focused, nodeParam);
  const print = useReactToPrint({
    contentRef: documentRef,
    documentTitle: `Decisao_${project.name}_${focused.id}`.replace(/[^\w-]+/g, "_"),
  });
  useRegisterAssistantContext({ screen: "decision", analysis: focused, selectedNodeId: null });

  const reviews = {
    decisions: latestByNode(ruleDecisions, focused.id),
    evidence: latestByNode(evidenceReviews, focused.id),
  };
  const pendencies = pendenciesOf(focused, project, contestations);
  const current = decisions.at(-1);
  const evidenceCount = focused.criteria.reduce(
    (sum, c) => sum + c.rules.reduce((n, r) => n + r.evidences.length, 0),
    0,
  );

  /** Header clicks change the open node without moving the page */
  const toggledHere = useRef<string | null>(null);
  const setNode = (nodeId: string, { scroll }: { scroll: boolean }) => {
    toggledHere.current = scroll ? null : nodeId;
    setSearchParams(
      (params) => {
        params.set(SELECTED_NODE_PARAM, nodeId);
        return params;
      },
      { replace: true },
    );
  };
  const openNode = (nodeId: string) => setNode(nodeId, { scroll: true });
  const toggle = (nodeId: string, parentId?: string) =>
    setNode(toggledNode(open, nodeId, parentId), { scroll: false });

  const setMethod = (value: Framework) =>
    setSearchParams({ [FRAMEWORK_PARAM]: value }, { replace: true });

  // A node chosen elsewhere (summary, pendency, assistant, link from the tree): bring it into view
  const reveal = useEffectEvent((nodeId: string) => {
    if (toggledHere.current === nodeId) return;
    const target = document.getElementById(reportAnchorId(focused, nodeId));
    target?.scrollIntoView({ behavior: "smooth", block: "start" });
    target?.animate(
      [{ backgroundColor: "var(--color-accent-soft)" }, { backgroundColor: "transparent" }],
      { duration: 1600, easing: "ease-out" },
    );
  });
  useEffect(() => {
    if (nodeParam) reveal(nodeParam);
  }, [nodeParam]);

  const active = useActiveSection();
  const scrollTo = (id: string) =>
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  const treeLink = paths.analysis(project.id, undefined, focused.framework);
  const methodControl =
    analyses.length > 1 ? (
      <SegmentedControl
        label="Método do documento"
        value={focused.framework}
        onChange={setMethod}
        options={analyses.map((a) => ({ value: a.framework, label: FRAMEWORKS[a.framework].label }))}
      />
    ) : null;

  return (
    // Large screens: header and index stay put, the document scrolls in its own box (design)
    <div className="flex flex-1 flex-col lg:min-h-0 lg:overflow-hidden print:block print:overflow-visible">
      <ProjectHeader
        project={project}
        showStatus={false}
        meta={[
          `Equipe: ${project.company ?? "não informada"}`,
          project.cutoffDate ? `Corte: ${formatDate(project.cutoffDate)}` : `Enviado em ${formatDate(project.createdAt)}`,
          pluralize(project.documents.length, "documento", "documentos"),
          `${pluralize(evidenceCount, "evidência localizada", "evidências localizadas")} (${framework.label})`,
          current
            ? `Decisão vigente: ${DECISION_OUTCOME_LABELS[current.outcome]} (${formatDate(current.decidedAt)})`
            : "Sem decisão registrada",
        ]}
        action={
          <a href="#decisao" className="btn-primary" onClick={(e) => (e.preventDefault(), scrollTo("decisao"))}>
            Registrar decisão
          </a>
        }
      />

      <div className="flex w-full flex-1 items-start gap-4 p-4 lg:min-h-0 print:block print:p-0">
        <aside className="hidden w-60 shrink-0 flex-col gap-4 rounded-3xl bg-surface p-4 shadow-card lg:flex print:hidden">
          {methodControl}
          <nav aria-label="Seções do documento" className="flex flex-col gap-1">
            <p className="px-3 pb-1 text-xs leading-4 font-medium text-fg-muted">Neste documento</p>
            {SECTIONS.map((section) => (
              <button
                key={section.id}
                type="button"
                aria-current={active === section.id ? "true" : undefined}
                onClick={() => scrollTo(section.id)}
                className={`flex items-center justify-between gap-2 rounded-2xl px-3 py-2.5 text-left text-base leading-6 transition-colors hover:bg-surface-sunken ${
                  active === section.id ? "bg-accent-soft font-semibold text-accent" : "text-fg"
                }`}
              >
                {section.id === "detalhamento" ? `Detalhamento · ${framework.label}` : section.label}
                {section.id === "pendencias" && pendencies.length > 0 && (
                  <span className="text-xs font-semibold text-state-attention-strong tabular-nums">
                    {pendencies.length}
                    <span className="sr-only"> pendências</span>
                  </span>
                )}
              </button>
            ))}
          </nav>
          <hr className="border-border-strong" />
          <div className="flex flex-col gap-2">
            <button type="button" className="btn-primary w-full" onClick={() => print()}>
              Baixar documento
            </button>
            <Link to={treeLink} className="btn-secondary w-full border-transparent">
              Voltar à árvore
            </Link>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col gap-4 lg:min-h-0 lg:self-stretch print:block">
          {/* Phones and tablets: the side panel's controls */}
          <div className="flex flex-wrap items-center gap-2 lg:hidden print:hidden">
            {methodControl}
            <button type="button" className="btn-primary ml-auto" onClick={() => print()}>
              Baixar documento
            </button>
            <Link to={treeLink} className="btn-secondary">
              Voltar à árvore
            </Link>
          </div>

          <article
            ref={documentRef}
            className="scroll-visible flex flex-col gap-12 rounded-3xl bg-surface px-5 py-8 shadow-card sm:px-12 sm:py-12 lg:min-h-0 lg:flex-1 lg:overflow-y-auto print:overflow-visible print:rounded-none print:px-0 print:py-0 print:shadow-none"
          >
            <ReportHeader
              project={project}
              analysis={focused}
              analyst={
                current
                  ? {
                      name: current.analystName,
                      note: `${DECISION_OUTCOME_LABELS[current.outcome]} · ${formatDate(current.decidedAt)}`,
                    }
                  : { name: user.name, note: "Sem decisão registrada" }
              }
            />
            <ReportSection title="Resumo" id="resumo">
              <ReportSummary analysis={focused} reviews={reviews} pendencies={pendencies} onOpen={openNode} />
            </ReportSection>
            <ReportSection title="Pendências antes de decidir" id="pendencias">
              <ReportPendencies pendencies={pendencies} onOpen={openNode} />
            </ReportSection>
            <ReportSection title={`Detalhamento · ${framework.label}`} id="detalhamento">
              <ReportDetails
                project={project}
                analysis={focused}
                markers={reviewMarkers(focused, contestations)}
                reviews={reviews}
                open={open}
                onToggle={toggle}
              />
            </ReportSection>
            {/* The form is not printed: the trail below carries the current decision */}
            <section id="decisao" className="scroll-mt-6">
              <DecisionForm analyses={analyses} focused={focused} ruleDecisions={ruleDecisions} />
            </section>
            <ReportSection title="Trilha de decisão" id="trilha">
              <DecisionTrail
                decisions={decisions}
                contestations={contestations}
                ruleDecisions={ruleDecisions}
                evidenceReviews={evidenceReviews}
                analyses={analyses}
                filesRead={project.documents.length}
              />
            </ReportSection>
          </article>
        </div>
      </div>
    </div>
  );
};

/** Section the analyst is reading (highlighted in the index) */
const useActiveSection = (): SectionId => {
  const [active, setActive] = useState<SectionId>("resumo");
  useEffect(() => {
    const visible = new Set<string>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) visible.add(entry.target.id);
          else visible.delete(entry.target.id);
        }
        const first = SECTIONS.find((s) => visible.has(s.id));
        if (first) setActive(first.id);
      },
      { rootMargin: "-15% 0px -55% 0px" },
    );
    for (const section of SECTIONS) {
      const element = document.getElementById(section.id);
      if (element) observer.observe(element);
    }
    return () => observer.disconnect();
  }, []);
  return active;
};
