import { ReactFlowProvider } from "@xyflow/react";
import { Link, useNavigate } from "react-router-dom";
import { ProjectHeader } from "@/components/layout/ProjectHeader";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { reviewMarkers } from "@/domain/contestations";
import { FRAMEWORKS } from "@/domain/frameworks";
import { SUGGESTED_CATEGORY_LABELS } from "@/domain/labels";
import { decidedCriteriaCount } from "@/domain/reviews";
import type { Analysis, Framework, Project } from "@/domain/types";
import { DetailPanel } from "@/features/analysis/detail/DetailPanel";
import { AnalysisGraph } from "@/features/analysis/graph/AnalysisGraph";
import { useAnalysisExplorer } from "@/features/analysis/useAnalysisExplorer";
import type { GraphView } from "@/features/analysis/useAnalysisExplorer";
import { useRegisterAssistantContext } from "@/features/assistant/assistantState";
import { formatDate, pluralize } from "@/lib/format";
import { paths } from "@/routes/paths";
import {
  useContestations,
  useEvidenceReviews,
  useRuleDecisions,
} from "@/services/queries";

interface AnalysisWorkspaceProps {
  project: Project;
  /** Analysis (method) on screen */
  analysis: Analysis;
  /** Every analysis of the project, one per method */
  analyses: Analysis[];
}

const VIEW_OPTIONS: { value: GraphView; label: string; title: string }[] = [
  { value: "criterion", label: "Critério", title: "Um critério com todas as regras e evidências" },
  { value: "overview", label: "Mapa geral", title: "Todos os critérios; clique para expandir" },
];

/* The provider wraps the panel too, so it can move the graph camera */
export const AnalysisWorkspace = (props: AnalysisWorkspaceProps) => (
  <ReactFlowProvider>
    <WorkspaceContent {...props} />
  </ReactFlowProvider>
);

/** Method the back-end does not produce yet: the front shows a fictitious example (mocks/illustrativeMcti.ts) */
const ILLUSTRATIVE_NOTE = "Exemplo ilustrativo: o back-end ainda não gera este método";

const WorkspaceContent = ({ project, analysis, analyses }: AnalysisWorkspaceProps) => {
  const navigate = useNavigate();
  const explorer = useAnalysisExplorer(analysis);
  useRegisterAssistantContext({
    screen: "analysis",
    analysis,
    selectedNodeId: explorer.selectedId,
  });
  const contestations = (useContestations(project.id).data ?? []).filter(
    (c) => c.analysisId === analysis.id,
  );
  const ruleDecisions = useRuleDecisions(project.id).data ?? [];
  const evidenceReviews = useEvidenceReviews(project.id).data ?? [];
  const markers = reviewMarkers(analysis, contestations);

  const rules = analysis.criteria.flatMap((c) => c.rules);
  const evidenceCount = rules.reduce((sum, r) => sum + r.evidences.length, 0);
  const decided = decidedCriteriaCount(analysis, ruleDecisions);

  const meta = [
    `Empresa: ${project.company ?? "não informada"}`,
    `Enviado em ${formatDate(project.createdAt)}`,
    pluralize(project.documents.length, "documento", "documentos"),
    `Método: ${FRAMEWORKS[analysis.framework].name}`,
    ...(analysis.illustrative ? [ILLUSTRATIVE_NOTE] : []),
    ...(analysis.suggestedCategory
      ? [`Classificação sugerida: ${SUGGESTED_CATEGORY_LABELS[analysis.suggestedCategory]}`]
      : []),
    pluralize(rules.length, "regra", "regras"),
    `${pluralize(evidenceCount, "evidência localizada", "evidências localizadas")}`,
  ];

  const toolbar = (
    <>
      {analyses.length > 1 && (
        <SegmentedControl<Framework>
          label="Método de análise"
          value={analysis.framework}
          options={analyses.map((a) => ({
            value: a.framework,
            label: FRAMEWORKS[a.framework].label,
            title: a.illustrative ? ILLUSTRATIVE_NOTE : FRAMEWORKS[a.framework].description,
          }))}
          onChange={(framework) => navigate(paths.analysis(project.id, undefined, framework))}
        />
      )}
      <SegmentedControl<GraphView>
        label="Visualização da árvore"
        value={explorer.view}
        options={VIEW_OPTIONS}
        onChange={explorer.setView}
      />
    </>
  );

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <ProjectHeader
        project={project}
        meta={meta}
        progress={`${decided} de ${analysis.criteria.length} critérios decididos pelo analista`}
        action={
          <Link to={paths.decision(project.id, analysis.framework, explorer.selectedId ?? undefined)} className="btn-primary">
            Gerar documento de decisão
          </Link>
        }
      />
      {/* pb-24 on phones: room for the assistant button */}
      <div className="flex min-h-[600px] flex-1 flex-col gap-4 p-4 pb-24 lg:flex-row lg:pb-4">
        <DetailPanel
          className="shrink-0 lg:w-[488px]"
          explorer={explorer}
          projectId={project.id}
          analysis={analysis}
          contestations={contestations}
          ruleDecisions={ruleDecisions}
          evidenceReviews={evidenceReviews}
        />
        <section
          aria-label="Árvore de evidências"
          className="relative h-[80vh] min-w-0 shrink-0 overflow-hidden rounded-xl bg-white/50 lg:h-auto lg:flex-1 lg:shrink"
        >
          <AnalysisGraph explorer={explorer} reviewMarkers={markers} toolbar={toolbar} />
        </section>
      </div>
    </div>
  );
};
