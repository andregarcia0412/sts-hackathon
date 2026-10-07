import { ArrowRight, ListCollapse, ListTree } from "lucide-react";
import { Group, Panel, Separator } from "react-resizable-panels";
import { Link } from "react-router-dom";
import { SUGGESTED_CATEGORY_LABELS } from "@/domain/labels";
import type { Analysis, Project } from "@/domain/types";
import { AnalysisBreadcrumb } from "@/features/analysis/AnalysisBreadcrumb";
import { NodeDetail } from "@/features/analysis/detail/NodeDetail";
import { AnalysisTree } from "@/features/analysis/tree/AnalysisTree";
import { useAnalysisExplorer } from "@/features/analysis/useAnalysisExplorer";
import { paths } from "@/routes/paths";

interface AnalysisWorkspaceProps {
  project: Project;
  analysis: Analysis;
}

const separatorClass =
  "bg-border transition-colors hover:bg-accent data-[separator=active]:bg-accent";

export const AnalysisWorkspace = ({ project, analysis }: AnalysisWorkspaceProps) => {
  const explorer = useAnalysisExplorer(analysis);

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
          <AnalysisBreadcrumb explorer={explorer} framework={analysis.framework} />
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button type="button" className="btn-ghost" onClick={explorer.collapseAll}>
            <ListCollapse className="size-4" aria-hidden />
            Ver todos os critérios
          </button>
          <button type="button" className="btn-ghost" onClick={explorer.expandAll}>
            <ListTree className="size-4" aria-hidden />
            Expandir tudo
          </button>
          <Link to={paths.decision(project.id)} className="btn-primary ml-2">
            Ir para a decisão
            <ArrowRight className="size-4" aria-hidden />
          </Link>
        </div>
      </div>

      <Group orientation="horizontal" className="min-h-0 flex-1">
        <Panel defaultSize="30%" minSize="260px" maxSize="60%">
          <Group orientation="vertical" className="h-full bg-surface">
            <Panel defaultSize="45%" minSize="120px" className="overflow-y-auto">
              <AnalysisTree explorer={explorer} />
            </Panel>
            <Separator className={`h-px ${separatorClass}`} />
            <Panel minSize="120px" className="overflow-y-auto">
              <NodeDetail explorer={explorer} />
            </Panel>
          </Group>
        </Panel>
        <Separator className={`w-px ${separatorClass}`} />
        <Panel minSize="30%">
          <div className="flex h-full items-center justify-center text-sm text-fg-muted">
            Grafo (próximo passo)
          </div>
        </Panel>
      </Group>
    </div>
  );
};
