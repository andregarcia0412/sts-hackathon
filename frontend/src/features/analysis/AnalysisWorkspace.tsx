import { ReactFlowProvider, useReactFlow } from "@xyflow/react";
import { ArrowRight, Crosshair, ListCollapse, ListTree } from "lucide-react";
import { Group, Panel, Separator } from "react-resizable-panels";
import { Link, useNavigate } from "react-router-dom";
import { FRAMEWORKS } from "@/domain/frameworks";
import { SUGGESTED_CATEGORY_LABELS } from "@/domain/labels";
import type { Analysis, Project } from "@/domain/types";
import { AnalysisBreadcrumb } from "@/features/analysis/AnalysisBreadcrumb";
import { NodeDetail } from "@/features/analysis/detail/NodeDetail";
import { AnalysisGraph } from "@/features/analysis/graph/AnalysisGraph";
import type { AnalysisFlowNode } from "@/features/analysis/graph/graphTypes";
import { useFrameGraph } from "@/features/analysis/graph/useFrameGraph";
import { AnalysisTree } from "@/features/analysis/tree/AnalysisTree";
import { useAnalysisExplorer } from "@/features/analysis/useAnalysisExplorer";
import { useRegisterAssistantContext } from "@/features/assistant/assistantState";
import { useMediaQuery } from "@/lib/useMediaQuery";
import { useContestations } from "@/services/queries";
import { paths } from "@/routes/paths";

interface AnalysisWorkspaceProps {
  project: Project;
  /** Analysis (method) on screen */
  analysis: Analysis;
  /** Every analysis of the project, one per method */
  analyses: Analysis[];
}

const separatorClass =
  "bg-border transition-colors hover:bg-accent data-[separator=active]:bg-accent";

/* The provider wraps the toolbar and the tree too, so they can move the graph camera */
export const AnalysisWorkspace = (props: AnalysisWorkspaceProps) => (
  <ReactFlowProvider>
    <WorkspaceContent {...props} />
  </ReactFlowProvider>
);

const WorkspaceContent = ({ project, analysis, analyses }: AnalysisWorkspaceProps) => {
  const navigate = useNavigate();
  const explorer = useAnalysisExplorer(analysis);
  useRegisterAssistantContext({
    screen: "analysis",
    analysis,
    selectedNodeId: explorer.selectedId,
  });
  const frameGraph = useFrameGraph();
  const { getNodes } = useReactFlow<AnalysisFlowNode>();
  // Desktop first: side by side; on small screens the graph goes below
  const isWide = useMediaQuery("(min-width: 768px)");
  const contestations = (useContestations(project.id).data ?? []).filter(
    (c) => c.analysisId === analysis.id,
  );
  const contestedIds = new Set(contestations.map((c) => c.nodeId));

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* Top bar: breadcrumb of the selection + actions */}
      <div className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-2 border-b border-border bg-surface px-4 py-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs text-fg-muted">
            {project.name}
            {analysis.suggestedCategory && (
              <> · Classificação sugerida: {SUGGESTED_CATEGORY_LABELS[analysis.suggestedCategory]}</>
            )}
          </p>
          <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
            {analyses.length > 1 && (
              <nav
                aria-label="Método de análise"
                className="flex shrink-0 rounded-md border border-border bg-surface-muted p-0.5"
              >
                {analyses.map((a) => (
                  <button
                    key={a.id}
                    type="button"
                    aria-pressed={a.id === analysis.id}
                    title={FRAMEWORKS[a.framework].description}
                    onClick={() =>
                      a.id !== analysis.id &&
                      navigate(paths.analysis(project.id, undefined, a.framework))
                    }
                    className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                      a.id === analysis.id
                        ? "bg-surface text-fg shadow-sm"
                        : "text-fg-muted hover:text-fg"
                    }`}
                  >
                    {FRAMEWORKS[a.framework].label}
                  </button>
                ))}
              </nav>
            )}
            <AnalysisBreadcrumb explorer={explorer} framework={analysis.framework} />
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1">
          <button type="button" className="btn-ghost" onClick={explorer.collapseAll}>
            <ListCollapse className="size-4" aria-hidden />
            Ver todos os critérios
          </button>
          <button type="button" className="btn-ghost" onClick={explorer.expandAll}>
            <ListTree className="size-4" aria-hidden />
            Expandir tudo
          </button>
          <button
            type="button"
            className="btn-ghost"
            onClick={() =>
              frameGraph(
                getNodes().filter((n) => !explorer.selectedId || n.id === explorer.selectedId),
                explorer.selectedId ? 0.25 : undefined,
              )
            }
            title="Centraliza o item selecionado, ou enquadra o grafo inteiro"
          >
            <Crosshair className="size-4" aria-hidden />
            Centralizar
          </button>
          <Link to={paths.decision(project.id, analysis.framework)} className="btn-primary ml-2">
            Ir para a decisão
            <ArrowRight className="size-4" aria-hidden />
          </Link>
        </div>
      </div>

      <Group
        key={isWide ? "wide" : "narrow"}
        orientation={isWide ? "horizontal" : "vertical"}
        className="min-h-0 flex-1"
      >
        <Panel
          defaultSize={isWide ? "30%" : "50%"}
          minSize={isWide ? "260px" : "160px"}
          maxSize={isWide ? "60%" : "80%"}
        >
          <Group orientation="vertical" className="h-full bg-surface">
            <Panel defaultSize="45%" minSize="120px" className="overflow-y-auto">
              <AnalysisTree explorer={explorer} contestedIds={contestedIds} />
            </Panel>
            <Separator className={`h-px ${separatorClass}`} />
            <Panel minSize="120px" className="overflow-y-auto">
              <NodeDetail explorer={explorer} contestations={contestations} />
            </Panel>
          </Group>
        </Panel>
        <Separator className={`${isWide ? "w-px" : "h-px"} ${separatorClass}`} />
        <Panel minSize={isWide ? "30%" : "20%"}>
          <AnalysisGraph explorer={explorer} contestedIds={contestedIds} />
        </Panel>
      </Group>
    </div>
  );
};
